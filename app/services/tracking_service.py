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
    tracking_item = {
        'id': f"track_{len(state.tracked_items)}_{int(time.time())}",
        'label': detection.get('label', 'unknown'),
        'confidence': detection.get('confidence', 0),
        'class_id': detection.get('class_id', -1),
        'bbox': detection.get('bbox', {}),
        'added_at': datetime.now().isoformat(),
        'last_seen': datetime.now().isoformat(),
        'is_present': True
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

def check_tracked_items(socketio):
    """
    Continuously check if tracked items are still present
    
    Args:
        socketio: SocketIO instance for emitting events
    """
    print(f"🔍 Started tracking monitor (checking every {state.tracking_interval}s)")
    
    while state.tracking_active:
        if not state.latest_detections or not state.tracked_items:
            time.sleep(state.tracking_interval)
            continue
            
        try:
            print(f"📊 Checking {len(state.tracked_items)} tracked items against {len(state.latest_detections)} detections")
            
            # Check each tracked item
            current_missing = []
            for tracked_item in state.tracked_items:
                item_found = False
                
                # Look for similar objects in current detections
                for detection in state.latest_detections:
                    if detection['label'] == tracked_item['label']:
                        # Use config confidence threshold
                        if detection['confidence'] > Config.DETECTION_CONFIDENCE_THRESHOLD:
                            item_found = True
                            tracked_item['last_seen'] = datetime.now().isoformat()
                            tracked_item['is_present'] = True
                            break
                
                if not item_found:
                    tracked_item['is_present'] = False
                    # Check if missing for more than threshold intervals
                    last_seen = datetime.fromisoformat(tracked_item['last_seen'])
                    threshold_seconds = state.tracking_interval * Config.MISSING_ITEM_THRESHOLD_MULTIPLIER
                    if (datetime.now() - last_seen).total_seconds() > threshold_seconds:
                        current_missing.append(tracked_item)
                        print(f"❌ Missing: {tracked_item['label']}")
                    else:
                        print(f"⚠️ Temporary loss: {tracked_item['label']}")
                else:
                    print(f"✅ Found: {tracked_item['label']}")
            
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

def acknowledge_alarm():
    """Acknowledge the alarm (silence it but keep tracking)"""
    state.alarm_active = False