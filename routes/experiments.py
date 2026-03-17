import os
import shutil
import subprocess
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_from_directory, jsonify
from .helpers import get_data, save_data, transliterate

experiments_bp = Blueprint('experiments', __name__, template_folder='../templates')

def get_experiment_folder_path(experiment):
    """Вычисляет полный путь к папке эксперимента."""
    folder_name = experiment.get('folder_name')
    if not folder_name:
        safe_name = transliterate(experiment.get('name', 'unnamed'))
        timestamp = experiment.get('_created_at', '')
        if timestamp:
            folder_name = f"{safe_name}_{timestamp}"
        else:
            folder_name = f"{safe_name}"
    
    return os.path.join(current_app.config['UPLOAD_FOLDER'], 'experiments', folder_name)

@experiments_bp.route('/')
def list_experiments():
    data = get_data(current_app.config['DATA_FILE'])
    
    experiments_list = data.get('experiments', [])
    for exp in experiments_list:
        if 'files' not in exp:
            exp['files'] = []
        if 'description' not in exp:
            exp['description'] = ''
        if 'results' not in exp:
            exp['results'] = ''
        if 'date' not in exp:
            exp['date'] = ''
            
    return render_template('experiment_list.html', experiments=experiments_list)

@experiments_bp.route('/add', methods=['GET', 'POST'])
def add_experiment():
    data = get_data(current_app.config['DATA_FILE'])
    if request.method == 'POST':
        name = request.form.get('name')
        desc = request.form.get('description')
        results = request.form.get('results')
        status = request.form.get('status')
        date = request.form.get('date')
        
        new_id = max([exp['id'] for exp in data.get('experiments', [])], default=0) + 1
        
        # Генерируем временную метку в формате DDMMYYYY_HHMMSS
        timestamp = datetime.now().strftime('%d%m%Y_%H%M%S')
        
        # Добавляем эксперимент в конец списка
        safe_name = transliterate(name)
        # Имя папки формируется как SAMPLE_NAME_CREATION_DATE
        folder_name = f"{safe_name}_{timestamp}"
        experiment_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'experiments', folder_name)
        os.makedirs(experiment_folder, exist_ok=True)
        
        # Обработка файлов
        files = []
        uploaded_files = request.files.getlist('files')
        for file in uploaded_files:
            if file and file.filename != '':
                file.save(os.path.join(experiment_folder, file.filename))
                files.append(file.filename)

        data['experiments'].append({
            'id': new_id, 
            'name': name, 
            'description': desc, 
            'results': results,
            'status': status, 
            'date': date,
            'files': files,
            'folder_name': folder_name,
            '_created_at': timestamp
        })
        save_data(current_app.config['DATA_FILE'], data)
        flash('Эксперимент добавлен!', 'success')
        return redirect(url_for('experiments.list_experiments'))
    
    return render_template('experiment_form.html', experiment=None)

@experiments_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_experiment(id):
    data = get_data(current_app.config['DATA_FILE'])
    experiment = next((exp for exp in data['experiments'] if exp['id'] == id), None)
    if not experiment:
        flash('Эксперимент не найден', 'error')
        return redirect(url_for('experiments.list_experiments'))

    if request.method == 'POST':
        experiment['name'] = request.form.get('name')
        experiment['description'] = request.form.get('description')
        experiment['results'] = request.form.get('results')
        experiment['status'] = request.form.get('status')
        experiment['date'] = request.form.get('date')

        # Загрузка новых файлов
        uploaded_files = request.files.getlist('files')
        experiment_folder = get_experiment_folder_path(experiment)
        
        # Убедимся, что папка существует
        if not os.path.exists(experiment_folder):
            os.makedirs(experiment_folder)

        for file in uploaded_files:
            if file and file.filename != '':
                file.save(os.path.join(experiment_folder, file.filename))
                if file.filename not in experiment['files']:
                    experiment['files'].append(file.filename)

        save_data(current_app.config['DATA_FILE'], data)
        flash('Эксперимент обновлен!', 'success')
        return redirect(url_for('experiments.list_experiments'))

    return render_template('experiment_form.html', experiment=experiment)

