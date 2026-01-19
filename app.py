# app.py
import json
import logging
import sys
import os
from datetime import datetime
from flask import Flask, jsonify, request, abort

from scheduler.api.handlers import TimetableHandler
from scheduler.core.engine import TimetableEngine

# Constants
AUTHORIZED_API_KEY = "KodP+4wZKhZa5ejOqJxXoKyZIJqJFhPZ/dCPem65bUE="
ALLOWED_ORIGINS = ["http://localhost:8000", "http://127.0.0.1:8000", "https://home-e-school.in"]

app = Flask(__name__)

def authorize_request():
    api_key = request.headers.get("X-API-KEY")
    if api_key != AUTHORIZED_API_KEY:
        abort(401, description="Unauthorized: Invalid API key")
    
    # Origin check (optional)
    origin = request.headers.get("Origin")
    if origin and origin not in ALLOWED_ORIGINS:
        abort(403, description="Forbidden: Origin not allowed")

# Logging Setup
logger = logging.getLogger('TimetableGenerator')
logger.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.WARNING)
console_formatter = logging.Formatter('%(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)

file_handler = logging.FileHandler('timetable_debug.log')
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - [%(name)s] - %(message)s')
file_handler.setFormatter(file_formatter)

logger.addHandler(console_handler)
logger.addHandler(file_handler)

@app.route('/generate', methods=['POST'])
def generate_timetable_api():
    authorize_request()
    
    try:
        logger.info("Received timetable generation request")
        start_time = datetime.now()
        
        laravel_data = request.get_json()
        if not isinstance(laravel_data, list):
            return jsonify({'status': 'error', 'message': 'Invalid format. Expected list of classes.'}), 400

        # Parse and Initialize
        classes = TimetableHandler.parse_payload(laravel_data)
        engine = TimetableEngine(classes)
        
        # Core Scheduling
        success = engine.schedule_all()
        
        # Format Results
        timetable = TimetableHandler.format_response(engine)
        
        # Response Metadata
        duration = (datetime.now() - start_time).total_seconds()
        
        result = {
            'status': 'success' if success else 'partial',
            'quality_check': 'passed' if success else 'issues_found', # Simplified for now
            'quality_issues': [] if success else ['Incomplete scheduling'],
            'timestamp': datetime.now().isoformat(),
            'processing_time_seconds': round(duration, 2),
            'timetable': timetable,
            'summary': {}, # Placeholder for backward compat if needed
            'stats': {
                'total_classes': len(classes),
                'assignments': engine.assignment_count,
                'backtracks': engine.backtrack_count
            }
        }

        logger.info(f"Generation finished in {duration}s. Status: {result['status']}")
        return jsonify(result), 200

    except Exception as e:
        logger.exception("Exception in /generate")
        return jsonify({
            'status': 'error',
            'timestamp': datetime.now().isoformat(),
            'error': str(e),
            'message': 'Internal Server Error'
        }), 500

@app.route('/test', methods=['GET'])
def test_endpoint():
    authorize_request()
    return jsonify({
        'status': 'success',
        'message': 'Modular Timetable Generator API is running',
        'timestamp': datetime.now().isoformat(),
        'version': '6.0-modular'
    })

@app.route('/progress', methods=['GET'])
def get_progress():
    # Simplified progress for now, could be expanded with a shared state
    return jsonify({
        'status': 'success',
        'message': 'Real-time progress reporting currently simplified in modular version',
        'timestamp': datetime.now().isoformat()
    })

if __name__ == "__main__":
    logger.info("🚀 Starting Modular Timetable Generator Server")
    app.run(host='0.0.0.0', port=5000, debug=False)