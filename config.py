"""
Configuration settings for the Object Tracking System
"""
import os

class Config:
    # ML API Configuration
    ML_API_URL = os.getenv('ML_API_URL', 'http://localhost:8000/predict')
    ML_API_TIMEOUT = int(os.getenv('ML_API_TIMEOUT', '10'))
    
    # Camera Configuration
    CAMERA_INDEX = int(os.getenv('CAMERA_INDEX', '0'))  # Manual camera index selection
    ENABLE_AUTO_CAMERA_DETECTION = os.getenv('ENABLE_AUTO_CAMERA_DETECTION', 'True').lower() == 'true'
    PREFERRED_CAMERAS = [0, 1, 2, 3, 4]  # Fallback camera indices for auto-detection
    DEFAULT_CAMERA_WIDTH = 640
    DEFAULT_CAMERA_HEIGHT = 480
    DEFAULT_CAMERA_FPS = 30
    JPEG_QUALITY = 80
    STREAM_FPS = 30  # Web streaming FPS
    
    # Detection Configuration
    AUTO_DETECTION_INTERVAL = 5  # seconds
    DETECTION_CONFIDENCE_THRESHOLD = 0.5
    
    # Tracking Configuration
    DEFAULT_TRACKING_INTERVAL = 5  # seconds
    MIN_TRACKING_INTERVAL = 1
    MAX_TRACKING_INTERVAL = 60
    MISSING_ITEM_THRESHOLD_MULTIPLIER = 2  # intervals
    
    # Flask Configuration
    FLASK_HOST = '0.0.0.0'
    FLASK_PORT = 5000  # Use different port for testing
    FLASK_DEBUG = True
    
    # SocketIO Configuration
    SOCKETIO_CORS_ALLOWED_ORIGINS = "*"