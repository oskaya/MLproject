"""
Camera Application - Connects to web app and sends frames (WSL/Ubuntu V4L2-ready)
"""
import cv2
import socketio
import base64
import time
import threading
import traceback
import glob
import os

from camera_config import CameraConfig

# ----- Linux/WSL sabitleri -----
LINUX_BACKEND = cv2.CAP_V4L2
FOURCC_TRY_ORDER = ("MJPG", "YUYV")  # Önce MJPG, olmazsa YUYV dene


def open_camera_linux_v4l2(dev_index: int, width: int, height: int, fps: int, fourcc_order=("MJPG", "YUYV")):
    """WSL/Ubuntu için V4L2 backend ile güvenli kamera açma.
       Başarılıysa (cap, fourcc) döner; aksi halde (None, None).
    """
    if not os.path.exists(f"/dev/video{dev_index}"):
        return None, None

    for fourcc in fourcc_order:
        cap = cv2.VideoCapture(dev_index, LINUX_BACKEND)
        if not cap.isOpened():
            try:
                cap.release()
            except Exception:
                pass
            continue

        # Sıra önemli: önce FOURCC, sonra çözünürlük/FPS
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*fourcc))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(width))
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(height))
        cap.set(cv2.CAP_PROP_FPS, int(fps))
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        ok, _ = cap.read()
        if ok:
            return cap, fourcc

        try:
            cap.release()
        except Exception:
            pass

    return None, None


def list_v4l2_indices():
    """Gerçek /dev/video* cihaz indekslerini döndürür (artarak)."""
    devs = []
    for p in glob.glob("/dev/video*"):
        name = os.path.basename(p)
        if name.startswith("video"):
            try:
                devs.append(int(name.replace("video", "")))
            except Exception:
                pass
    return sorted(devs)


