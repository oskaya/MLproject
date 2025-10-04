"""
ML Detection Service
Handles communication with ML API and object detection
"""
import requests
import base64
import io
import time
import threading
from datetime import datetime
from webapp_config import WebAppConfig
from app.state import latest_frame, latest_detections, auto_detection_active, camera_streaming
import app.state as state

def detect_objects(frame_data):
    """
    Send frame to ML API for object detection
    
    Args:
        frame_data: Base64 encoded image data
        
    Returns:
        List of detected objects or None if error
    """
    try:
        # Convert base64 frame to bytes
        image_bytes = base64.b64decode(frame_data)
        files = {'file': ('frame.jpg', io.BytesIO(image_bytes), 'image/jpeg')}
        
        # Send to ML API
        response = requests.post(WebAppConfig.ML_API_URL, files=files, timeout=WebAppConfig.ML_API_TIMEOUT)
        
        if response.status_code == 200:
            ml_result = response.json()
            
            # Debug: Print ML response format
            print(f"🔍 ML API Response: {ml_result}")
            
            # Transform ML response
            detections = []
            for detection in ml_result.get('detections', []):
                # Convert bbox format: {x1, y1, x2, y2} -> {x, y, width, height}
                bbox_raw = detection.get('bbox', {})
                bbox_converted = {}
                if bbox_raw and 'x1' in bbox_raw:
                    bbox_converted = {
                        'x': bbox_raw['x1'],
                        'y': bbox_raw['y1'], 
                        'width': bbox_raw['x2'] - bbox_raw['x1'],
                        'height': bbox_raw['y2'] - bbox_raw['y1']
                    }
                
                detection_item = {
                    'label': detection['label'],
                    'confidence': detection['confidence'],
                    'class_id': detection['class_id'],
                    'bbox': bbox_converted
                }
                print(f"🔍 Detection: {detection_item}")
                detections.append(detection_item)
            
            return detections
        else:
            print(f"❌ ML API error: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Detection error: {e}")
        return None

def auto_detect_objects(socketio):
    """
    Automatically detect objects at regular intervals
    
    Args:
        socketio: SocketIO instance for emitting events
    """
    print(f"🤖 Started automatic object detection (every {WebAppConfig.AUTO_DETECTION_INTERVAL} seconds)")
    
    while state.auto_detection_active and state.camera_streaming:
        if state.latest_frame:
            try:
                print("📡 Auto-detecting objects...")
                
                detections = detect_objects(state.latest_frame)
                
                if detections is not None:
                    # Enhance detections with tracking info
                    enhanced_detections = []
                    for detection in detections:
                        enhanced_detection = detection.copy()
                        # Check if this object is already being tracked (with bbox proximity)
                        enhanced_detection['is_tracked'] = state.is_object_already_tracked(
                            detection['label'], 
                            detection.get('class_id'),
                            detection.get('bbox')  # Pass bbox for proximity matching
                        )
                        enhanced_detections.append(enhanced_detection)
                    
                    state.latest_detections = enhanced_detections
                    print(f"📊 Auto-detected {len(enhanced_detections)} objects ({len([d for d in enhanced_detections if d['is_tracked']])} already tracked)")
                    
                    # Send to frontend with tracking info
                    socketio.emit('auto_detection_result', {
                        'detections': enhanced_detections,
                        'image': state.latest_frame,
                        'timestamp': datetime.now().isoformat()
                    })
                    
            except Exception as e:
                print(f"❌ Auto-detection error: {e}")
        
        time.sleep(WebAppConfig.AUTO_DETECTION_INTERVAL)
    
    print("🛑 Auto-detection stopped")

def start_auto_detection(socketio):
    """Start automatic detection in a separate thread"""
    if not state.auto_detection_active:
        state.auto_detection_active = True
        if state.auto_detection_thread is None or not state.auto_detection_thread.is_alive():
            state.auto_detection_thread = threading.Thread(
                target=auto_detect_objects, 
                args=(socketio,), 
                daemon=True
            )
            state.auto_detection_thread.start()

def stop_auto_detection():
    """Stop automatic detection"""
    state.auto_detection_active = False