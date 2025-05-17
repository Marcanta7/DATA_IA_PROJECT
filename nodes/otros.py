from typing import Dict, Any
from states import DietState

def otros(state: DietState) -> DietState:
    """
    Nodo que maneja las interacciones fuera del ámbito de las dietas.
    Informa al usuario que solo se pueden responder preguntas relacionadas con planes alimenticios.
    
    Args:
        state: Estado actual del agente
        
    Returns:
        Respuesta del nodo con el mensaje correspondiente.
    """
    print("¡Hola! Soy un asistente especializado en nutrición y dietas personalizadas. "
                    "Puedo ayudarte a crear planes alimenticios, resolver dudas sobre intolerancias, "
                    "o darte ideas de menús saludables.\n\n"
                    "No puedo responder preguntas fuera de este tema. "
                    "¿En qué puedo ayudarte relacionado con tu alimentación?")
    
    return state

    """return {
        "messages": [
            {
                "role": "assistant",
                "content": (
                    "¡Hola! Soy un asistente especializado en nutrición y dietas personalizadas. "
                    "Puedo ayudarte a crear planes alimenticios, resolver dudas sobre intolerancias, "
                    "o darte ideas de menús saludables.\n\n"
                    "No puedo responder preguntas fuera de este tema. "
                    "¿En qué puedo ayudarte relacionado con tu alimentación?"
                )
            }
        ],
        "next": None  # Indica que el flujo se detiene hasta nueva entrada del usuario
    }"""
