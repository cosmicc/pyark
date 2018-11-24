import os
from modules.configreader import psql_db, psql_host, psql_port, psql_user, psql_pw, secsalt


class BaseConfig(object):
    DEBUG = False
    SECRET_KEY = os.urandom(32)
    SQLALCHEMY_ECHO = False
    SWAGGER_UI_JSONEDITOR = True
    SECURITY_PASSWORD_SALT = secsalt
    SQLALCHEMY_DATABASE_URI = f"postgresql://{psql_user}:{psql_pw}@{psql_host}:{psql_port}/{psql_db}"
    SECURITY_TRACKABLE = True
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECURITY_REGISTERABLE = False


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_ECHO = True
