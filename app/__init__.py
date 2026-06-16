import os
from flask import Flask
from .config import config
from .extensions import db, migrate
import importlib
from .graphql_api import create_graphql_view

REST_API_V = os.environ.get('REST_API_V', 'v1')
api_module = importlib.import_module(f'.api.{REST_API_V}', package=__name__)

def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)
    migrate.init_app(app, db)

    app.register_blueprint(api_module.bp, url_prefix=f'/api/{REST_API_V}')
    app.add_url_rule('/graphql', view_func=create_graphql_view(), methods=['GET', 'POST'])

    return app

