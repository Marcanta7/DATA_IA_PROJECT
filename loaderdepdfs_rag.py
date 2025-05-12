import os
import fitz  # PyMuPDF
import torch
import weaviate
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter
from weaviate.classes.init import Auth
from weaviate.classes.config import Property, DataType
import time
import glob # Para encontrar archivos PDF

# --- 0. Conexión a Weaviate Cloud ---
weaviate_url = os.environ.get("WEAVIATE_URL")
weaviate_api_key = os.environ.get("WEAVIATE_API_KEY")

if not weaviate_url or not weaviate_api_key:
    print("❌ Error: WEAVIATE_URL y WEAVIATE_API_KEY deben estar en las variables de entorno.")
    exit()

# --- Cliente Weaviate ---
try:
    client = weaviate.connect_to_weaviate_cloud(
        cluster_url=weaviate_url,
        auth_credentials=Auth.api_key(weaviate_api_key), # Correcto para v4 Auth
    )
    print(f"🔌 Conexión a Weaviate ({weaviate_url}): {client.is_ready()}")
except Exception as e:
    print(f"❌ Error conectando a Weaviate: {e}")
    exit()

# --- 1. Cargar modelo HuggingFace (Multilingual E5 Large) ---
model_name = "intfloat/multilingual-e5-large"
print(f"🧠 Cargando modelo de embeddings: {model_name}...")
start_model_load = time.time()
try:
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    embedding_model = SentenceTransformer(model_name, device=device)
    print(f"✅ Modelo cargado en {time.time() - start_model_load:.2f}s en: {embedding_model.device}")
    EMBEDDING_DIMENSION = embedding_model.get_sentence_embedding_dimension()
    print(f"📏 Dimensión del Embedding: {EMBEDDING_DIMENSION}")
except Exception as e:
    print(f"❌ Error cargando modelo '{model_name}': {e}")
    if client.is_connected(): client.close()
    exit()

# --- 2. Extraer texto por Página ---
def extract_text_from_pdf_pages(pdf_path):
    """Extrae texto página por página de un PDF."""
    pages_data = []
    pdf_base_name = os.path.basename(pdf_path)
    try:
        doc = fitz.open(pdf_path)
        print(f"📄 Procesando {len(doc)} páginas en '{pdf_base_name}'...")
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            page_text = page.get_text("text", sort=True)

            if page_text.strip(): # Solo guardar si hay texto
                 pages_data.append({
                     "page_number": page_num + 1,
                     "text": page_text,
                 })
        doc.close()
        print(f"📄 Datos de texto extraídos de {len(pages_data)} páginas de '{pdf_base_name}'.")
        return pages_data
    except Exception as e:
        print(f"❌ Error abriendo o procesando PDF '{pdf_path}': {e}")
        return []

# --- 3. Split semántico del texto ---
def split_text_semantically(pages_data_list, chunk_size=2600, chunk_overlap=600):
    """Divide el texto de cada página."""
    chunks_with_info = []
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        is_separator_regex=False,
    )
    print(f"✂️ Dividiendo texto (chunk_size={chunk_size}, overlap={chunk_overlap})...")
    total_chunks = 0
    for page_data in pages_data_list:
        page_num = page_data["page_number"]
        page_text = page_data["text"]

        page_chunks = splitter.split_text(page_text)
        for i, chunk_text in enumerate(page_chunks):
            chunks_with_info.append({
                "page_number": page_num,
                "text": chunk_text,
                "chunk_index_on_page": i,
            })
        total_chunks += len(page_chunks)
    print(f"✂️ Texto dividido en {total_chunks} chunks.")
    return chunks_with_info

# --- 4. Embeddings con HF (Batch) ---
def embed_text_chunks_batch(chunks_info: list[dict], model_name_for_prefix: str):
    """Genera embeddings para los textos en chunks_info usando SentenceTransformer en batch."""
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

