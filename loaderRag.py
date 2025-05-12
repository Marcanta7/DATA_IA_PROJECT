import os
import fitz  # PyMuPDF
import torch
import weaviate
from sentence_transformers import SentenceTransformer
# Ajusta la importación según tu versión
from langchain_text_splitters import RecursiveCharacterTextSplitter
# from langchain.docstore.document import Document # Ya no necesitamos Document aquí

from weaviate.classes.init import Auth
from weaviate.classes.config import Property, DataType, Configure
import time
import glob
import traceback
import re # Para limpieza

# ... (Conexión a Weaviate, Carga de Modelo igual que antes) ...
# --- 0. Conexión a Weaviate Cloud ---
weaviate_url = os.environ.get("WEAVIATE_URL")
weaviate_api_key = os.environ.get("WEAVIATE_API_KEY")
# ... (error handling) ...
try:
    client = weaviate.connect_to_weaviate_cloud(
        cluster_url=weaviate_url, auth_credentials=Auth.api_key(weaviate_api_key)
    )
    print(f"🔌 Conexión a Weaviate ({weaviate_url}): {client.is_ready()}")
except Exception as e:
    print(f"❌ Error conectando a Weaviate: {e}")
    exit()

# --- 1. Cargar modelo HuggingFace ---
model_name = "intfloat/multilingual-e5-large"
# ... (error handling) ...
try:
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    embedding_model = SentenceTransformer(model_name, device=device)
    EMBEDDING_DIMENSION = embedding_model.get_sentence_embedding_dimension()
    print(f"✅ Modelo cargado ({model_name}) en {embedding_model.device}. Dimensión: {EMBEDDING_DIMENSION}")
except Exception as e:
    print(f"❌ Error cargando modelo '{model_name}': {e}")
    if client.is_connected(): client.close()
    exit()


# --- 2. Extraer y Aplanar Texto del PDF (MODIFICADO) ---
def extract_and_flatten_text_from_pdf(pdf_path):
    """
    Extrae todo el texto de un PDF, lo concatena, y lo limpia/aplana
    eliminando saltos de línea y espacios extra.

    Returns:
        tuple: (cleaned_full_text: str, pdf_base_name: str) o (None, pdf_base_name) si falla.
    """
    all_text = []
    pdf_base_name = os.path.basename(pdf_path)
    try:
        doc = fitz.open(pdf_path)
        print(f"📄 Extrayendo texto de {len(doc)} páginas en '{pdf_base_name}'...")
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            page_text = page.get_text("text", sort=True)
            if page_text.strip():
                all_text.append(page_text)
        doc.close()

        if not all_text:
            print(f"⚠️ No se encontró texto útil en '{pdf_base_name}'.")
            return None, pdf_base_name

        # Concatenar todo el texto con espacios
        full_raw_text = " ".join(all_text)

        # Aplanar: Reemplazar todos los saltos de línea (y tabulaciones) con espacios
        cleaned_full_text = re.sub(r'[\n\t]+', ' ', full_raw_text)
        # Colapsar múltiples espacios en uno solo
        cleaned_full_text = re.sub(r'\s{2,}', ' ', cleaned_full_text).strip()

        print(f"📄 Texto extraído y aplanado de '{pdf_base_name}' (Longitud: {len(cleaned_full_text)}).")
        return cleaned_full_text, pdf_base_name

    except Exception as e:
        print(f"❌ Error abriendo o procesando PDF '{pdf_path}': {e}")
        traceback.print_exc()
        return None, pdf_base_name

# --- 3. Split por Tamaño (MODIFICADO) ---
def split_flattened_text_by_size(flattened_text, source_pdf_name, chunk_size=700, chunk_overlap=150):
    """
    Divide el texto aplanado priorizando el tamaño y el solapamiento.
    """
    if not flattened_text:
        return []

    # Usar RecursiveCharacterTextSplitter pero con separadores mínimos
    # para que se base más en la longitud. El espacio es importante.
    # Si quitas " " podría intentar cortar palabras si no hay más separadores.
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        is_separator_regex=False,
        separators=[" ", ""], # Prioriza espacio, luego caracteres si es necesario
        # keep_separator=False # No necesitamos mantener el espacio necesariamente
    )

    print(f"✂️ Dividiendo texto aplanado de '{source_pdf_name}' por tamaño (chunk_size={chunk_size}, overlap={chunk_overlap})...")

    text_chunks = splitter.split_text(flattened_text)

    # Crear la estructura de salida
    chunks_with_info = []
    for i, chunk_text in enumerate(text_chunks):
        # Filtrado opcional de chunks residuales MUY pequeños (menos probable ahora)
        # min_len = 50 # ejemplo
        # if len(chunk_text) < min_len:
        #     print(f"  -> Saltando chunk residual muy corto (len={len(chunk_text)}): '{chunk_text[:30]}...'")
        #     continue

        chunks_with_info.append({
            "text": chunk_text,
            "page_number": 0, # Placeholder, ya no es relevante
            "source_pdf": source_pdf_name,
            # "chunk_index_overall": i # Índice global opcional
        })

    print(f"✂️ Texto aplanado dividido en {len(chunks_with_info)} chunks.")
    return chunks_with_info

