import csv
import json
import time
import logging
import os
import pandas as pd
import requests
from io import StringIO
import chardet
import re
from google.cloud import bigquery
from google.cloud import storage
import pandas_gbq
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
OFF_API_SEARCH_V1_URL = "https://world.openfoodfacts.org/cgi/search.pl"
OFF_API_PRODUCT_V2_URL_TEMPLATE = "https://world.openfoodfacts.org/api/v2/product/{barcode}.json"

SLEEP_TIME = 6
USER_AGENT = os.environ.get('USER_AGENT', "MercadonaProductEnricher/1.2") 
MERCADONA_BRANDS = ["hacendado"]

# GCP Configuration from environment variables
GCP_PROJECT = os.environ.get('GCP_PROJECT', 'diap3-458416')
GCS_BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME', 'bucket_csv_scraper')
GCS_FILE_NAME = os.environ.get('GCS_FILE_NAME', 'mercadona_products.csv')
BQ_DATASET = os.environ.get('BQ_DATASET', 'food_data')
BQ_TABLE = os.environ.get('BQ_TABLE', 'mercadona_enriched_products')

# Initialize GCP clients
storage_client = storage.Client(project=GCP_PROJECT)
bq_client = bigquery.Client(project=GCP_PROJECT)

def detect_encoding(file_content):
    result = chardet.detect(file_content)
    encoding = result['encoding']
    confidence = result['confidence']
    logger.info(f"Detected encoding: {encoding} with confidence: {confidence}")
    return encoding

def clean_product_name_for_search(product_name, brand_to_remove=None):
    if not isinstance(product_name, str):
        return ""
    name = product_name.lower()
    if brand_to_remove:
        name = name.replace(brand_to_remove.lower(), "")

    name = re.sub(r'\b\d+\s*bricks?\s*x\s*\d+\s*g\b', '', name, flags=re.IGNORECASE).strip()
    name = re.sub(r'\bp(ie|aquete|ieza)\s*\d+\s*g\s*(aprox\.?)?\b', '', name, flags=re.IGNORECASE).strip()
    name = re.sub(r'\b(paquete|bolsa|tarrina|bandeja|brick)\b', '', name, flags=re.IGNORECASE).strip()
    name = re.sub(r'\b\d+\s*ud(s)?\.?\b', '', name, flags=re.IGNORECASE).strip()
    name = re.sub(r'\b\d+x\d+\s*g\b', '', name, flags=re.IGNORECASE).strip()
    name = re.sub(r'\b\d+(\.\d+)?\s*(g|kg|l|ml)\b', '', name, flags=re.IGNORECASE).strip()
    name = re.sub(r'\baprox\.?\b', '', name, flags=re.IGNORECASE).strip()
    name = re.sub(r'\s+', ' ', name).strip()

    if not name or len(name.split()) < 1:
        name = product_name.lower()
        if brand_to_remove:
             name = name.replace(brand_to_remove.lower(), "").strip()
        name = " ".join(name.split()[:3])
    return name

