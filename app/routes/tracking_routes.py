"""
Tracking Routes
API endpoints for object tracking management
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
import app.state as state
from app.services import tracking_service, auth_service
from app import socketio

bp = Blueprint('tracking', __name__, url_prefix='/api/tracking')

@bp.route('/add', methods=['POST'])
@auth_service.login_required
def add_tracking():
    """Add detected object to tracking list"""
    data = request.get_json()
    detection = data.get('detection')
    
    if not detection:
        return jsonify({'success': False, 'message': 'No detection data provided'})
    
    tracking_item = tracking_service.add_to_tracking(detection)
    
    if tracking_item is None:
        return jsonify({
            'success': False, 
            'message': 'Object is already being tracked'
        })
    
    # Refresh detection tracking status
    tracking_service.refresh_detection_tracking_status(socketio)
    
    return jsonify({
        'success': True,
        'message': 'Object added to tracking',
        'item': tracking_item
    })

@bp.route('/remove', methods=['POST'])
@auth_service.login_required
def remove_from_tracking():
    """Remove object from tracking list"""
    data = request.get_json()
    item_id = data.get('item_id')
    
    tracking_service.remove_from_tracking(item_id)
    
    # Refresh detection tracking status after removal
    tracking_service.refresh_detection_tracking_status(socketio)
    
    return jsonify({'success': True, 'message': 'Item removed from tracking'})

@bp.route('/start', methods=['POST'])
@auth_service.login_required
def start_tracking():
    """Start active tracking"""
    success, message = tracking_service.start_tracking(socketio)
    
    return jsonify({'success': success, 'message': message})

@bp.route('/stop', methods=['POST'])
@auth_service.login_required
def stop_tracking():
    """Stop active tracking"""
    tracking_service.stop_tracking()
    return jsonify({'success': True, 'message': 'Tracking stopped'})

@bp.route('/status', methods=['GET'])
@auth_service.login_required
def tracking_status():
    """Get current tracking status"""
    return jsonify(state.get_tracking_status())

@bp.route('/clear', methods=['POST'])
@auth_service.login_required
def clear_tracking():
    """Clear all tracked items"""
    tracking_service.clear_tracking()
    
    # Refresh detection tracking status after clearing
    tracking_service.refresh_detection_tracking_status(socketio)
    
    return jsonify({'success': True, 'message': 'All tracked items cleared'})

@bp.route('/interval', methods=['POST'])
@auth_service.login_required
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
@auth_service.login_required
def get_tracking_interval():
    """Get current tracking interval"""
    return jsonify({'interval': state.tracking_interval})

@bp.route('/alarm/acknowledge', methods=['POST'])
@auth_service.login_required
def acknowledge_alarm():
    """Acknowledge the alarm (silence it but keep tracking)"""
    try:
        tracking_service.acknowledge_alarm(socketio)
        return jsonify({'success': True, 'message': 'Alarm acknowledged'})
    except Exception as e:
        print(f"❌ Error in acknowledge_alarm: {e}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@bp.route('/alarm/enable/<item_id>', methods=['POST'])
@auth_service.login_required
def enable_alarm(item_id):
    """Re-enable alarm for a specific tracked item"""
    try:
        for tracked_item in state.tracked_items:
            if tracked_item['id'] == item_id:
                tracked_item['alarm_enabled'] = True
                print(f"🔔 Enabled alarm for: {tracked_item['label']}")
                return jsonify({'success': True, 'message': f'Alarm enabled for {tracked_item["label"]}'})
        
        return jsonify({'success': False, 'message': 'Item not found'}), 404
    except Exception as e:
        print(f"❌ Error in enable_alarm: {e}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500