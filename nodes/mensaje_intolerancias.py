"""
Nodo de LangGraph que simplemente avisa al usuario que ha entendido las intolerancias detectadas.
"""
from states import DietState

def mensaje_intolerancias(state: DietState) -> DietState:
    print("[NODE] mensaje_intolerancias")
    intolerancias = state.intolerances if hasattr(state, 'intolerances') else []
    if intolerancias:
        mensaje = f"He entendido que tienes intolerancias a: {', '.join(intolerancias)}."
    else:
        mensaje = "No he detectado intolerancias específicas."
    from utils import append_message
    append_message(state, {"role": "assistant", "content": mensaje})
    return state
