from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import requests
import json
import uuid
import datetime

# Configure API endpoint for the deployed agent
AGENT_URL = "https://diet-agent-447775611622.europe-west1.run.app"

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

# Initialize FastAPI
app = FastAPI(title="Nutribot Bridge API")

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development, adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session storage (replace with Firestore in production)
sessions = {}

# API endpoints
@app.get("/sessions", response_model=SessionResponse)
async def list_sessions():
    """List all available sessions"""
    # Generate a new session ID
    new_session_id = f"usuario_{uuid.uuid4().hex[:8]}"
    
    return SessionResponse(
        session_id=new_session_id,
        sessions=list(sessions.keys())
    )

@app.post("/message", response_model=MessageResponse)
async def process_message(request: MessageRequest, background_tasks: BackgroundTasks):
    """Process a message and get a response from the agent"""
    
    # If no session_id provided, create a new one
    if not request.session_id:
        session_id = f"usuario_{uuid.uuid4().hex[:8]}"
    else:
        session_id = request.session_id
    
    try:
        # Forward the request to the deployed agent
        response = requests.post(
            f"{AGENT_URL}/chat",
            json={
                "session_id": session_id,
                "message": request.message
            }
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        
        # Get the response data
        data = response.json()
        
        # Store session for future reference
        sessions[session_id] = {
            "last_active": datetime.datetime.now().isoformat()
        }
        
        # Return the response
        return MessageResponse(
            session_id=session_id,
            response=data.get("response", "No response"),
            state={
                "messages": [
                    {"role": "user", "content": request.message},
                    {"role": "assistant", "content": data.get("response", "No response")}
                ]
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")

@app.get("/")
async def root():
    """Root endpoint to verify API is running"""
    return {"message": "Nutribot Bridge API is running"}

@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run"""
    # Forward health check to the deployed agent
    try:
        response = requests.get(f"{AGENT_URL}/health")
        if response.status_code == 200:
            return {"status": "healthy", "agent_status": "connected"}
        else:
            return {"status": "healthy", "agent_status": "disconnected"}
    except:
        return {"status": "healthy", "agent_status": "disconnected"}

# Run the FastAPI app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_bridge:app", host="0.0.0.0", port=8000, reload=True)