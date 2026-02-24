import os
from dotenv import load_dotenv
from flask import Flask
from backend.config import Config
from backend.routes import bp

# Cargar variables de entorno desde .env
load_dotenv()

def create_app():
    from flask_babel import Babel
    from flask_caching import Cache
    from flask_login import LoginManager
    from backend.models import init_db, get_user_by_id
    app = Flask(__name__)
    app.config.from_object(Config)
    app.secret_key = os.environ.get('SECRET_KEY', 'supersecretkey')
    app.register_blueprint(bp)
    from backend.aloxamento import aloxamento_bp
    app.register_blueprint(aloxamento_bp)

    # Configuración de cache
    from backend.cache import cache
    app.config['CACHE_TYPE'] = 'simple'
    cache.init_app(app)

    # Flask-Login
    login_manager = LoginManager(app)
    login_manager.login_view = 'main.login'
    login_manager.login_message = 'Debes iniciar sesión para acceder a esta páxina.'

    @login_manager.user_loader
    def load_user(user_id):
        return get_user_by_id(int(user_id))

    # Soporte multilingüe (os catálogos .po implementaranse máis adiante)
    app.config['BABEL_DEFAULT_LOCALE'] = app.config.get('BABEL_DEFAULT_LOCALE', 'gl')
    app.config['BABEL_SUPPORTED_LOCALES'] = app.config.get('BABEL_SUPPORTED_LOCALES', ['gl', 'es', 'en'])
    babel = Babel(app)

    def get_locale():
        from flask import request
        return request.args.get('lang') or app.config.get('BABEL_DEFAULT_LOCALE', 'gl')
    app.jinja_env.globals['get_locale'] = get_locale

    # Inicializar a base de datos ao iniciar a app
    with app.app_context():
        init_db()

    @app.errorhandler(404)
    def not_found(e):
        from flask import render_template
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(e):
        from flask import render_template
        return render_template('500.html'), 500

    return app
