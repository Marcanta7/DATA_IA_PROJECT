import weaviate
from weaviate.classes.query import Filter
from weaviate.classes.init import Auth
import torch
from sentence_transformers import SentenceTransformer
import os
from dotenv import load_dotenv
from states import DietState
from langchain.tools import tool

load_dotenv()

# Conexión y modelo cargado (igual que en tu script)
WEAVIATE_URL = os.getenv("WEAVIATE_URL")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")
CLASS_NAME = "InfoDietasAplanado"
MODEL_NAME = "intfloat/multilingual-e5-large"

# --- Inicialización de cliente y modelo de embeddings ---
client = weaviate.connect_to_weaviate_cloud(
    cluster_url=WEAVIATE_URL,
    auth_credentials=Auth.api_key(WEAVIATE_API_KEY),
)

device = "cuda" if torch.cuda.is_available() else "cpu"
embedding_model = SentenceTransformer(MODEL_NAME, device=device)

def buscar_info_dietas(state: DietState, k: int = 5) -> DietState:
    """Busca información relevante sobre dietas, almacenada en base de Weaviate (colección InfoDietas) para consultar."""
    try:
        # Asegurar que messages es una lista de dicts
        messages = state["messages"]
        if not isinstance(messages, list) or not messages:
            raise ValueError("El estado no contiene mensajes válidos.")
        last_msg = messages[-1]
        if isinstance(last_msg, dict):
            query = last_msg.get("content", "")
        else:
            query = str(last_msg)
        query_with_prefix = f"query: {query}" if "e5" in MODEL_NAME.lower() else query
        query_embedding = embedding_model.encode(query_with_prefix).tolist()

        collection = client.collections.get(CLASS_NAME)

        results = collection.query.near_vector(
            near_vector=query_embedding,
            limit=k
        )

        if not results.objects:
            state["info_dietas"] = "No se encontró información relevante en la base de conocimiento."
            return state

        response = ""
        for obj in results.objects:
            texto = obj.properties.get("text", "")
            pagina = obj.properties.get("page_number", 0)
            fuente = obj.properties.get("source_pdf", "unknown")
            response += f"\n📄 *{fuente}* (página {pagina}):\n{texto.strip()}\n"

        # Añade la info al estado
        state["info_dietas"] = response.strip()
        return state

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        state["info_dietas"] = f"[ERROR] No se encontró información relevante en la base de conocimiento. Detalles: {e}\nTraceback:\n{tb}"
        return state
    finally:
        try:
            client.close()
        except Exception:
            pass
    
"""
PARA EL QUE LO QUIERA PROBAR QUE DESCOMENTE EL CODIGO DE ABAJO:
"""

# if __name__ == "__main__":
#     try:
#         state = DietState(
#             intolerances=[],
#             forbidden_foods=[],
#             diet={},
#             budget=None,
#             grocery_list=[],
#             messages=[{"role": "user", "content": "Dieta vegana"}]
#         )
#         result = buscar_info_dietas(state)
#         print(result)
#     finally:
#         try:
#             client.close()
#         except Exception:
#             pass