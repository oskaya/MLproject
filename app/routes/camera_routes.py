"""
Camera Routes
API endpoints for camera control
"""
from flask import Blueprint, jsonify
from datetime import datetime
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
    
    # If alarm was active, notify frontend that it's cleared due to camera stop
    if state.alarm_active:
        socketio.emit('alarm_cleared', {
            'reason': 'camera_stopped',
            'timestamp': datetime.now().isoformat()
        })
    
    state.reset_tracking_state()
    
    # Clear frontend UI elements
    socketio.emit('clear_frame')  # Clear the video frame
    socketio.emit('clear_detections')  # Clear current detections list
    socketio.emit('clear_tracking_ui')  # Clear tracking controls
    
    socketio.emit('camera_command', {'action': 'stop'})
    return jsonify({'success': True, 'message': 'Camera stop command sent'})

@bp.route('/status', methods=['GET'])
def camera_status():
    return jsonify(state.get_camera_status())