#!/bin/bash
# Script to deploy Streamlit app to Cloud Run

echo "🔨 Building Streamlit app container..."
# Create a build config file on the fly
cat > cloudbuild-temp.yaml << EOF
steps:
  # Build the container image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/diap3-458416/nutribot-streamlit:latest', '-f', 'Dockerfile.streamlit', '.']
    timeout: '1800s'
  
  # Push the container image to Container Registry
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/diap3-458416/nutribot-streamlit:latest']
  
images:
  - 'gcr.io/diap3-458416/nutribot-streamlit:latest'
timeout: '1800s'
EOF

gcloud builds submit --config=cloudbuild-temp.yaml

if [ $? -eq 0 ]; then
  echo "✅ Build successful!"
  echo "🚀 Deploying Streamlit app to Cloud Run..."
  
  gcloud run deploy nutribot-streamlit \
    --image=gcr.io/diap3-458416/nutribot-streamlit:latest \
    --region=europe-west1 \
    --platform=managed \
    --allow-unauthenticated \
    --memory=2Gi \
    --cpu=1 \
    --timeout=300
    
  echo "🎉 Deployment process completed!"
else
  echo "❌ Build failed. Please check the logs."
fi