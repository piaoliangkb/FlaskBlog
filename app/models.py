from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, AnonymousUserMixin
from . import db, login_manager
from flask import current_app
from datetime import datetime

class PERMISSION:
    FOLLOW = 1
    COMMENT = 2
    WRITE = 4
    MODERATE = 8#FIND THE COMMENTS INAPPROPRIIATE中等的
    ADMIN = 16

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(64), unique = True)
    default = db.Column(db.Boolean, default = False, index = True)
    permissions = db.Column(db.Integer)
    users = db.relationship('User', backref = 'role', lazy = 'dynamic')

    def __init__(self,**kwargs):
        super(Role,self).__init__(**kwargs)
        if self.permissions is None:
            self.permissions=0

    @staticmethod
    #静态方法不需要实例化，直接使用类名+方法即可直接调用
    def insert_roles():
        roles = {
            'User': [PERMISSION.FOLLOW, PERMISSION.COMMENT],
            'Moderator': [PERMISSION.FOLLOW, PERMISSION.COMMENT, PERMISSION.WRITE, PERMISSION.MODERATE],
            'Adminstrator': [PERMISSION.FOLLOW, PERMISSION.COMMENT, PERMISSION.WRITE, PERMISSION.MODERATE,
                             PERMISSION.ADMIN],
        }
        default_role='User'
        for r in roles:
            role=Role.query.filter_by(name=r).first()
            #查找Role表种是否有对应的用户类型
            if role is None:
                role=Role(name=r)
            #如果Role表种没有对应的用户类型，则将新的用户类型加入到Role表中
            role.reset_permissions()
            for perm in roles[r]:
                role.add_permission(perm)
            role.default= (role.name==default_role)
            db.session.add(role)
        db.session.commit()

    def add_permission(self,perm):
        if not self.has_permission(perm):
            self.permissions += perm

    def remove_permission(self,perm):
        if self.has_permission(perm):
            self.permissions -= perm

    def reset_permissions(self):
        self.permissions=0

    def has_permission(self,perm):
        return self.permissions & perm == perm

    def __repr__(self):
        return '<Role %r>' % self.name


class User(UserMixin,db.Model):
    __tablename__='users'
    id=db.Column(db.Integer,primary_key=True)
    username=db.Column(db.String(64),unique=True,index=True)
    role_id=db.Column(db.Integer,db.ForeignKey('roles.id'))
    password_hash=db.Column(db.String(128))
    email=db.Column(db.String(64),unique=True,index=True)

    #展示信息
    name=db.Column(db.String(64))#real name
    location=db.Column(db.String(64))
    about_me=db.Column(db.Text())
    member_since=db.Column(db.DateTime(),default=datetime.utcnow)
    last_seen=db.Column(db.DateTime(),default=datetime.utcnow)
    #添加用户头像
    avatar=db.Column(db.String(128),default=None)

    def __init__(self,**kwargs):
        super(User,self).__init__(**kwargs)
        if self.role is None:
            if self.email == current_app.config['FLASKY_ADMIN']:
                self.role=Role.query.filter_by(permissions=0xff).first()
            if self.role is None:
                self.role=Role.query.filter_by(default=True).first()

    def ping(self):
        self.last_seen=datetime.utcnow()
        db.session.add(self)

    def can(self,permissions):
        return self.role is not None and (self.role.permissions & permissions) == permissions

    def is_administrator(self):
        return self.can(PERMISSION.ADMIN)

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self,password):
        self.password_hash=generate_password_hash(password)

    def verify_password(self,password):
        return check_password_hash(self.password_hash,password)

    def __repr__(self):
        return '<User %r>' % self.username
#一个python类代表一个数据库模型，类中的属性代表数据库表中的列

class AnonymousUser(AnonymousUserMixin):
    def can(self,permissions):
        return False

    def is_adminstrator(self):
        return False
login_manager.anonymout_user=AnonymousUser

from . import login_manager
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
#加载用户的回调函数