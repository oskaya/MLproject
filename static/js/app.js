// Object Tracking System JavaScript

// Initialize socket connection and global variables
const socket = io();
let isTracking = false;
let trackingInterval = 5;
let lastDetections = [];

// =============================================================================
// Socket Event Handlers
// =============================================================================

// Socket events for camera status
socket.on('camera_status', function(data) {
    console.log('📹 Camera status update:', data);
    updateCameraStatus(data.connected, data.streaming);
    if (data.error) {
        alert('Camera Error: ' + data.error);
    }
});

// Live frame updates
socket.on('live_frame', function(data) {
    console.log('📺 Received live frame');
    const liveFrame = document.getElementById('liveFrame');
    const noCamera = document.getElementById('noCamera');
    const detectionInfo = document.getElementById('detectionInfo');
    
    if (data.frame) {
        liveFrame.src = 'data:image/jpeg;base64,' + data.frame;
        liveFrame.style.display = 'block';
        noCamera.style.display = 'none';
        detectionInfo.style.display = 'block';
        
        // Update stream status
        document.getElementById('detectionStatus').textContent = 'Live Stream';
    }
});

// Auto-detection results every 5 seconds
socket.on('auto_detection_result', function(data) {
    console.log('🤖 Auto-detection result:', data);
    lastDetections = data.detections;
    updateDetectionOverlays(data.detections);
    updateCurrentDetections(data.detections);
    
    // Update detection info
    document.getElementById('detectionStatus').textContent = 'Auto-detecting';
    document.getElementById('detectionCount').textContent = data.detections.length;
    document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
});

// Alarm events
socket.on('alarm_triggered', function(data) {
    showAlarm(data.missing_items);
    playAlarmSound();
});

socket.on('alarm_cleared', function(data) {
    console.log('✅ Alarm cleared:', data.reason || 'manual');
    hideAlarm();
});

// Alarm acknowledged event
socket.on('alarm_acknowledged', function(data) {
    console.log('✅ Alarm acknowledged by user');
    hideAlarm();
});

// Detection tracking status update
socket.on('detection_tracking_update', function(data) {
    console.log('🔄 Detection tracking status updated');
    lastDetections = data.detections;
    updateCurrentDetections(data.detections);
});

// Connection debug
socket.on('connect', function() {
    console.log('🔌 Connected to web app');
});

socket.on('disconnect', function() {
    console.log('🔌 Disconnected from web app');
});

// =============================================================================
// Detection and Overlay Functions
// =============================================================================

// Update detection overlays on live frame
function updateDetectionOverlays(detections) {
    const overlay = document.getElementById('videoOverlay');
    const liveFrame = document.getElementById('liveFrame');
    
    // Clear existing overlays
    overlay.innerHTML = '';
    
    if (!detections || detections.length === 0) return;
    
    // Wait for image to load to get correct dimensions
    const updateOverlays = () => {
        const scaleX = liveFrame.offsetWidth / 640;
        const scaleY = liveFrame.offsetHeight / 480;
        
        detections.forEach((detection, index) => {
            const bbox = detection.bbox;
            
            // Create bounding box
            const boxDiv = document.createElement('div');
            boxDiv.className = 'detection-bbox';
            boxDiv.style.left = (bbox.x1 * scaleX) + 'px';
            boxDiv.style.top = (bbox.y1 * scaleY) + 'px';
            boxDiv.style.width = ((bbox.x2 - bbox.x1) * scaleX) + 'px';
            boxDiv.style.height = ((bbox.y2 - bbox.y1) * scaleY) + 'px';
            
            // Create label
            const labelDiv = document.createElement('div');
            labelDiv.className = 'detection-label';
            labelDiv.textContent = `${detection.label} (${(detection.confidence * 100).toFixed(1)}%)`;
            
            boxDiv.appendChild(labelDiv);
            overlay.appendChild(boxDiv);
        });
    };

    if (liveFrame.complete && liveFrame.offsetWidth > 0) {
        updateOverlays();
    } else {
        liveFrame.onload = updateOverlays;
    }
}

