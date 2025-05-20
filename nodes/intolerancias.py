from dotenv import load_dotenv
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from states import DietState, IntolerancesState, ForbiddenFoodsState, EliminationUpdateState
from duckduckgo_search import DDGS 
import json
from utils import identify_removed_intolerances
import logging

load_dotenv()

api_key = os.getenv('GOOGLE_API_KEY')

model = ChatGoogleGenerativeAI(model="gemini-2.0-flash-001", api_key=api_key)

# Configure logging
logger = logging.getLogger("diet-agent-app")

def load_prompt(path: str) -> dict:
    """
    Load prompts from JSON file with robust path handling.
    Will try multiple paths and provide a fallback if no file is found.
    """
    # List of possible paths to try
    possible_paths = [
        path,                                    # Original path
        path.replace('//', '/'),                 # Fix double slash
        'src/prompts.json',                      # Root relative
        '/app/src/prompts.json',                 # Absolute in container
        os.path.join(os.path.dirname(__file__), '..', 'src', 'prompts.json'),  # Relative to script
        os.path.join(os.path.dirname(__file__), 'prompts.json'),  # Same directory as script
        'prompts.json',                          # Current directory
    ]
    
    # Log attempted paths
    logger.info(f"Looking for prompts.json in multiple locations")
    
    # Try each path
    for p in possible_paths:
        try:
            logger.info(f"Trying to open prompts.json at: {p}")
            with open(p, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"Successfully loaded prompts from: {p}")
                return data
        except (FileNotFoundError, IsADirectoryError):
            logger.info(f"File not found at: {p}")
            continue
        except Exception as e:
            logger.error(f"Error loading file at {p}: {str(e)}")
            continue
    
    # If we get here, none of the paths worked
    logger.error(f"Failed to find prompts.json in any location")
    
    # Create minimal default prompts
    logger.info("Creating minimal default prompts as fallback")
    default_prompts = {
        "extract_intolerances_prompt": """
        Based on the user's message, extract any food intolerances they mention.
        User text: {user_text}
        Known intolerances: {known_intolerances}
        """,
        "duckduckgo_query": "foods to avoid with {intolerance} intolerance or allergy",
        "extract_forbidden_foods_prompt": """
        Based on the search results about {intolerance} intolerance, extract a list of foods that should be avoided.
        Known forbidden foods: {known_foods}
        Raw text: {raw_text}
        """,
        "detect_no_longer_intolerant_prompt": """
        Analyze if the user text indicates they are no longer intolerant to certain foods.
        User text: {user_text}
        Previous intolerances: {previous_intolerances}
        Previous forbidden foods: {forbidden_previous_foods}
        """
    }
    return default_prompts

try:
    prompts = load_prompt("src//prompts.json")
    logger.info("Successfully loaded prompts")
except Exception as e:
    logger.error(f"Error loading prompts: {str(e)}")
    # Fallback to minimal prompts if loading fails
    prompts = {
        "extract_intolerances_prompt": """
        Based on the user's message, extract any food intolerances they mention.
        User text: {user_text}
        Known intolerances: {known_intolerances}
        """,
        "duckduckgo_query": "foods to avoid with {intolerance} intolerance or allergy",
        "extract_forbidden_foods_prompt": """
        Based on the search results about {intolerance} intolerance, extract a list of foods that should be avoided.
        Known forbidden foods: {known_foods}
        Raw text: {raw_text}
        """,
        "detect_no_longer_intolerant_prompt": """
        Analyze if the user text indicates they are no longer intolerant to certain foods.
        User text: {user_text}
        Previous intolerances: {previous_intolerances}
        Previous forbidden foods: {forbidden_previous_foods}
        """
    }
    logger.info("Using fallback prompts")

