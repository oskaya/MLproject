"""
Web Application Configuration
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Allow insecure transport for development
if os.getenv('FLASK_ENV') == 'development':
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

class WebAppConfig:
    # ML API Configuration
    ML_API_URL = os.getenv('ML_API_URL', 'http://localhost:8000/predict')
    ML_API_TIMEOUT = int(os.getenv('ML_API_TIMEOUT', '10'))
    
    # Detection Configuration
    AUTO_DETECTION_INTERVAL = 5  # seconds
    DETECTION_CONFIDENCE_THRESHOLD = 0.3  # Lower threshold for better tracking of already tracked items
    
    # Tracking Configuration
    DEFAULT_TRACKING_INTERVAL = 5  # seconds
    MIN_TRACKING_INTERVAL = 1
    MAX_TRACKING_INTERVAL = 60
    MISSING_ITEM_THRESHOLD_MULTIPLIER = 2  # intervals
    
    # Flask Configuration
    FLASK_HOST = '0.0.0.0'
    FLASK_PORT = 5000
    FLASK_DEBUG = True
    
    # SocketIO Configuration
    SOCKETIO_CORS_ALLOWED_ORIGINS = "*"
    
    # Authentication Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # GitHub OAuth Configuration
    GITHUB_CLIENT_ID = os.getenv('GITHUB_CLIENT_ID')
    GITHUB_CLIENT_SECRET = os.getenv('GITHUB_CLIENT_SECRET') 
    GITHUB_OAUTH_SCOPE = 'user:email'  # Using public organization membership instead of read:org
    
    # Organization Authorization
    #ALLOWED_GITHUB_ORG = os.getenv('ALLOWED_GITHUB_ORG', 'InfoTech-Academy')
    
    # Username Whitelist (alternative to organization check)
    ALLOWED_GITHUB_USERS = os.getenv('ALLOWED_GITHUB_USERS', 'oskaya,ErsinOzturk10,SemaIstek').split(',')  # Comma separated usernames
    
    # Session Configuration
    SESSION_TIMEOUT_HOURS = 24  # hours
    PERMANENT_SESSION_LIFETIME = SESSION_TIMEOUT_HOURS * 3600  # seconds
    
    # Camera Display Configuration (for web interface)
    DEFAULT_CAMERA_WIDTH = 640
    DEFAULT_CAMERA_HEIGHT = 480
    JPEG_QUALITY = 80