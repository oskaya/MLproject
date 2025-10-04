"""
Object Tracking System - Modular Application Package
"""
import os
from datetime import timedelta
from flask import Flask
from flask_socketio import SocketIO
from webapp_config import WebAppConfig

# Global socketio instance
socketio = None

def create_app():
    """Application factory function"""
    global socketio
    
    # Create Flask app with correct template and static folder paths
    # Get the parent directory of the app package (project root)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    app = Flask(__name__, 
                template_folder=os.path.join(base_dir, 'templates'),
                static_folder=os.path.join(base_dir, 'static'))
    
    # Configure Flask app
    app.config['SECRET_KEY'] = WebAppConfig.SECRET_KEY
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(seconds=WebAppConfig.PERMANENT_SESSION_LIFETIME)
    
    socketio = SocketIO(app, cors_allowed_origins=WebAppConfig.SOCKETIO_CORS_ALLOWED_ORIGINS)
    
    # Import routes and handlers after app creation to avoid circular imports
    from app.routes import camera_routes, tracking_routes, main_routes, auth_routes
    from app.handlers import socket_handlers
    
    # Register blueprints
    app.register_blueprint(main_routes.bp)
    app.register_blueprint(camera_routes.bp)
    app.register_blueprint(tracking_routes.bp)
    app.register_blueprint(auth_routes.bp)
    
    # Register socket handlers
    socket_handlers.register_handlers(socketio)
    
    return app, socketio