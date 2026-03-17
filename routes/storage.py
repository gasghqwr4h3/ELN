from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from .helpers import get_data, save_data

storage_bp = Blueprint('storage', __name__, template_folder='../templates')

@storage_bp.route('/')
def list_storages():
    data = get_data(current_app.config['DATA_FILE'])
    storages = data.get('storages', [])
    all_samples = data.get('samples', [])
    
    # Создаем список для отображения, включая виртуальное хранилище "Нет хранилища"
    display_list = []
    
    # 1. Собираем образцы без хранилища
    no_storage_samples = [s for s in all_samples if not s.get('storage_id')]
    
    # Добавляем виртуальную запись в начало списка
    display_list.append({
        'id': 'none',
        'name': 'Нет хранилища',
        'location': '-',
        'description': 'Образцы, не привязанные к конкретному шкафчику/кабинету',
        'samples': no_storage_samples
    })
    
    # 2. Обрабатываем реальные хранилища
    for storage in storages:
        # Находим образцы, привязанные к этому хранилищу
        linked_samples = [s for s in all_samples if s.get('storage_id') == storage['id']]
        
        # Добавляем список образцов прямо в объект хранилища для шаблона
        storage['samples'] = linked_samples
        display_list.append(storage)
    
    return render_template('storage_list.html', storages=display_list)

@storage_bp.route('/move/<id>/<direction>')
def move_storage(id, direction):
    """Переместить хранилище вверх или вниз."""
    if id == 'none':
        flash('Виртуальное хранилище нельзя переместить', 'warning')
        return redirect(url_for('storage.list_storages'))
    
    data = get_data(current_app.config['DATA_FILE'])
    storages = data.get('storages', [])
    
    try:
        id = int(id)
    except ValueError:
        flash('Неверный ID хранилища', 'error')
        return redirect(url_for('storage.list_storages'))
    
    # Находим индекс текущего хранилища
    current_idx = None
    for i, s in enumerate(storages):
        if s['id'] == id:
            current_idx = i
            break
    
    if current_idx is None:
        flash('Хранилище не найдено', 'error')
        return redirect(url_for('storage.list_storages'))
    
    # Определяем новый индекс
    if direction == 'up' and current_idx > 0:
        new_idx = current_idx - 1
    elif direction == 'down' and current_idx < len(storages) - 1:
        new_idx = current_idx + 1
    else:
        flash('Перемещение невозможно', 'info')
        return redirect(url_for('storage.list_storages'))
    
    # Меняем местами
    storages[current_idx], storages[new_idx] = storages[new_idx], storages[current_idx]
    save_data(current_app.config['DATA_FILE'], data)
    flash('Хранилище перемещено', 'success')
    return redirect(url_for('storage.list_storages'))

@storage_bp.route('/add', methods=['GET', 'POST'])
def add_storage():
    if request.method == 'POST':
        name = request.form.get('name')
        location = request.form.get('location')
        desc = request.form.get('description')
        
        data = get_data(current_app.config['DATA_FILE'])
        # Получаем максимальный ID только среди реальных хранилищ (исключаем 'none')
        real_storages = [s for s in data.get('storages', []) if isinstance(s.get('id'), int)]
        new_id = max([s['id'] for s in real_storages], default=0) + 1
        
        data['storages'].append({
            'id': new_id, 'name': name, 'location': location, 'description': desc
        })
        save_data(current_app.config['DATA_FILE'], data)
        flash('Хранилище добавлено!', 'success')
        return redirect(url_for('storage.list_storages'))
    return render_template('storage_form.html', storage=None)

@storage_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_storage(id):
    data = get_data(current_app.config['DATA_FILE'])
    storage = next((s for s in data['storages'] if s['id'] == id), None)
    
    if not storage:
        flash('Хранилище не найдено', 'error')
        return redirect(url_for('storage.list_storages'))

    if request.method == 'POST':
        storage['name'] = request.form.get('name')
        storage['location'] = request.form.get('location')
        storage['description'] = request.form.get('description')
        save_data(current_app.config['DATA_FILE'], data)
        flash('Хранилище обновлено!', 'success')
        return redirect(url_for('storage.list_storages'))
    
    return render_template('storage_form.html', storage=storage)

@storage_bp.route('/delete/<int:id>')
def delete_storage(id):
    data = get_data(current_app.config['DATA_FILE'])
    data['storages'] = [s for s in data['storages'] if s['id'] != id]
    
    # Отвязываем образцы от удаленного хранилища (они перейдут в "Нет хранилища")
    for sample in data['samples']:
        if sample.get('storage_id') == id:
            sample['storage_id'] = None
            
    save_data(current_app.config['DATA_FILE'], data)
    flash('Хранилище удалено', 'info')
    return redirect(url_for('storage.list_storages'))