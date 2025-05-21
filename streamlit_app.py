import streamlit as st
import requests
import json
import pandas as pd
import base64
import os
import sys
from datetime import datetime
from PIL import Image

# Configure API endpoints
# You can use either the direct agent URL or the API bridge URL
DIRECT_AGENT_URL = "https://diet-agent-447775611622.europe-west1.run.app"  # Direct agent URL
API_BRIDGE_URL = "https://nutribot-api-447775611622.europe-west1.run.app"  # API bridge URL if deployed

# Choose which API to use - you can switch between them for testing
API_URL = DIRECT_AGENT_URL  # or API_BRIDGE_URL

# Function to download a file
def get_download_link(file_path, file_name):
    with open(file_path, "rb") as file:
        contents = file.read()
    b64 = base64.b64encode(contents).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{file_name}">Descargar {file_name}</a>'
    return href

# Set page config
st.set_page_config(
    page_title="nutribot",
    page_icon="🍽️",
    layout="wide"
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
    
if "session_id" not in st.session_state:
    # Get available sessions from the API
    try:
        response = requests.get(f"{API_URL}/health")
        if response.status_code == 200:
            st.session_state.session_id = f"usuario_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            st.session_state.available_sessions = []
        else:
            st.error(f"Error connecting to API: {response.text}")
            st.session_state.available_sessions = []
            st.session_state.session_id = "usuario_new"
    except Exception as e:
        st.error(f"Error connecting to API: {str(e)}")
        if "Connection refused" in str(e):
            st.error("The API server is not running. Make sure to start the API server first.")
        st.session_state.available_sessions = []
        st.session_state.session_id = "usuario_new"

# Sidebar for session management
with st.sidebar:
    # Display logo in sidebar as well
    try:
        sidebar_logo = Image.open("nutribot_logo.png")  # Adjust the path if needed
        st.image(sidebar_logo, width=150)
    except Exception as e:
        pass  # Silently fail if the logo isn't found in sidebar
        
    st.title("🍽️ nutribot")
    
    # Session management
    st.subheader("Gestión de Sesiones")
    
    # Option to create a new session
    if st.button("Crear Nueva Sesión"):
        st.session_state.session_id = f"usuario_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        st.session_state.messages = []
        st.success(f"Nueva sesión creada: {st.session_state.session_id}")
        st.rerun()
    
    # Display current session ID
    st.info(f"Sesión actual: {st.session_state.session_id}")
    
    # Check for CSV files to download
    st.subheader("Descargar Archivos")
    
    lista_compra_path = "lista_compra.csv"
    lista_compra_precio_path = "lista_compra_con_precio.csv"
    
    # Also check in nodes directory
    nodes_lista_compra_path = os.path.join("nodes", "lista_compra.csv")
    nodes_lista_compra_precio_path = os.path.join("nodes", "lista_compra_con_precio.csv")
    
    if os.path.exists(lista_compra_path):
        st.markdown(get_download_link(lista_compra_path, "lista_compra.csv"), unsafe_allow_html=True)
    elif os.path.exists(nodes_lista_compra_path):
        st.markdown(get_download_link(nodes_lista_compra_path, "lista_compra.csv"), unsafe_allow_html=True)
        
    if os.path.exists(lista_compra_precio_path):
        st.markdown(get_download_link(lista_compra_precio_path, "lista_compra_con_precio.csv"), unsafe_allow_html=True)
    elif os.path.exists(nodes_lista_compra_precio_path):
        st.markdown(get_download_link(nodes_lista_compra_precio_path, "lista_compra_con_precio.csv"), unsafe_allow_html=True)
    
    # About section
    st.subheader("Sobre nutribot")
    st.markdown("""
    Este asistente te ayuda a crear dietas personalizadas y listas de compra,
    teniendo en cuenta tus intolerancias alimentarias y preferencias dietéticas.
    
    Algunas cosas que puedes preguntar:
    - "Hazme una dieta alta en proteínas"
    - "Tengo intolerancia a la lactosa"
    - "¿Qué alimentos contienen gluten?"
    """)

# Main content area
st.title("nutribot 🍎")

# Display the Nutribot logo
try:
    logo = Image.open("nutribot_logo.png")  # Adjust the path if needed
    st.image(logo, width=300)
except Exception as e:
    st.warning("Logo not found. Please save the Nutribot logo as 'nutribot_logo.png' in the app directory.")

# Initialize chat interface
if st.session_state.messages:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("¿En qué puedo ayudarte hoy?"):
    # Add user message to chat interface
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Display a spinner while waiting for a response
    with st.spinner("Pensando..."):
        # Send message to the API
        try:
            response = requests.post(
                f"{API_URL}/chat",
                json={"session_id": st.session_state.session_id, "message": prompt}
            )
            
            if response.status_code == 200:
                data = response.json()
                assistant_response = data["response"]
                
                # Add assistant response to chat interface
                st.session_state.messages.append({"role": "assistant", "content": assistant_response})
                with st.chat_message("assistant"):
                    st.markdown(assistant_response)
                
            else:
                st.error(f"Error: {response.text}")
        except Exception as e:
            st.error(f"Error connecting to API: {str(e)}")
            if "Connection refused" in str(e):
                st.error("The API server is not running. Make sure to start the API server first.")