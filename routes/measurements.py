import os
import shutil
import subprocess
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory, jsonify
from .helpers import get_data, save_data, transliterate

measurements_bp = Blueprint('measurements', __name__, template_folder='../templates')

def get_measurement_folder_path(measurement):
    """Вычисляет полный путь к папке измерения."""
    folder_name = measurement.get('folder_name')
    if not folder_name:
        safe_name = transliterate(measurement.get('name', 'unnamed'))
        folder_name = f"{measurement['id']}_{safe_name}"
    
    return os.path.join(current_app.config['UPLOAD_FOLDER'], 'measurements', folder_name)

def get_unique_measurement_folder_name(safe_name, measurements_list, current_id=None):
    """Генерирует уникальное имя папки для измерения, добавляя индекс при совпадении имен.
    
    Args:
        safe_name: Транслитерированное имя измерения
        measurements_list: Список всех измерений
        current_id: ID текущего измерения (для исключения при редактировании)
    
    Returns:
        Уникальное имя папки в формате {index}_{safe_name} или {index}_{safe_name}_{dup_index}
    """
    # Считаем, сколько измерений с таким именем уже существует
    dup_count = 0
    for m in measurements_list:
        if current_id and m['id'] == current_id:
            continue
        folder_name = m.get('folder_name', '')
        if folder_name:
            # Извлекаем базовое имя из формата {index}_{name} или {index}_{name}_{dup_index}
            parts = folder_name.split('_', 1)
            if len(parts) > 1:
                base_name = parts[1]
                # Проверяем, совпадает ли базовое имя (без возможного суффикса _N)
                base_parts = base_name.rsplit('_', 1)
                if len(base_parts) == 2 and base_parts[1].isdigit():
                    check_name = base_parts[0]
                else:
                    check_name = base_name
                if check_name == safe_name:
                    dup_count += 1
    
    # Находим позицию для нового измерения
    next_index = len(measurements_list) + 1 if not current_id else max([i for i, s in enumerate(measurements_list) if s['id'] != current_id], default=-1) + 2
    
    # Если есть дубликаты, добавляем индекс
    if dup_count > 0:
        return f"{next_index}_{safe_name}_{dup_count}"
    else:
        return f"{next_index}_{safe_name}"

def rename_measurement_folders(data):
    """Переименовывает папки всех измерений в соответствии с их порядковым номером."""
    measurements = data.get('measurements', [])
    # Сначала собираем статистику по именам
    name_counts = {}
    for m in measurements:
        safe_name = transliterate(m.get('name', 'unnamed'))
        name_counts[safe_name] = name_counts.get(safe_name, 0) + 1
    
    for idx, measurement in enumerate(measurements):
        old_folder_name = measurement.get('folder_name', '')
        safe_name = transliterate(measurement.get('name', 'unnamed'))
        
        # Если такое имя не единственное, добавляем индекс дубликата
        if name_counts.get(safe_name, 0) > 1:
            # Считаем, какой по счету это измерение с таким именем
            dup_index = 0
            for i, meas in enumerate(measurements):
                if transliterate(meas.get('name', 'unnamed')) == safe_name:
                    dup_index += 1
                    if i == idx:
                        break
            new_folder_name = f"{idx + 1}_{safe_name}_{dup_index}"
        else:
            new_folder_name = f"{idx + 1}_{safe_name}"
        
        if old_folder_name != new_folder_name:
            old_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'measurements', old_folder_name)
            new_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'measurements', new_folder_name)
            
            if os.path.exists(old_path) and old_path != new_path:
                try:
                    os.rename(old_path, new_path)
                    measurement['folder_name'] = new_folder_name
                except Exception as e:
                    flash(f'Не удалось переименовать папку измерения {measurement["name"]}: {e}', 'warning')
            elif os.path.exists(new_path):
                measurement['folder_name'] = new_folder_name
            else:
                # Папка не существует, просто обновляем имя
                measurement['folder_name'] = new_folder_name

