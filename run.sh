#!/bin/bash

echo "============================================="
echo "Starting Diet Assistant Application"
echo "============================================="

# Check if the nodes directory exists
if [ ! -d "nodes" ]; then
    echo "Error: The 'nodes' directory does not exist."
    echo "Please make sure you're running this script from the project root directory."
    exit 1
fi

# Check if the necessary files exist in the nodes directory
for file in states.py intolerancias.py assistant.py; do
    if [ ! -f "nodes/$file" ]; then
        echo "Error: Required file 'nodes/$file' not found."
        echo "Please make sure all required modules are in the nodes directory."
        exit 1
    fi
done

# Start the FastAPI server in the background
echo "Starting API server..."
python api.py &
API_PID=$!

# Wait for the API to be available
echo "Waiting for API to be available..."
MAX_RETRIES=30
COUNT=0
while ! curl -s http://localhost:8000/docs > /dev/null && [ $COUNT -lt $MAX_RETRIES ]; do
    sleep 1
    COUNT=$((COUNT+1))
    echo "Waiting... ($COUNT/$MAX_RETRIES)"
done

if [ $COUNT -eq $MAX_RETRIES ]; then
    echo "API server failed to start properly."
    kill $API_PID
    exit 1
fi

echo "API server is running!"

# Start Streamlit
echo "Starting Streamlit app..."
streamlit run app.py

# When Streamlit closes, kill the API server
echo "Shutting down API server..."
kill $API_PID