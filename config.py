"""
Configuration settings for the Flask application.
"""

import os

class Config:
    # Get the base directory of the application
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    # Flask Settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_secret_key'
    
    # File Upload Settings
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    EXPORT_FOLDER = os.path.join(BASE_DIR, 'exports')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Optimization Settings
    DEFAULT_BUDGET = 0
    
    # Ensure upload and export directories exist
    @staticmethod
    def init_app(app):
        try:
            # Use /tmp directory for Vercel's ephemeral filesystem
            if 'VERCEL' in os.environ:
                app.config['UPLOAD_FOLDER'] = '/tmp/uploads'
                app.config['EXPORT_FOLDER'] = '/tmp/exports'
            
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            os.makedirs(app.config['EXPORT_FOLDER'], exist_ok=True)
        except Exception as e:
            # Log error but don't crash the app
            print(f"Warning: Could not create directories: {str(e)}")