@measurements_bp.route('/')
def list_measurements():
    data = get_data(current_app.config['DATA_FILE'])
    
    measurements_list = data.get('measurements', [])
    for m in measurements_list:
        if 'files' not in m:
            m['files'] = []
        if 'note' not in m:
            m['note'] = ''
        if 'status' not in m:
            m['status'] = ''
        if 'description' not in m:
            m['description'] = ''
        if 'measurement_program' not in m:
            m['measurement_program'] = ''
            
    return render_template('measurement_list.html', measurements=measurements_list)

@measurements_bp.route('/add', methods=['GET', 'POST'])
def add_measurement():
    data = get_data(current_app.config['DATA_FILE'])
    if request.method == 'POST':
        name = request.form.get('name')
        desc = request.form.get('description')
        measurement_program = request.form.get('measurement_program')
        note = request.form.get('note')
        status = request.form.get('status')
        date = request.form.get('date')
        
        new_id = max([m['id'] for m in data.get('measurements', [])], default=0) + 1
        
        # Добавляем измерение в конец списка
        safe_name = transliterate(name)
        # Генерируем уникальное имя папки с учетом возможных дубликатов
        folder_name = get_unique_measurement_folder_name(safe_name, data['measurements'])
        measurement_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'measurements', folder_name)
        os.makedirs(measurement_folder, exist_ok=True)
        
        # Обработка файлов
        files = []
        uploaded_files = request.files.getlist('files')
        for file in uploaded_files:
            if file and file.filename != '':
                file.save(os.path.join(measurement_folder, file.filename))
                files.append(file.filename)

        data['measurements'].append({
            'id': new_id, 
            'name': name, 
            'description': desc, 
            'measurement_program': measurement_program,
            'note': note,
            'status': status, 
            'date': date,
            'files': files,
            'folder_name': folder_name
        })
        save_data(current_app.config['DATA_FILE'], data)
        flash('Измерение добавлено!', 'success')
        return redirect(url_for('measurements.list_measurements'))
    
    return render_template('measurement_form.html', measurement=None)

@measurements_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_measurement(id):
    data = get_data(current_app.config['DATA_FILE'])
    measurement = next((m for m in data['measurements'] if m['id'] == id), None)
    if not measurement:
        flash('Измерение не найдено', 'error')
        return redirect(url_for('measurements.list_measurements'))

    if request.method == 'POST':
        old_name = measurement['name']
        measurement['name'] = request.form.get('name')
        measurement['description'] = request.form.get('description')
        measurement['measurement_program'] = request.form.get('measurement_program')
        measurement['note'] = request.form.get('note')
        measurement['status'] = request.form.get('status')
        measurement['date'] = request.form.get('date')
        
        # Переименовываем папки всех измерений в соответствии с их порядком (на случай изменения имени)
        rename_measurement_folders(data)

        # Загрузка новых файлов
        uploaded_files = request.files.getlist('files')
        measurement_folder = get_measurement_folder_path(measurement)
        
        # Убедимся, что папка существует
        if not os.path.exists(measurement_folder):
            os.makedirs(measurement_folder)

        for file in uploaded_files:
            if file and file.filename != '':
                file.save(os.path.join(measurement_folder, file.filename))
                if file.filename not in measurement['files']:
                    measurement['files'].append(file.filename)

        save_data(current_app.config['DATA_FILE'], data)
        flash('Измерение обновлено!', 'success')
        return redirect(url_for('measurements.list_measurements'))

    return render_template('measurement_form.html', measurement=measurement)

@measurements_bp.route('/delete/<int:id>')
def delete_measurement(id):
    data = get_data(current_app.config['DATA_FILE'])
    measurement = next((m for m in data['measurements'] if m['id'] == id), None)
    
    if measurement:
        # Получаем путь к папке и удаляем её полностью
        folder_path = get_measurement_folder_path(measurement)
        if os.path.exists(folder_path):
            try:
                shutil.rmtree(folder_path)
            except Exception as e:
                flash(f'Не удалось удалить папку с файлами: {e}', 'error')
        
        data['measurements'] = [m for m in data['measurements'] if m['id'] != id]
        
        # Переименовываем папки в соответствии с новым порядком после удаления
        rename_measurement_folders(data)
        
        save_data(current_app.config['DATA_FILE'], data)
        flash('Измерение и его файлы удалены', 'info')
    
    return redirect(url_for('measurements.list_measurements'))

