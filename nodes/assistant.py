from typing import Dict, Any
from states import DietState
from langchain_google_genai import ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('GOOGLE_API_KEY')

model = ChatGoogleGenerativeAI(model="gemini-2.0-flash-001", api_key=api_key)

def router(state: DietState) -> Dict[str, Any]:
    """
    Analiza el mensaje del usuario y decide qué nodo activar a continuación.
    
    Args:
        state: Estado actual del agente
    
    Returns:
        Diccionario con el siguiente nodo a ejecutar
    """
    # Obtener el último mensaje del usuario
    user_message = ""
    for message in reversed(state["messages"]):
        # Soporta tanto dicts como HumanMessage
        role = None
        content = None
        if isinstance(message, dict):
            role = message.get("role")
            content = message.get("content")
        else:
            # HumanMessage o similar
            role = getattr(message, "role", None) or getattr(message, "type", None)
            content = getattr(message, "content", None)
        if role == "user":
            user_message = content
            break
    
    # Prompt para determinar la intención del usuario
    router_prompt = """
    Analiza el siguiente mensaje del usuario y determina su intención principal.
    
    Mensaje del usuario: {user_message}
    
    Elige una de las siguientes opciones:
    - "intolerancias": Si el usuario menciona alergias, intolerancias alimentarias o restricciones dietéticas.
    - "generar_dieta": Si el usuario pide una dieta, plan alimenticio o menú.
    - "lista_compra": Si el usuario solicita una lista de compra basada en la dieta.
    - "informacion": Si el usuario pide información general sobre dietas o nutrición.
    - "chat": Para cualquier otra consulta o conversación general.
    
    Responde solo con una de estas opciones sin explicaciones adicionales.
    """
    
    # Enviar el prompt al modelo
    response = model.invoke(router_prompt.format(user_message=user_message))
    intent = response.content.strip().lower()
    
    # Definir el siguiente nodo basado en la intención detectada
    if "intolerancias" in intent:
        return {"next": "intolerancias"}
    elif "generar_dieta" in intent or "generar dieta" in intent or "dieta" in intent:
        return {"next": "experto_dietas"}
    elif "lista_compra" in intent or "lista de la compra" in intent:
        return {"next": "experto_dietas"}
    elif "informacion" in intent or "información" in intent:
        return {"next": "experto_dietas"}
    elif "otros" in intent:
        return {"next": "otros"}
    else:
        return {"next": "otros"}