def intolerance_search(state: DietState) -> DietState:
    """
    This node is an intorlerance search that will help the user with their intolerances.
    It will search the users intolerances and then will return a list of foods that they are intolerant to.

    Args:
        state.intolerances (List[str]): list of intolerances

    Returns:
        str: list of foods that the user is intolerant to
    """

    # Obtiene el último mensaje enviado por el usuario
    prompt_user = ""
    for message in reversed(state.messages):
        if message.get("role") == "user" and message.get("content"):
            prompt_user = message["content"]
            break

    # Identificar y eliminar intolerancias que el usuario ya no tiene
    intolerances_to_remove = identify_removed_intolerances(prompt_user, state.intolerances)
    
    # Filtra la lista de intolerancias para quitar las que ya no aplican    
    state.intolerances = [
        intolerance for intolerance in state.intolerances
        if intolerance.lower() not in [item.lower() for item in intolerances_to_remove]
    ]

    # Prepara el prompt para extraer nuevas intolerancias del mensaje del usuario
    extraction_intolerances_prompt = prompts['extract_intolerances_prompt'].format(
        user_text=prompt_user,
        known_intolerances=json.dumps(state.intolerances)
    )

    # Utiliza un modelo de IA para identificar nuevas intolerancias mencionadas por el usuario
    new_intolerances = model.with_structured_output(IntolerancesState).invoke(extraction_intolerances_prompt)
    
    # Añade las nuevas intolerancias identificadas a la lista existente
    state.intolerances.extend(new_intolerances["intolerances"])

    # Plantilla para construir la consulta de búsqueda en DuckDuckGo
    query_template = prompts["duckduckgo_query"]

    # Para cada nueva intolerancia, busca información sobre alimentos prohibidos relacionados
    with DDGS() as ddgs:
        for intolerance in new_intolerances["intolerances"]:
            # Crea la consulta de búsqueda para esta intolerancia específica
            query_search = query_template.format(intolerance=intolerance)
            searchs = []

            # Recopila los primeros 5 resultados de la búsqueda
            for result in ddgs.text(query_search, max_results=5):
                searchs.append(result['body'])
            
            # Une todos los resultados de búsqueda en un solo texto
            raw_text = "\n".join(searchs)
            
            # Prepara el prompt para extraer alimentos prohibidos del texto obtenido
            extraction_foods_prompt = prompts['extract_forbidden_foods_prompt'].format(
                intolerance=intolerance,
                known_foods=json.dumps(state.forbidden_foods), 
                raw_text=raw_text
            )

            # Utiliza el modelo para identificar alimentos prohibidos basados en la intolerancia
            new_forbidden_foods = model.with_structured_output(ForbiddenFoodsState).invoke(extraction_foods_prompt)
            # Añade los nuevos alimentos prohibidos a la lista existente
            state.forbidden_foods.extend(new_forbidden_foods['forbidden_foods'])

    # Elimina duplicados de las listas de intolerancias y alimentos prohibidos
    state.intolerances = list(set(state.intolerances))
    state.forbidden_foods = list(set(state.forbidden_foods))
    
    # Detecta si el usuario ha indicado que ya no tiene ciertas intolerancias
    detect_no_longer_intolerant_prompt = prompts["detect_no_longer_intolerant_prompt"].format(
        user_text=prompt_user,
        previous_intolerances=json.dumps(state.intolerances),
        forbidden_previous_foods=json.dumps(state.forbidden_foods),
    )
    
    # Analiza el mensaje del usuario para identificar intolerancias o alimentos a eliminar
    elimination_update = model.with_structured_output(EliminationUpdateState).invoke(detect_no_longer_intolerant_prompt)
    
    # Filtra para asegurarse de que solo se eliminen intolerancias mencionadas explícitamente en el mensaje
    elimination_update.intolerancias = [
        intolerancia for intolerancia in elimination_update.intolerancias
        if intolerancia.lower() in prompt_user.lower()
    ]

    # Si hay elementos a eliminar, actualiza las listas correspondientes
    if elimination_update.eliminate:
        # Elimina intolerancias que ya no aplican
        for intolerace in elimination_update.intolerancias:
            if intolerace in state.intolerances:
                state.intolerances.remove(intolerace)
            else:
                # Mensaje de depuración si no se encuentra la intolerancia en la lista
                print(f"Intolerancia {intolerace} no encontrada en la lista de intolerancias.")
        
        # Elimina alimentos prohibidos que ya no aplican
        for food in elimination_update.alimentos:
            if food in state.forbidden_foods:
                state.forbidden_foods.remove(food)
            else:
                # Mensaje de depuración si no se encuentra el alimento en la lista
                print(f"Alimento {food} no encontrado en la lista de alimentos prohibidos.")
    
    # Devuelve el estado actualizado
    return state

"""
PARA EL QUE LO QUIERA PROBAR QUE DESCOMENTE EL CODIGO DE ABAJO:
"""

# if __name__ == "__main__":
#    initial_state = {
#         'intolerances': ['gluten', 'lactosa'],
#         'forbidden_foods': ['cebada', 'leche', 'cócteles', 'pizzas', 'masas', 'triticale', 'escanda', 'panes', 'licores de crema', 'farro', 'cereales del desayuno', 'kamut', 'bulgur', 'productos lácteos', 'espelta', 'sopas', 'productos cárnicos', 'pasta', 'rebozados', 'centeno', 'galletas', 'hamburguesas', 'salsas', 'pasteles', 'trigo'],
#         'diet': [],
#         'budget': 50.0,
#         'grocery_list': [],
#         'messages': [{'role': 'user', 'content': 'Al final si que puedo comer pan'}]
#         }
#    state = intolerance_search(initial_state)
#    print(state)