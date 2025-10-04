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

def calculate_bbox_distance(bbox1, bbox2):
    """
    Calculate distance between two bounding boxes using center points
    
    Args:
        bbox1, bbox2: Bounding box dictionaries with 'x', 'y', 'width', 'height'
        
    Returns:
        Euclidean distance between center points
    """
    if not bbox1 or not bbox2:
        return float('inf')
    
    # Calculate center points
    center1_x = bbox1.get('x', 0) + bbox1.get('width', 0) / 2
    center1_y = bbox1.get('y', 0) + bbox1.get('height', 0) / 2
    
    center2_x = bbox2.get('x', 0) + bbox2.get('width', 0) / 2
    center2_y = bbox2.get('y', 0) + bbox2.get('height', 0) / 2
    
    # Euclidean distance
    distance = ((center1_x - center2_x) ** 2 + (center1_y - center2_y) ** 2) ** 0.5
    return distance

def calculate_bbox_overlap_ratio(bbox1, bbox2):
    """
    Calculate overlap ratio between two bounding boxes
    
    Args:
        bbox1, bbox2: Bounding box dictionaries with 'x', 'y', 'width', 'height'
        
    Returns:
        Overlap ratio (0.0 to 1.0), where 1.0 means complete overlap
    """
    if not bbox1 or not bbox2:
        return 0.0
    
    # Get coordinates
    x1_1, y1_1 = bbox1.get('x', 0), bbox1.get('y', 0)
    x1_2, y1_2 = x1_1 + bbox1.get('width', 0), y1_1 + bbox1.get('height', 0)
    
    x2_1, y2_1 = bbox2.get('x', 0), bbox2.get('y', 0)
    x2_2, y2_2 = x2_1 + bbox2.get('width', 0), y2_1 + bbox2.get('height', 0)
    
    # Calculate intersection area
    inter_x1 = max(x1_1, x2_1)
    inter_y1 = max(y1_1, y2_1)
    inter_x2 = min(x1_2, x2_2)
    inter_y2 = min(y1_2, y2_2)
    
    if inter_x2 <= inter_x1 or inter_y2 <= inter_y1:
        return 0.0
    
    intersection_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
    bbox1_area = bbox1.get('width', 0) * bbox1.get('height', 0)
    bbox2_area = bbox2.get('width', 0) * bbox2.get('height', 0)
    
    # Use smaller bbox area for ratio calculation
    smaller_area = min(bbox1_area, bbox2_area)
    if smaller_area == 0:
        return 0.0
    
    return intersection_area / smaller_area

def is_object_already_tracked(label, class_id=None, bbox=None, proximity_threshold=50):
    """
    Check if an object is already being tracked using label and bbox proximity
    
    Args:
        label: Object label to check
        class_id: Optional class ID for more precise matching
        bbox: Bounding box for proximity matching
        proximity_threshold: Maximum distance for considering objects as same (pixels)
        
    Returns:
        Boolean indicating if object is already tracked
    """
    for tracked_item in tracked_items:
        if tracked_item['label'] == label:
            # If class_id is provided, use it for more precise matching
            if class_id is not None and tracked_item.get('class_id') != class_id:
                continue
                
            # If bbox is provided, use proximity matching
            if bbox is not None and 'bbox' in tracked_item:
                distance = calculate_bbox_distance(bbox, tracked_item['bbox'])
                overlap_ratio = calculate_bbox_overlap_ratio(bbox, tracked_item['bbox'])
                
                print(f"🔍 Proximity check: {label} - distance: {distance:.1f}px, overlap: {overlap_ratio:.2f}, threshold: {proximity_threshold}px")
                
                # Consider it the same object if:
                # 1. Distance is within threshold, OR
                # 2. Overlap ratio is significant (>30%)
                if distance <= proximity_threshold or overlap_ratio > 0.3:
                    print(f"❌ {label} already tracked (distance: {distance:.1f}px <= {proximity_threshold}px OR overlap: {overlap_ratio:.2f} > 0.3)")
                    return True
            else:
                # Fallback to label-only matching if no bbox provided
                print(f"❌ {label} already tracked (no bbox, label-only match)")
                return True
    print(f"✅ {label} not tracked yet")
    return False

def get_tracked_labels():
    """Get set of all currently tracked object labels"""
    return {item['label'] for item in tracked_items}