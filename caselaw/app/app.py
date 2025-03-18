import os
from flask import Flask
from flask_jwt_extended import JWTManager
from app.config.config import get_config_by_name
from app.initialize_functions import initialize_route, initialize_db, initialize_swagger
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_principal import Principal
# from flask_rbac import RBAC
from flask_migrate import Migrate

bcrypt = Bcrypt()
jwt = JWTManager()
migrate = Migrate()
# cors = CORS()
# rbac = RBAC()
principal = Principal()

def create_app(config=None) -> Flask:
    from app.db.models import db
    """
    Create a Flask application.

    Args:
        config: The configuration object to use.

    Returns:
        A Flask application instance.
    """
    
    app = Flask(__name__)
   # Initialize extensions
    
    bcrypt.init_app(app)
    jwt.init_app(app)
    principal.init_app(app)
    CORS(app)

    # rbac.init_app(app)

    if config:
        app.config.from_object(get_config_by_name(config))
    # os.makedirs(os.path.join(app.root_path, app.config['UPLOAD_FOLDER']), exist_ok=True)
    # Initialize extensions
    initialize_db(app)

    # Register blueprints
    initialize_route(app)

    # Initialize Swagger
    initialize_swagger(app)

    # Setup JWT error handlers and callbacks
    setup_jwt_callbacks(app)

    migrate.init_app(app, db) 
    return app

def setup_jwt_callbacks(app):
    """Setup JWT error handlers and callbacks"""
    from flask import jsonify
    from app.db.models import User
    
    @jwt.user_identity_loader
    def user_identity_lookup(user):
        """
        Function that takes any object passed to create_access_token
        and converts it to a JSON serializable format.
        """
        return str(user.id)
    
    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        """
        Function that loads a user from your database whenever
        a protected route is accessed.
        """
        identity = jwt_data["sub"]
        return User.query.filter_by(id=identity).one_or_none()
    
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({
            'status': 'error',
            'message': 'The token has expired',
            'code': 'token_expired'
        }), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({
            'status': 'error',
            'message': 'Signature verification failed',
            'code': 'invalid_token'
        }), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({
            'status': 'error',
            'message': 'Request does not contain an access token',
            'code': 'authorization_required'
        }), 401
    
    @jwt.needs_fresh_token_loader
    def token_not_fresh_callback(jwt_header, jwt_payload):
        return jsonify({
            'status': 'error',
            'message': 'The token is not fresh',
            'code': 'fresh_token_required'
        }), 401