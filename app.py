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
import threading
from datetime import datetime, timedelta
from typing import List, Dict

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Configuration
ML_API_URL = "http://localhost:8000/predict"

# Global state
camera_connected = False
camera_streaming = False
latest_frame = None
latest_detections = []
tracked_items = []
tracking_active = False
tracking_interval = 5  # Default 5 seconds
alarm_active = False
missing_items = []
tracking_thread = None
auto_detection_thread = None
auto_detection_active = False

@app.route('/')
def index():
    return render_template('index.html')

# Fix the socketio.emit calls - remove broadcast=True parameter

def auto_detect_objects():
    """Automatically detect objects every 5 seconds when camera is streaming"""
    global latest_frame, latest_detections, auto_detection_active
    
    print("🤖 Started automatic object detection (every 5 seconds)")
    
    while auto_detection_active and camera_streaming:
        if latest_frame:
            try:
                print("📡 Auto-detecting objects...")
                
                # Convert base64 frame to bytes
                image_bytes = base64.b64decode(latest_frame)
                files = {'file': ('frame.jpg', io.BytesIO(image_bytes), 'image/jpeg')}
                
                # Send to ML API
                response = requests.post(ML_API_URL, files=files, timeout=10)
                
                if response.status_code == 200:
                    ml_result = response.json()
                    
                    # Transform ML response
                    detections = []
                    for detection in ml_result.get('detections', []):
                        detections.append({
                            'label': detection['label'],
                            'confidence': detection['confidence'],
                            'class_id': detection['class_id'],
                            'bbox': detection['bbox']
                        })
                    
                    latest_detections = detections
                    print(f"📊 Auto-detected {len(detections)} objects")
                    
                    # Send to frontend - FIXED: removed broadcast=True
                    socketio.emit('auto_detection_result', {
                        'detections': detections,
                        'image': latest_frame,
                        'timestamp': datetime.now().isoformat()
                    })
                    
                else:
                    print(f"❌ ML API error: {response.status_code}")
                    
            except Exception as e:
                print(f"❌ Auto-detection error: {e}")
        
        time.sleep(5)  # Wait 5 seconds
    
    print("🛑 Auto-detection stopped")

def check_tracked_items():
    """Continuously check if tracked items are still present"""
    global alarm_active, missing_items, latest_detections, tracking_active
    
    print(f"🔍 Started tracking monitor (checking every {tracking_interval}s)")
    
    while tracking_active:
        if not latest_detections or not tracked_items:
            time.sleep(tracking_interval)
            continue
            
        try:
            print(f"📊 Checking {len(tracked_items)} tracked items against {len(latest_detections)} detections")
            
            # Check each tracked item
            current_missing = []
            for tracked_item in tracked_items:
                item_found = False
                
                # Look for similar objects in current detections
                for detection in latest_detections:
                    if detection['label'] == tracked_item['label']:
                        # Simple matching by label and confidence threshold
                        if detection['confidence'] > 0.5:
                            item_found = True
                            tracked_item['last_seen'] = datetime.now().isoformat()
                            tracked_item['is_present'] = True
                            break
                
                if not item_found:
                    tracked_item['is_present'] = False
                    # Check if missing for more than 2 intervals
                    last_seen = datetime.fromisoformat(tracked_item['last_seen'])
                    if (datetime.now() - last_seen).total_seconds() > (tracking_interval * 2):
                        current_missing.append(tracked_item)
                        print(f"❌ Missing: {tracked_item['label']}")
                    else:
                        print(f"⚠️ Temporary loss: {tracked_item['label']}")
                else:
                    print(f"✅ Found: {tracked_item['label']}")
            
            # Update missing items
            missing_items = current_missing
            
            # Trigger alarm if items missing - FIXED: removed broadcast=True
            if missing_items and not alarm_active:
                alarm_active = True
                print(f"🚨 ALARM TRIGGERED: {len(missing_items)} items missing!")
                socketio.emit('alarm_triggered', {
                    'missing_items': missing_items,
                    'timestamp': datetime.now().isoformat()
                })
            elif not missing_items and alarm_active:
                alarm_active = False
                print("✅ All items found - alarm cleared")
                socketio.emit('alarm_cleared', {
                    'timestamp': datetime.now().isoformat()
                })
                    
        except Exception as e:
            print(f"❌ Error checking tracked items: {e}")
        
        time.sleep(tracking_interval)
    
    print("🛑 Tracking monitor stopped")

# Also fix the other socketio.emit calls in the WebSocket handlers:
@socketio.on('connect')
def handle_web_client_connect():
    print("🌐 Web client connected")
    emit('camera_status', {
        'connected': camera_connected,
        'streaming': camera_streaming
    })
@socketio.on('camera_ready')
def handle_camera_ready(data):
    global camera_connected, camera_streaming, auto_detection_active, auto_detection_thread
    camera_connected = True
    camera_streaming = True
    print(f"📹 Camera ready: Index {data.get('camera_index')}, Resolution: {data.get('resolution')}")
    
    # Start auto-detection
    auto_detection_active = True
    if auto_detection_thread is None or not auto_detection_thread.is_alive():
        auto_detection_thread = threading.Thread(target=auto_detect_objects, daemon=True)
        auto_detection_thread.start()
    
    # FIXED: removed broadcast=True
    emit('camera_status', {
        'connected': True, 
        'streaming': True,
        'camera_info': data
    })

