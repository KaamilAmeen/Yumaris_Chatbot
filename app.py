import os
import logging
from flask import Flask, render_template, request, jsonify, session
from werkzeug.middleware.proxy_fix import ProxyFix
from database_service import init_db, close_db_session
from firebase_service import initialize_firebase
from chatbot import process_user_message

# Create the Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Initialize Database
init_db()

# Initialize Firebase (for backward compatibility)
initialize_firebase()

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Clean up database session when app shuts down
@app.teardown_appcontext
def shutdown_session(exception=None):
    close_db_session()

@app.route('/')
def index():
    """Render the main chat interface."""
    return render_template(
        'index.html',
        firebase_api_key=os.environ.get("FIREBASE_API_KEY", ""),
        firebase_project_id=os.environ.get("FIREBASE_PROJECT_ID", ""),
        gemini_api_key=os.environ.get("GEMINI_API_KEY", "")
    )

@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Process incoming chat messages from the user.
    This endpoint accepts user messages, processes them through the NLP module,
    and returns the appropriate chatbot response.
    """
    try:
        data = request.json
        user_message = data.get('message', '')
        session_id = data.get('session_id', '')
        
        # Store session ID if it doesn't exist yet
        if not session.get('chat_session_id'):
            session['chat_session_id'] = session_id
        
        # Process the message and get the response
        response = process_user_message(user_message, session_id)
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Error processing chat message: {str(e)}", exc_info=True)
        return jsonify({
            'message': "I'm sorry, I encountered an error processing your request. Please try again.",
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
