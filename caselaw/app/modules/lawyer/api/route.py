from flask import jsonify
from app.db.models import Case, Lawyer, db
from app.modules.lawyer import lawyer_bp
from flask_jwt_extended import jwt_required, get_jwt_identity

@lawyer_bp.route('/handle-cases/<string:case_id>', methods=['GET'])
@jwt_required()
def handle_case(case_id):
    lawyer_id = get_jwt_identity()
    lawyer = Lawyer.query.get(lawyer_id)

    if not lawyer:
        return jsonify({"message": "Lawyer not found"}), 404

    case = Case.query.get(case_id)
    if not case:
        return jsonify({"message": "Case not found"}), 404

    if case.status != 'Pending' or case.lawyer_id is not None:
        return jsonify({"message": "Case is already assigned or not available"}), 400

    # Assign the case to the lawyer
    case.lawyer_id = lawyer.id
    case.status = 'Under Review'
    lawyer.active_cases += 1
    db.session.commit()

    return jsonify({
        "message": f"Case {case_id} has been assigned to Lawyer {lawyer_id}",
        "lawyer_active_cases": lawyer.active_cases
    }), 200

@lawyer_bp.route('/available-case', methods=['GET'])
@jwt_required()
def get_available_cases():
    lawyer_id = get_jwt_identity()
    lawyer = Lawyer.query.get(lawyer_id)

    if not lawyer:
        return jsonify({"message": "Lawyer not found"}), 404

    available_cases = Case.query.filter(
        Case.lawyer_id == None, 
        Case.status == "Pending"
    ).all()

    if not available_cases:
        return jsonify({"message": "No available cases at the moment"}), 404

    return jsonify({
        "available_cases": [case.to_json() for case in available_cases]
    }), 200

@lawyer_bp.route('/assigned-cases', methods=['GET'])
@jwt_required()
def get_assigned_cases():
    lawyer_id = get_jwt_identity()
    lawyer = Lawyer.query.get(lawyer_id)

    if not lawyer:
        return jsonify({"message": "Lawyer not found"}), 404

    assigned_cases = Case.query.filter_by(lawyer_id=lawyer_id).all()

    if not assigned_cases:
        return jsonify({"message": "No cases assigned to this lawyer"}), 404

    return jsonify({
        "assigned_cases": [case.to_json() for case in assigned_cases]
    }), 200