class CameraApp:
    def __init__(self, webapp_url=None):
        self.webapp_url = webapp_url or CameraConfig.WEBAPP_URL
        self.sio = socketio.Client(
            reconnection=True,
            reconnection_attempts=getattr(CameraConfig, "MAX_RECONNECT_ATTEMPTS", 10),
            reconnection_delay=getattr(CameraConfig, "RECONNECT_DELAY", 5),
        )
        self.camera = None
        self.is_running = False
        self.camera_index = int(CameraConfig.CAMERA_INDEX)
        self.enable_auto_detection = bool(CameraConfig.ENABLE_AUTO_CAMERA_DETECTION)
        self.frame_skip_count = int(getattr(CameraConfig, "FRAME_SKIP_COUNT", 1))
        self._stop_event = threading.Event()
        self._selected_fourcc = None
        self.setup_events()

    # ---- Camera helpers (Linux/WSL) ----
    def find_available_camera(self):
        # 1) .env'deki index
        print(f"🔍 Testing /dev/video{self.camera_index} with V4L2...")
        test, fourcc = open_camera_linux_v4l2(
            dev_index=self.camera_index,
            width=CameraConfig.DEFAULT_CAMERA_WIDTH,
            height=CameraConfig.DEFAULT_CAMERA_HEIGHT,
            fps=CameraConfig.DEFAULT_CAMERA_FPS,
        )
        if test:
            test.release()
            self._selected_fourcc = fourcc
            print(f"✅ Found working camera at index {self.camera_index} (FOURCC={fourcc})")
            return self.camera_index, fourcc

        print(f"❌ Configured camera index {self.camera_index} not available with V4L2")

        # 2) (Opsiyonel) Auto-detect
        if self.enable_auto_detection:
            indices = list_v4l2_indices()
            print(f"🔄 Scanning V4L2 devices: {indices}")
            for idx in indices:
                if idx == self.camera_index:
                    continue
                test, fourcc = open_camera_linux_v4l2(
                    dev_index=idx,
                    width=CameraConfig.DEFAULT_CAMERA_WIDTH,
                    height=CameraConfig.DEFAULT_CAMERA_HEIGHT,
                    fps=CameraConfig.DEFAULT_CAMERA_FPS,
                )
                if test:
                    test.release()
                    self._selected_fourcc = fourcc
                    print(f"✅ Found working fallback camera at index {idx} (FOURCC={fourcc})")
                    return idx, fourcc
            print("❌ No fallback cameras available")
        else:
            print("⚠️ Auto-detection disabled - only using configured camera index")

        return None, None

    # ---- Socket.IO events ----
    def setup_events(self):
        @self.sio.event
        def connect():
            print("✅ Connected to web app")
            self.sio.emit('camera_connect', {'camera_id': 'external_cam'})

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
            action = (data or {}).get('action')
            if action == 'start':
                self.start_camera()
            elif action == 'stop':
                self.stop_camera()

    # ---- Connection ----
    def connect(self):
        try:
            print(f"🔄 Attempting to connect to {self.webapp_url}...")
            self.sio.connect(self.webapp_url, transports=['websocket', 'polling'])
            return True
        except Exception as e:
            print(f"❌ Failed to connect: {e}")
            traceback.print_exc()
            return False

    # ---- Camera start/stop ----
    def start_camera(self):
        if self.is_running:
            print("⚠️  Camera already running")
            return

        print("🔄 Starting camera...")
        idx, fourcc = self.find_available_camera()
        if idx is None:
            print("❌ No cameras available")
            self.sio.emit('camera_error', {'message': 'No cameras available'})
            return

        # Aynı FOURCC ile gerçekten aç
        self.camera, _ = open_camera_linux_v4l2(
            dev_index=idx,
            width=CameraConfig.DEFAULT_CAMERA_WIDTH,
            height=CameraConfig.DEFAULT_CAMERA_HEIGHT,
            fps=CameraConfig.DEFAULT_CAMERA_FPS,
            fourcc_order=(fourcc,),  # önce bulunanı zorla
        )
        if not self.camera or not self.camera.isOpened():
            print(f"❌ Failed to open camera {idx}")
            self.sio.emit('camera_error', {'message': f'Failed to open camera {idx}'})
            return

        self._selected_fourcc = fourcc
        print(f"ℹ️ Using FOURCC: {fourcc}")

        # Test frame
        ret, test_frame = self.camera.read()
        if not ret or test_frame is None:
            print("❌ Cannot read from camera")
            try:
                self.camera.release()
            except Exception:
                pass
            self.camera = None
            self.sio.emit('camera_error', {'message': 'Cannot read from camera'})
            return

        self.is_running = True
        self._stop_event.clear()
        threading.Thread(target=self._capture_loop, daemon=True).start()
        print(f"✅ Camera started successfully on index {idx}")

        self.sio.emit('camera_ready', {
            'camera_index': idx,
            'resolution': f"{test_frame.shape[1]}x{test_frame.shape[0]}",
            'fps': CameraConfig.STREAM_FPS,
            'fourcc': fourcc
        })

    def stop_camera(self):
        if not self.is_running:
            print("⚠️  Camera already stopped")
            return

        print("🔄 Stopping camera...")
        self.is_running = False
        self._stop_event.set()
        if self.camera:
            try:
                self.camera.release()
            except Exception:
                pass
            self.camera = None
        print("⏹️  Camera stopped")
        self.sio.emit('camera_stopped', {})

    # ---- Capture loop ----
    def _capture_loop(self):
        frame_count = 0
        sent_in_window = 0
        window_start = time.time()

        try:
            while self.is_running and self.camera and not self._stop_event.is_set():
                ret, frame = self.camera.read()
                if not ret or frame is None:
                    print("⚠️  Failed to read frame")
                    time.sleep(0.05)
                    continue

                frame_count += 1

                # İstenirse frame skip
                if self.frame_skip_count > 1 and (frame_count % self.frame_skip_count) != 0:
                    time.sleep(1.0 / max(1, CameraConfig.STREAM_FPS))
                    continue

                # Gerekirse boyutla
                if (frame.shape[1] != CameraConfig.DEFAULT_CAMERA_WIDTH) or (frame.shape[0] != CameraConfig.DEFAULT_CAMERA_HEIGHT):
                    frame = cv2.resize(frame, (CameraConfig.DEFAULT_CAMERA_WIDTH, CameraConfig.DEFAULT_CAMERA_HEIGHT))

                # JPEG encode
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), CameraConfig.JPEG_QUALITY]
                ok, buffer = cv2.imencode('.jpg', frame, encode_param)
                if not ok:
                    print("⚠️  JPEG encode failed")
                    time.sleep(0.01)
                    continue

                frame_b64 = base64.b64encode(buffer).decode('utf-8')

                # Emit frame
                self.sio.emit('frame_data', {
                    'frame': frame_b64,
                    'timestamp': time.time()
                })
                sent_in_window += 1

                # 5 sn'de bir FPS raporu
                now = time.time()
                if now - window_start >= 5.0:
                    fps = sent_in_window / (now - window_start)
                    print(f"📸 Streaming at {fps:.1f} FPS ({sent_in_window} frames in {now - window_start:.1f}s)")
                    window_start = now
                    sent_in_window = 0

                # Pace
                time.sleep(1.0 / max(1, CameraConfig.STREAM_FPS))
        except Exception as e:
            print(f"❌ Capture loop crashed: {e}")
            traceback.print_exc()
            self.sio.emit('camera_error', {'message': f'Capture loop crashed: {e}'})
            self.stop_camera()

    # ---- Run ----
    def run(self):
        if self.connect():
            print("🎯 Camera app ready. Use web interface to start/stop camera.")
            print("Press Ctrl+C to stop.")
            try:
                self.sio.wait()
            except KeyboardInterrupt:
                print("\n🛑 Shutting down...")
                self.stop_camera()
                try:
                    self.sio.disconnect()
                except Exception:
                    pass
        else:
            print("❌ Failed to start camera app")


if __name__ == '__main__':
    print("🚀 Starting Camera Application (WSL/Ubuntu V4L2)...")
    app = CameraApp()
    app.run()