# --- 5. Crear/Verificar clase Weaviate (solo texto) ---
def ensure_weaviate_class(client_instance, class_name, vector_dimension):
    """Verifica si la clase existe, si no, la crea para almacenar texto."""
    try:
        if not client_instance.collections.exists(class_name):
            print(f"🏗️ Creando clase '{class_name}' en Weaviate...")
            client_instance.collections.create(
                name=class_name,
                vectorizer_config=None,
                properties=[
                    Property(name="text", data_type=DataType.TEXT, description="Contenido del chunk de texto"),
                    Property(name="page_number", data_type=DataType.INT, description="Número de página original"),
                    Property(name="source_pdf", data_type=DataType.TEXT, description="Nombre del archivo PDF de origen"), # Muy importante para identificar la fuente
                    Property(name="chunk_index_on_page", data_type=DataType.INT, description="Índice del chunk dentro de la página"),
                    # Podrías añadir una propiedad "title" si tus PDFs tienen títulos que puedas extraer
                    # Property(name="title", data_type=DataType.TEXT, description="Título del documento o sección"),
                ]
            )
            print(f"✅ Clase '{class_name}' creada (Dimensión vectorial: {vector_dimension}).")
        else:
            print(f"✅ Clase '{class_name}' ya existe. Se añadirán nuevos datos a esta clase.")
            # Opcional: Verificar si el esquema existente es compatible
            # current_config = client_instance.collections.get(class_name).config.get()
            # print(f"   Propiedades existentes: {[prop.name for prop in current_config.properties]}")
    except Exception as e:
        print(f"❌ Error al crear/verificar la clase '{class_name}': {str(e)}")
        raise e

# --- 6. Subir a Weaviate en batches (solo texto) ---
def upload_data_to_weaviate(client_instance, class_name, embeddings, chunks_info_list, source_pdf_name):
    """Sube los datos (propiedades + vector) a Weaviate en batches a la clase especificada."""
    if not client_instance.is_connected():
        print("❌ Cliente Weaviate no conectado. No se puede subir datos.")
        return

    try:
        collection = client_instance.collections.get(class_name)
    except Exception as e:
        print(f"❌ Error obteniendo la colección '{class_name}': {e}. Asegúrate que la clase existe y fue creada correctamente.")
        return

    object_count = 0
    start_upload_time = time.time()
    print(f"⬆️ Preparando subida de {len(embeddings)} objetos de '{source_pdf_name}' a la clase '{class_name}' en Weaviate...")

    with collection.batch.dynamic() as batch:
        for i, embedding in enumerate(embeddings):
            if i >= len(chunks_info_list):
                print(f"⚠️ Advertencia: Desajuste Embeddings/Chunks. Deteniendo en índice {i}.")
                break

            chunk_info = chunks_info_list[i]
            text_content = chunk_info.get("text", "")
            if not text_content.strip():
                print(f"   ⏭️ Saltando chunk vacío (pág {chunk_info.get('page_number', 'N/A')}, índice {chunk_info.get('chunk_index_on_page', 'N/A')}).")
                continue

            properties_payload = {
                "text": text_content,
                "page_number": chunk_info.get("page_number", 0),
                "source_pdf": source_pdf_name, # Esta propiedad es clave para saber de qué PDF vino el chunk
                "chunk_index_on_page": chunk_info.get("chunk_index_on_page", -1),
                # "title": pdf_filename, # O un título más específico si lo tienes
            }

            batch.add_object(properties=properties_payload, vector=embedding)
            object_count += 1

    print(f"⬆️ Subida de {object_count} objetos de '{source_pdf_name}' a '{class_name}' finalizada en {time.time() - start_upload_time:.2f}s.")
    print(f"📊 Total de objetos añadidos al batch desde '{source_pdf_name}': {object_count}")


