from app.modules.lawyer import lawyer_bp
from app.modules.client import client_bp
from flask import Flask
from flasgger import Swagger
from app.modules.auth import auth_bp
from app.db.models import Role, db


def create_roles():
    roles = ['admin', 'lawyer', 'client']  # Just a list of names
    
    for role_name in roles:
        role = Role.query.filter_by(name=role_name).first()
        if not role:
            role = Role(name=role_name)
            db.session.add(role)
    
    db.session.commit()


def initialize_route(app: Flask):
    with app.app_context():
        app.register_blueprint(lawyer_bp, url_prefix='/api/lawyer')
        app.register_blueprint(client_bp, url_prefix='/api/client')
        app.register_blueprint(auth_bp, url_prefix='/api/auth')


def initialize_db(app: Flask):
    with app.app_context():
        db.init_app(app)
        db.create_all()
        create_roles()


def initialize_swagger(app: Flask):
    with app.app_context():
        swagger = Swagger(app)
        return swagger

"""
def create_default_roles():
    # Create default roles if they don't exist
    from app.db.db import db
    from app.db.db import Role 
    
    # Default roles
    default_roles = [
        {'name': 'admin', 'description': 'Administrator with full access'},
        {'name': 'lawyer', 'description': 'Lawyer with case management access'},
        {'name': 'client', 'description': 'Regular client with limited access'}
    ]
    
    for role_data in default_roles:
        role = Role.query.filter_by(name=role_data['name']).first()
        if not role:
            role = Role(name=role_data['name'], description=role_data['description'])
            db.session.add(role)
    
    db.session.commit()
"""