from quart import Quart
from .views import webapp


app = create_app('config.BaseConfig')
