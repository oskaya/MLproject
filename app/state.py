"""
Global Application State
Centralized state management for the object tracking system
"""
from datetime import datetime
from config import Config

# Camera state
camera_connected = False
camera_streaming = False
latest_frame = None

# Detection state
latest_detections = []
auto_detection_active = False
auto_detection_thread = None

# Tracking state
tracked_items = []
tracking_active = False
tracking_interval = Config.DEFAULT_TRACKING_INTERVAL
tracking_thread = None

# Alarm state
alarm_active = False
missing_items = []

def reset_camera_state():
    """Reset all camera-related state"""
    global camera_connected, camera_streaming, latest_frame, auto_detection_active
    camera_connected = False
    camera_streaming = False
    latest_frame = None
    auto_detection_active = False

def reset_tracking_state():
    """Reset all tracking-related state"""
    global tracking_active, alarm_active, missing_items
    tracking_active = False
    alarm_active = False
    missing_items = []

def get_camera_status():
    """Get current camera status"""
    return {
        'connected': camera_connected,
        'streaming': camera_streaming,
        'has_frame': latest_frame is not None
    }

def get_tracking_status():
    """Get current tracking status"""
    return {
        'tracking_active': tracking_active,
        'tracking_interval': tracking_interval,
        'alarm_active': alarm_active,
        'tracked_items': tracked_items,
        'missing_items': missing_items,
        'count': len(tracked_items)
    }