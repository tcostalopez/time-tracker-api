from flask import Flask, request, jsonify, render_template, g
from datetime import datetime
import logging
import os
import json
import requests  # ✅ Correctly import requests at the top

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder="templates")
app.secret_key = os.environ.get("SESSION_SECRET", "your-secret-key")

# Define session storage file
SESSION_FILE = "sessions.json"

# Load sessions from file
def load_sessions():
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, "r") as file:
            return json.load(file)
    return {}

# Save sessions to file
def save_sessions(sessions):
    with open(SESSION_FILE, "w") as file:
        json.dump(sessions, file, default=str)

# Load sessions before each request
@app.before_request
def before_request():
    g.sessions = load_sessions()

@app.route('/')
def index():
    """Debug Flask Template Rendering"""
    try:
        return render_template("index.html"), 200, {'Content-Type': 'text/html'}
    except Exception as e:
        logger.error(f"Error rendering index.html: {str(e)}")
        return f"Error: {str(e)}", 500  # Show error in the browser if template rendering fails

@app.route('/api/start', methods=['POST'])
def start_timing():
    """Start a new timing session"""
    try:
        data = request.get_json() or {}
        activity = data.get('activity', 'Walk')  # Get activity from JSON body
        session_id = datetime.now().strftime('%Y%m%d%H%M%S')

        g.sessions[session_id] = {
            'start_time': datetime.now().isoformat(),
            'activity': activity
        }
        save_sessions(g.sessions)

        logger.debug(f"Started session {session_id}")
        return jsonify({'status': 'success', 'session_id': session_id, 'message': 'Timing started'})
    except Exception as e:
        logger.error(f"Error starting session: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Failed to start timing'}), 500

@app.route('/api/stop', methods=['POST'])
def stop_timing():
    """Stop timing and calculate duration"""
    try:
        data = request.get_json() or {}
        session_id = data.get('session_id')

        if not session_id or session_id not in g.sessions:
            return jsonify({'status': 'error', 'message': 'Invalid session ID'}), 400

        session = g.sessions[session_id]
        start_time = datetime.fromisoformat(session['start_time'])
        end_time = datetime.now()
        duration = end_time - start_time
        minutes, seconds = divmod(int(duration.total_seconds()), 60)

        response_text = f"{session['activity']} Duration: {minutes} minutes {seconds} seconds"

        # Clean up the session
        del g.sessions[session_id]
        save_sessions(g.sessions)

        logger.debug(f"Completed session {session_id}: {response_text}")
        return jsonify({
            'status': 'success',
            'formatted_text': response_text,
            'duration_minutes': minutes,
            'duration_seconds': seconds
        })
    except Exception as e:
        logger.error(f"Error stopping session: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Failed to stop timing'}), 500

@app.route('/ping/start', methods=['GET'])
def ping_start():
    """UptimeRobot GET route to trigger /api/start"""
    try:
        # Internally send a POST request to /api/start
        response = requests.post("https://time-tracker-api-laiz.onrender.com/api/start", json={"activity": "UptimeRobot Keep Alive"})
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/ping/stop', methods=['GET'])
def ping_stop():
    """UptimeRobot GET route to trigger /api/stop"""
    try:
        # Internally send a POST request to /api/stop
        response = requests.post("https://time-tracker-api-laiz.onrender.com/api/stop", json={"session_id": "UptimeRobotSession"})
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    # Use the port assigned by Render dynamically
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
