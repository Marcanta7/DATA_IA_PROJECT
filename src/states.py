from langgraph.graph import MessagesState
from typing import Optional, List, TypedDict, Annotated
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

class DietState(MessagesState):
    intolerances: List[str] = []
    forbidden_foods: List[str] = []
    diet: Dict[int, Dict[str, Dict[str, Tuple[float, str]]]]
    budget: Optional[float] = None
    grocery_list: List[str] = None

class SearchState(TypedDict):
    query: str

class IntolerancesState(TypedDict):
    intolerances: List[str]

class ForbiddenFoodsState(TypedDict):  
    forbidden_foods: List[str]

class EliminationUpdateState(BaseModel):
    eliminate: bool = Field(..., description="True si el usuario menciona explícitamente que ya no es intolerante a algo.")
    intolerancias: list[str] = Field(default=[], description="Lista de intolerancias que el usuario ha mencionado explícitamente que ya no tiene, y que están presentes en las intolerancias anteriores.")
    alimentos: list[str] = Field(default=[], description="Alimentos prohibidos anteriores que el usuario menciona explícitamente y que están asociados solo a las intolerancias eliminadas.")