def search_product_openfoodfacts(search_terms, target_brand=None, barcode=None):
    headers = {'User-Agent': USER_AGENT}
    common_fields = 'product_name,brands,nutriments,nutriscore_grade,ecoscore_grade,nova_group,ingredients_text,code,quantity'

    # 1. Try direct barcode lookup using v2 product endpoint
    if barcode and isinstance(barcode, str) and barcode.strip().isdigit():
        sanitized_barcode = barcode.strip()
        logger.info(f"Attempting barcode lookup for: {sanitized_barcode}")
        try:
            url = OFF_API_PRODUCT_V2_URL_TEMPLATE.format(barcode=sanitized_barcode)
            response = requests.get(url, headers=headers, params={'fields': common_fields})
            response.raise_for_status()
            data = response.json()
            if data.get('status') == 1 and data.get('product'):
                logger.info(f"Barcode match found: {data['product'].get('product_name', 'N/A')}")
                return data.get('product')
            else:
                logger.info(f"No product found for barcode {sanitized_barcode}")
        except Exception as e:
            logger.warning(f"Error during barcode lookup for {sanitized_barcode}: {e}")

    # 2. Fall back to search by name using v1 search API
    if not search_terms or not search_terms.strip():
        logger.warning("Empty product name provided for search.")
        return None

    params_v1 = {
        'action': 'process',
        'search_terms': search_terms,
        'search_simple': 1,
        'json': 1,
        'page_size': 5,
        'fields': common_fields
    }

    if target_brand:
        params_v1['tagtype_0'] = 'brands'
        params_v1['tag_contains_0'] = 'contains'
        params_v1['tag_0'] = target_brand.lower()
        logger.info(f"Attempting v1 API name search for '{search_terms}' with brand filter '{target_brand}'")
    else:
        logger.info(f"Attempting v1 API name search for '{search_terms}' (no brand filter)")

    try:
        response = requests.get(OFF_API_SEARCH_V1_URL, params=params_v1, headers=headers)
        response.raise_for_status()
        data = response.json()

        if data.get('count', 0) > 0 and data.get('products'):
            products_found = data.get('products')
            logger.info(f"Found {len(products_found)} product(s) via v1 API")

            if target_brand:
                for product in products_found:
                    product_brands_str = product.get('brands', '').lower()
                    if any(b.strip() == target_brand.lower() for b in product_brands_str.split(',')):
                        logger.info(f"Prioritized v1 match for brand '{target_brand}'")
                        return product

            if products_found:
                return products_found[0]

    except Exception as e:
        logger.warning(f"Error during v1 API name search for '{search_terms}': {e}")

    return None

def enrich_product_data(product_row):
    full_product_name = product_row.get('Nombre', '')
    if not full_product_name:
        logger.warning("Skipping row due to empty product name.")
        return product_row

    detected_brand_for_filter = None
    for brand in MERCADONA_BRANDS:
        if brand in full_product_name.lower():
            detected_brand_for_filter = brand
            break

    search_name_cleaned = clean_product_name_for_search(full_product_name, brand_to_remove=detected_brand_for_filter)
    barcode = product_row.get('Barcode') or product_row.get('barcode') 

    logger.info(f"Processing: '{full_product_name}' with cleaned search: '{search_name_cleaned}'")

    off_product = search_product_openfoodfacts(search_name_cleaned, target_brand=detected_brand_for_filter, barcode=barcode)

    logger.info(f"Sleeping for {SLEEP_TIME} seconds...")
    time.sleep(SLEEP_TIME)

    enriched_product = product_row.copy()
    if off_product:
        nutriments = off_product.get('nutriments', {})
        logger.info(f"Match found: {off_product.get('product_name', '')}")
        enriched_product.update({
            'off_product_name': off_product.get('product_name', ''),
            'off_barcode': off_product.get('code', ''),
            'off_brands': off_product.get('brands', ''),
            'off_quantity': off_product.get('quantity', ''),
            'nutriscore_grade': off_product.get('nutriscore_grade', ''),
            'ecoscore_grade': off_product.get('ecoscore_grade', ''),
            'nova_group': off_product.get('nova_group', ''),
            'ingredients_text': off_product.get('ingredients_text', ''),
            'energy_kcal_100g': nutriments.get('energy-kcal_100g', nutriments.get('energy_100g','')),
            'fat_100g': nutriments.get('fat_100g', ''),
            'saturated_fat_100g': nutriments.get('saturated-fat_100g', ''),
            'carbohydrates_100g': nutriments.get('carbohydrates_100g', ''),
            'sugars_100g': nutriments.get('sugars_100g', ''),
            'fiber_100g': nutriments.get('fiber_100g', ''),
            'proteins_100g': nutriments.get('proteins_100g', ''),
            'salt_100g': nutriments.get('salt_100g', ''),
            'sodium_100g': nutriments.get('sodium_100g', '')
        })
    else:
        logger.warning(f"No match found for: '{search_name_cleaned}'")
        keys_to_add = ['off_product_name', 'off_barcode', 'off_brands', 'off_quantity', 'nutriscore_grade', 
                       'ecoscore_grade', 'nova_group', 'ingredients_text', 'energy_kcal_100g', 
                       'fat_100g', 'saturated_fat_100g', 'carbohydrates_100g', 'sugars_100g', 
                       'fiber_100g', 'proteins_100g', 'salt_100g', 'sodium_100g']
        for key in keys_to_add:
            enriched_product[key] = None
    
    # Add processing timestamp
    enriched_product['processed_at'] = datetime.utcnow().isoformat()
    
    return enriched_product

