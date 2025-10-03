"""
Main Application Entry Point
Modular Object Tracking System
"""
from config import Config
from app import create_app
from app.handlers.socket_handlers import register_handlers

def main():
    """Main application function"""
    # Create app and socketio instances
    app, socketio = create_app()
    
    # Register socket handlers
    register_handlers(socketio)
    
    # Print startup information
    print("🚀 Starting Object Tracking Web App...")
    print(f"📡 ML API URL: {Config.ML_API_URL}")
    print(f"📹 Camera Index: {Config.CAMERA_INDEX}")
    print(f"🔍 Auto Camera Detection: {'Enabled' if Config.ENABLE_AUTO_CAMERA_DETECTION else 'Disabled'}")
    print(f"🌐 Server: http://{Config.FLASK_HOST}:{Config.FLASK_PORT}")
    
    # Run the application
    socketio.run(
        app, 
        host=Config.FLASK_HOST, 
        port=Config.FLASK_PORT, 
        debug=Config.FLASK_DEBUG
    )

if __name__ == '__main__':
    main()