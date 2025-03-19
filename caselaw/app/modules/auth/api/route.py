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
            # Create the role if it doesn't exist
            return jsonify({
                'status': 'error',
                'message': f'Role not found: {data["userType"]}'
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

@auth_bp.route('/google', methods=['GET'])
def google_login():
    """Initiate Google OAuth flow"""
    auth_type = request.args.get('auth_type', 'login')
    session['auth_type'] = auth_type  # Store auth type in session for later use
    
    if not google.authorized:
        return redirect(url_for('auth_bp.google.login'))
    
    return redirect(url_for('auth_bp.google_login_callback'))

@auth_bp.route('/google/callback', methods=['GET'])
def google_login_callback():
    """Handle Google OAuth callback"""
    if not google.authorized:
        return jsonify({
            'status': 'error',
            'message': 'Failed to authorize with Google'
        }), 401
    
    # Get Google user info
    resp = google.get('/oauth2/v2/userinfo')
    if not resp.ok:
        return jsonify({
            'status': 'error',
            'message': 'Failed to get user info from Google'
        }), 401
    
    google_info = resp.json()
    
    # Ensure required fields are present
    email = google_info.get('email')
    if not email:
        return jsonify({
            'status': 'error',
            'message': 'Email not provided by Google OAuth'
        }), 400
        
    firstname = google_info.get('given_name')
    if not firstname:
        return jsonify({
            'status': 'error',
            'message': 'First name not provided by Google OAuth'
        }), 400
    
    lastname = google_info.get('family_name', '')  # Optional
    
    # Find existing user by email
    user = User.query.filter_by(email=email).first()
    auth_type = session.get('auth_type', 'login')
    
    # Handle sign up or login based on auth_type
    if auth_type == 'signup' and not user:
        # Create new user for signup
        new_user = Client(
            firstname=firstname,
            lastname=lastname,
            email=email,
            # oauth_provider='google'
        )
        
        # Set a random password for the user
        import uuid
        random_password = str(uuid.uuid4())
        new_user.password = random_password
        
        # Assign default role (client)
        default_role = Role.query.filter_by(name='client').first()
        if not default_role:
            # Create client role if it doesn't exist
            default_role = Role(name='client')
            db.session.add(default_role)
            db.session.flush()
            
        new_user.add_role(default_role)
        
        # Save user to database and get ID
        db.session.add(new_user)
        db.session.flush()  # This is critical to get the user.id
        
        # Create client record for new user
        # new_client = Client(
        #     id=new_user.id  # Use the same ID as the parent user
        # )
        db.session.add(new_user)
        
        try:
            db.session.commit()
            # Set user for token creation
            user = new_user
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': f'Failed to create user account: {str(e)}'
            }), 500
            
    elif auth_type == 'login' and not user:
        # User tried to login with Google but doesn't have an account
        return jsonify({
            'status': 'error',
            'message': 'No account found with this email. Please sign up first.'
        }), 404
    
    # Generate tokens for the user
    access_token = create_access_token(identity=user)
    refresh_token = create_refresh_token(identity=user)
    
    # Clean up session
    session.pop('auth_type', None)
    
    # Frontend redirect URL with tokens
    frontend_url = request.cookies.get('redirect_uri', 'http://localhost:5173')
    redirect_url = f"{frontend_url}?access_token={access_token}&refresh_token={refresh_token}"
    
    return redirect(redirect_url)