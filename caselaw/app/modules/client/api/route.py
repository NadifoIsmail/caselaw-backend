from flask import jsonify, make_response, request, current_app
from werkzeug.utils import secure_filename
import os
# from app import db
from app.db.models import Case, Client , Lawyer,db
from app.modules.client import client_bp
from flask_jwt_extended import jwt_required, get_jwt_identity

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@client_bp.route('/case-submit/<string:user_id>', methods=['POST'])
@jwt_required()
def handle_submitted_case(user_id:str):
    try:
        # Verify if request has data
        if not request.form:
            return jsonify({
                'status': 'error',
                'message': 'No data provided'
            }), 400

        # Get form data
        data = {
            'title': request.form.get('title'),
            'description': request.form.get('description'),
            'urgency_level': request.form.get('urgencyLevel'),
            'communication_method': request.form.get('communicationMethod'),
            'special_requirements': request.form.get('specialRequirements')
        }

        # Validate required fields
        required_fields = ['title', 'description', 'urgency_level', 'communication_method']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            return jsonify({
                'status': 'error',
                'message': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400

        # Get client
        client = Client.query.get(user_id)
        if not client:
            return jsonify({
                'status': 'error',
                'message': 'Client not found'
            }), 404

        # Create new case
        new_case = Case(
            title=data['title'],
            description=data['description'],
            urgency=data['urgency_level'],
            communication_method=data['communication_method'],
            special_requirements=data['special_requirements'],
            client_id=client.id,
            status='Pending'
        )

        # Handle file uploads
        if 'documents' in request.files:
            files = request.files.getlist('documents')
            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    # Save file and create document record
                    new_case.add_document(
                        file_name=filename,
                        file_data=file.read(),
                        uploaded_by=client.id
                    )

        # Save case to database
        db.session.add(new_case)
        db.session.commit()

        return jsonify({
            'status': 'success',
            'message': 'Case submitted successfully',
            'case_id': new_case.id
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'An error occurred: {str(e)}'
        }), 500
    

@client_bp.route('/cases/<string:user_id>',methods=['GET'])
@jwt_required()
def get_client_cases(user_id:str):
    try:
        client = Client.query.get(user_id)
        if not client:
            return jsonify({
                'status': 'error',
                'message': 'Client not found'
            }), 404

        cases = Case.query.filter_by(client_id=client.id).all()
        # return cases if empty return empty list
        cases_data = [case.to_json() for case in cases] if cases else []

        return jsonify({
            'status': 'success',
            'data': cases_data
        }), 200

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'An error occurred: {str(e)}'
        }), 500
    


def submit_case(self, case_details):
        new_case = Case(
            title=case_details.get('title'),
            description=case_details.get('description'),
            category=case_details.get('category'),
            status='Pending',
            client_id=self.id
        )
        db.session.add(new_case)
        db.session.commit()
        return new_case


@client_bp.route('/get-lawyers', methods=['POST'])
@jwt_required()
def find_lawyer_by_specialization():
        data = request.get_json()

        if data is None:
             return jsonify({
                  'success':'error',
                  'message':'input required'
                  
             })
        
        lawyers = Lawyer.query.filter_by(specialization=data.get['specialization']).all()

        if lawyers is None:
             return jsonify({
                  'success':'error',
                  'message':'no lawyers found with that specialization'
             })
        

        return jsonify({
             'success' : 'success',
             'message' : 'list of lawyers by specialization',
             'data': {
                  'lawyers' : lawyers
             }
        })

