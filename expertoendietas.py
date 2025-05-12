from langchain.tools import tool
import weaviate
from weaviate.classes.query import Filter
from weaviate.classes.init import Auth
from sentence_transformers import SentenceTransformer
import os
import torch

# Conexión y modelo cargado (igual que en tu script)
WEAVIATE_URL = os.environ["WEAVIATE_URL"]
WEAVIATE_API_KEY = os.environ["WEAVIATE_API_KEY"]
CLASS_NAME = "InfoDietas"
MODEL_NAME = "intfloat/multilingual-e5-large"

# --- Inicialización de cliente y modelo de embeddings ---
client = weaviate.connect_to_weaviate_cloud(
    cluster_url=WEAVIATE_URL,
    auth_credentials=Auth.api_key(WEAVIATE_API_KEY),
)

device = "cuda" if torch.cuda.is_available() else "cpu"
embedding_model = SentenceTransformer(MODEL_NAME, device=device)

@tool
def buscar_info_dietas(query: str, k: int = 5) -> str:
    """Busca información relevante en la base de Weaviate (colección InfoDietas) a partir de una consulta."""
    try:
        # Incluir el prefijo si usas un modelo E5
        query_with_prefix = f"query: {query}" if "e5" in MODEL_NAME.lower() else query
        query_embedding = embedding_model.encode(query_with_prefix).tolist()

        collection = client.collections.get(CLASS_NAME)

        results = collection.query.near_vector(
            near_vector=query_embedding,
            limit=k
        )

        if not results.objects:
            return "No se encontró información relevante en la base de conocimiento."

        response = ""
        for obj in results.objects:
            texto = obj.properties.get("text", "")
            pagina = obj.properties.get("page_number", "?")
            fuente = obj.properties.get("source_pdf", "desconocido")
            response += f"\n📄 *{fuente}* (página {pagina}):\n{texto.strip()}\n"

        return response.strip()

    except Exception as e:
        return f"❌ Error en la búsqueda: {str(e)}"
