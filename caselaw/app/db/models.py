import os
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from datetime import datetime
import uuid
from flask import current_app, url_for
from werkzeug.utils import secure_filename

db = SQLAlchemy()
bcrypt = Bcrypt()

# Association table for User-Role relationship
user_roles = db.Table('user_roles',
    db.Column('user_id', db.String(36), db.ForeignKey('users.id'), primary_key=True),
    db.Column('role_id', db.String(36), db.ForeignKey('roles.id'), primary_key=True)
)

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String(255), unique=True, nullable=False)
    firstname = db.Column(db.String(100), nullable=False)
    lastname = db.Column(db.String(100), nullable=False)
    profile_image = db.Column(db.String(255), nullable=True, default=lambda: current_app.config['DEFAULT_PROFILE_IMAGE'])
    _password = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    roles = db.relationship('Role', secondary=user_roles, backref=db.backref('users', lazy='dynamic'))
    
    # Polymorphic identity for inheritance
    type = db.Column(db.String(50))
    __mapper_args__ = {
        'polymorphic_on': type,
        'polymorphic_identity': 'user'
    }
    
    # Methods
    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')
    
    @password.setter
    def password(self, password):
        self._password = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def verify_password(self, password):
        return bcrypt.check_password_hash(self._password, password)
    
    def get_role(self):
        return [role.name for role in self.roles]
    
    def add_role(self, role):
        if role not in self.roles:
            self.roles.append(role)
    
    def remove_role(self, role):
        if role in self.roles:
            self.roles.remove(role)

    def update_profile_image(self, file):
        """Update user profile image"""
        if file:
            upload_folder = current_app.config['UPLOAD_FOLDER']

            # Ensure upload folder exists
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)

            # Delete old profile image (if not the default)
            if self.profile_image and self.profile_image != current_app.config['DEFAULT_PROFILE_IMAGE']:
                old_file_path = os.path.join(upload_folder, self.profile_image)
                if os.path.exists(old_file_path):
                    os.remove(old_file_path)

            # Generate unique filename
            filename = secure_filename(f"profile_{self.id}_{file.filename}")
            file_path = os.path.join(upload_folder, filename)

            # Save file
            file.save(file_path)

            # Update database
            self.profile_image = filename
            db.session.commit()

            return True
        return False

    def get_profile_image_url(self):
        if not self.profile_image:
            return url_for('static', filename=current_app.config['DEFAULT_PROFILE_IMAGE'], _external=True)

        return url_for('static', filename=f"uploads/{self.profile_image}", _external=True)
    
    def to_json(self):
        return {
            'id': self.id,
            'email': self.email,
            'firstname': self.firstname,
            'lastname': self.lastname,
            'roles': [role.name for role in self.roles],
            'profile_image': self.get_profile_image_url(),
        }

class Role(db.Model):
    __tablename__ = 'roles'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(50), unique=True, nullable=False)
    
    def to_json(self):
        return {
            'id': self.id,
            'name': self.name
        }

class Client(User):
    __tablename__ = 'clients'
    
    id = db.Column(db.String(36), db.ForeignKey('users.id'), primary_key=True)
    phone = db.Column(db.String(20))
    address = db.Column(db.String(255))
    location = db.Column(db.String(100))
    
    # Relationships
    cases = db.relationship('Case', backref='client', lazy='dynamic')
    
    __mapper_args__ = {
        'polymorphic_identity': 'client',
    }
    
    
    
    def get_cases(self):
        return self.cases.all()
    
    def update_profile(self, profile_data):
        for key, value in profile_data.items():
            if hasattr(self, key) and key not in ['id', '_password', 'created_at', 'updated_at', 'type']:
                setattr(self, key, value)
        db.session.commit()
        return self
    
    def to_json(self):
        base_json = super().to_json()
        client_json = {
            'phone': self.phone,
            'address': self.address,
            'location': self.location,
            # 'cases': [case.id for case in self.cases]
        }
        return {**base_json, **client_json}

