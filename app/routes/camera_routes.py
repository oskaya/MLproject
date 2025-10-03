"""
Camera Routes
API endpoints for camera control
"""
from flask import Blueprint, jsonify
import app.state as state
from app.services import ml_service
from app import socketio

bp = Blueprint('camera', __name__, url_prefix='/api/camera')

@bp.route('/start', methods=['POST'])
def start_camera():
    if not state.camera_connected:
        return jsonify({'success': False, 'message': 'Camera not connected'})
    
    socketio.emit('camera_command', {'action': 'start'})
    return jsonify({'success': True, 'message': 'Camera start command sent'})

@bp.route('/stop', methods=['POST'])
def stop_camera():
    if not state.camera_connected:
        return jsonify({'success': False, 'message': 'Camera not connected'})
    
    # Stop auto-detection and tracking when camera stops
    ml_service.stop_auto_detection()
    state.reset_tracking_state()
    
    socketio.emit('camera_command', {'action': 'stop'})
    return jsonify({'success': True, 'message': 'Camera stop command sent'})

@bp.route('/status', methods=['GET'])
def camera_status():
    return jsonify(state.get_camera_status())