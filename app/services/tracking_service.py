"""
Tracking Service
Handles object tracking and monitoring
"""
import time
import threading
from datetime import datetime
from config import Config
import app.state as state

def add_to_tracking(detection):
    """
    Add detected object to tracking list
    
    Args:
        detection: Object detection data
        
    Returns:
        Created tracking item
    """
    # Check if already tracked to prevent duplicates (using bbox proximity)
    if state.is_object_already_tracked(
        detection.get('label'), 
        detection.get('class_id'),
        detection.get('bbox'),
        proximity_threshold=25  # Tighter threshold for better separation
    ):
        return None
        
    tracking_item = {
        'id': f"track_{len(state.tracked_items)}_{int(time.time())}",
        'label': detection.get('label', 'unknown'),
        'confidence': detection.get('confidence', 0),
        'class_id': detection.get('class_id', -1),
        'bbox': detection.get('bbox', {}),
        'added_at': datetime.now().isoformat(),
        'last_seen': datetime.now().isoformat(),
        'is_present': True,
        'alarm_enabled': True,  # Enable alarm by default
        'missing_count': 0  # Initialize missing count for hysteresis
    }
    
    state.tracked_items.append(tracking_item)
    return tracking_item

def remove_from_tracking(item_id):
    """Remove object from tracking list"""
    state.tracked_items[:] = [item for item in state.tracked_items if item['id'] != item_id]

def clear_tracking():
    """Clear all tracked items"""
    state.tracked_items.clear()
    state.tracking_active = False
    state.alarm_active = False

def refresh_detection_tracking_status(socketio):
    """
    Refresh the tracking status of current detections and emit update
    
    Args:
        socketio: SocketIO instance for emitting events
    """
    if state.latest_detections:
        # Update tracking status for all current detections
        enhanced_detections = []
        for detection in state.latest_detections:
            enhanced_detection = detection.copy()
            enhanced_detection['is_tracked'] = state.is_object_already_tracked(
                detection['label'], 
                detection.get('class_id')
            )
            enhanced_detections.append(enhanced_detection)
        
        state.latest_detections = enhanced_detections
        
        # Emit updated detections to frontend
        socketio.emit('detection_tracking_update', {
            'detections': enhanced_detections,
            'timestamp': datetime.now().isoformat()
        })

