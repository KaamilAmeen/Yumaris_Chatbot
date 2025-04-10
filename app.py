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
    Process incoming text-only chat messages from the user.
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

@app.route('/api/chat-with-file', methods=['POST'])
def chat_with_file():
    """
    Process incoming chat messages with file attachments.
    This endpoint accepts user messages with file uploads, processes them through the NLP module,
    and returns the appropriate chatbot response with product analysis.
    """
    try:
        # Get text message and session ID
        user_message = request.form.get('message', '')
        session_id = request.form.get('session_id', '')
        
        # Check if we have a file attachment
        if 'file' not in request.files:
            return jsonify({
                'message': "I didn't receive any file. Please try attaching it again.",
            }), 400
            
        file = request.files['file']
        
        # Validate file
        if file.filename == '':
            return jsonify({
                'message': "The file appears to be empty. Please try another file.",
            }), 400
            
        # For now, we only support image files
        if not file.content_type.startswith('image/'):
            return jsonify({
                'message': "I can only analyze image files at the moment. Please upload an image file.",
            }), 400
            
        # Save the file temporarily to analyze it
        import os
        from werkzeug.utils import secure_filename
        import tempfile
        
        temp_dir = tempfile.gettempdir()
        filename = secure_filename(file.filename)
        filepath = os.path.join(temp_dir, filename)
        file.save(filepath)
        
        try:
            # Process message with image analysis
            from chatbot import process_image_message
            response = process_image_message(user_message, filepath, session_id)
            
            # Clean up temp file after processing
            os.remove(filepath)
            
            return jsonify(response)
            
        except Exception as e:
            # Clean up temp file if there was an error
            if os.path.exists(filepath):
                os.remove(filepath)
            raise e
    
    except Exception as e:
        logger.error(f"Error processing file upload: {str(e)}", exc_info=True)
        return jsonify({
            'message': "I'm sorry, I encountered an error processing your file. Please try again.",
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
