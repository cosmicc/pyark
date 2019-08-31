import os

from modules.configreader import psql_db, psql_host, psql_port, psql_pw, psql_user, secsalt, testing_seckey


class BaseConfig(object):
    DEBUG = False
    SECRET_KEY = testing_seckey
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
    SECRET_KEY = testing_seckey