def download_from_gcs():
    """Download CSV from Google Cloud Storage"""
    logger.info(f"Downloading file from GCS: gs://{GCS_BUCKET_NAME}/{GCS_FILE_NAME}")
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(GCS_FILE_NAME)
    content = blob.download_as_bytes()
    return content

def write_to_bigquery(df):
    """Write DataFrame to BigQuery"""
    table_id = f"{GCP_PROJECT}.{BQ_DATASET}.{BQ_TABLE}"
    logger.info(f"Writing {len(df)} rows to BigQuery table: {table_id}")
    
    # Convert numpy types to Python native types for BigQuery compatibility
    df = df.copy()
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str).replace('nan', None).replace('N/A', None)
    
    # Write to BigQuery using pandas_gbq with location specified
    pandas_gbq.to_gbq(
        df, 
        table_id,
        project_id=GCP_PROJECT,
        if_exists='replace',
        progress_bar=False,
        location='europe-west1'  # Your dataset location
    )
    logger.info(f"Successfully wrote data to BigQuery")

def process_batch(products, batch_size=100):
    """Process products in batches and write to BigQuery"""
    all_enriched = []
    total_products = len(products)
    
    for i in range(0, total_products, batch_size):
        batch = products[i:i+batch_size]
        logger.info(f"Processing batch {i//batch_size + 1} of {(total_products + batch_size - 1)//batch_size}")
        
        enriched_batch = []
        for product in batch:
            enriched_product = enrich_product_data(product)
            enriched_batch.append(enriched_product)
        
        # Convert to DataFrame
        batch_df = pd.DataFrame(enriched_batch)
        
        # Write this batch to BigQuery
        write_mode = 'replace' if i == 0 else 'append'
        pandas_gbq.to_gbq(
            batch_df,
            f"{GCP_PROJECT}.{BQ_DATASET}.{BQ_TABLE}",
            project_id=GCP_PROJECT,
            if_exists=write_mode,
            progress_bar=False,
            location='europe-west1'  # Your dataset location
        )
        
        all_enriched.extend(enriched_batch)
        logger.info(f"Batch {i//batch_size + 1} written to BigQuery")
    
    return pd.DataFrame(all_enriched)

def main():
    logger.info("Starting Mercadona Product Enrichment Cloud Run Job")
    logger.info(f"Project: {GCP_PROJECT}, Bucket: {GCS_BUCKET_NAME}, File: {GCS_FILE_NAME}")
    
    try:
        # Download CSV from GCS
        csv_content = download_from_gcs()
        
        # Detect encoding and read CSV
        encoding = detect_encoding(csv_content)
        df = pd.read_csv(StringIO(csv_content.decode(encoding)))
        
        # Check for required columns
        if 'Nombre' not in df.columns:
            logger.error(f"'Nombre' column not found. Available columns: {df.columns.tolist()}")
            return
        
        # Process price column if exists
        price_col_name = next((col for col in df.columns if 'precio' in col.lower() or 'price' in col.lower()), None)
        if price_col_name:
            try:
                df[price_col_name] = df[price_col_name].astype(str).str.replace('€','',regex=False).str.replace(',','.',regex=False).str.strip()
                df[price_col_name] = df[price_col_name].str.extract(r'(\d+\.?\d*)')[0]
                df[price_col_name] = pd.to_numeric(df[price_col_name], errors='coerce')
                logger.info(f"Standardized price column '{price_col_name}'.")
            except Exception as e:
                logger.warning(f"Could not fully convert price column '{price_col_name}': {e}")
        
        # Process products in batches
        products = df.to_dict('records')
        logger.info(f"Starting enrichment of {len(products)} products")
        
        # Process in batches to avoid memory issues
        enriched_df = process_batch(products, batch_size=50)
        
        logger.info(f"Enrichment complete. Processed {len(enriched_df)} products.")
        
    except Exception as e:
        logger.error(f"Error occurred: {e}")
        raise e

if __name__ == "__main__":
    main()