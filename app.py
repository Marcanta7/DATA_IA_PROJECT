import streamlit as st
import requests
import json
import pandas as pd
import base64
import os
import sys
from datetime import datetime

# Configure API endpoint
API_URL = "http://localhost:8000"  # Update this with your API URL when deployed

# Function to download a file
def get_download_link(file_path, file_name):
    with open(file_path, "rb") as file:
        contents = file.read()
    b64 = base64.b64encode(contents).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{file_name}">Descargar {file_name}</a>'
    return href

# Set page config
st.set_page_config(
    page_title="Asistente de Dietas",
    page_icon="🍽️",
    layout="wide"
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
    
if "session_id" not in st.session_state:
    # Get available sessions from the API
    try:
        response = requests.get(f"{API_URL}/sessions")
        if response.status_code == 200:
            data = response.json()
            st.session_state.available_sessions = data["sessions"]
            st.session_state.session_id = data["session_id"]  # Default to the new session ID
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
    st.title("🍽️ Asistente de Dietas")
    
    # Session selection
    st.subheader("Gestión de Sesiones")
    
    # Option to select an existing session or create a new one
    session_option = st.radio(
        "Selecciona una opción:",
        ["Continuar sesión existente", "Iniciar nueva sesión"]
    )
    
    if session_option == "Continuar sesión existente" and st.session_state.available_sessions:
        selected_session = st.selectbox(
            "Selecciona una sesión:",
            st.session_state.available_sessions
        )
        
        if st.button("Cargar Sesión"):
            st.session_state.session_id = selected_session
            # Clear current messages to load from the selected session
            st.session_state.messages = []
            st.success(f"Sesión {selected_session} cargada")
            st.rerun()
    
    elif session_option == "Iniciar nueva sesión":
        if st.button("Crear Nueva Sesión"):
            # Get a new session ID from the API
            try:
                response = requests.get(f"{API_URL}/sessions")
                if response.status_code == 200:
                    data = response.json()
                    st.session_state.session_id = data["session_id"]
                    st.session_state.messages = []
                    st.success(f"Nueva sesión creada: {st.session_state.session_id}")
                    st.rerun()
                else:
                    st.error(f"Error creating new session: {response.text}")
            except Exception as e:
                st.error(f"Error creating new session: {str(e)}")
    
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
    st.subheader("Sobre el Asistente")
    st.markdown("""
    Este asistente te ayuda a crear dietas personalizadas y listas de compra,
    teniendo en cuenta tus intolerancias alimentarias y preferencias dietéticas.
    
    Algunas cosas que puedes preguntar:
    - "Hazme una dieta alta en proteínas"
    - "Tengo intolerancia a la lactosa"
    - "¿Qué alimentos contienen gluten?"
    """)

# Main content area
st.title("Asistente de Dietas Personalizadas 🍎")

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
                f"{API_URL}/message",
                json={"session_id": st.session_state.session_id, "message": prompt}
            )
            
            if response.status_code == 200:
                data = response.json()
                assistant_response = data["response"]
                
                # Add assistant response to chat interface
                st.session_state.messages.append({"role": "assistant", "content": assistant_response})
                with st.chat_message("assistant"):
                    st.markdown(assistant_response)
                
                # Check if any diet information to display
                if "diet" in data["state"] and data["state"]["diet"]:
                    with st.expander("Ver Detalles de la Dieta"):
                        st.subheader("Plan Dietético")
                        
                        # If the diet is serialized, deserialize it
                        diet_data = data["state"]["diet"]
                        if "diet_serialized" in data["state"]:
                            try:
                                diet_data = json.loads(data["state"]["diet_serialized"])
                            except:
                                pass
                        
                        # Display diet information
                        if isinstance(diet_data, dict):
                            for day, meals in diet_data.items():
                                st.markdown(f"#### Día {day}")
                                if isinstance(meals, dict):
                                    for meal_name, foods in meals.items():
                                        st.markdown(f"**{meal_name.capitalize()}:**")
                                        if isinstance(foods, dict):
                                            food_items = [f"{food} - {amount[0]} {amount[1]}" 
                                                        for food, amount in foods.items()]
                                            st.markdown("\n".join([f"- {item}" for item in food_items]))
                                        else:
                                            st.markdown(f"{foods}")
                
                # Check if there's a grocery list to display
                if "grocery_list" in data["state"] and data["state"]["grocery_list"]:
                    with st.expander("Ver Lista de Compra"):
                        st.subheader("Lista de Compra")
                        grocery_list = data["state"]["grocery_list"]
                        if isinstance(grocery_list, list) and grocery_list:
                            # Display as a dataframe if it has a structured format
                            if isinstance(grocery_list[0], dict):
                                df = pd.DataFrame(grocery_list)
                                st.dataframe(df)
                            else:
                                # Display as a simple list
                                st.markdown("\n".join([f"- {item}" for item in grocery_list]))
                                
            else:
                st.error(f"Error: {response.text}")
        except Exception as e:
            st.error(f"Error connecting to API: {str(e)}")
            if "Connection refused" in str(e):
                st.error("The API server is not running. Make sure to start the API server first.")