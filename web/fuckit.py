from active_alchemy import ActiveAlchemy
from flask_login import LoginManager, UserMixin
from modules.configreader import psql_host, psql_port, psql_user, psql_pw, psql_db
from flask import Flask
# from web.api.routes import mod as apimod
from .views import mod as webuimod

app = Flask(__name__)

app.config['SECRET_KEY'] = '669v445Xyrzqkt@4N*%!74XkerrHQmz5^86eaKS^Cr4nF3a6KW5gUQTXZPRTmQm7'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

db = ActiveAlchemy(f"postgresql+pg8000://{psql_user}:{psql_pw}@{psql_host}:{psql_port}/{psql_db}", app=app)


class users(UserMixin, db.Model):
    username = db.Column(db.String(15), unique=True)
    password = db.Column(db.String(80))
    email = db.Column(db.String(50), unique=True)


app.register_blueprint(webuimod, url_prefix='/')
# app.register_blueprint(apimod, url_prefix='/api')