# --- 4. Embeddings con HF (Batch) ---
# (Sin cambios necesarios aquí, sigue esperando lista de dicts con "text")
def embed_text_chunks_batch(chunks_info: list[dict], model_name_for_prefix: str):
    # ... (código igual que antes) ...
    chunks_text = [info["text"] for info in chunks_info]
    if not chunks_text: return []
    print(f"🧠 Generando embeddings para {len(chunks_text)} chunks...")
    start_embed_time = time.time()
    prefix = ""
    if "e5" in model_name_for_prefix.lower():
         prefix = "passage: "
         chunks_text = [prefix + chunk for chunk in chunks_text]
    try:
        embeddings = embedding_model.encode(chunks_text, show_progress_bar=True, batch_size=32)
        print(f"🧠 Embeddings generados en {time.time() - start_embed_time:.2f}s.")
        return embeddings.tolist()
    except Exception as e:
        print(f"❌ Error durante la generación de embeddings: {e}")
        return []

# --- 5. Crear/Verificar clase Weaviate (MODIFICADO - page_number opcional o placeholder) ---
def ensure_weaviate_class(client_instance, class_name, vector_dimension):
    """Verifica si la clase existe, si no, la crea."""
    try:
        if not client_instance.collections.exists(class_name):
            print(f"🏗️ Creando clase '{class_name}' en Weaviate...")
            client_instance.collections.create(
                name=class_name,
                vectorizer_config=Configure.Vectorizer.none(),
                properties=[
                    Property(name="text", data_type=DataType.TEXT, description="Contenido del chunk de texto"),
                    # Mantener page_number como INT pero tratarlo como no fiable o placeholder (e.g., siempre 0)
                    Property(name="page_number", data_type=DataType.INT, description="Placeholder (página no relevante con este método)"),
                    Property(name="source_pdf", data_type=DataType.TEXT, description="Nombre del archivo PDF de origen"),
                ]
            )
            print(f"✅ Clase '{class_name}' creada.")
        else:
            print(f"✅ Clase '{class_name}' ya existe.")
            # Opcional: Verificar propiedades existentes
            # current_config = client_instance.collections.get(class_name).config.get()
            # print(f"   Propiedades existentes: {[prop.name for prop in current_config.properties]}")
    except Exception as e:
        print(f"❌ Error al crear/verificar la clase '{class_name}': {str(e)}")
        raise e

# --- 6. Subir a Weaviate en batches (MODIFICADO - usa page_number=0) ---
def upload_data_to_weaviate(client_instance, class_name, embeddings, chunks_info_list):
    """Sube los datos (propiedades + vector) a Weaviate en batches."""
    # ... (Validaciones iniciales igual que antes) ...
    if not client_instance.is_connected(): #...
        print("❌ Cliente Weaviate no conectado.")
        return
    if not embeddings or not chunks_info_list or len(embeddings) != len(chunks_info_list): #...
        print(f"❌ Error: Desajuste Embeddings/Chunks.")
        return
    try:
        collection = client_instance.collections.get(class_name)
    except Exception as e: #...
        print(f"❌ Error obteniendo la colección '{class_name}': {e}.")
        return

    object_count = 0
    start_upload_time = time.time()
    # Obtener el source_pdf del primer chunk para el mensaje de log
    source_pdf_name = chunks_info_list[0].get("source_pdf", "desconocido") if chunks_info_list else "desconocido"
    print(f"⬆️ Preparando subida de {len(embeddings)} objetos de '{source_pdf_name}' a '{class_name}'...")

    with collection.batch.dynamic() as batch:
        for i, embedding in enumerate(embeddings):
            chunk_info = chunks_info_list[i]
            text_content = chunk_info.get("text", "")
            if not text_content.strip() or embedding is None:
                # print(f"   ⏭️ Saltando chunk vacío o sin embedding.") # Opcional: log detallado
                continue

            properties_payload = {
                "text": text_content,
                "page_number": chunk_info.get("page_number", 0), # Siempre será 0 o el valor asignado en split
                "source_pdf": chunk_info.get("source_pdf", "Unknown"),
            }

            batch.add_object(properties=properties_payload, vector=embedding)
            object_count += 1

    print(f"⬆️ Subida de {object_count} objetos de '{source_pdf_name}' a '{class_name}' finalizada en {time.time() - start_upload_time:.2f}s.")


