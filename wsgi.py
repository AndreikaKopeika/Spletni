#!/usr/bin/env python3
"""
WSGI entry point for production deployment
"""
import os
from app import app, socketio

if __name__ == "__main__":
    # Production settings
    app.config['DEBUG'] = False
    app.config['TESTING'] = False
    
    # Get port from environment or use default
    port = int(os.environ.get('PORT', 5000))
    
    # Run with production server
    socketio.run(app, 
                host='0.0.0.0', 
                port=port, 
                debug=False, 
                allow_unsafe_werkzeug=False)
