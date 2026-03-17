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
        
        # Создаем папку для измерения
        safe_name = transliterate(name)
        folder_name = f"{new_id}_{safe_name}"
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
        
        # Если название изменилось, переименовываем папку
        if measurement['name'] != old_name:
            safe_name = transliterate(measurement['name'])
            new_folder_name = f"{id}_{safe_name}"
            old_path = get_measurement_folder_path(measurement)
            
            # Корректируем старый путь, если folder_name еще не обновлен
            if not measurement.get('folder_name') or old_name not in measurement.get('folder_name', ''):
                 old_safe = transliterate(old_name)
                 old_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'measurements', f"{id}_{old_safe}")

            new_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'measurements', new_folder_name)
            
            if os.path.exists(old_path) and old_path != new_path:
                try:
                    os.rename(old_path, new_path)
                    measurement['folder_name'] = new_folder_name
                except Exception as e:
                    flash(f'Не удалось переименовать папку: {e}', 'warning')
            elif os.path.exists(new_path):
                measurement['folder_name'] = new_folder_name

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
