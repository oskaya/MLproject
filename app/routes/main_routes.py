"""
Main Routes
Basic application routes
"""
from flask import Blueprint, render_template
from app.services import auth_service

bp = Blueprint('main', __name__)

@bp.route('/')
@auth_service.login_required
def index():
    user = auth_service.get_current_user()
    return render_template('index.html', user=user)