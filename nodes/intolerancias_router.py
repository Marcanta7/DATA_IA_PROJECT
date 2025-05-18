"""
Nodo de LangGraph que decide, tras analizar el último mensaje del usuario, si debe ir a mensaje_intolerancias o a experto_dietas.
Utiliza el LLM y un prompt específico para decidir la intención tras el paso de intolerancias.
"""
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

def intolerancias_router(state: DietState) -> DietState:
    print("[NODE] intolerancias_router")
    """
    Decide si tras intolerancias debe ir a mensaje_intolerancias o experto_dietas.
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
        print("[WARN intolerancias_router] No se encontró mensaje de usuario válido en el historial.")
    router_prompt = prompts["intolerancias_router_prompt"].format(user_message=prompt_user)
    response = model.invoke(router_prompt)
    normalized = response.content.strip().replace('"', '').replace("'", "").lower()
    print("ESTO SACA EL LLM: ", normalized)
    print(f"[DEBUG intolerancias_router] Valor devuelto por el modelo: '{normalized}'")
    state.next_after_intolerancias = ("experto_dietas" if normalized == "quiere_dieta" else "mensaje_intolerancias")
    return state