@measurements_bp.route('/delete_file/<int:measurement_id>/<filename>')
def delete_file(measurement_id, filename):
    data = get_data(current_app.config['DATA_FILE'])
    measurement = next((m for m in data['measurements'] if m['id'] == measurement_id), None)
    
    if measurement and filename in measurement.get('files', []):
        measurement_folder = get_measurement_folder_path(measurement)
        file_path = os.path.join(measurement_folder, filename)
        
        if os.path.exists(file_path):
            os.remove(file_path)
        
        measurement['files'].remove(filename)
        save_data(current_app.config['DATA_FILE'], data)
        flash(f'Файл {filename} удален', 'info')
    
    return redirect(url_for('measurements.edit_measurement', id=measurement_id))

@measurements_bp.route('/file/<int:measurement_id>/<filename>')
def download_file(measurement_id, filename):
    data = get_data(current_app.config['DATA_FILE'])
    measurement = next((m for m in data['measurements'] if m['id'] == measurement_id), None)
    
    if measurement:
        measurement_folder = get_measurement_folder_path(measurement)
        if os.path.exists(measurement_folder) and filename in os.listdir(measurement_folder):
            return send_from_directory(measurement_folder, filename)
    
    return "Файл не найден", 404

@measurements_bp.route('/folder/<int:measurement_id>')
def open_folder(measurement_id):
    """Открывает папку измерения в проводнике Windows."""
    data = get_data(current_app.config['DATA_FILE'])
    measurement = next((m for m in data['measurements'] if m['id'] == measurement_id), None)
    
    if measurement:
        folder_path = get_measurement_folder_path(measurement)
        
        if os.path.exists(folder_path):
            try:
                subprocess.Popen(['explorer', folder_path])
                flash('Папка открыта в проводнике', 'success')
            except Exception as e:
                flash(f'Ошибка при открытии папки: {e}', 'error')
        else:
            flash('Папка не найдена на диске', 'error')
    else:
        flash('Измерение не найдено', 'error')
        
    return redirect(url_for('measurements.list_measurements'))

@measurements_bp.route('/move/<int:id>/<direction>')
def move_measurement(id, direction):
    """Переместить измерение вверх или вниз."""
    data = get_data(current_app.config['DATA_FILE'])
    measurements = data.get('measurements', [])
    
    # Находим индекс текущего измерения
    current_idx = None
    for i, m in enumerate(measurements):
        if m['id'] == id:
            current_idx = i
            break
    
    if current_idx is None:
        flash('Измерение не найдено', 'error')
        return redirect(url_for('measurements.list_measurements'))
    
    # Определяем новый индекс
    if direction == 'up' and current_idx > 0:
        new_idx = current_idx - 1
    elif direction == 'down' and current_idx < len(measurements) - 1:
        new_idx = current_idx + 1
    else:
        flash('Перемещение невозможно', 'info')
        return redirect(url_for('measurements.list_measurements'))
    
    # Меняем местами
    measurements[current_idx], measurements[new_idx] = measurements[new_idx], measurements[current_idx]
    
    # Переименовываем папки в соответствии с новым порядком
    rename_measurement_folders(data)
    
    save_data(current_app.config['DATA_FILE'], data)
    flash('Измерение перемещено', 'success')
    return redirect(url_for('measurements.list_measurements'))

@measurements_bp.route('/<int:id>/status', methods=['POST'])
def update_status(id):
    """AJAX endpoint для обновления статуса измерения."""
    data = get_data(current_app.config['DATA_FILE'])
    measurement = next((m for m in data['measurements'] if m['id'] == id), None)
    
    if measurement:
        req_data = request.get_json()
        measurement['status'] = req_data.get('status', '')
        save_data(current_app.config['DATA_FILE'], data)
        return jsonify({'success': True})
    
    return jsonify({'success': False}), 404