# --- 7. MAIN (Adaptado al nuevo flujo) ---
if __name__ == "__main__":
    overall_start_time = time.time()

    pdf_folder_path = "/Users/admin/Desktop/AgenteDietas/" # ¡AJUSTA ESTA RUTA!
    # Usa un nombre de clase diferente si cambiaste radicalmente el método de chunking
    NOMBRE_DE_CLASE_UNIFICADO = "InfoDietasAplanado"  # <--- ¡ELIGE Y AJUSTA ESTE NOMBRE!

    print(f"🏛️  Todos los documentos se cargarán en la clase Weaviate: '{NOMBRE_DE_CLASE_UNIFICADO}'")
    # ... (Validaciones de carpeta y búsqueda de PDFs igual que antes) ...
    if not os.path.isdir(pdf_folder_path): #...
         print(f"❌ Error: La carpeta de PDFs no existe: {pdf_folder_path}")
         if client.is_connected(): client.close(); exit()
    pdf_files = list(set(glob.glob(os.path.join(pdf_folder_path, "*.pdf")) + glob.glob(os.path.join(pdf_folder_path, "*.PDF"))))
    if not pdf_files: #...
        print(f"🤷 No se encontraron archivos PDF en: {pdf_folder_path}")
        if client.is_connected(): client.close(); exit()
    print(f"📚 Encontrados {len(pdf_files)} archivos PDF para procesar...")

    total_processed_files = 0
    total_failed_files = 0

    try:
        # Asegurar que la clase existe ANTES del bucle
        ensure_weaviate_class(client, NOMBRE_DE_CLASE_UNIFICADO, EMBEDDING_DIMENSION)

        for pdf_path in pdf_files:
            # 1. Extraer y Aplanar el texto completo del PDF
            flattened_text, pdf_filename = extract_and_flatten_text_from_pdf(pdf_path)

            if flattened_text is None:
                print(f"⚠️ No se pudo procesar o no había texto en '{pdf_filename}'. Saltando.")
                total_failed_files += 1
                continue # Saltar al siguiente PDF

            print(f"\n🚀 Procesando '{pdf_filename}' (aplanado) para añadir a '{NOMBRE_DE_CLASE_UNIFICADO}'")
            start_pdf_time = time.time()

            try:
                # 2. Dividir el texto aplanado por tamaño
                # ¡Ajusta chunk_size y overlap aquí según necesites!
                # Tamaños más grandes pueden ser mejores para RAG si el modelo los soporta
                chunks_info = split_flattened_text_by_size(
                    flattened_text,
                    pdf_filename,
                    chunk_size=1000, # Ejemplo: Aumentado
                    chunk_overlap=200  # Ejemplo: Aumentado
                )
                if not chunks_info:
                    print(f"⚠️ No se generaron chunks de '{pdf_filename}'. Saltando.")
                    total_failed_files += 1
                    continue

                # 3. Generar Embeddings
                embeddings = embed_text_chunks_batch(chunks_info, model_name)
                if not embeddings or len(embeddings) != len(chunks_info):
                     print(f"❌ Error/desajuste en embeddings para '{pdf_filename}'. Saltando subida.")
                     total_failed_files += 1
                     continue

                # 4. Subir datos a Weaviate
                upload_data_to_weaviate(client, NOMBRE_DE_CLASE_UNIFICADO, embeddings, chunks_info)

                total_processed_files += 1
                print(f"✅ Procesamiento de '{pdf_filename}' completado en {time.time() - start_pdf_time:.2f}s.")

            except Exception as e_pdf:
                print(f"\n❌ Error procesando el PDF individual '{pdf_filename}' después de la extracción: {e_pdf}")
                traceback.print_exc()
                total_failed_files += 1
                print(f"⚠️ Saltando '{pdf_filename}' debido a error. Continuando...")
                continue

    except Exception as e_main:
        print(f"\n❌ Error General Crítico: {e_main}")
        traceback.print_exc()

    finally:
        # ... (Resumen y cierre de conexión igual que antes) ...
        print("\n--- Resumen de Ingesta ---")
        print(f"Total de archivos PDF encontrados: {len(pdf_files)}")
        print(f"Archivos procesados y (probablemente) subidos con éxito: {total_processed_files}")
        print(f"Archivos fallidos o saltados: {total_failed_files}")
        print(f"Duración total del proceso: {time.time() - overall_start_time:.2f} segundos.")
        print("--------------------------")
        if client.is_connected():
            client.close()
            print("🚪 Conexión a Weaviate cerrada.")