from flask import jsonify, redirect, request, session, url_for
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt_identity, jwt_required
from app.db.models import Client, Lawyer, Role, User, db
from app.modules.auth import auth_bp

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    data = request.get_json()
    
    # Check if required fields are present
    required_fields = ['firstName', 'lastName', 'email', 'password', 'userType']

    if data.get('userType') == 'lawyer':
        required_fields.append('barNumber')

    for field in required_fields:
        if field not in data:
            return jsonify({
                'status': 'error',
                'message': f'Missing required field: {field}'
            }), 400

    # Check if email already exists
    if User.query.filter_by(email=data['email']).first():
        return jsonify({
            'status': 'error',
            'message': 'Email already registered'
        }), 409
    
    try:
        # Create the specific user type directly instead of creating a generic User first
        if data['userType'] == 'client':
            new_user = Client(
                email=data['email'],
                firstname=data['firstName'],
                lastname=data['lastName'],
                phone=data.get('phone', ''),
                address=data.get('address', ''),
                location=data.get('location', '')
            )
            new_user.password = data['password']  # This will be hashed by the setter
            
        elif data['userType'] == 'lawyer':
            new_user = Lawyer(
                email=data['email'],
                firstname=data['firstName'],
                lastname=data['lastName'],
                bar_number=data['barNumber'],
                specialization=data.get('specialization', '')
            )
            new_user.password = data['password']  # This will be hashed by the setter
            
        else:
            return jsonify({
                'status': 'error',
                'message': f'Invalid user type: {data["userType"]}'
            }), 400
        
        # Assign the user-provided role
        user_role = Role.query.filter_by(name=data['userType']).first()
        if not user_role:
            return jsonify({
                'status' : 'error',
                'message' : 'Role not found'
            })
            
        new_user.add_role(user_role)

        # Save to database
        db.session.add(new_user)
        db.session.commit()
        
        # Generate tokens
        access_token = create_access_token(identity=new_user)
        refresh_token = create_refresh_token(identity=new_user)

        return jsonify({
            'status': 'success',
            'message': 'User registered successfully',
            'data': {
                'user': new_user.to_json(),
                'access_token': access_token,
                'refresh_token': refresh_token
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'Database error: {str(e)}'
        }), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """Authenticate a user and return JWT tokens"""
    data = request.get_json()
    
    # Check if required fields are present
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({
            'status': 'error',
            'message': 'Email and password are required'
        }), 400
    
    # Find the user by email
    user = User.query.filter_by(email=data['email']).first()
    
    # Check if user exists and password is correct
    if not user or not user.verify_password(data['password']):
        return jsonify({
            'status': 'error',
            'message': 'Invalid email or password'
        }), 401
    
    # Generate tokens
    access_token = create_access_token(identity=user)
    refresh_token = create_refresh_token(identity=user)
    
    return jsonify({
        'status': 'success',
        'message': 'Login successful',
        'data': {
            'user': user.to_json(),
            'access_token': access_token,
            'refresh_token': refresh_token
        }
    }), 200


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({
            'status': 'error',
            'message': 'User not found'
        }), 404
    
    # Create new access token
    access_token = create_access_token(identity=user)
    
    return jsonify({
        'status': 'success',
        'message': 'Token refreshed',
        'data': {
            'access_token': access_token
        }
    }), 200


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_user_profile():
    """Get current user profile"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({
            'status': 'error',
            'message': 'User not found'
        }), 404
    
    return jsonify({
        'status': 'success',
        'data': {
            'user': user.to_json()
        }
    }), 200
