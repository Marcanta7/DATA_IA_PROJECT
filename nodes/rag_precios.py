import pandas as pd
from sentence_transformers import SentenceTransformer, util
from google.cloud import bigquery

# Load the embeddings model
model = SentenceTransformer('intfloat/multilingual-e5-large')

# Configure BigQuery client - Cloud Run will use the assigned service account
client = bigquery.Client()

# Query to fetch data from the specific table
query = """
SELECT Nombre, Descripcion_del_producto, off_product_name
FROM `diap3-458416.food_data.mercadona_enriched_products_clean`
"""

# Execute the query and load results into a DataFrame
precios_df = client.query(query).to_dataframe()

# Ensure the required columns exist
if 'Nombre' not in precios_df.columns:
    raise ValueError("La tabla debe tener una columna llamada 'Nombre' con los nombres de los productos.")

# Get product names and descriptions combined
productos = (precios_df['Nombre'].astype(str) + " " +
             precios_df['Descripcion_del_producto'].astype(str) + " " +
             precios_df['off_product_name'].astype(str)).tolist()
productos_embeddings = model.encode(productos, convert_to_tensor=True)

def buscar_producto(prompt_usuario, top_k=5):
    """
    Devuelve los top_k productos más similares al prompt_usuario.
    Retorna una lista de tuplas: (nombre, fila, score)
    """
    prompt_emb = model.encode(prompt_usuario, convert_to_tensor=True)
    similitudes = util.cos_sim(prompt_emb, productos_embeddings)[0]
    # Obtener los índices de los top_k productos más similares
    top_indices = similitudes.topk(top_k).indices.cpu().numpy()
    
    resultados = []
    for idx in top_indices:
        nombre = productos[idx]
        fila = precios_df.iloc[idx]
        score = similitudes[idx].item()
        resultados.append((nombre, fila, score))
    
    return resultados

if __name__ == "__main__":
    while True:
        prompt = input("¿Qué producto buscas? ")
        resultados = buscar_producto(prompt, top_k=5)
        print(f"Top 5 productos más parecidos a: '{prompt}'\n")
        for i, (nombre, fila, score) in enumerate(resultados, 1):
            print(f"{i}. {nombre} (score: {score:.2f})")
            print(fila)
            print("-"*60)