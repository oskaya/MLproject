"""
Main Application Entry Point
Guard Vision V2 - Advanced Security Monitoring System
"""
import os

# Allow insecure transport for development (must be set before importing OAuth libraries)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

from webapp_config import WebAppConfig
from app import create_app
from app.handlers.socket_handlers import register_handlers

def main():
    """Main application function"""
    # Create app and socketio instances
    app, socketio = create_app()
    
    # Register socket handlers
    register_handlers(socketio)
    
    # Debug: Print all routes
    print("🔧 Available routes:")
    for rule in app.url_map.iter_rules():
        print(f"   {rule.rule} -> {rule.endpoint}")
    
    # Print startup information
    print("🚀 Starting Guard Vision V2...")
    print(f"📡 ML API URL: {WebAppConfig.ML_API_URL}")
    print(f"🌐 Server: http://{WebAppConfig.FLASK_HOST}:{WebAppConfig.FLASK_PORT}")
    
    # Run the application
    socketio.run(
        app, 
        host=WebAppConfig.FLASK_HOST, 
        port=WebAppConfig.FLASK_PORT, 
        debug=WebAppConfig.FLASK_DEBUG
    )

if __name__ == '__main__':
    main()