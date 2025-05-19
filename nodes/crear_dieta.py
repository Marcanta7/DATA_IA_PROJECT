from states import DietState
from langchain_google_genai import ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('GOOGLE_API_KEY')

def crear_dieta(state: DietState) -> DietState:
    print("[NODE] crear_dieta")
    """Crea una dieta basada en las intolerancias y alimentos prohibidos."""
    model = ChatGoogleGenerativeAI(model="gemini-2.0-flash-001", api_key=api_key)

    import ast
    prompt = (
        "Genera una dieta semanal vegana en formato de diccionario de Python, con la siguiente estructura exacta:\n"
        "{\n"
        "  1: {\n"
        "    'desayuno': {'alimento1': (cantidad, 'unidad'), ...},\n"
        "    'comida': {...},\n"
        "    'cena': {...}\n"
        "  },\n"
        "  ...\n"
        "  7: {...}\n"
        "}\n"
        "Donde la clave principal es el día de la semana (1=lunes, 7=domingo), cada comida es un diccionario de alimentos, y cada alimento es una tupla (cantidad, unidad (solo usa g o ml como unidad)). "
        "No añadas texto ni explicaciones, solo el diccionario Python. "
        f"Ten en cuenta estas intolerancias: {state.intolerances}, y estos alimentos prohibidos: {state.forbidden_foods}. "
        f"Información adicional relevante: {state.info_dietas}"
    )

    response = model.invoke(prompt)

    # Extraer el contenido de la respuesta de forma segura
    if hasattr(response, "content"):
        content = response.content
    elif isinstance(response, dict) and "content" in response:
        content = response["content"]
    else:
        content = str(response)

    # Intentar extraer solo el bloque de diccionario de la respuesta
    import re
    dieta_dict = None
    dict_match = re.search(r"\{[\s\S]*\}", content)
    dict_str = dict_match.group(0) if dict_match else content
    # Limpiar saltos de línea y espacios innecesarios
    dict_str = dict_str.strip()
    try:
        dieta_dict = ast.literal_eval(dict_str)
        if not isinstance(dieta_dict, dict):
            raise ValueError("La respuesta no es un diccionario.")
        state.diet = dieta_dict
        # Añade la dieta como mensaje del asistente usando append_message
        resumen = "¡Aquí tienes tu dieta semanal!\n" + str(state.diet)
        from utils import append_message
        append_message(state, {"role": "assistant", "content": resumen})
    except Exception as e:
        print(f"[WARN] No se pudo convertir la dieta a dict: {e}")
        state.diet = {"texto": content, "error": "La dieta generada no tiene el formato esperado."}
        # SOLO añade un mensaje de error, nunca ambos
        from utils import append_message
        append_message(state, {"role": "assistant", "content": "No se pudo generar la dieta correctamente."})
        # Limita a los dos últimos mensajes assistant
        assistant_msgs = [m for m in state.messages if m.get("role") == "assistant"]
        print("Len assistant_msgs:", len(assistant_msgs))
        if len(assistant_msgs) > 2:
            keep = set(id(m) for m in assistant_msgs[-2:])
            state.messages = [m for m in state.messages if m.get("role") != "assistant" or id(m) in keep]
    
    return state