import os
import shutil
import subprocess
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory
from .helpers import get_data, save_data, transliterate

samples_bp = Blueprint('samples', __name__, template_folder='../templates')

def get_sample_folder_path(sample):
    """Вычисляет полный путь к папке образца."""
    # Используем сохраненное имя папки или генерируем новое на основе имени
    folder_name = sample.get('folder_name')
    if not folder_name:
        safe_name = transliterate(sample.get('name', 'unnamed'))
        folder_name = f"{sample['id']}_{safe_name}"
    
    return os.path.join(current_app.config['UPLOAD_FOLDER'], 'samples', folder_name)

def rename_sample_folders(data):
    """Переименовывает папки всех образцов в соответствии с их порядковым номером."""
    samples = data.get('samples', [])
    for idx, sample in enumerate(samples):
        old_folder_name = sample.get('folder_name', '')
        safe_name = transliterate(sample.get('name', 'unnamed'))
        new_folder_name = f"{idx + 1}_{safe_name}"
        
        if old_folder_name != new_folder_name:
            old_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'samples', old_folder_name)
            new_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'samples', new_folder_name)
            
            if os.path.exists(old_path) and old_path != new_path:
                try:
                    os.rename(old_path, new_path)
                    sample['folder_name'] = new_folder_name
                except Exception as e:
                    flash(f'Не удалось переименовать папку образца {sample["name"]}: {e}', 'warning')
            elif os.path.exists(new_path):
                sample['folder_name'] = new_folder_name
            else:
                # Папка не существует, просто обновляем имя
                sample['folder_name'] = new_folder_name

@samples_bp.route('/')
def list_samples():
    data = get_data(current_app.config['DATA_FILE'])
    storages_map = {s['id']: s['name'] for s in data.get('storages', [])}
    
    samples_list = data.get('samples', [])
    for sample in samples_list:
        sample['storage_name'] = storages_map.get(sample.get('storage_id'), 'Нет хранилища')
        if 'files' not in sample:
            sample['files'] = []
        if 'note' not in sample:
            sample['note'] = ''
        if 'status' not in sample:
            sample['status'] = ''
            
    return render_template('sample_list.html', samples=samples_list, storages=data.get('storages', []))

@samples_bp.route('/add', methods=['GET', 'POST'])
def add_sample():
    data = get_data(current_app.config['DATA_FILE'])
    if request.method == 'POST':
        name = request.form.get('name')
        desc = request.form.get('description')
        note = request.form.get('note')
        status = request.form.get('status')
        storage_id = request.form.get('storage_id')
        if storage_id: storage_id = int(storage_id)
        
        new_id = max([s['id'] for s in data.get('samples', [])], default=0) + 1
        
        # Добавляем образец в конец списка
        safe_name = transliterate(name)
        # Номер папки будет равен позиции в списке + 1
        folder_name = f"{len(data['samples']) + 1}_{safe_name}"
        
        # Обработка файлов
        files = []
        uploaded_files = request.files.getlist('files')
        if uploaded_files:
            # Создаём папку только если есть файлы для загрузки
            sample_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'samples', folder_name)
            os.makedirs(sample_folder, exist_ok=True)
            for file in uploaded_files:
                if file and file.filename != '':
                    file.save(os.path.join(sample_folder, file.filename))
                    files.append(file.filename)

        data['samples'].append({
            'id': new_id, 
            'name': name, 
            'description': desc, 
            'note': note,
            'status': status,
            'storage_id': storage_id, 
            'files': files,
            'folder_name': folder_name
        })
        save_data(current_app.config['DATA_FILE'], data)
        flash('Образец добавлен!', 'success')
        return redirect(url_for('samples.list_samples'))
    
    return render_template('sample_form.html', sample=None, storages=data.get('storages', []))

@samples_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_sample(id):
    data = get_data(current_app.config['DATA_FILE'])
    sample = next((s for s in data['samples'] if s['id'] == id), None)
    if not sample:
        flash('Образец не найден', 'error')
        return redirect(url_for('samples.list_samples'))

    if request.method == 'POST':
        old_name = sample['name']
        sample['name'] = request.form.get('name')
        sample['description'] = request.form.get('description')
        sample['note'] = request.form.get('note')
        sample['status'] = request.form.get('status')
        s_id = request.form.get('storage_id')
        sample['storage_id'] = int(s_id) if s_id else None
        
        # Переименовываем папки всех образцов в соответствии с их порядком (на случай изменения имени)
        rename_sample_folders(data)

        # Загрузка новых файлов
        uploaded_files = request.files.getlist('files')
        sample_folder = get_sample_folder_path(sample)
        
        # Убедимся, что папка существует
        if not os.path.exists(sample_folder):
            os.makedirs(sample_folder)

        for file in uploaded_files:
            if file and file.filename != '':
                file.save(os.path.join(sample_folder, file.filename))
                if file.filename not in sample['files']:
                    sample['files'].append(file.filename)

        save_data(current_app.config['DATA_FILE'], data)
        flash('Образец обновлен!', 'success')
        return redirect(url_for('samples.list_samples'))

    return render_template('sample_form.html', sample=sample, storages=data.get('storages', []))

