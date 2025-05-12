import os
import pandas as pd
from google.cloud import storage, bigquery
import tempfile
import duckdb

# Se cargan las variables de entorno desde env.yaml automáticamente por GCP
GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME")
FILENAME_1 = os.environ.get("FILENAME_1")  # productos Mercadona
FILENAME_2 = os.environ.get("FILENAME_2")  # datos OFF
DATASET_ID = os.environ.get("DATASET_ID")
TABLE_ID = os.environ.get("TABLE_ID")

def process_csvs(event, context):
    file_name = event["name"]

    if file_name not in [FILENAME_1, FILENAME_2]:
        print(f"Ignorando archivo no esperado: {file_name}")
        return

    print(f"Procesando archivo nuevo: {file_name}")

    storage_client = storage.Client()
    bucket = storage_client.bucket(GCS_BUCKET_NAME)

    # Descargar ambos archivos en local (tempfiles)
    temp_dir = tempfile.mkdtemp()
    local_file1 = os.path.join(temp_dir, FILENAME_1)
    local_file2 = os.path.join(temp_dir, FILENAME_2)

    blob1 = bucket.blob(FILENAME_1)
    blob1.download_to_filename(local_file1)
    print(f"{FILENAME_1} descargado.")

    blob2 = bucket.blob(FILENAME_2)
    blob2.download_to_filename(local_file2)
    print(f"{FILENAME_2} descargado.")

    # Cargar CSVs con DuckDB
    con = duckdb.connect()
    df_mercadona = con.execute(f"SELECT * FROM read_csv_auto('{local_file1}')").df()
    df_off = con.execute(f"SELECT * FROM read_csv_auto('{local_file2}')").df()

    # Unión usando una similitud básica de nombre (mejora esto según tu caso)
    df_merged = pd.merge(df_mercadona, df_off, on="product_name", how="left")

    print(f"Unión completada. Filas resultantes: {len(df_merged)}")

    # Subir a BigQuery
    bq_client = bigquery.Client()
    table_ref = bq_client.dataset(DATASET_ID).table(TABLE_ID)

    job = bq_client.load_table_from_dataframe(df_merged, table_ref)
    job.result()

    print(f"Datos subidos a BigQuery: {DATASET_ID}.{TABLE_ID}")