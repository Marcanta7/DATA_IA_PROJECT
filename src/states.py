from langgraph.graph import MessagesState
from typing import Optional, List, TypedDict, Annotated
from langgraph.graph.message import add_messages

class DietState(MessagesState):
    intolerances: List[str] = []
    forbidden_foods: List[str] = []
    diet: List[str] = []
    budget: Optional[float] = None
    grocery_list: List[str] = None

class SearchState(TypedDict):
    query: str

class IntolerancesState(TypedDict):
    intolerances: List[str]

class ForbiddenFoodsState(TypedDict):  
    forbidden_foods: List[str]