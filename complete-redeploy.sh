#!/bin/bash
# Script to make a complete redeployment of the agent with comprehensive error handling

echo "🔍 Creating deployment directory..."
DEPLOY_DIR="diet-agent-deploy"
mkdir -p $DEPLOY_DIR

# Copy fixed main.py to deployment directory
echo "📝 Creating main.py with robust error handling..."
cat > $DEPLOY_DIR/main.py << 'EOF'
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

# Add src directory to Python path if it exists
src_dir = os.path.join(current_dir, 'src')
if os.path.exists(src_dir) and src_dir not in sys.path:
    sys.path.insert(0, src_dir)
    logger.info(f"Added {src_dir} to Python path")
    if os.path.exists(src_dir):
        logger.info(f"Files in src directory: {os.listdir(src_dir)}")

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
EOF

# Copy Dockerfile to deployment directory
echo "📝 Creating Dockerfile..."
cat > $DEPLOY_DIR/Dockerfile << 'EOF'
# Multi-stage build for optimized dependency installation
FROM python:3.9-slim as builder

# Set up environment
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Create a virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies in groups to better manage timeouts
# First, install core dependencies
RUN pip install --upgrade pip && \
    pip install pandas requests python-dotenv werkzeug==2.0.1 flask==2.0.1 gunicorn==20.1.0

# Then install machine learning libraries
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu

# Install NLP dependencies
RUN pip install spacy sentence-transformers fuzzywuzzy python-Levenshtein && \
    pip install https://github.com/explosion/spacy-models/releases/download/es_core_news_sm-3.7.0/es_core_news_sm-3.7.0-py3-none-any.whl

# Install vector DB and search dependencies
RUN pip install weaviate-client==4.12.0 duckduckgo-search

# Install Google Cloud dependencies
RUN pip install google-cloud-firestore google-cloud-bigquery google-cloud-secret-manager

# Finally install LangChain and LangGraph
RUN pip install langgraph langchain langchain_google_genai==2.1.4

# Second stage: runtime image
FROM python:3.9-slim

# Set environment variables
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8080

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY . .

# Run the application with gunicorn
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app
EOF

# Create requirements.txt
echo "📝 Creating requirements.txt..."
cat > $DEPLOY_DIR/requirements.txt << 'EOF'
# Core dependencies
langgraph
langchain
langchain_google_genai==2.1.4
python-dotenv
flask==2.0.1
werkzeug==2.0.1
gunicorn==20.1.0

# Data processing
pandas
requests

# Vector search and NLP
duckduckgo-search
spacy
weaviate-client==4.12.0
sentence-transformers
torch
fuzzywuzzy
python-Levenshtein

# Google Cloud dependencies
google-cloud-firestore
google-cloud-bigquery
google-cloud-secret-manager

# SpaCy language model
https://github.com/explosion/spacy-models/releases/download/es_core_news_sm-3.7.0/es_core_news_sm-3.7.0-py3-none-any.whl
EOF

# Copy your existing nodes directory to the deploy directory
echo "📁 Copying nodes directory..."
if [ -d "nodes" ]; then
    cp -r nodes $DEPLOY_DIR/
    echo "✅ nodes directory copied successfully"
else
    echo "⚠️ nodes directory not found"
fi

# Copy the src directory to the deploy directory
echo "📁 Copying src directory..."
if [ -d "src" ]; then
    cp -r src $DEPLOY_DIR/
    echo "✅ src directory copied successfully"
else
    echo "⚠️ src directory not found"
    # Create a minimal src directory with an empty prompts.json as fallback
    mkdir -p $DEPLOY_DIR/src
    echo "{}" > $DEPLOY_DIR/src/prompts.json
    echo "🔧 Created minimal src directory with empty prompts.json as fallback"
fi

# Copy prompts.json to multiple locations for redundancy
echo "📁 Ensuring prompts.json is available in multiple locations..."
if [ -f "src/prompts.json" ]; then
    # Copy to root directory
    cp src/prompts.json $DEPLOY_DIR/
    echo "✅ prompts.json copied to root directory"
    
    # Copy to nodes directory
    cp src/prompts.json $DEPLOY_DIR/nodes/
    echo "✅ prompts.json copied to nodes directory"
