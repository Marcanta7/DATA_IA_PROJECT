from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import asyncio
import uuid
import datetime
import copy
import json
import pickle
import base64
import sys
import os
import importlib.util
from google.cloud import firestore

# Add nodes directory to Python path with absolute path
current_dir = os.path.dirname(os.path.abspath(__file__))
nodes_dir = os.path.join(current_dir, 'nodes')
sys.path.insert(0, nodes_dir)

# Print debugging information
print(f"Python path: {sys.path}")
print(f"Looking for modules in: {nodes_dir}")
if os.path.exists(nodes_dir):
    print(f"Files in nodes directory: {os.listdir(nodes_dir)}")
else:
    print(f"Warning: nodes directory {nodes_dir} does not exist!")

# Function to load Python modules from file paths
def load_module(name, file_path):
    print(f"Loading module {name} from {file_path}")
    spec = importlib.util.spec_from_file_location(name, file_path)
    if spec is None:
        raise ImportError(f"Could not find module {name} at {file_path}")
    
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # Add to sys.modules cache
    spec.loader.exec_module(module)
    return module

# Import LangGraph dependencies
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver

# Load agent modules from files
try:
    # Check if states.py exists
    states_path = os.path.join(nodes_dir, "states.py")
    if not os.path.exists(states_path):
        raise FileNotFoundError(f"states.py not found at {states_path}")
    
    # Load all modules from file paths
    states_module = load_module("states", os.path.join(nodes_dir, "states.py"))
    intolerancias_module = load_module("intolerancias", os.path.join(nodes_dir, "intolerancias.py"))
    mensaje_intolerancias_module = load_module("mensaje_intolerancias", os.path.join(nodes_dir, "mensaje_intolerancias.py"))
    intolerancias_router_module = load_module("intolerancias_router", os.path.join(nodes_dir, "intolerancias_router.py"))
    listacompra_module = load_module("listacompra", os.path.join(nodes_dir, "listacompra.py"))
    assistant_module = load_module("assistant", os.path.join(nodes_dir, "assistant.py"))
    expertoendietas_module = load_module("expertoendietas", os.path.join(nodes_dir, "expertoendietas.py"))
    crear_dieta_module = load_module("crear_dieta", os.path.join(nodes_dir, "crear_dieta.py"))
    convertidor_module = load_module("convertidor", os.path.join(nodes_dir, "convertidor.py"))
    otros_module = load_module("otros", os.path.join(nodes_dir, "otros.py"))
    
    # Access components from the modules
    DietState = states_module.DietState
    intolerance_search = intolerancias_module.intolerance_search
    mensaje_intolerancias = mensaje_intolerancias_module.mensaje_intolerancias
    intolerancias_router = intolerancias_router_module.intolerancias_router
    generar_lista_compra_csv = listacompra_module.generar_lista_compra_csv
    router = assistant_module.router
    buscar_info_dietas = expertoendietas_module.buscar_info_dietas
    crear_dieta = crear_dieta_module.crear_dieta
    poner_precio = convertidor_module.poner_precio
    otros = otros_module.otros
    
    print("✅ Successfully loaded all modules")
