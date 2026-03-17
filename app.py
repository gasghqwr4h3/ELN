import os
from flask import Flask, render_template
from routes.samples import samples_bp
from routes.storage import storage_bp
from routes.measurements import measurements_bp
from routes.experiments import experiments_bp

def create_app():
    app = Flask(__name__)
    app.secret_key = 'lab_secret_key_change_in_production'
    
    base_dir = os.path.abspath(os.path.dirname(__file__))
    app.config['UPLOAD_FOLDER'] = os.path.join(base_dir, 'uploads')
    app.config['DATA_FILE'] = os.path.join(base_dir, 'data', 'lab_data.json')
    
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.dirname(app.config['DATA_FILE']), exist_ok=True)

    app.register_blueprint(samples_bp, url_prefix='/samples')
    app.register_blueprint(storage_bp, url_prefix='/storage')
    app.register_blueprint(measurements_bp, url_prefix='/measurements')
    app.register_blueprint(experiments_bp, url_prefix='/experiments')

    @app.route('/')
    def index():
        from routes.helpers import get_data
        data = get_data(app.config['DATA_FILE'])
        stats = {
            'samples': len(data.get('samples', [])),
            'storages': len(data.get('storages', [])),
            'measurements': len(data.get('measurements', [])),
            'experiments': len(data.get('experiments', []))
        }
        return render_template('index.html', stats=stats, data=data)

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=False)