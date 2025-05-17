from typing import Dict, Any
from states import DietState

def otros(state: DietState) -> DietState:
    """
    Nodo que maneja las interacciones fuera del ámbito de las dietas.
    Añade el mensaje de respuesta al historial de mensajes (state['messages']) y devuelve el estado actualizado.
    """
    respuesta = (
        "¡Hola! Soy un asistente especializado en nutrición y dietas personalizadas. "
        "Puedo ayudarte a crear planes alimenticios, resolver dudas sobre intolerancias, "
        "o darte ideas de menús saludables.\n\n"
        "No puedo responder preguntas fuera de este tema. "
        "¿En qué puedo ayudarte relacionado con tu alimentación?"
    )
    state.messages.append({"role": "assistant", "content": respuesta})
    return state