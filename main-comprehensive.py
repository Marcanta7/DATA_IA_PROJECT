import os
import sys
import logging
import traceback
from flask import Flask, request, jsonify
import json
import datetime
import uuid
from dotenv import load_dotenv

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("diet-agent-app")

# Load environment variables from .env file
load_dotenv()

# Log the Python path and working directory
logger.info(f"Python path: {sys.path}")
logger.info(f"Working directory: {os.getcwd()}")
logger.info(f"Files in working directory: {os.listdir('.')}")

# Add current directory to path to ensure all modules are accessible
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
    logger.info(f"Added {current_dir} to Python path")

# Add nodes directory to Python path if it exists
nodes_dir = os.path.join(current_dir, 'nodes')
if os.path.exists(nodes_dir) and nodes_dir not in sys.path:
    sys.path.insert(0, nodes_dir)
    logger.info(f"Added {nodes_dir} to Python path")
    if os.path.exists(nodes_dir):
        logger.info(f"Files in nodes directory: {os.listdir(nodes_dir)}")

# Initialize the app
app = Flask(__name__)

# Define explicit import functions to avoid scope issues
def import_arquitecture():
    """Import the arquitecture module and its components."""
    try:
        # First try direct import
        import arquitecture
        logger.info("Successfully imported arquitecture module")
        return (
            arquitecture.workflow, 
            arquitecture.FirestoreSaver, 
            arquitecture.generate_session_id, 
            arquitecture.validate_state
        )
    except ImportError:
        # If not found, try from specific paths
        logger.info("Trying alternative import paths...")
        
        # Try from current directory
        arquitecture_path = os.path.join(current_dir, 'arquitecture.py')
        if os.path.exists(arquitecture_path):
            logger.info(f"Found arquitecture.py at {arquitecture_path}")
            import importlib.util
            spec = importlib.util.spec_from_file_location("arquitecture", arquitecture_path)
            arquitecture = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(arquitecture)
            logger.info("Successfully imported arquitecture from file")
            return (
                arquitecture.workflow, 
                arquitecture.FirestoreSaver, 
                arquitecture.generate_session_id, 
                arquitecture.validate_state
            )
        
        # Try from nodes directory
        arquitecture_path = os.path.join(nodes_dir, 'arquitecture.py')
        if os.path.exists(arquitecture_path):
            logger.info(f"Found arquitecture.py at {arquitecture_path}")
            import importlib.util
            spec = importlib.util.spec_from_file_location("arquitecture", arquitecture_path)
            arquitecture = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(arquitecture)
            logger.info("Successfully imported arquitecture from nodes directory")
            return (
                arquitecture.workflow, 
                arquitecture.FirestoreSaver, 
                arquitecture.generate_session_id, 
                arquitecture.validate_state
            )
        
        raise ImportError("Could not import arquitecture module")

def import_langgraph():
    """Import LangGraph modules."""
    try:
        from langgraph.checkpoint.memory import InMemorySaver
        logger.info("Successfully imported LangGraph")
        return InMemorySaver
    except ImportError:
        logger.error("Failed to import LangGraph")
        raise

# Try to import all required modules
try:
    workflow, FirestoreSaver, generate_session_id, validate_state = import_arquitecture()
    InMemorySaver = import_langgraph()
    
    # Now we're sure these variables are defined in the global scope
    # Initialize Firebase/Firestore connection
    memory_saver = InMemorySaver()
    firestore_saver = FirestoreSaver(
        collection_name="diet_conversations",
        project_id="diap3-458416",
        database_id="agente-context-prueba"
    )
    
    # Compile the graph
    graph = workflow.compile(checkpointer=memory_saver)
    
    logger.info("Successfully initialized LangGraph workflow and Firestore")
except Exception as e:
    logger.error(f"Error during initialization: {e}")
    logger.error(traceback.format_exc())
    sys.exit(1)  # Exit if initialization fails - we need these components

# Log if important environment variables are present
def log_env_vars():
    """Log whether important environment variables are present."""
    env_vars = ['GOOGLE_API_KEY', 'WEAVIATE_API_KEY', 'WEAVIATE_URL']
    for var in env_vars:
        logger.info(f"Environment variable {var} is {'present' if var in os.environ else 'missing'}")

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