// Update current detections list
function updateCurrentDetections(detections) {
    const container = document.getElementById('currentDetections');
    
    if (!detections || detections.length === 0) {
        container.innerHTML = '<p>No objects detected in current frame.</p>';
        return;
    }
    
    container.innerHTML = `
        <p><strong>${detections.length} objects detected:</strong></p>
        ${detections.map(detection => {
            // Create track button HTML based on tracking status
            let trackButtonHtml = '';
            if (detection.is_tracked) {
                trackButtonHtml = '<span class="btn btn-success" style="opacity: 0.6; cursor: not-allowed;">Already Tracked ✓</span>';
            } else {
                trackButtonHtml = `<button class="btn btn-primary" onclick="addToTracking(${JSON.stringify(detection).replace(/"/g, '&quot;')})">Track This</button>`;
            }
            
            return `
                <div class="detection-item ${detection.is_tracked ? 'already-tracked' : ''}">
                    <div class="item-info">
                        <div class="item-label">
                            ${detection.label}
                            <span class="confidence">${(detection.confidence * 100).toFixed(1)}%</span>
                            ${detection.is_tracked ? '<span class="tracking-indicator">🔍 Tracked</span>' : ''}
                        </div>
                        <div class="item-details">
                            Class ID: ${detection.class_id} • 
                            BBox: (${detection.bbox.x1.toFixed(0)}, ${detection.bbox.y1.toFixed(0)}) - 
                            (${detection.bbox.x2.toFixed(0)}, ${detection.bbox.y2.toFixed(0)})
                        </div>
                    </div>
                    ${trackButtonHtml}
                </div>
            `;
        }).join('')}
    `;
}

// =============================================================================
// Camera Functions
// =============================================================================

// Update camera status
function updateCameraStatus(connected, streaming = false) {
    const statusEl = document.getElementById('cameraStatus');
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    const liveFrame = document.getElementById('liveFrame');
    const noCamera = document.getElementById('noCamera');
    const detectionInfo = document.getElementById('detectionInfo');
    
    if (connected && streaming) {
        statusEl.className = 'status status-connected';
        statusEl.textContent = '📷 Camera: Connected & Streaming (Auto-Detection Active)';
        startBtn.disabled = true;
        stopBtn.disabled = false;
    } else if (connected) {
        statusEl.className = 'status status-connected';
        statusEl.textContent = '📷 Camera: Connected (Not Streaming)';
        startBtn.disabled = false;
        stopBtn.disabled = false;
        liveFrame.style.display = 'none';
        noCamera.style.display = 'block';
        detectionInfo.style.display = 'none';
    } else {
        statusEl.className = 'status status-disconnected';
        statusEl.textContent = '📷 Camera: Disconnected';
        startBtn.disabled = true;
        stopBtn.disabled = true;
        liveFrame.style.display = 'none';
        noCamera.style.display = 'block';
        detectionInfo.style.display = 'none';
    }
}

// Camera control functions
async function startCamera() {
    try {
        const response = await fetch('/api/camera/start', { method: 'POST' });
        const data = await response.json();
        if (!data.success) alert(data.message);
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

async function stopCamera() {
    try {
        const response = await fetch('/api/camera/stop', { method: 'POST' });
        const data = await response.json();
        if (!data.success) alert(data.message);
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

// =============================================================================
// Tracking Functions
// =============================================================================

// Interval control functions
async function changeInterval(delta) {
    const newInterval = trackingInterval + delta;
    if (newInterval < 1 || newInterval > 60) {
        alert('Interval must be between 1-60 seconds');
        return;
    }
    
    try {
        const response = await fetch('/api/tracking/interval', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ interval: newInterval })
        });
        
        const data = await response.json();
        if (data.success) {
            trackingInterval = newInterval;
            document.getElementById('intervalDisplay').textContent = `${trackingInterval} seconds`;
        } else {
            alert(data.message);
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

// Add object to tracking
async function addToTracking(detection) {
    // Check if already tracked (client-side check)
    if (detection.is_tracked) {
        alert('This object is already being tracked!');
        return;
    }
    
    try {
        const response = await fetch('/api/tracking/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ detection })
        });
        
        const data = await response.json();
        if (data.success) {
            console.log('✅ Object added to tracking:', data.item);
            updateTrackingStatus();
            // Note: Detection list will be updated automatically via socket event
        } else {
            alert(data.message);
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

// Toggle tracking on/off
async function toggleTracking() {
    try {
        const action = isTracking ? 'stop' : 'start';
        const response = await fetch(`/api/tracking/${action}`, { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            updateTrackingStatus();
        } else {
            alert(data.message);
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

// Clear all tracking
async function clearTracking() {
    if (confirm('Clear all tracked items?')) {
        try {
            const response = await fetch('/api/tracking/clear', { method: 'POST' });
            const data = await response.json();
            
            if (data.success) {
                updateTrackingStatus();
            }
        } catch (error) {
            alert('Error: ' + error.message);
        }
    }
}

// Update tracking status display
async function updateTrackingStatus() {
    try {
        const response = await fetch('/api/tracking/status');
        const data = await response.json();
        
        const container = document.getElementById('trackedItems');
        const trackingBtn = document.getElementById('trackingBtn');
        
        // Update interval display
        trackingInterval = data.tracking_interval;
        document.getElementById('intervalDisplay').textContent = `${trackingInterval} seconds`;
        
        // Show status
        let statusHtml = '';
        if (data.tracking_active) {
            if (data.alarm_active) {
                statusHtml = '<div style="color: red; font-weight: bold;">🚨 ALARM ACTIVE - Items Missing!</div>';
            } else {
                statusHtml = `<div style="color: green; font-weight: bold;">✅ Tracking Active (checking every ${data.tracking_interval}s)</div>`;
            }
        }
        
        if (data.tracked_items.length === 0) {
            container.innerHTML = statusHtml + 'No items being tracked.';
            trackingBtn.disabled = true;
        } else {
            container.innerHTML = statusHtml + `
                <p><strong>${data.count} items being tracked:</strong></p>
                ${data.tracked_items.map(item => `
                    <div class="tracked-item" style="${!item.is_present ? 'border-left: 4px solid red;' : ''}">
                        <div class="item-info">
                            <div class="item-label">
                                ${item.label} ${!item.is_present ? '❌ MISSING' : '✅'}
                            </div>
                            <div class="item-details">
                                Added: ${new Date(item.added_at).toLocaleTimeString()} • 
                                Confidence: ${(item.confidence * 100).toFixed(1)}%
                                ${!item.is_present ? `<br><strong>Last seen: ${new Date(item.last_seen).toLocaleTimeString()}</strong>` : ''}
                            </div>
                        </div>
                        <button class="btn btn-danger" onclick="removeFromTracking('${item.id}')">
                            Remove
                        </button>
                    </div>
                `).join('')}
            `;
            trackingBtn.disabled = false;
        }
        
        isTracking = data.tracking_active;
        document.getElementById('trackingBtn').textContent = 
            isTracking ? 'Stop Tracking' : 'Start Tracking';
        document.getElementById('trackingBtn').className = 
            `btn ${isTracking ? 'btn-danger' : 'btn-success'}`;
            
    } catch (error) {
        console.error('Error updating tracking status:', error);
    }
}

// Remove item from tracking
async function removeFromTracking(itemId) {
    try {
        const response = await fetch('/api/tracking/remove', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ item_id: itemId })
        });
        
        if (response.ok) {
            updateTrackingStatus();
        }
    } catch (error) {
        alert('Error: ' + error.message);
    }
}

// =============================================================================
// Alarm Functions
// =============================================================================

// Show alarm panel
function showAlarm(missingItems) {
    const alarmPanel = document.getElementById('alarmPanel');
    const missingList = document.getElementById('missingItemsList');
    
    alarmPanel.className = 'alarm-panel alarm-active';
    
    missingList.innerHTML = missingItems.map(item => `
        <div class="missing-item">
            <strong>${item.label}</strong> - Last seen: ${new Date(item.last_seen).toLocaleTimeString()}
        </div>
    `).join('');
}

// Hide alarm panel
function hideAlarm() {
    const alarmPanel = document.getElementById('alarmPanel');
    alarmPanel.className = 'alarm-panel';
}

// Acknowledge alarm
async function acknowledgeAlarm() {
    try {
        console.log('🔕 Acknowledging alarm...');
        const response = await fetch('/api/tracking/alarm/acknowledge', { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            console.log('✅ Alarm acknowledged successfully');
            // Don't hide alarm here - let the socket event handle it
        } else {
            console.error('❌ Failed to acknowledge alarm:', data.message);
            alert('Failed to acknowledge alarm: ' + data.message);
        }
    } catch (error) {
        console.error('❌ Error acknowledging alarm:', error);
        alert('Error acknowledging alarm: ' + error.message);
    }
}

// Play alarm sound
function playAlarmSound() {
    try {
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        oscillator.frequency.value = 800;
        oscillator.type = 'square';
        
        gainNode.gain.setValueAtTime(0, audioContext.currentTime);
        gainNode.gain.linearRampToValueAtTime(0.3, audioContext.currentTime + 0.01);
        gainNode.gain.exponentialRampToValueAtTime(0.001, audioContext.currentTime + 0.3);
        
        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.3);
    } catch (error) {
        console.log('Audio not available');
    }
}

// =============================================================================
// Initialization
// =============================================================================

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    updateTrackingStatus();
    setInterval(updateTrackingStatus, 5000);
});