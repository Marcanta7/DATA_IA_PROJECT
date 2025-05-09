from dotenv import load_dotenv
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from states import DietState, SearchState, IntolerancesState, ForbiddenFoodsState
from duckduckgo_search import DDGS 
import json
import kagglehub
from utils import identify_removed_intolerances

load_dotenv()

api_key = os.getenv('GOOGLE_API_KEY')

model = ChatGoogleGenerativeAI(model="gemini-2.0-flash-001", api_key=api_key)

def load_prompt(path: str) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

prompts = load_prompt("src//prompts.json")

def assistant_dietician(state: DietState) -> str:
    """
    This node is an assistant dietician that will help the user with their diet.
    It will ask the user for their intolerances, diet, and budget. It will then give the user a list of recipes that fit their needs.

    The assistant has the following tools:
    - Intolerance_search: to search in DuckDuckGo for which foods the user is intolerant to.
    - Diet_search: search the best diets for the user.
    - Budget_search: search for the best recipes that fit the user's budget with the db of the supermarket.

    Args:
        state.intolerances (List[str]): list of intolerances
        state.diet (List[str]): list of diets done by the user
        state.budget (float): budget of the user

    Returns:
        str: supermarket shopping list
    """
    pass  # Placeholder for implementation
    


def intolerance_search(state: DietState) -> DietState:
    """
    This node is an intorlerance search that will help the user with their intolerances.
    It will search the users intolerances and then will return a list of foods that they are intolerant to.

    Args:
        state.intolerances (List[str]): list of intolerances

    Returns:
        str: list of foods that the user is intolerant to
    """

    prompt_user = ""
    for message in reversed(state["messages"]):
        if message["role"] == "user":
           prompt_user = message["content"] 
           break

    # Identificar y eliminar intolerancias que el usuario ya no tiene
    intolerances_to_remove = identify_removed_intolerances(prompt_user, state['intolerances'])
    state['intolerances'] = [
        intolerance for intolerance in state['intolerances']
        if intolerance.lower() not in [item.lower() for item in intolerances_to_remove]
    ]

    extraction_intolerances_prompt = prompts['extract_intolerances_prompt'].format(
        user_text=prompt_user,
        known_intolerances=json.dumps(state['intolerances'])
    )
    new_intolerances = model.with_structured_output(IntolerancesState).invoke(extraction_intolerances_prompt)
    
    state['intolerances'].extend(new_intolerances['intolerances'])

    query_template = prompts["duckduckgo_query"]

    with DDGS() as ddgs:
        for intolerance in new_intolerances['intolerances']:
            query_search = query_template.format(intolerance=intolerance)
            searchs = []

            for result in ddgs.text(query_search, max_results=5):
                searchs.append(result['body'])
            
            raw_text = "\n".join(searchs)
            
            extraction_foods_prompt = prompts['extract_forbidden_foods_prompt'].format(
                intolerance=intolerance,
                known_foods=json.dumps(state['forbidden_foods']), 
                raw_text=raw_text
            )

            new_forbidden_foods = model.with_structured_output(ForbiddenFoodsState).invoke(extraction_foods_prompt)
            state['forbidden_foods'].extend(new_forbidden_foods['forbidden_foods'])

    state['intolerances'] = list(set(state['intolerances']))
    state['forbidden_foods'] = list(set(state['forbidden_foods']))
    return state


def diet_expertise(state: DietState) -> DietState:
    """
    This node generates a weekly diet plan based on forbidden foods and previous diet history.

    Args:
        state (DietState): Must contain 'forbidden_foods' and 'summary' (diet_summary).

    Returns:
        DietState: Updated state with the new diet plan in 'diet' field.
    """


    weekly_diet_prompt = prompts["weekly_diet_prompt"].format(
        forbidden_foods=", ".join(state["forbidden_foods"]),
        diet_summary=state["summary"]
    )

    response = model.invoke(weekly_diet_prompt)

    state["diet"] = response.content
    return state
    

if __name__ == "__main__":
    initial_state = {
        'intolerances': ['lactosa'],
        'forbidden_foods': ['cócteles', 'productos lácteos', 'leche', 'licores de crema'],
        'diet': [],
        'budget': 50.0,
        'grocery_list': [],
        'messages': [{'role': 'user', 'content': 'Al final no soy intolerante a la lactosa, pero sí a los cócteles y productos lácteos.'}]
        }

    state = intolerance_search(initial_state)
    print(state)