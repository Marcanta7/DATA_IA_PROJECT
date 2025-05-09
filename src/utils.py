# prepare_embeddings.py

import pandas as pd
import faiss
import numpy as np
import kagglehub
import json
import os
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv
import spacy

'''
# 1. Cargar las variables de entorno
load_dotenv()

# 2. Descargar dataset de Kaggle
path = kagglehub.dataset_download("thegurusteam/mercadona-es-product-pricing")
print(f"✅ Dataset descargado en: {path}")

# 3. Cargar productos.json
products_path = os.path.join(path, "thegurus-opendata-mercadona-es-products.csv")

df = pd.read_csv(products_path)

# 4. Preparar textos para embeddings
df = df[df["name"].notna()]  # Filtramos solo productos con nombre

def build_text(row):
    return f"{row['name']} - {row.get('description', '')}"

texts = df.apply(build_text, axis=1).tolist()

# 5. Crear embeddings usando Google
embedding_model = GoogleGenerativeAIEmbeddings(
    model="models/embedding-001",
    google_api_key=os.getenv("GOOGLE_API_KEY")
)

print("🚀 Generando embeddings...")
embeddings = embedding_model.embed_documents(texts)

# 6. Crear FAISS index
dimension = len(embeddings[0])
index = faiss.IndexFlatL2(dimension)
index.add(np.array(embeddings))

# 7. Guardar FAISS index
faiss.write_index(index, "faiss_products.index")
print("✅ FAISS index guardado en 'faiss_products.index'")

# 8. Guardar mapping de productos
with open("products_mapping.json", "w", encoding="utf-8") as f:
    json.dump(products_data, f, indent=2, ensure_ascii=False)

print("✅ Mapeo de productos guardado en 'products_mapping.json'")
'''

nlp = spacy.load("es_core_news_sm")

def identify_removed_intolerances(user_prompt: str, current_intolerances: list) -> list:
    """
    Identifica las intolerancias que el usuario menciona que ya no tiene.
    """
    removed = []
    doc = nlp(user_prompt.lower())
    negations = set([token.head.text for token in doc if token.dep_ == 'neg'])

    for intolerance in current_intolerances:
        intolerance_doc = nlp(intolerance.lower())
        for neg in negations:
            # Buscar si la intolerancia aparece después de una negación
            for token in intolerance_doc:
                if token.text in doc.text and token.i > [t.i for t in doc if t.text == neg][0]:
                    removed.append(intolerance)
                    break # Si se encuentra una negación, pasar a la siguiente intolerancia
            if removed and intolerance in removed:
                break # Evitar añadir la misma intolerancia varias veces

        # Buscar frases explícitas como "ya no soy intolerante a la ..."
        if f"no soy intolerante a {intolerance.lower()}" in doc.text:
            if intolerance not in removed:
                removed.append(intolerance)

    return list(set(removed))