else
    echo "⚠️ src/prompts.json not found, creating minimal version in multiple locations"
    # Create a minimal prompts.json in root directory
    cat > $DEPLOY_DIR/prompts.json << 'EOF'
{
  "extract_intolerances_prompt": "Based on the user's message, extract any food intolerances they mention.\nUser text: {user_text}\nKnown intolerances: {known_intolerances}",
  "duckduckgo_query": "foods to avoid with {intolerance} intolerance or allergy",
  "extract_forbidden_foods_prompt": "Based on the search results about {intolerance} intolerance, extract a list of foods that should be avoided.\nKnown forbidden foods: {known_foods}\nRaw text: {raw_text}",
  "detect_no_longer_intolerant_prompt": "Analyze if the user text indicates they are no longer intolerant to certain foods.\nUser text: {user_text}\nPrevious intolerances: {previous_intolerances}\nPrevious forbidden foods: {forbidden_previous_foods}"
}
EOF
    echo "✅ Created minimal prompts.json in root directory"
    
    # Copy to nodes directory
    cp $DEPLOY_DIR/prompts.json $DEPLOY_DIR/nodes/
    echo "✅ Copied minimal prompts.json to nodes directory"
fi

# Copy the arquitecture.py file if it exists
if [ -f "arquitecture.py" ]; then
    cp arquitecture.py $DEPLOY_DIR/
    echo "✅ arquitecture.py copied successfully"
else
    echo "⚠️ arquitecture.py not found, searching in nodes directory..."
    if [ -f "nodes/arquitecture.py" ]; then
        cp nodes/arquitecture.py $DEPLOY_DIR/
        echo "✅ arquitecture.py found in nodes directory and copied"
    else
        echo "❌ arquitecture.py not found anywhere, deployment will fail!"
    fi
fi

# Copy any .env file if it exists
if [ -f ".env" ]; then
    cp .env $DEPLOY_DIR/
    echo "✅ .env file copied successfully"
elif [ -f "nodes/.env" ]; then
    cp nodes/.env $DEPLOY_DIR/
    echo "✅ .env file found in nodes directory and copied"
else
    echo "⚠️ .env file not found, environment variables will need to be set elsewhere"
fi

# Create a Cloud Build config
echo "📝 Creating Cloud Build config..."
cat > $DEPLOY_DIR/cloudbuild.yaml << 'EOF'
steps:
# Build the container image
- name: 'gcr.io/cloud-builders/docker'
  args: ['build', '-t', 'gcr.io/$PROJECT_ID/diet-agent:latest', '.']
  timeout: '3600s'  # 1 hour timeout for build

# Push the container image to Container Registry
- name: 'gcr.io/cloud-builders/docker'
  args: ['push', 'gcr.io/$PROJECT_ID/diet-agent:latest']

images:
- 'gcr.io/$PROJECT_ID/diet-agent:latest'
timeout: '3600s'
EOF

# Print a summary of what's being deployed
echo "📋 Deployment Summary:"
echo "- Main application code"
echo "- Nodes directory"
echo "- Src directory"
echo "- prompts.json in multiple locations for redundancy"
echo "- arquitecture.py"
echo "- Environment variables"

# Now deploy using Cloud Build from the deploy directory
echo "🚀 Starting deployment with Cloud Build..."
cd $DEPLOY_DIR
gcloud builds submit --config=cloudbuild.yaml

if [ $? -eq 0 ]; then
  echo "✅ Build successful!"
  echo "🚀 Deploying to Cloud Run..."
  
  gcloud run deploy diet-agent \
    --image=gcr.io/diap3-458416/diet-agent:latest \
    --region=europe-west1 \
    --platform=managed \
    --allow-unauthenticated \
    --memory=4Gi \
    --cpu=2 \
    --timeout=900
    
  echo "🎉 Deployment process completed!"
else
  echo "❌ Build failed. Please check the logs."
fi

# Clean up the deploy directory
cd ..
echo "🧹 Cleaning up deployment directory..."
# Uncomment to remove the directory after deployment: 
# rm -rf $DEPLOY_DIR