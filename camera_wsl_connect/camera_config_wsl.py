"""
Camera Application Configuration (WSL/Ubuntu-friendly)
"""
import os
from dotenv import load_dotenv

load_dotenv()

def _as_bool(val: str, default: bool) -> bool:
    if val is None:
        return default
    return str(val).strip().lower() in ("1", "true", "yes", "on")

class CameraConfig:
    # ====== Web socket / server ======
    WEBAPP_URL = os.getenv("WEBAPP_URL", "http://localhost:5000")

    # ====== Camera selection (WSL) ======
    # WSL’de doğru cihazı biliyoruz: /dev/video0 → CAMERA_INDEX=0
    CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))
    # Otomatik tarama WSL’de genelde gereksiz; istersen açıp /dev/video* tararız.
    ENABLE_AUTO_CAMERA_DETECTION = _as_bool(os.getenv("ENABLE_AUTO_CAMERA_DETECTION", "False"), False)
    # Not: PREFERRED_CAMERAS Windows için anlamlıydı; Linux tarafında kullanılmıyor.
    PREFERRED_CAMERAS = [0]  # geriye uyumluluk için bırakıyoruz, kullanılmıyor

    # ====== Capture / Stream ======
    # WSL’de en stabil başlangıç: 640x480 @ 15 FPS + MJPG
    DEFAULT_CAMERA_WIDTH  = int(os.getenv("DEFAULT_CAMERA_WIDTH",  "640"))
    DEFAULT_CAMERA_HEIGHT = int(os.getenv("DEFAULT_CAMERA_HEIGHT", "480"))
    DEFAULT_CAMERA_FPS    = int(os.getenv("DEFAULT_CAMERA_FPS",    "15"))
    JPEG_QUALITY          = int(os.getenv("JPEG_QUALITY",          "80"))
    STREAM_FPS            = int(os.getenv("STREAM_FPS",            "15"))
    FRAME_SKIP_COUNT      = int(os.getenv("FRAME_SKIP_COUNT",      "1"))

    # (Opsiyonel) FOURCC tercih sıranı .env’den verebilmek için:
    # Örn: FOURCC_ORDER="MJPG,YUYV"
    FOURCC_ORDER = tuple(
        [c.strip() for c in os.getenv("FOURCC_ORDER", "MJPG,YUYV").split(",") if c.strip()]
    )

    # ====== Reconnect / Resilience ======
    RECONNECT_DELAY         = int(os.getenv("RECONNECT_DELAY",         "5"))
    MAX_RECONNECT_ATTEMPTS  = int(os.getenv("MAX_RECONNECT_ATTEMPTS",  "10"))

    # ====== Logging ======
    LOG_LEVEL           = os.getenv("LOG_LEVEL", "INFO")
    ENABLE_DEBUG_OUTPUT = _as_bool(os.getenv("ENABLE_DEBUG_OUTPUT", "True"), True)
