"""
Camera Application Configuration
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class CameraConfig:
    # Camera Connection Configuration
    WEBAPP_URL = os.getenv('WEBAPP_URL', 'http://localhost:5000')
    
    # Camera Configuration
    CAMERA_INDEX = int(os.getenv('CAMERA_INDEX', '0'))  # Manual camera index selection
    ENABLE_AUTO_CAMERA_DETECTION = os.getenv('ENABLE_AUTO_CAMERA_DETECTION', 'True').lower() == 'true'
    PREFERRED_CAMERAS = [0, 1, 2, 3, 4]  # Fallback camera indices for auto-detection
    DEFAULT_CAMERA_WIDTH = 640
    DEFAULT_CAMERA_HEIGHT = 480
    DEFAULT_CAMERA_FPS = 30
    JPEG_QUALITY = 80
    STREAM_FPS = 30  # Web streaming FPS
    
    # Camera App Specific Settings
    RECONNECT_DELAY = 5  # seconds to wait before reconnecting to webapp
    MAX_RECONNECT_ATTEMPTS = 10
    FRAME_SKIP_COUNT = 1  # Send every Nth frame to reduce bandwidth
    
    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    ENABLE_DEBUG_OUTPUT = os.getenv('ENABLE_DEBUG_OUTPUT', 'True').lower() == 'true'