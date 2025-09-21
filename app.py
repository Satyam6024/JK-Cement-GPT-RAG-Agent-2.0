"""
Flask web application for CementGPT RAG Agent
"""

import os
import json
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
import uuid

# Import your RAG agent
try:
    from rag_agent import get_initialization_status, require_vertex_ai
    from rag_agent.agent import root_agent
    RAG_AVAILABLE = True
except ImportError as e:
    print(f"Warning: RAG agent not available: {e}")
    RAG_AVAILABLE = False
    root_agent = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
CORS(app)

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file upload

# Store conversation history (in production, use a database)
conversations = {}


@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')


@app.route('/api/status')
def api_status():
    """Check system status"""
    if not RAG_AVAILABLE:
        return jsonify({
            'status': 'error',
            'message': 'RAG agent not available. Please check your setup.',
            'rag_available': False
        })
    
    try:
        is_initialized, error_msg = get_initialization_status()
        return jsonify({
            'status': 'success' if is_initialized else 'error',
            'message': 'System ready' if is_initialized else f'Initialization failed: {error_msg}',
            'rag_available': RAG_AVAILABLE,
            'vertex_ai_initialized': is_initialized,
            'agent_loaded': root_agent is not None
        })
    except Exception as e:
        logger.error(f"Status check error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Status check failed: {str(e)}',
            'rag_available': False
        })


@app.route('/api/chat', methods=['POST'])
def api_chat():
    """Handle chat messages"""
    if not RAG_AVAILABLE or not root_agent:
        return jsonify({
            'status': 'error',
            'message': 'RAG agent not available. Please check your setup.'
        }), 500
    
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({
                'status': 'error',
                'message': 'No message provided'
            }), 400
        
        user_message = data['message'].strip()
        if not user_message:
            return jsonify({
                'status': 'error',
                'message': 'Empty message'
            }), 400
        
        # Get or create session ID
        session_id = session.get('session_id')
        if not session_id:
            session_id = str(uuid.uuid4())
            session['session_id'] = session_id
        
        # Initialize conversation history if needed
        if session_id not in conversations:
            conversations[session_id] = []
        
        # Add user message to history
        conversations[session_id].append({
            'role': 'user',
            'message': user_message,
            'timestamp': datetime.now().isoformat()
        })
        
        # Get response from RAG agent
        logger.info(f"Processing message: {user_message[:100]}...")
        agent_response = root_agent.send_message(user_message)
        
        # Add agent response to history
        conversations[session_id].append({
            'role': 'agent',
            'message': agent_response,
            'timestamp': datetime.now().isoformat()
        })
        
        # Limit conversation history (keep last 50 messages)
        if len(conversations[session_id]) > 50:
            conversations[session_id] = conversations[session_id][-50:]
        
        return jsonify({
            'status': 'success',
            'response': agent_response,
            'session_id': session_id
        })
        
    except Exception as e:
        logger.error(f"Chat error: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Processing error: {str(e)}'
        }), 500


@app.route('/api/conversation-history')
def api_conversation_history():
    """Get conversation history for current session"""
    session_id = session.get('session_id')
    if not session_id or session_id not in conversations:
        return jsonify({
            'status': 'success',
            'history': []
        })
    
    return jsonify({
        'status': 'success',
        'history': conversations[session_id]
    })


@app.route('/api/clear-conversation', methods=['POST'])
def api_clear_conversation():
    """Clear conversation history for current session"""
    session_id = session.get('session_id')
    if session_id and session_id in conversations:
        conversations[session_id] = []
    
    return jsonify({
        'status': 'success',
        'message': 'Conversation cleared'
    })


@app.route('/api/corpus/list')
def api_list_corpora():
    """List all available corpora"""
    if not RAG_AVAILABLE or not root_agent:
        return jsonify({
            'status': 'error',
            'message': 'RAG agent not available'
        }), 500
    
    try:
        # Use the agent to list corpora
        response = root_agent.send_message("List all available corpora")
        
        return jsonify({
            'status': 'success',
            'response': response
        })
        
    except Exception as e:
        logger.error(f"List corpora error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to list corpora: {str(e)}'
        }), 500


@app.route('/api/corpus/create', methods=['POST'])
def api_create_corpus():
    """Create a new corpus"""
    if not RAG_AVAILABLE or not root_agent:
        return jsonify({
            'status': 'error',
            'message': 'RAG agent not available'
        }), 500
    
    try:
        data = request.get_json()
        if not data or 'name' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Corpus name is required'
            }), 400
        
        corpus_name = data['name'].strip()
        if not corpus_name:
            return jsonify({
                'status': 'error',
                'message': 'Corpus name cannot be empty'
            }), 400
        
        # Use the agent to create corpus
        response = root_agent.send_message(f"Create a corpus called '{corpus_name}'")
        
        return jsonify({
            'status': 'success',
            'response': response,
            'corpus_name': corpus_name
        })
        
    except Exception as e:
        logger.error(f"Create corpus error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to create corpus: {str(e)}'
        }), 500


@app.route('/api/corpus/add-document', methods=['POST'])
def api_add_document():
    """Add a document to a corpus"""
    if not RAG_AVAILABLE or not root_agent:
        return jsonify({
            'status': 'error',
            'message': 'RAG agent not available'
        }), 500
    
    try:
        data = request.get_json()
        if not data or 'corpus_name' not in data or 'document_url' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Corpus name and document URL are required'
            }), 400
        
        corpus_name = data['corpus_name'].strip()
        document_url = data['document_url'].strip()
        
        if not corpus_name or not document_url:
            return jsonify({
                'status': 'error',
                'message': 'Corpus name and document URL cannot be empty'
            }), 400
        
        # Use the agent to add document
        response = root_agent.send_message(f"Add this document to corpus '{corpus_name}': {document_url}")
        
        return jsonify({
            'status': 'success',
            'response': response
        })
        
    except Exception as e:
        logger.error(f"Add document error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to add document: {str(e)}'
        }), 500


@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {str(error)}")
    return render_template('500.html'), 500


if __name__ == '__main__':
    # Development server
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    logger.info(f"Starting Flask app on port {port} (debug={debug})")
    app.run(host='0.0.0.0', port=port, debug=debug)