@socketio.on('camera_stopped')
def handle_camera_stopped(data):
    global camera_streaming, auto_detection_active
    camera_streaming = False
    auto_detection_active = False
    print("📹 Camera stopped")
    # FIXED: removed broadcast=True
    emit('camera_status', {
        'connected': camera_connected, 
        'streaming': False
    })

@socketio.on('frame_data')
def handle_frame_data(data):
    global latest_frame
    latest_frame = data['frame']
    # Send live frame to frontend - this broadcasts the frame to all connected clients
    socketio.emit('live_frame', {
        'frame': data['frame'],
        'timestamp': data.get('timestamp', datetime.now().isoformat())
    })
    # Debug: print occasionally to confirm frames are being received
    import random
    if random.randint(1, 30) == 1:  # Print every ~30th frame
        print(f"📺 Broadcasting live frame to web clients")

@socketio.on('camera_error')
def handle_camera_error(data):
    print(f"❌ Camera error: {data.get('message')}")
    # FIXED: removed broadcast=True
    emit('camera_status', {
        'connected': camera_connected,
        'streaming': False,
        'error': data.get('message')
    })

@socketio.on('camera_connect')
def handle_camera_connect(data):
    global camera_connected
    camera_connected = True
    camera_id = data.get('camera_id', 'unknown')
    print(f"📹 Camera connected: {camera_id}")
    # FIXED: removed broadcast=True
    emit('camera_status', {'connected': True})

@socketio.on('camera_disconnect')
def handle_camera_disconnect():
    global camera_connected, camera_streaming, latest_frame, auto_detection_active
    camera_connected = False
    camera_streaming = False
    latest_frame = None
    auto_detection_active = False
    print("📹 Camera disconnected")
    # FIXED: removed broadcast=True
    emit('camera_status', {'connected': False, 'streaming': False})

# API endpoints for web interface
@app.route('/api/camera/start', methods=['POST'])
def start_camera():
    if not camera_connected:
        return jsonify({'success': False, 'message': 'Camera not connected'})
    
    socketio.emit('camera_command', {'action': 'start'})
    return jsonify({'success': True, 'message': 'Camera start command sent'})

@app.route('/api/camera/stop', methods=['POST'])
def stop_camera():
    global auto_detection_active, tracking_active
    if not camera_connected:
        return jsonify({'success': False, 'message': 'Camera not connected'})
    
    # Stop auto-detection and tracking when camera stops
    auto_detection_active = False
    tracking_active = False
    
    socketio.emit('camera_command', {'action': 'stop'})
    return jsonify({'success': True, 'message': 'Camera stop command sent'})

@app.route('/api/camera/status', methods=['GET'])
def camera_status():
    return jsonify({
        'connected': camera_connected,
        'streaming': camera_streaming,
        'has_frame': latest_frame is not None
    })

# Removed /api/detect endpoint - now automatic

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
    global tracking_active, tracking_thread
    
    if not tracked_items:
        return jsonify({'success': False, 'message': 'No items to track'})
    
    if tracking_active:
        return jsonify({'success': False, 'message': 'Tracking already active'})
    
    tracking_active = True
    
    # Start monitoring thread
    if tracking_thread is None or not tracking_thread.is_alive():
        tracking_thread = threading.Thread(target=check_tracked_items, daemon=True)
        tracking_thread.start()
    
    return jsonify({'success': True, 'message': f'Tracking started (checking every {tracking_interval}s)'})

@app.route('/api/tracking/stop', methods=['POST'])
def stop_tracking():
    """Stop active tracking"""
    global tracking_active, alarm_active
    tracking_active = False
    alarm_active = False
    return jsonify({'success': True, 'message': 'Tracking stopped'})

@app.route('/api/tracking/status', methods=['GET'])
def tracking_status():
    """Get current tracking status"""
    return jsonify({
        'tracking_active': tracking_active,
        'tracking_interval': tracking_interval,
        'alarm_active': alarm_active,
        'tracked_items': tracked_items,
        'missing_items': missing_items,
        'count': len(tracked_items)
    })

@app.route('/api/tracking/clear', methods=['POST'])
def clear_tracking():
    """Clear all tracked items"""
    global tracked_items, tracking_active, alarm_active
    tracked_items = []
    tracking_active = False
    alarm_active = False
    return jsonify({'success': True, 'message': 'All tracked items cleared'})

@app.route('/api/tracking/interval', methods=['POST'])
def set_tracking_interval():
    """Set tracking check interval"""
    global tracking_interval
    
    data = request.get_json()
    new_interval = data.get('interval')
    
    if not new_interval or not isinstance(new_interval, int) or new_interval < 1 or new_interval > 60:
        return jsonify({'success': False, 'message': 'Interval must be between 1-60 seconds'})
    
    tracking_interval = new_interval
    print(f"⏱️ Tracking interval changed to {tracking_interval} seconds")
    
    return jsonify({
        'success': True, 
        'message': f'Tracking interval set to {tracking_interval} seconds',
        'interval': tracking_interval
    })

@app.route('/api/tracking/interval', methods=['GET'])
def get_tracking_interval():
    """Get current tracking interval"""
    return jsonify({'interval': tracking_interval})

@app.route('/api/alarm/acknowledge', methods=['POST'])
def acknowledge_alarm():
    """Acknowledge the alarm (silence it but keep tracking)"""
    global alarm_active
    alarm_active = False
    return jsonify({'success': True, 'message': 'Alarm acknowledged'})

if __name__ == '__main__':
    print("Starting Object Tracking Web App...")
    print(f"ML API URL: {ML_API_URL}")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)