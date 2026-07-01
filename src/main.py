import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # DON'T CHANGE THIS !!!

from flask import Flask, send_from_directory, request, jsonify
from src.routes.api import api_bp
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)

# Rate limiting
request_counts = {}
RATE_LIMIT = 10  # requests per minute
RATE_WINDOW = 60  # seconds

# Middleware for rate limiting
@app.before_request
def rate_limit():
    if request.path.startswith('/api/'):
        client_ip = request.remote_addr
        current_time = time.time()
        
        # Clean up old entries
        for ip in list(request_counts.keys()):
            if current_time - request_counts[ip]['timestamp'] > RATE_WINDOW:
                del request_counts[ip]
        
        # Check rate limit
        if client_ip in request_counts:
            if request_counts[client_ip]['count'] >= RATE_LIMIT:
                return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429
            request_counts[client_ip]['count'] += 1
        else:
            request_counts[client_ip] = {'count': 1, 'timestamp': current_time}

# Register blueprints - IMPORTANT: Register after all routes are defined in api.py
app.register_blueprint(api_bp, url_prefix='/api')

# Serve static files
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Resource not found"}), 404

@app.errorhandler(429)
def too_many_requests(e):
    return jsonify({"error": "Rate limit exceeded. Please try again later."}), 429

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