except Exception as e:
    print(f"❌ Error loading modules: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Request and response models
class MessageRequest(BaseModel):
    session_id: Optional[str] = None
    message: str

class SessionResponse(BaseModel):
    session_id: str
    sessions: List[str]

class MessageResponse(BaseModel):
    session_id: str
    response: str
    state: Dict[str, Any]

# FirestoreSaver implementation
class FirestoreSaver:
    def __init__(self, 
                 collection_name: str = "diet_conversations", 
                 project_id: str = "diap3-458416",
                 database_id: str = "agente-context-prueba"
                ):
        self.collection_name = collection_name
        self.db = firestore.Client(project=project_id, database=database_id)
        self._cache = {}
        print(f"🔌 Connected to Firestore (database: {database_id}, collection: {collection_name})")
    
    def get(self, key: str) -> Optional[Dict]:
        # Try to get from cache first
        if key in self._cache:
            return self._cache[key]
        
        # Try to get from Firestore
        doc_ref = self.db.collection(self.collection_name).document(key)
        doc = doc_ref.get()
        
        if not doc.exists:
            return None
        
        data = doc.to_dict()
        
        # Deserialize pickled data if needed
        if "pickled_data" in data:
            pickled_data = base64.b64decode(data["pickled_data"])
            state = pickle.loads(pickled_data)
        else:
            state = data
            
            # Restore numeric keys in diet structure
            if "diet" in state and "diet_serialized" in state:
                try:
                    state["diet"] = json.loads(state["diet_serialized"])
                    del state["diet_serialized"]
                except:
                    print("⚠️ Error deserializing diet")
        
        # Update cache
        self._cache[key] = state
        return state
    
    def put(self, key: str, value: Dict) -> None:
        # Update cache
        self._cache[key] = value
        
        # Create a copy to avoid modifying the original
        firestore_value = copy.deepcopy(value)
        
        # Preprocess data to be compatible with Firestore
        if "diet" in firestore_value and isinstance(firestore_value["diet"], dict):
            try:
                firestore_value["diet_serialized"] = json.dumps(firestore_value["diet"])
                diet_simple = {}
                for day, meals in firestore_value["diet"].items():
                    day_str = f"día_{day}" if isinstance(day, int) else str(day)
                    diet_simple[day_str] = {}
                    for meal_name, items in meals.items():
                        diet_simple[day_str][meal_name] = list(items.keys()) if isinstance(items, dict) else "Info no disponible"
                
                firestore_value["diet"] = diet_simple
            except Exception as e:
                print(f"⚠️ Error serializing diet: {e}")
                firestore_value["diet"] = {}
                firestore_value["diet_serialized"] = "{}"
        
        # Save to Firestore
        doc_ref = self.db.collection(self.collection_name).document(key)
        
        try:
            doc_ref.set(firestore_value)
        except TypeError as e:
            print(f"⚠️ Error saving to Firestore: {e}")
            pickled_data = pickle.dumps(value)
            encoded_data = base64.b64encode(pickled_data).decode('utf-8')
            doc_ref.set({"pickled_data": encoded_data})
    
    def list_sessions(self):
        try:
            return [doc.id for doc in self.db.collection(self.collection_name).list_documents()]
        except Exception as e:
            print(f"Error listing sessions: {e}")
            return []

# Initialize FastAPI
app = FastAPI(title="Diet Assistant API")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development, adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Firestore Saver
firestore_saver = FirestoreSaver()

# Initialize agent graph
workflow = StateGraph(DietState)
workflow.add_node("input_usuario", router)
workflow.add_node("intolerancias", intolerance_search)
workflow.add_node("intolerancias_router", intolerancias_router)
workflow.add_node("mensaje_intolerancias", mensaje_intolerancias)
workflow.add_node("experto_dietas", buscar_info_dietas)
workflow.add_node("crear_dieta", crear_dieta)
workflow.add_node("hacer_lista_compra", generar_lista_compra_csv)
workflow.add_node("poner_precio", poner_precio)
workflow.add_node("otros", otros)

# Transitions
workflow.set_entry_point("input_usuario")
workflow.add_conditional_edges(
    "input_usuario",
    lambda x: getattr(x, "next", "otros"),
    {
        "intolerancias": "intolerancias",
        "experto_dietas": "experto_dietas",
        "otros": "otros"
    }
)
workflow.add_edge("intolerancias", "intolerancias_router")
workflow.add_conditional_edges(
    "intolerancias_router",
    lambda x: getattr(x, "next_after_intolerancias", "mensaje_intolerancias"),
    {
        "mensaje_intolerancias": "mensaje_intolerancias",
        "experto_dietas": "experto_dietas"
    }
)
workflow.add_edge("mensaje_intolerancias", END)
workflow.add_edge("experto_dietas", "crear_dieta")
workflow.add_edge("crear_dieta", "hacer_lista_compra")
workflow.add_edge("hacer_lista_compra", "poner_precio")
workflow.add_edge("poner_precio", END)
workflow.add_edge("otros", END)

# Compile the graph
memory_saver = InMemorySaver()
graph = workflow.compile(checkpointer=memory_saver)

# API endpoints
@app.get("/sessions", response_model=SessionResponse)
async def list_sessions():
    """List all available sessions"""
    sessions = firestore_saver.list_sessions()
    
    # Create a new session ID if needed
    if not sessions:
        new_session_id = f"usuario_1"
    else:
        # Extract numbers from existing session IDs
        user_numbers = []
        for session in sessions:
            try:
                if session.startswith("usuario_"):
                    num = int(session.split("_")[1])
                    user_numbers.append(num)
            except (ValueError, IndexError):
                continue
        
        # Generate next session ID
        next_number = max(user_numbers, default=0) + 1
        new_session_id = f"usuario_{next_number}"
    
    return SessionResponse(
        session_id=new_session_id,
        sessions=sessions
    )

@app.post("/message", response_model=MessageResponse)
async def process_message(request: MessageRequest, background_tasks: BackgroundTasks):
    """Process a message and get a response from the agent"""
    
    # If no session_id provided, create a new one
    if not request.session_id:
        session_id = f"usuario_{uuid.uuid4().hex[:8]}"
    else:
        session_id = request.session_id
    
    # Get current state or create new one
    state = firestore_saver.get(session_id)
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
    
    # Update metadata
    if "metadata" in state:
        state["metadata"]["last_active"] = datetime.datetime.now().isoformat()
    
    # Add user message to state
    state["messages"].append({"role": "user", "content": request.message})
    prev_len = len(state["messages"])
    
    try:
        # Process with the agent
        result = graph.invoke(
            state,
            config={"configurable": {"thread_id": session_id}},
        )
        state = result  # Update state
        
        # Update metadata
        if "metadata" in state:
            state["metadata"]["last_active"] = datetime.datetime.now().isoformat()
        
        # Get assistant's response
        new_msgs = state["messages"][prev_len:]
        assistant_msgs = [m for m in new_msgs if m.get("role") == "assistant"]
        
        if assistant_msgs:
            response_text = assistant_msgs[-1]['content']
        else:
            response_text = "No response from assistant"
        
        # Save state in the background
        background_tasks.add_task(firestore_saver.put, session_id, state)
        
        return MessageResponse(
            session_id=session_id,
            response=response_text,
            state=state
        )
        
    except Exception as e:
        # Log error and add to metadata
        if "metadata" in state:
            state["metadata"]["last_active"] = datetime.datetime.now().isoformat()
            state["metadata"]["last_error"] = str(e)
        
        # Try to save state despite error
        background_tasks.add_task(firestore_saver.put, session_id, state)
        
        # Print detailed error info
        import traceback
        print(f"Error processing message: {str(e)}")
        traceback.print_exc()
        
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")

@app.get("/")
async def root():
    """Root endpoint to verify API is running"""
    return {"message": "Diet Assistant API is running"}

@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run"""
    return {"status": "healthy"}

# Run the FastAPI app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)