def check_tracked_items(socketio):
    """
    Continuously check if tracked items are still present
    
    Args:
        socketio: SocketIO instance for emitting events
    """
    print(f"🔍 Started tracking monitor (checking every {state.tracking_interval}s)")
    print(f"📋 Debug: tracking_active={state.tracking_active}, tracked_items={len(state.tracked_items)}")
    
    while state.tracking_active:
        print(f"🔄 Loop iteration: tracking_active={state.tracking_active}, latest_detections={len(state.latest_detections) if state.latest_detections else 0}, tracked_items={len(state.tracked_items)}")
        
        if not state.tracked_items:
            print(f"⏳ No items to track - skipping")
            time.sleep(state.tracking_interval)
            continue
            
        try:
            print(f"📊 Checking {len(state.tracked_items)} tracked items against {len(state.latest_detections)} detections")
            
            # Check each tracked item
            current_missing = []
            for tracked_item in state.tracked_items:
                item_found = False
                best_match = None
                best_distance = float('inf')
                
                # Look for similar objects in current detections (if any)
                if state.latest_detections:
                    for detection in state.latest_detections:
                        if detection['label'] == tracked_item['label']:
                            # Use lower threshold for tracking (more lenient for already tracked items)
                            tracking_threshold = 0.3  # Lower than detection threshold for better continuity
                            if detection['confidence'] > tracking_threshold:
                                # Calculate bbox proximity for better matching
                                distance = state.calculate_bbox_distance(
                                    tracked_item.get('bbox', {}), 
                                    detection.get('bbox', {})
                                )
                                overlap_ratio = state.calculate_bbox_overlap_ratio(
                                    tracked_item.get('bbox', {}), 
                                    detection.get('bbox', {})
                                )
                                
                                # Consider it a match if close enough or overlapping
                                if distance <= 100 or overlap_ratio > 0.2:  # More lenient for tracking
                                    if distance < best_distance:
                                        best_distance = distance
                                        best_match = detection
                
                if best_match:
                    item_found = True
                    tracked_item['last_seen'] = datetime.now().isoformat()
                    tracked_item['is_present'] = True
                    tracked_item['bbox'] = best_match.get('bbox', {})  # Update bbox position
                    print(f"✅ Found: {tracked_item['label']} (confidence: {best_match['confidence']:.2f}, distance: {best_distance:.1f}px)")
                    tracked_item['missing_count'] = 0
                
                if not item_found:
                    # Increment missing count for hysteresis
                    missing_count = tracked_item.get('missing_count', 0) + 1
                    tracked_item['missing_count'] = missing_count
                    
                    # Only mark as missing after multiple consecutive failures
                    if missing_count >= 2:  # Require 2 consecutive misses before marking as not present
                        tracked_item['is_present'] = False
                        print(f"❌ {tracked_item['label']} confirmed missing after {missing_count} checks")
                        
                        # Check if missing for more than threshold intervals AND alarm is enabled
                        if tracked_item.get('alarm_enabled', True):
                            last_seen = datetime.fromisoformat(tracked_item['last_seen'])
                            threshold_seconds = state.tracking_interval * Config.MISSING_ITEM_THRESHOLD_MULTIPLIER
                            time_missing = (datetime.now() - last_seen).total_seconds()
                            print(f"⏰ {tracked_item['label']} missing for {time_missing:.1f}s (threshold: {threshold_seconds}s)")
                            if time_missing > threshold_seconds:
                                current_missing.append(tracked_item)
                                print(f"❌ Missing: {tracked_item['label']}")
                            else:
                                print(f"⚠️ Temporary loss: {tracked_item['label']}")
                        else:
                            print(f"🔇 {tracked_item['label']} missing but alarm disabled")
                    else:
                        print(f"🔍 {tracked_item['label']} not found (attempt {missing_count}/2)")
            
            # Update missing items
            state.missing_items = current_missing
            
            # Trigger alarm if items missing
            if state.missing_items and not state.alarm_active:
                state.alarm_active = True
                print(f"🚨 ALARM TRIGGERED: {len(state.missing_items)} items missing!")
                socketio.emit('alarm_triggered', {
                    'missing_items': state.missing_items,
                    'timestamp': datetime.now().isoformat()
                })
            elif not state.missing_items and state.alarm_active:
                state.alarm_active = False
                print("✅ All items found - alarm cleared")
                socketio.emit('alarm_cleared', {
                    'timestamp': datetime.now().isoformat()
                })
                    
        except Exception as e:
            print(f"❌ Error checking tracked items: {e}")
        
        time.sleep(state.tracking_interval)
    
    print("🛑 Tracking monitor stopped")

def start_tracking(socketio):
    """Start active tracking"""
    if not state.tracked_items:
        return False, 'No items to track'
    
    if state.tracking_active:
        return False, 'Tracking already active'
    
    state.tracking_active = True
    
    # Start monitoring thread
    if state.tracking_thread is None or not state.tracking_thread.is_alive():
        state.tracking_thread = threading.Thread(
            target=check_tracked_items,
            args=(socketio,),
            daemon=True
        )
        state.tracking_thread.start()
    
    return True, f'Tracking started (checking every {state.tracking_interval}s)'

def stop_tracking():
    """Stop active tracking"""
    state.tracking_active = False
    state.alarm_active = False

def set_tracking_interval(new_interval):
    """Set tracking check interval"""
    if not isinstance(new_interval, int) or new_interval < Config.MIN_TRACKING_INTERVAL or new_interval > Config.MAX_TRACKING_INTERVAL:
        return False, f'Interval must be between {Config.MIN_TRACKING_INTERVAL}-{Config.MAX_TRACKING_INTERVAL} seconds'
    
    state.tracking_interval = new_interval
    print(f"⏱️ Tracking interval changed to {state.tracking_interval} seconds")
    return True, f'Tracking interval set to {state.tracking_interval} seconds'

def acknowledge_alarm(socketio):
    """Acknowledge the alarm (disable alarms for currently missing items)"""
    # Disable alarms for all currently missing items
    for item in state.missing_items:
        # Find the item in tracked_items and disable its alarm
        for tracked_item in state.tracked_items:
            if tracked_item['id'] == item['id']:
                tracked_item['alarm_enabled'] = False
                print(f"🔇 Disabled alarm for: {tracked_item['label']}")
                break
    
    state.alarm_active = False
    state.missing_items = []  # Clear missing items list
    
    # Notify frontend that alarm was acknowledged
    socketio.emit('alarm_acknowledged', {
        'timestamp': datetime.now().isoformat()
    })
    
    print("✅ Alarm acknowledged - disabled alarms for missing items")