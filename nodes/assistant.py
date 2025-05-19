from typing import Dict, Any
from states import DietState
from langchain_google_genai import ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv
import json

load_dotenv()
api_key = os.getenv('GOOGLE_API_KEY')

model = ChatGoogleGenerativeAI(model="gemini-2.0-flash-001", api_key=api_key)

def load_prompt(path: str) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

prompts = load_prompt("src//prompts.json")

def router(state: DietState) -> DietState:
    print("[NODE] router")
    """
    Analiza el mensaje del usuario y decide qué nodo activar a continuación.
    """
    
    # Asegura que state.messages es una lista
    if not getattr(state, "messages", None):
        state.messages = []
    # Busca el último mensaje del usuario de forma robusta
    prompt_user = ""
    for message in reversed(state.messages):
        if isinstance(message, dict) and message.get("role") == "user" and message.get("content"):
            prompt_user = message["content"]
            break
    if not prompt_user:
        print("[WARN router] No se encontró mensaje de usuario válido en el historial.")

    router_prompt = prompts["router_prompt"].format(
        user_message=prompt_user
    )

    response = model.invoke(router_prompt)
    normalized = response.content.strip().replace('"', '').replace("'", "").lower()

    # Elimina todos los mensajes del assistant excepto los dos últimos
    assistant_msgs = [m for m in state.messages if m.get("role") == "assistant"]
    if len(assistant_msgs) > 2:
        # Conserva solo los dos últimos
        keep = set(id(m) for m in assistant_msgs[-2:])
        state.messages = [m for m in state.messages if m.get("role") != "assistant" or id(m) in keep]

    # Nueva lógica: usar el resultado exacto del router_prompt
    if normalized == "intolerancias_y_dieta":
        state.next = "intolerancias"
        state.next_after_intolerancias = "experto_dietas"
    elif normalized == "intolerancias":
        state.next = "intolerancias"
        state.next_after_intolerancias = "mensaje_intolerancias"
    elif normalized == "generar_dieta":
        state.next = "experto_dietas"
    else:
        state.next = "otros"
    return state