@samples_bp.route('/delete/<int:id>')
def delete_sample(id):
    data = get_data(current_app.config['DATA_FILE'])
    sample = next((s for s in data['samples'] if s['id'] == id), None)
    
    if sample:
        # Получаем путь к папке и удаляем её полностью
        folder_path = get_sample_folder_path(sample)
        if os.path.exists(folder_path):
            try:
                shutil.rmtree(folder_path)
            except Exception as e:
                flash(f'Не удалось удалить папку с файлами: {e}', 'error')
        
        data['samples'] = [s for s in data['samples'] if s['id'] != id]
        
        # Переименовываем папки в соответствии с новым порядком после удаления
        rename_sample_folders(data)
        
        save_data(current_app.config['DATA_FILE'], data)
        flash('Образец и его файлы удалены', 'info')
    
    return redirect(url_for('samples.list_samples'))

@samples_bp.route('/delete_file/<int:sample_id>/<filename>')
def delete_file(sample_id, filename):
    data = get_data(current_app.config['DATA_FILE'])
    sample = next((s for s in data['samples'] if s['id'] == sample_id), None)
    
    if sample and filename in sample.get('files', []):
        sample_folder = get_sample_folder_path(sample)
        file_path = os.path.join(sample_folder, filename)
        
        if os.path.exists(file_path):
            os.remove(file_path)
        
        sample['files'].remove(filename)
        
        # Если файлов больше нет, удаляем папку
        if not sample['files']:
            if os.path.exists(sample_folder):
                try:
                    os.rmdir(sample_folder)
                except Exception as e:
                    flash(f'Не удалось удалить пустую папку: {e}', 'warning')
        
        save_data(current_app.config['DATA_FILE'], data)
        flash(f'Файл {filename} удален', 'info')
    
    return redirect(url_for('samples.edit_sample', id=sample_id))

@samples_bp.route('/file/<int:sample_id>/<filename>')
def download_file(sample_id, filename):
    data = get_data(current_app.config['DATA_FILE'])
    sample = next((s for s in data['samples'] if s['id'] == sample_id), None)
    
    if sample:
        sample_folder = get_sample_folder_path(sample)
        if os.path.exists(sample_folder) and filename in os.listdir(sample_folder):
            return send_from_directory(sample_folder, filename)
    
    return "Файл не найден", 404

@samples_bp.route('/folder/<int:sample_id>')
def open_folder(sample_id):
    """Открывает папку образца в проводнике Windows."""
    data = get_data(current_app.config['DATA_FILE'])
    sample = next((s for s in data['samples'] if s['id'] == sample_id), None)
    
    if sample:
        folder_path = get_sample_folder_path(sample)
        
        if os.path.exists(folder_path):
            try:
                # Команда для открытия папки в Windows
                subprocess.Popen(['explorer', folder_path])
                flash('Папка открыта в проводнике', 'success')
            except Exception as e:
                flash(f'Ошибка при открытии папки: {e}', 'error')
        else:
            flash('Папка не найдена на диске', 'error')
    else:
        flash('Образец не найден', 'error')
        
    return redirect(url_for('samples.list_samples'))

@samples_bp.route('/move/<int:id>/<direction>')
def move_sample(id, direction):
    """Переместить образец вверх или вниз."""
    data = get_data(current_app.config['DATA_FILE'])
    samples = data.get('samples', [])
    
    # Находим индекс текущего образца
    current_idx = None
    for i, s in enumerate(samples):
        if s['id'] == id:
            current_idx = i
            break
    
    if current_idx is None:
        flash('Образец не найден', 'error')
        return redirect(url_for('samples.list_samples'))
    
    # Определяем новый индекс
    if direction == 'up' and current_idx > 0:
        new_idx = current_idx - 1
    elif direction == 'down' and current_idx < len(samples) - 1:
        new_idx = current_idx + 1
    else:
        flash('Перемещение невозможно', 'info')
        return redirect(url_for('samples.list_samples'))
    
    # Меняем местами
    samples[current_idx], samples[new_idx] = samples[new_idx], samples[current_idx]
    
    # Переименовываем папки в соответствии с новым порядком
    rename_sample_folders(data)
    
    save_data(current_app.config['DATA_FILE'], data)
    flash('Образец перемещен', 'success')
    return redirect(url_for('samples.list_samples'))