# --- 7. MAIN ---
if __name__ == "__main__":
    overall_start_time = time.time()

    # --- Configuración ---
    # ¡CAMBIA ESTO A LA RUTA DE TU CARPETA CON PDFs!
    pdf_folder_path = "/Users/admin/Desktop/AgenteDietas/" # Ejemplo
    
    # !!!!! CAMBIO IMPORTANTE !!!!!
    # Define UN nombre de clase fijo para TODOS tus documentos/recetas.
    # Este es el nombre de la colección en Weaviate donde se guardarán todos los vectores.
    # Elige un nombre descriptivo. Si son recetas, podría ser "Recetas" o "DocumentosRecetas".
    # Si es para tu "AgenteDietas", podría ser "InfoDietas" o algo similar.
    NOMBRE_DE_CLASE_UNIFICADO = "InfoDietas"  # <--- ¡ELIGE Y AJUSTA ESTE NOMBRE!
    # Asegúrate de que este nombre cumpla con las reglas de Weaviate (empezar con mayúscula, alfanumérico).
    # Por ejemplo: "Recetas", "DocumentosGenerales", "BaseDeConocimiento"

    print(f"🏛️  Todos los documentos se cargarán en la clase Weaviate: '{NOMBRE_DE_CLASE_UNIFICADO}'")

    if not os.path.isdir(pdf_folder_path):
        print(f"❌ Error: La carpeta de PDFs no existe en la ruta: {pdf_folder_path}")
        if client.is_connected(): client.close()
        exit()

    pdf_files = glob.glob(os.path.join(pdf_folder_path, "*.pdf"))
    pdf_files += glob.glob(os.path.join(pdf_folder_path, "*.PDF")) # Incluir .PDF en mayúsculas
    pdf_files = list(set(pdf_files)) # Eliminar duplicados

    if not pdf_files:
        print(f"🤷 No se encontraron archivos PDF en: {pdf_folder_path}")
        if client.is_connected(): client.close()
        exit()

    print(f"📚 Encontrados {len(pdf_files)} archivos PDF para procesar y añadir a la clase '{NOMBRE_DE_CLASE_UNIFICADO}'.")

    try:
        # --- PASO CLAVE: Asegurar que la clase unificada existe ANTES del bucle ---
        ensure_weaviate_class(client, NOMBRE_DE_CLASE_UNIFICADO, EMBEDDING_DIMENSION)

        for pdf_path in pdf_files:
            pdf_filename = os.path.basename(pdf_path) # Usaremos esto para la propiedad 'source_pdf'
            print(f"\n🚀 Iniciando proceso para PDF: '{pdf_filename}' (se añadirá a '{NOMBRE_DE_CLASE_UNIFICADO}')")
            start_pdf_time = time.time()

            # Ya no generamos un class_name por PDF, usamos NOMBRE_DE_CLASE_UNIFICADO

            try:
                # --- Pasos para cada PDF ---
                # La clase ya está asegurada fuera del bucle.

                pages_text_data = extract_text_from_pdf_pages(pdf_path)
                if not pages_text_data:
                    print(f"⚠️ No se pudo extraer texto del PDF '{pdf_filename}'. Saltando este archivo.")
                    continue

                # Ajusta chunk_size y chunk_overlap según tus necesidades.
                # Para recetas o info de dietas, chunks más pequeños podrían ser mejores.
                chunks_info = split_text_semantically(pages_text_data, chunk_size=700, chunk_overlap=150)
                if not chunks_info:
                    print(f"⚠️ No se generaron chunks a partir del texto de '{pdf_filename}'. Saltando este archivo.")
                    continue

                embeddings = embed_text_chunks_batch(chunks_info, model_name)
                if not embeddings or len(embeddings) != len(chunks_info):
                     print(f"❌ Error o desajuste en embeddings para '{pdf_filename}' ({len(embeddings) if embeddings else 0} vs {len(chunks_info)}). Saltando subida para este archivo.")
                     continue

                # Subir datos a la CLASE UNIFICADA, pasando el pdf_filename como source_pdf
                upload_data_to_weaviate(client, NOMBRE_DE_CLASE_UNIFICADO, embeddings, chunks_info, pdf_filename)

                print(f"\n✅ Procesamiento del PDF '{pdf_filename}' completado y datos añadidos a '{NOMBRE_DE_CLASE_UNIFICADO}' en {time.time() - start_pdf_time:.2f} segundos.")

            except Exception as e_pdf: # Error específico del procesamiento de un PDF
                print(f"\n❌ Error procesando el PDF individual '{pdf_filename}': {e_pdf}")
                import traceback
                traceback.print_exc()
                # Decidir si continuar con el siguiente PDF o parar todo. Por ahora, continuamos.
                print(f"⚠️ Saltando el PDF '{pdf_filename}' debido a un error. Continuando con el siguiente...")
                continue

    except Exception as e_main: # Error en la configuración inicial o creación de clase
        print(f"\n❌ Error General Crítico en el script (posiblemente al asegurar la clase '{NOMBRE_DE_CLASE_UNIFICADO}'): {e_main}")
        import traceback
        traceback.print_exc()

    finally: # Este bloque se ejecutará siempre, incluso si hay errores
        print(f"\n🎉🎉🎉 Proceso de ingesta finalizado en {time.time() - overall_start_time:.2f} segundos. 🎉🎉🎉")
        if client.is_connected():
            client.close()
            print("🚪 Conexión a Weaviate cerrada.")