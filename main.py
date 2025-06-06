import os
import sys
import logging
import traceback
from dotenv import load_dotenv
from flask import Flask, request, jsonify
import json
import datetime
import uuid

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("diet-agent-app")

# Load environment variables from .env file
load_dotenv()

# Log environment variables (but not their values)
def log_env_vars():
    """Log whether important environment variables are present."""
    env_vars = ['GOOGLE_API_KEY', 'WEAVIATE_API_KEY', 'WEAVIATE_URL']
    for var in env_vars:
        logger.info(f"Environment variable {var} is {'present' if var in os.environ else 'missing'}")

# Initialize the app
app = Flask(__name__)

try:
    # Import your LangGraph workflow
    from arquitecture import workflow, FirestoreSaver, generate_session_id, validate_state
    from langgraph.checkpoint.memory import InMemorySaver

    # Initialize Firebase/Firestore connection
    memory_saver = InMemorySaver()
    firestore_saver = FirestoreSaver(
        collection_name="diet_conversations",
        project_id="diap3-458416",
        database_id="agente-context-prueba"
    )

    # Compile the graph
    graph = workflow.compile(checkpointer=memory_saver)
    
    logger.info("Successfully initialized LangGraph workflow")
except Exception as e:
    logger.error(f"Error during workflow initialization: {e}")
    logger.error(traceback.format_exc())

# Log environment variables at startup
log_env_vars()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "timestamp": datetime.datetime.now().isoformat()})

@app.route('/chat', methods=['POST'])
def chat():
    """Chat endpoint that processes messages and returns responses."""
    try:
        data = request.json
        
        # Extract session ID and user message
        session_id = data.get('session_id')
        user_message = data.get('message')
        
        if not user_message:
            return jsonify({"error": "No message provided"}), 400
            
        # Generate a new session ID if not provided
        if not session_id:
            session_id = generate_session_id()
            logger.info(f"Created new session: {session_id}")
        
        # Get existing state or create new one
        state = firestore_saver.get(session_id)
        
        # If no state exists, initialize a new one
        if state is None:
            state = {
                "messages": [],
                "intolerances": [],
                "forbidden_foods": [],
                "diet": {},
                "budget": None,
                "info_dietas": "",
                "grocery_list": [],
                "metadata": {
                    "created_at": datetime.datetime.now().isoformat(),
                    "last_active": datetime.datetime.now().isoformat(),
                    "session_id": session_id
                }
            }
        
        # Add the user message to the state
        state["messages"].append({"role": "user", "content": user_message})
        prev_len = len(state["messages"])
        
        # Process the message through the graph
        result = graph.invoke(
            state,
            config={"configurable": {"thread_id": session_id}},
        )
        
        # Update the state with the result
        state = result
        
        # Update metadata
        if "metadata" in state:
            state["metadata"]["last_active"] = datetime.datetime.now().isoformat()
        
        # Extract new assistant messages
        new_msgs = state["messages"][prev_len:]
        assistant_msgs = [m for m in new_msgs if m.get("role") == "assistant"]
        
        # Get the latest assistant message
        response = assistant_msgs[-1]["content"] if assistant_msgs else "No response generated."
        
        # Save state to Firestore
        if validate_state(state):
            firestore_saver.put(session_id, state)
        
        # Return the response
        return jsonify({
            "session_id": session_id,
            "response": response
        })
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route('/', methods=['GET'])
def root():
    """Root endpoint for basic health check."""
    return jsonify({
        "status": "online",
        "service": "diet-agent",
        "version": "1.0",
        "timestamp": datetime.datetime.now().isoformat(),
        "endpoints": ["/health", "/chat"]
    })

# Add better error handling
@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled exception: {str(e)}")
    logger.error(traceback.format_exc())
    return jsonify({"error": "An unexpected error occurred", "details": str(e)}), 500

if __name__ == "__main__":
    # Get port from environment variable or default to 8080
    port = int(os.environ.get("PORT", 8080))
    
    # Run the Flask app
    app.run(host="0.0.0.0", port=port, debug=False)