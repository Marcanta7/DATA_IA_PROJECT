from langgraph.graph import MessageState
from typing import Optional, List, TypedDict, Annotated
from langgraph.graph.message import add_messages

class DietState(MessageState):
    intolerances: List[str] = []
    forbidden_foods: List[str] = []
    diet: Dict[int, Dict[str, Dict[str, Tuple[float, str]]]]
    budget: Optional[float] = None
    


class SearchState(TypedDict):
    query: str

class IntolerancesState(TypedDict):
    intolerances: List[str]

class ForbiddenFoodsState(TypedDict):
    forbidden_foods: List[str]