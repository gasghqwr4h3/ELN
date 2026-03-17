from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from .helpers import get_data, save_data

installations_bp = Blueprint('installations', __name__, template_folder='../templates')

@installations_bp.route('/')
def list_installations():
    data = get_data(current_app.config['DATA_FILE'])
    return render_template('installation_list.html', installations=data.get('installations', []))

@installations_bp.route('/add', methods=['GET', 'POST'])
def add_installation():
    if request.method == 'POST':
        name = request.form.get('name')
        location = request.form.get('location')
        desc = request.form.get('description')
        
        data = get_data(current_app.config['DATA_FILE'])
        new_id = max([i['id'] for i in data.get('installations', [])], default=0) + 1
        
        data['installations'].append({
            'id': new_id, 
            'name': name, 
            'location': location, 
            'description': desc,
            'status': 'Active' # Active, Maintenance, Broken
        })
        save_data(current_app.config['DATA_FILE'], data)
        flash('Установка добавлена!', 'success')
        return redirect(url_for('installations.list_installations'))
    return render_template('installation_form.html', installation=None)

@installations_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_installation(id):
    data = get_data(current_app.config['DATA_FILE'])
    inst = next((i for i in data['installations'] if i['id'] == id), None)
    
    if not inst:
        flash('Установка не найдена', 'error')
        return redirect(url_for('installations.list_installations'))

    if request.method == 'POST':
        inst['name'] = request.form.get('name')
        inst['location'] = request.form.get('location')
        inst['description'] = request.form.get('description')
        inst['status'] = request.form.get('status')
        save_data(current_app.config['DATA_FILE'], data)
        flash('Установка обновлена!', 'success')
        return redirect(url_for('installations.list_installations'))
    
    return render_template('installation_form.html', installation=inst)

@installations_bp.route('/delete/<int:id>')
def delete_installation(id):
    data = get_data(current_app.config['DATA_FILE'])
    # Проверка: нельзя удалить установку, если есть активные измерения на ней (опционально)
    # Для простоты просто удаляем из списка, записи измерений останутся историей
    data['installations'] = [i for i in data['installations'] if i['id'] != id]
    save_data(current_app.config['DATA_FILE'], data)
    flash('Установка удалена из реестра', 'info')
    return redirect(url_for('installations.list_installations'))