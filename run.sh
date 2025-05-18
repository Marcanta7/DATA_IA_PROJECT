#!/bin/bash

# Function to kill processes using specific ports
kill_port() {
    PORT=$1
    echo "Checking for processes using port $PORT..."
    PID=$(lsof -ti:$PORT)
    if [ ! -z "$PID" ]; then
        echo "Found process $PID using port $PORT. Killing it..."
        kill -9 $PID
        sleep 1
    else
        echo "No process found using port $PORT"
    fi
}

# Kill any process using ports 8000 (API) and 8501 (Streamlit)
kill_port 8000
kill_port 8501

# Also try to kill by process name
echo "Stopping any running Python/Streamlit processes..."
pkill -f "python api.py" || true
pkill -f "streamlit run app.py" || true
pkill -f "uvicorn" || true
sleep 2

# Clear Python cache
echo "Clearing Python cache..."
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

# Start the FastAPI server in the background
echo "Starting API server..."
python api.py &
API_PID=$!

# Wait for the API to be available
echo "Waiting for API to be available..."
MAX_RETRIES=30
COUNT=0
while ! curl -s http://localhost:8000/docs > /dev/null 2>&1 && [ $COUNT -lt $MAX_RETRIES ]; do
    sleep 1
    COUNT=$((COUNT+1))
    echo "Waiting... ($COUNT/$MAX_RETRIES)"
done

if [ $COUNT -eq $MAX_RETRIES ]; then
    echo "API server failed to start properly."
    kill $API_PID 2>/dev/null || true
    exit 1
fi

echo "API server is running!"

# Start Streamlit
echo "Starting Streamlit app..."
streamlit run app.py

# When Streamlit closes, kill the API server
echo "Shutting down API server..."
kill $API_PID 2>/dev/null || true