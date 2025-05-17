from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Agente Dietista API")

class DietaRequest(BaseModel):
    edad: int
    peso: float
    objetivos: str
    intolerancias: list[str] = []
    alimentos_prohibidos: list[str] = []
    presupuesto: float | None = None

@app.post('/crear-dieta', summary='Genera una dieta personalizada', tags=['Dieta'])
async def crear_dieta(dieta: DietaRequest):
    """
    Crea una dieta personalizada basada en:
    - Edad, peso y objetivos del usuario
    - Intolerancias y alimentos prohibidos
    - Presupuesto opcional
    
    Ejemplo:
    {
        "edad": 30,
        "peso": 70.5,
        "objetivos": "perder peso",
        "intolerancias": ["lactosa"],
        "alimentos_prohibidos": ["nueces"],
        "presupuesto": 150.0
    }
    """
    try:
        logger.info(f"Solicitud recibida: {dieta.dict()}")
        
        from nodes.crear_dieta import generar_dieta
        
        # Validación adicional
        if dieta.edad < 18:
            raise ValueError("Edad mínima es 18 años")
        if dieta.peso <= 0:
            raise ValueError("Peso debe ser positivo")
            
        resultado = generar_dieta(**dieta.dict())
        
        return {
            "success": True,
            "data": resultado,
            "message": "Dieta generada exitosamente"
        }
        
    except ImportError:
        logger.error("Error: No se encontró el módulo crear_dieta")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor - módulo no encontrado"
        )
    except ValueError as e:
        logger.warning(f"Validación fallida: {str(e)}")
        raise HTTPException(
            status_code=422,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar la solicitud: {str(e)}"
        )