class Lawyer(User):
    __tablename__ = 'lawyers'
    
    id = db.Column(db.String(36), db.ForeignKey('users.id'), primary_key=True)
    specialization = db.Column(db.String(100))
    bar_number = db.Column(db.String(50), unique=True, nullable=True)
    active_cases = db.Column(db.Integer, default=0)
    rating = db.Column(db.Float, default=0.0)
    
    # Relationships
    cases = db.relationship('Case', backref='lawyer', lazy='dynamic')
    
    __mapper_args__ = {
        'polymorphic_identity': 'lawyer',
    }

    
    def accept_case(self, case_id):
        case = Case.query.get(case_id)
        if case and case.status == 'Pending':
            case.lawyer_id = self.id
            case.status = 'Under Review'
            self.active_cases += 1
            db.session.commit()
            return True
        return False
    
    def get_assigned_cases(self):
        return self.cases.all()
    
    def update_specialization(self, specialization):
        self.specialization = specialization
        db.session.commit()
        return self
    
    def update_lawyers_profile(self, profile_data):
        for key, value in profile_data.items():
            if hasattr(self, key) and key not in ['id', '_password', 'created_at', 'updated_at', 'type']:
                setattr(self, key, value)
        db.session.commit()
        return self
    
    def rate_lawyer(self, rating_value):
        # Calculate new average rating
        current_cases = self.cases.filter(Case.status == 'Closed').count()
        if current_cases > 0:
            self.rating = ((self.rating * (current_cases - 1)) + rating_value) / current_cases
            db.session.commit()
        else:
            self.rating = rating_value
            db.session.commit()
        return self.rating
    
    def to_json(self):
        base_json = super().to_json()
        lawyer_json = {
            'specialization': self.specialization,
            'active_cases': self.active_cases,
            'rating': self.rating,
            'cases': [case.id for case in self.cases]
        }
        return {**base_json, **lawyer_json}

class Case(db.Model):
    __tablename__ = 'cases'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='Pending')
    urgency = db.Column(db.String(20), nullable=False, default='low')
    communication_method = db.Column(db.String(100), nullable=False, default='Email')
    special_requirements = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign Keys
    client_id = db.Column(db.String(36), db.ForeignKey('clients.id'), nullable=False)
    lawyer_id = db.Column(db.String(36), db.ForeignKey('lawyers.id'), nullable=True)
    
    # Relationships
    documents = db.relationship('Document', backref='case', lazy='dynamic')
    
    def assign_lawyer(self, lawyer_id):
        lawyer = Lawyer.query.get(lawyer_id)
        if lawyer:
            self.lawyer_id = lawyer_id
            self.status = 'Under Review'
            lawyer.active_cases += 1
            db.session.commit()
            return True
        return False
    
    def update_status(self, new_status):
        valid_statuses = ["Pending", "Under Review", "In Progress", "Resolved", "Closed"]
        if new_status in valid_statuses:
            # If case is being closed, decrement lawyer's active_cases
            if new_status == 'Closed' and self.status != 'Closed' and self.lawyer_id:
                lawyer = Lawyer.query.get(self.lawyer_id)
                if lawyer and lawyer.active_cases > 0:
                    lawyer.active_cases -= 1
            
            self.status = new_status
            db.session.commit()
            return True
        return False
    
    def add_document(self, file_name, file_data, uploaded_by):
        """
        Add a new document to the case
        
        Parameters:
        file_name (str): Name of the file
        file_data (bytes): Binary data of the file
        uploaded_by (str): ID of the user who uploaded the document
        
        Returns:
        Document: The newly created document
        """
        new_document = Document(
            file_name=file_name,
            file_data=file_data,
            case_id=self.id,
            uploaded_by=uploaded_by
        )
        db.session.add(new_document)
        db.session.commit()
        return new_document
    
    def get_case_details(self):
        """
        Get comprehensive details of the case including related entities
        
        Returns:
        dict: Case details with client, lawyer, and documents information
        """
        case_details = self.to_json()
        case_details['client'] = self.get_client().to_json() if self.get_client() else None
        case_details['lawyer'] = self.get_lawyer().to_json() if self.get_lawyer() else None
        case_details['documents'] = [doc.to_json() for doc in self.documents]
        return case_details
    
    def get_client(self):
        """
        Get the client associated with this case
        
        Returns:
        Client: The client object
        """
        return Client.query.get(self.client_id)
    
    def get_lawyer(self):
        """
        Get the lawyer associated with this case
        
        Returns:
        Lawyer: The lawyer object or None if no lawyer is assigned
        """
        if self.lawyer_id:
            return Lawyer.query.get(self.lawyer_id)
        return None
    
    def to_json(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'category': self.category,
            'status': self.status,
            'updated': self.updated_at,
            'client': self.get_client().to_json().get('firstname') + " " + self.get_client().to_json().get('lastname') if self.get_client() else None,
            'lawyer': self.get_lawyer().to_json().get('firstname') + " " + self.get_lawyer().to_json().get('lastname') if self.get_lawyer() else None,
        }

class Document(db.Model):
    __tablename__ = 'documents'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    file_name = db.Column(db.String(255), nullable=False)
    file_data = db.Column(db.LargeBinary, nullable=True)  # Or use a cloud storage reference
    case_id = db.Column(db.String(36), db.ForeignKey('cases.id'), nullable=False)
    uploaded_by = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    uploader = db.relationship('User', backref='uploaded_documents')
    
    def to_json(self):
        return {
            'id': self.id,
            'file_name': self.file_name,
            'case_id': self.case_id,
            'uploaded_by': self.uploaded_by,
            'uploaded_at': self.uploaded_at.isoformat()
        }