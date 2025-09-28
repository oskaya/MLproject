"""
Camera Application - Connects to web app and sends frames
"""
import cv2
import socketio
import base64
import time
import threading

class CameraApp:
    def __init__(self, webapp_url="http://localhost:5000"):
        self.webapp_url = webapp_url
        self.sio = socketio.Client()
        self.camera = None
        self.is_running = False
        self.preferred_cameras = [2, 0, 1, 3, 4]  # External camera first
        self.setup_events()
        
    def find_available_camera(self):
        """Find the first available camera"""
        for cam_index in self.preferred_cameras:
            print(f"🔍 Testing camera index {cam_index}...")
            cap = cv2.VideoCapture(cam_index)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    print(f"✅ Found working camera at index {cam_index}")
                    cap.release()
                    return cam_index
                cap.release()
        return None
        
    def setup_events(self):
        @self.sio.event
        def connect():
            print("✅ Connected to web app")
            self.sio.emit('camera_connect', {'camera_id': 'external_cam'})
            # Just notify connection, don't auto-start camera
            
        @self.sio.event
        def disconnect():
            print("❌ Disconnected from web app")
            self.stop_camera()
            
        @self.sio.event
        def connect_error(data):
            print(f"❌ Connection error: {data}")
            
        @self.sio.on('camera_command')
        def handle_command(data):
            print(f"📥 Received command: {data}")
            action = data.get('action')
            if action == 'start':
                self.start_camera()
            elif action == 'stop':
                self.stop_camera()
    
    def connect(self):
        try:
            print(f"🔄 Attempting to connect to {self.webapp_url}...")
            self.sio.connect(self.webapp_url)
            return True
        except Exception as e:
            print(f"❌ Failed to connect: {e}")
            return False
    
    def start_camera(self):
        if self.is_running:
            print("⚠️  Camera already running")
            return
            
        print("🔄 Starting camera...")
        
        # Find available camera
        camera_index = self.find_available_camera()
        if camera_index is None:
            print("❌ No cameras available")
            # Notify web app of failure
            self.sio.emit('camera_error', {'message': 'No cameras available'})
            return
            
        self.camera = cv2.VideoCapture(camera_index)
        if not self.camera.isOpened():
            print(f"❌ Failed to open camera {camera_index}")
            self.sio.emit('camera_error', {'message': f'Failed to open camera {camera_index}'})
            return
            
        # Set camera properties
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.camera.set(cv2.CAP_PROP_FPS, 30)
        
        # Test if we can read a frame
        ret, test_frame = self.camera.read()
        if not ret:
            print("❌ Cannot read from camera")
            self.camera.release()
            self.sio.emit('camera_error', {'message': 'Cannot read from camera'})
            return
            
        self.is_running = True
        threading.Thread(target=self._capture_loop, daemon=True).start()
        print(f"✅ Camera started successfully on index {camera_index}")
        
        # Notify web app that camera is ready
        self.sio.emit('camera_ready', {
            'camera_index': camera_index,
            'resolution': f"{test_frame.shape[1]}x{test_frame.shape[0]}"
        })
    
    def stop_camera(self):
        if not self.is_running:
            print("⚠️  Camera already stopped")
            return
            
        print("🔄 Stopping camera...")
        self.is_running = False
        if self.camera:
            self.camera.release()
            self.camera = None
        print("⏹️  Camera stopped")
        
        # Notify web app
        self.sio.emit('camera_stopped', {})
    
    def _capture_loop(self):
        frame_count = 0
        last_report = time.time()
        
        while self.is_running and self.camera:
            ret, frame = self.camera.read()
            if ret:
                frame_count += 1
                # Resize for better performance
                frame = cv2.resize(frame, (640, 480))
                
                # Encode to base64
                _, buffer = cv2.imencode('.jpg', frame)
                frame_b64 = base64.b64encode(buffer).decode('utf-8')
                
                # Send to web app
                self.sio.emit('frame_data', {
                    'frame': frame_b64,
                    'timestamp': time.time()
                })
                
                # Debug info every 5 seconds
                current_time = time.time()
                if current_time - last_report >= 5:
                    fps = frame_count / (current_time - last_report + 5)
                    print(f"📸 Streaming at {fps:.1f} FPS ({frame_count} frames sent)")
                    frame_count = 0
                    last_report = current_time
                
            else:
                print("⚠️  Failed to read frame")
                time.sleep(0.1)
                
            time.sleep(0.033)  # ~30 FPS
    
    def run(self):
        if self.connect():
            print("🎯 Camera app ready. Use web interface to start/stop camera.")
            print("Press Ctrl+C to stop.")
            try:
                self.sio.wait()
            except KeyboardInterrupt:
                print("\n🛑 Shutting down...")
                self.stop_camera()
                self.sio.disconnect()
        else:
            print("❌ Failed to start camera app")

if __name__ == '__main__':
    print("🚀 Starting Camera Application...")
    app = CameraApp()
    app.run()