@experiments_bp.route('/delete/<int:id>')
def delete_experiment(id):
    data = get_data(current_app.config['DATA_FILE'])
    experiment = next((exp for exp in data['experiments'] if exp['id'] == id), None)
    
    if experiment:
        # Получаем путь к папке и удаляем её полностью
        folder_path = get_experiment_folder_path(experiment)
        if os.path.exists(folder_path):
            try:
                shutil.rmtree(folder_path)
            except Exception as e:
                flash(f'Не удалось удалить папку с файлами: {e}', 'error')
        
        data['experiments'] = [exp for exp in data['experiments'] if exp['id'] != id]
        
        save_data(current_app.config['DATA_FILE'], data)
        flash('Эксперимент и его файлы удалены', 'info')
    
    return redirect(url_for('experiments.list_experiments'))

@experiments_bp.route('/delete_file/<int:experiment_id>/<filename>')
def delete_file(experiment_id, filename):
    data = get_data(current_app.config['DATA_FILE'])
    experiment = next((exp for exp in data['experiments'] if exp['id'] == experiment_id), None)
    
    if experiment and filename in experiment.get('files', []):
        experiment_folder = get_experiment_folder_path(experiment)
        file_path = os.path.join(experiment_folder, filename)
        
        if os.path.exists(file_path):
            os.remove(file_path)
        
        experiment['files'].remove(filename)
        save_data(current_app.config['DATA_FILE'], data)
        flash(f'Файл {filename} удален', 'info')
    
    return redirect(url_for('experiments.edit_experiment', id=experiment_id))

@experiments_bp.route('/file/<int:experiment_id>/<filename>')
def download_file(experiment_id, filename):
    data = get_data(current_app.config['DATA_FILE'])
    experiment = next((exp for exp in data['experiments'] if exp['id'] == experiment_id), None)
    
    if experiment:
        experiment_folder = get_experiment_folder_path(experiment)
        if os.path.exists(experiment_folder) and filename in os.listdir(experiment_folder):
            return send_from_directory(experiment_folder, filename)
    
    return "Файл не найден", 404

@experiments_bp.route('/folder/<int:experiment_id>')
def open_folder(experiment_id):
    """Открывает папку эксперимента в проводнике Windows."""
    data = get_data(current_app.config['DATA_FILE'])
    experiment = next((exp for exp in data['experiments'] if exp['id'] == experiment_id), None)
    
    if experiment:
        folder_path = get_experiment_folder_path(experiment)
        
        if os.path.exists(folder_path):
            try:
                subprocess.Popen(['explorer', folder_path])
                flash('Папка открыта в проводнике', 'success')
            except Exception as e:
                flash(f'Ошибка при открытии папки: {e}', 'error')
        else:
            flash('Папка не найдена на диске', 'error')
    else:
        flash('Эксперимент не найден', 'error')
        
    return redirect(url_for('experiments.list_experiments'))

@experiments_bp.route('/move/<int:id>/<direction>')
def move_experiment(id, direction):
    """Переместить эксперимент вверх или вниз."""
    data = get_data(current_app.config['DATA_FILE'])
    experiments = data.get('experiments', [])
    
    # Находим индекс текущего эксперимента
    current_idx = None
    for i, exp in enumerate(experiments):
        if exp['id'] == id:
            current_idx = i
            break
    
    if current_idx is None:
        flash('Эксперимент не найден', 'error')
        return redirect(url_for('experiments.list_experiments'))
    
    # Определяем новый индекс
    if direction == 'up' and current_idx > 0:
        new_idx = current_idx - 1
    elif direction == 'down' and current_idx < len(experiments) - 1:
        new_idx = current_idx + 1
    else:
        flash('Перемещение невозможно', 'info')
        return redirect(url_for('experiments.list_experiments'))
    
    # Меняем местами
    experiments[current_idx], experiments[new_idx] = experiments[new_idx], experiments[current_idx]
    
    save_data(current_app.config['DATA_FILE'], data)
    flash('Эксперимент перемещен', 'success')
    return redirect(url_for('experiments.list_experiments'))

@experiments_bp.route('/<int:id>/status', methods=['POST'])
def update_status(id):
    """AJAX endpoint для обновления статуса эксперимента."""
    data = get_data(current_app.config['DATA_FILE'])
    experiment = next((exp for exp in data['experiments'] if exp['id'] == id), None)
    
    if experiment:
        req_data = request.get_json()
        experiment['status'] = req_data.get('status', '')
        save_data(current_app.config['DATA_FILE'], data)
        return jsonify({'success': True})
    
    return jsonify({'success': False}), 404
