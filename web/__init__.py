from flask import Flask
from flask_security import SQLAlchemyUserDatastore
from flask_socketio import SocketIO

from .database import db, security
from .models import Role, User

socketio = SocketIO()


def create_app(config_object):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_object)
    register_extensions(app)
    register_blueprints(app)
    user_datastore = SQLAlchemyUserDatastore(db, User, Role)
    security.init_app(app, user_datastore, register_blueprint=True)
    socketio.init_app(app)
    return app


def register_blueprints(app):
    from .webui.views import webui
    from .api.views import webapi
    app.register_blueprint(webui, url_prefix='/')


def register_extensions(app):
    db.init_app(app)
    if app.debug:
        try:
            from flask_debugtoolbar import DebugToolbarExtension
            DebugToolbarExtension(app)
        except ImportError:
            pass


app = create_app('config.BaseConfig')
