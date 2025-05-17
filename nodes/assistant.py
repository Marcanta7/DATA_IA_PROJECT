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
    """
    Analiza el mensaje del usuario y decide qué nodo activar a continuación.
    """
    
    # Busca el último mensaje del usuario
    prompt_user = ""
    for message in reversed(state.messages):
        if message.get("role") == "user" and message.get("content"):
            prompt_user = message["content"]
            break

    router_prompt = prompts["router_prompt"].format(
        user_message=prompt_user
    )

    response = model.invoke(router_prompt)
    normalized = response.content.strip().replace('"', '').replace("'", "").lower()

    # Determina el siguiente nodo
    if normalized in ["intolerancias", "intolerancia", "alergia", "alergias"]:
        state.next = "intolerancias"
    elif normalized in ["generar_dieta", "dieta", "dietas", "experto", "experto dietas", "crear dieta"]:
        state.next = "experto_dietas"
    else:
        state.next = "otros"
    return state