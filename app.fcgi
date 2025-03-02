#!/usr/bin/python3
import sys
import os

# Add your site-packages path (adjust username and Python version as needed)
sys.path.insert(0, '/home/username/python/lib/python3.8/site-packages')
# Add your project path
sys.path.insert(0, '/home/username/public_html')

from flup.server.fcgi import WSGIServer
from app import app  # Import your Flask application

if __name__ == '__main__':
    WSGIServer(app).run()