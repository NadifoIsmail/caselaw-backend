

from flask import Blueprint


lawyer_bp = Blueprint('lawyer_bp', __name__)

import app.modules.lawyer.api.route