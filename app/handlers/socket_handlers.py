"""
SocketIO Event Handlers
Handles real-time communication between camera app and web interface
"""
import random
from datetime import datetime
from flask_socketio import emit
import app.state as state
from app.services import ml_service

def register_handlers(socketio):
    """Register all socket event handlers"""
    
    @socketio.on('connect')
    def handle_web_client_connect():
        print("🌐 Web client connected")
        emit('camera_status', {
            'connected': state.camera_connected,
            'streaming': state.camera_streaming
        })

    @socketio.on('camera_ready')
    def handle_camera_ready(data):
        state.camera_connected = True
        state.camera_streaming = True
        print(f"📹 Camera ready: Index {data.get('camera_index')}, Resolution: {data.get('resolution')}")
        
        # Start auto-detection
        ml_service.start_auto_detection(socketio)
        
        emit('camera_status', {
            'connected': True, 
            'streaming': True,
            'camera_info': data
        })

    @socketio.on('camera_stopped')
    def handle_camera_stopped(data):
        # If alarm was active, clear it due to camera stop
        if state.alarm_active:
            socketio.emit('alarm_cleared', {
                'reason': 'camera_stopped',
                'timestamp': datetime.now().isoformat()
            })
            
        state.camera_streaming = False
        ml_service.stop_auto_detection()
        state.reset_tracking_state()  # Reset tracking state when camera stops
        print("📹 Camera stopped - alarms cleared")
        emit('camera_status', {
            'connected': state.camera_connected, 
            'streaming': False
        })

    @socketio.on('frame_data')
    def handle_frame_data(data):
        state.latest_frame = data['frame']
        # Send live frame to frontend
        socketio.emit('live_frame', {
            'frame': data['frame'],
            'timestamp': data.get('timestamp', datetime.now().isoformat())
        })
        # Debug: print occasionally to confirm frames are being received
        if random.randint(1, 30) == 1:  # Print every ~30th frame
            print(f"📺 Broadcasting live frame to web clients")

    @socketio.on('camera_error')
    def handle_camera_error(data):
        print(f"❌ Camera error: {data.get('message')}")
        emit('camera_status', {
            'connected': state.camera_connected,
            'streaming': False,
            'error': data.get('message')
        })

    @socketio.on('camera_connect')
    def handle_camera_connect(data):
        state.camera_connected = True
        camera_id = data.get('camera_id', 'unknown')
        print(f"📹 Camera connected: {camera_id}")
        emit('camera_status', {'connected': True})

    @socketio.on('camera_disconnect')
    def handle_camera_disconnect():
        # If alarm was active, clear it due to camera disconnect
        if state.alarm_active:
            socketio.emit('alarm_cleared', {
                'reason': 'camera_disconnected',
                'timestamp': datetime.now().isoformat()
            })
            
        state.reset_camera_state()
        state.reset_tracking_state()  # Also reset tracking state
        print("📹 Camera disconnected - alarms cleared")
        emit('camera_status', {'connected': False, 'streaming': False})