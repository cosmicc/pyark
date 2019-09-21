from quart import Quart, Blueprint
from .views import webapp


def create_app(config_object):
    app = Quart(__name__, instance_relative_config=True)
    app.config.from_object(config_object)
    register_blueprints(app)
    return app


def register_blueprints(app):
    Blueprint(webapp, url_prefix='/')


app = create_app('config.BaseConfig')
