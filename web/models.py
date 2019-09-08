from flask_security import RoleMixin, UserMixin
from web.database import db

roles_users = db.Table('roles_users', db.Column('user_id', db.Integer(), db.ForeignKey('web_users.id')), db.Column('role_id', db.Integer(), db.ForeignKey('web_roles.id')))


class Role(db.Model, RoleMixin):
    __tablename__ = 'web_roles'
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

    def __repr__(self):
        return '%s - %s' % (self.name, self.description)


class User(db.Model, UserMixin):
    __tablename__ = 'web_users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    last_login_at = db.Column(db.DateTime())
    current_login_at = db.Column(db.DateTime())
    last_login_ip = db.Column(db.String(100))
    current_login_ip = db.Column(db.String(100))
    login_count = db.Column(db.Integer)
    active = db.Column(db.Boolean())
    confirmed_at = db.Column(db.DateTime())
    timezone = db.Column(db.String(25))
    steamid = db.Column(db.String(17), unique=True)
    roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))

    def __repr__(self):
        return '%s - %s' % (self.code, self.name)
