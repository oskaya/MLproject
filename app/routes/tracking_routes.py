"""
Tracking Routes
API endpoints for object tracking
"""
from flask import Blueprint, request, jsonify
import app.state as state
from app.services import tracking_service
from app import socketio

bp = Blueprint('tracking', __name__, url_prefix='/api/tracking')

@bp.route('/add', methods=['POST'])
def add_to_tracking():
    """Add detected object to tracking list"""
    data = request.get_json()
    detection = data.get('detection')
    
    if not detection:
        return jsonify({'success': False, 'message': 'No detection data provided'})
    
    tracking_item = tracking_service.add_to_tracking(detection)
    
    return jsonify({
        'success': True,
        'message': 'Object added to tracking',
        'item': tracking_item
    })

@bp.route('/remove', methods=['POST'])
def remove_from_tracking():
    """Remove object from tracking list"""
    data = request.get_json()
    item_id = data.get('item_id')
    
    tracking_service.remove_from_tracking(item_id)
    
    return jsonify({'success': True, 'message': 'Item removed from tracking'})

@bp.route('/start', methods=['POST'])
def start_tracking():
    """Start active tracking"""
    success, message = tracking_service.start_tracking(socketio)
    
    return jsonify({'success': success, 'message': message})

@bp.route('/stop', methods=['POST'])
def stop_tracking():
    """Stop active tracking"""
    tracking_service.stop_tracking()
    return jsonify({'success': True, 'message': 'Tracking stopped'})

@bp.route('/status', methods=['GET'])
def tracking_status():
    """Get current tracking status"""
    return jsonify(state.get_tracking_status())

@bp.route('/clear', methods=['POST'])
def clear_tracking():
    """Clear all tracked items"""
    tracking_service.clear_tracking()
    return jsonify({'success': True, 'message': 'All tracked items cleared'})

@bp.route('/interval', methods=['POST'])
def set_tracking_interval():
    """Set tracking check interval"""
    data = request.get_json()
    new_interval = data.get('interval')
    
    success, message = tracking_service.set_tracking_interval(new_interval)
    
    response = {'success': success, 'message': message}
    if success:
        response['interval'] = state.tracking_interval
        
    return jsonify(response)

@bp.route('/interval', methods=['GET'])
def get_tracking_interval():
    """Get current tracking interval"""
    return jsonify({'interval': state.tracking_interval})

@bp.route('/alarm/acknowledge', methods=['POST'])
def acknowledge_alarm():
    """Acknowledge the alarm (silence it but keep tracking)"""
    tracking_service.acknowledge_alarm()
    return jsonify({'success': True, 'message': 'Alarm acknowledged'})