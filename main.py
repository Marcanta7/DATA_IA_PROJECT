from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from nodes.arquitecture import workflow
from nodes.states import DietState
from typing import List, Optional
import os

app = FastAPI(title="Agente Dietista API", description="API para interactuar con el agente dietista")

# Modelos Pydantic para validación
class DietaRequest(BaseModel):
    edad: int
    peso: float
    objetivos: str
    intolerancias: List[str] = []
    alimentos_prohibidos: List[str] = []
    presupuesto: Optional[float] = None

class ListaCompraRequest(BaseModel):
    dieta: dict

@app.post("/crear-dieta", summary="Crea un plan dietético personalizado")
async def crear_dieta_endpoint(request: DietaRequest):
    """
    Crea una dieta basada en:
    - Edad
    - Peso
    - Objetivos (ej: perder peso, ganar músculo)
    - Intolerancias alimentarias
    - Alimentos prohibidos
    - Presupuesto opcional
    """
    try:
        # Inicializar estado
        initial_state = DietState(
            edad=request.edad,
            peso=request.peso,
            objetivos=request.objetivos,
            forbidden_foods=request.alimentos_prohibidos,
            budget=request.presupuesto
        )
        
        # Ejecutar workflow
        result = workflow.run(initial_state)
        
        return {
            "dieta": result.diet,
            "lista_compra": result.grocery_list
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy", "model": "gemini-2.0-flash-001"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)