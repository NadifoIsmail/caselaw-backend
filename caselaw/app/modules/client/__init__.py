

from flask import Blueprint


client_bp = Blueprint('client_bp', __name__)

import app.modules.client.api.route