"""
Main Web Application - Controls camera and handles ML detection/tracking
"""
from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO, emit
import requests
import json
import time
import base64
import io
from datetime import datetime
from typing import List, Dict

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Configuration
ML_API_URL = "http://localhost:8000/predict"

# Global state
camera_connected = False
latest_frame = None
tracked_items = []
tracking_active = False

@app.route('/')
def index():
    return render_template('index.html')

# WebSocket handlers for camera communication
@socketio.on('camera_ready')
def handle_camera_ready(data):
    global camera_connected
    camera_connected = True
    print(f"📹 Camera ready: Index {data.get('camera_index')}, Resolution: {data.get('resolution')}")
    emit('camera_status', {
        'connected': True, 
        'streaming': True,
        'camera_info': data
    }, broadcast=True)

@socketio.on('camera_stopped')
def handle_camera_stopped(data):
    print("📹 Camera stopped")
    emit('camera_status', {
        'connected': camera_connected, 
        'streaming': False
    }, broadcast=True)

@socketio.on('connect')
def handle_web_client_connect():
    print("🌐 Web client connected")
    # Send current camera status to newly connected client
    emit('camera_status', {
        'connected': camera_connected,
        'streaming': latest_frame is not None
    })

@socketio.on('disconnect')
def handle_web_client_disconnect():
    print("🌐 Web client disconnected")
    
@socketio.on('camera_error')
def handle_camera_error(data):
    print(f"❌ Camera error: {data.get('message')}")
    emit('camera_status', {
        'connected': camera_connected, 
        'streaming': False,
        'error': data.get('message')
    }, broadcast=True)

@socketio.on('camera_connect')
def handle_camera_connect(data):
    global camera_connected
    camera_connected = True
    print(f"Camera connected: {data.get('camera_id', 'unknown')}")
    emit('camera_status', {'connected': True}, broadcast=True)

@socketio.on('camera_disconnect')
def handle_camera_disconnect():
    global camera_connected, latest_frame
    camera_connected = False
    latest_frame = None
    print("Camera disconnected")
    emit('camera_status', {'connected': False}, broadcast=True)

@socketio.on('frame_data')
def handle_frame_data(data):
    global latest_frame
    latest_frame = data['frame']
    # Broadcast frame to web clients if needed
    emit('new_frame', data, broadcast=True)

# API endpoints for web interface
@app.route('/api/camera/start', methods=['POST'])
def start_camera():
    if not camera_connected:
        return jsonify({'success': False, 'message': 'Camera not connected'})
    
    socketio.emit('camera_command', {'action': 'start'})
    return jsonify({'success': True, 'message': 'Camera start command sent'})

@app.route('/api/camera/stop', methods=['POST'])
def stop_camera():
    if not camera_connected:
        return jsonify({'success': False, 'message': 'Camera not connected'})
    
    socketio.emit('camera_command', {'action': 'stop'})
    return jsonify({'success': True, 'message': 'Camera stop command sent'})

@app.route('/api/camera/status', methods=['GET'])
def camera_status():
    return jsonify({
        'connected': camera_connected,
        'has_frame': latest_frame is not None
    })

@app.route('/api/detect', methods=['POST'])
def detect_objects():
    """Get object detections from ML model"""
    global latest_frame
    
    if not latest_frame:
        return jsonify({'success': False, 'message': 'No frame available'})
    
    try:
        # Convert base64 frame to bytes
        image_bytes = base64.b64decode(latest_frame)
        
        # Prepare file for ML API
        files = {
            'file': ('frame.jpg', io.BytesIO(image_bytes), 'image/jpeg')
        }
        
        # Send to ML API
        response = requests.post(ML_API_URL, files=files, timeout=10)
        
        if response.status_code == 200:
            ml_result = response.json()
            
            # Transform ML response to frontend format
            detections = []
            for detection in ml_result.get('detections', []):
                detections.append({
                    'label': detection['label'],
                    'confidence': detection['confidence'],
                    'class_id': detection['class_id'],
                    'bbox': detection['bbox']
                })
            
            return jsonify({
                'success': True,
                'detections': detections,
                'num_detections': ml_result.get('num_detections', len(detections)),
                'image': latest_frame,  # Include the image
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False, 
                'message': f'ML API error: {response.status_code}'
            })
            
    except Exception as e:
        print(f"Detection error: {str(e)}")
        return jsonify({
            'success': False, 
            'message': f'Detection error: {str(e)}'
        })

@app.route('/api/tracking/add', methods=['POST'])
def add_to_tracking():
    """Add detected object to tracking list"""
    global tracked_items
    
    data = request.get_json()
    detection = data.get('detection')
    
    if not detection:
        return jsonify({'success': False, 'message': 'No detection data provided'})
    
    tracking_item = {
        'id': f"track_{len(tracked_items)}_{int(time.time())}",
        'label': detection.get('label', 'unknown'),
        'confidence': detection.get('confidence', 0),
        'class_id': detection.get('class_id', -1),
        'bbox': detection.get('bbox', {}),
        'added_at': datetime.now().isoformat(),
        'last_seen': datetime.now().isoformat(),
        'is_present': True
    }
    
    tracked_items.append(tracking_item)
    
    return jsonify({
        'success': True,
        'message': 'Object added to tracking',
        'item': tracking_item
    })

@app.route('/api/tracking/remove', methods=['POST'])
def remove_from_tracking():
    """Remove object from tracking list"""
    global tracked_items
    
    data = request.get_json()
    item_id = data.get('item_id')
    
    tracked_items = [item for item in tracked_items if item['id'] != item_id]
    
    return jsonify({'success': True, 'message': 'Item removed from tracking'})

@app.route('/api/tracking/start', methods=['POST'])
def start_tracking():
    """Start active tracking"""
    global tracking_active
    
    if not tracked_items:
        return jsonify({'success': False, 'message': 'No items to track'})
    
    tracking_active = True
    return jsonify({'success': True, 'message': 'Tracking started'})

@app.route('/api/tracking/stop', methods=['POST'])
def stop_tracking():
    """Stop active tracking"""
    global tracking_active
    tracking_active = False
    return jsonify({'success': True, 'message': 'Tracking stopped'})

@app.route('/api/tracking/status', methods=['GET'])
def tracking_status():
    """Get current tracking status"""
    return jsonify({
        'tracking_active': tracking_active,
        'tracked_items': tracked_items,
        'count': len(tracked_items)
    })

@app.route('/api/tracking/clear', methods=['POST'])
def clear_tracking():
    """Clear all tracked items"""
    global tracked_items, tracking_active
    tracked_items = []
    tracking_active = False
    return jsonify({'success': True, 'message': 'All tracked items cleared'})

if __name__ == '__main__':
    print("Starting Object Tracking Web App...")
    print(f"ML API URL: {ML_API_URL}")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)