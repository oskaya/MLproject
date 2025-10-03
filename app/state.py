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
    """Get current tracking status with detailed information"""
    return {
        'tracked_items': tracked_items,
        'tracking_active': tracking_active,
        'tracking_interval': tracking_interval,
        'alarm_active': alarm_active,
        'missing_items': missing_items,
        'auto_detection_active': auto_detection_active,
        'camera_streaming': camera_streaming,
        'latest_detections': latest_detections
    }

def is_object_already_tracked(label, class_id=None):
    """
    Check if an object with the same label (and optionally class_id) is already being tracked
    
    Args:
        label: Object label to check
        class_id: Optional class ID for more precise matching
        
    Returns:
        Boolean indicating if object is already tracked
    """
    for tracked_item in tracked_items:
        if tracked_item['label'] == label:
            # If class_id is provided, use it for more precise matching
            if class_id is not None:
                return tracked_item.get('class_id') == class_id
            return True
    return False

def get_tracked_labels():
    """Get set of all currently tracked object labels"""
    return {item['label'] for item in tracked_items}