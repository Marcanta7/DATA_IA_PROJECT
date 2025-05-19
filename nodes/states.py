from typing import Optional, List, TypedDict, Annotated, Dict, Tuple
from pydantic import BaseModel, Field
import operator

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple

@dataclass
class DietState:
    intolerances: List[str] = field(default_factory=list)
    forbidden_foods: List[str] = field(default_factory=list)
    diet: Dict[str, Dict[str, Dict[str, Tuple[float, str]]]] = field(default_factory=dict)
    budget: Optional[float] = None
    grocery_list: List[str] = field(default_factory=list)
    info_dietas: str = ""
    next: Optional[str] = None
    next_after_intolerancias: Optional[str] = None
    messages: Annotated[List[dict], operator.add] = field(default_factory=list)  # historial completo
    assistant_messages: List[str] = field(default_factory=list)  # solo los mensajes assistant, siempre strings simples


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
