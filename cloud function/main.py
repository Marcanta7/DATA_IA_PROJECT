import pandas as pd
import re
import difflib
import logging
import chardet
from tqdm import tqdm
from google.cloud import storage
from google.cloud import bigquery
import tempfile
import os
from io import BytesIO

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def detect_encoding(file_bytes):
    """Detect the encoding of a file from bytes"""
    result = chardet.detect(file_bytes[:10000])  # Check first 10kb
    encoding = result['encoding']
    confidence = result['confidence']
    logger.info(f"Detected encoding: {encoding} with confidence: {confidence}")
    return encoding

def clean_text(text):
    """Basic text cleaning for comparison"""
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def download_blob_as_bytes(bucket_name, blob_name):
    """Download blob from GCS as bytes"""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    
    logger.info(f"Downloading {blob_name} from bucket {bucket_name}")
    return blob.download_as_bytes()

def load_dataframe_from_gcs(bucket_name, file_name):
    """Load a dataframe from GCS with encoding detection"""
    # Download the file as bytes
    file_bytes = download_blob_as_bytes(bucket_name, file_name)
    
    # Detect encoding
    encoding = detect_encoding(file_bytes)
    
    # Try different separators
    for sep in [',', ';', '\t']:
        try:
            df = pd.read_csv(BytesIO(file_bytes), sep=sep, encoding=encoding)
            if len(df.columns) > 1:
                logger.info(f"Successfully loaded {file_name} with separator '{sep}' and encoding '{encoding}'")
                return df
        except Exception as e:
            logger.debug(f"Failed to load with separator '{sep}': {e}")
    
    # Try with common encodings as fallback
    for enc in ['latin1', 'iso-8859-1', 'cp1252', 'utf-16', 'utf-8-sig']:
        if enc != encoding:  # Skip if we already tried this encoding
            try:
                df = pd.read_csv(BytesIO(file_bytes), encoding=enc)
                logger.info(f"Successfully loaded {file_name} with fallback encoding '{enc}'")
                return df
            except Exception as e:
                logger.debug(f"Failed with encoding '{enc}': {e}")
    
    raise ValueError(f"Could not load {file_name} with any encoding or separator")

def upload_to_bigquery(df, dataset_id, table_id, project_id=None):
    """Upload a DataFrame to BigQuery"""
    if project_id is None:
        # Use default project
        client = bigquery.Client()
        project_id = client.project
    else:
        client = bigquery.Client(project=project_id)
    
    # Construct a full table reference
    table_ref = f"{project_id}.{dataset_id}.{table_id}"
    
    logger.info(f"Uploading {len(df)} rows to BigQuery table {table_ref}")
    
    # Configure job options
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,  # Replace any existing table
        autodetect=True  # Auto-detect schema
    )
    
    # Upload to BigQuery
    job = client.load_table_from_dataframe(df, table_ref, job_config=job_config)
    
    # Wait for job to complete
    job.result()
    
    # Get upload result
    table = client.get_table(table_ref)
    logger.info(f"Loaded {table.num_rows} rows to {table_ref}")

def process_and_match(event, context):
    """Cloud Function entry point function that processes GCS files and loads to BigQuery"""
    # Configuration parameters - CUSTOMIZE THESE
    project_id = "your-project-id"  # Replace with your GCP project ID
    bucket_name = "your-bucket-name"  # Replace with your GCS bucket name
    products_file = "mercadona_products.csv"  # Source product data
    nutrition_file = "openfoodfacts_export.csv"  # Nutrition data
    result_file = "enriched_mercadona_products.csv"  # Result file in GCS (optional)
    bq_dataset = "product_data"  # BigQuery dataset
    bq_table = "enriched_products"  # BigQuery table
    
    # For GCS trigger, get the file that triggered the function
    if event and 'name' in event:
        file = event['name']
        logger.info(f"Function triggered by {file}")
        # Only process if the trigger file is one of our input files
        if file != products_file and file != nutrition_file:
            logger.info(f"Ignoring non-target file: {file}")
            return
    
    # Load product data from GCS
    try:
        products_df = load_dataframe_from_gcs(bucket_name, products_file)
        logger.info(f"Loaded {len(products_df)} products from {products_file}")
    except Exception as e:
        logger.error(f"Failed to load products file: {e}")
        raise
    
    # Identify product name column
    product_name_cols = ['Nombre', 'producto', 'product_name', 'nombre', 'name']
    product_name_col = None
    
    for col in product_name_cols:
        if col in products_df.columns:
            product_name_col = col
            break
    
    if not product_name_col:
        # Try to infer a name column
        for col in products_df.columns:
            if 'product' in col.lower() or 'nombre' in col.lower() or 'name' in col.lower():
                product_name_col = col
                logger.info(f"Using column '{col}' as product name based on name similarity")
                break
        
        # If still no column, use the first string column
        if not product_name_col:
            for col in products_df.columns:
                if products_df[col].dtype == 'object':
                    product_name_col = col
                    logger.info(f"Using first text column '{col}' as product name")
                    break
    
    if not product_name_col:
        logger.error(f"No product name column found in {products_file}. Columns: {products_df.columns.tolist()}")
        raise ValueError(f"Could not identify product name column in {products_file}")
    
    logger.info(f"Using '{product_name_col}' as product name column")
    
    # Load nutrition data from GCS
    try:
        # Special handling for potentially large nutrition file
        nutrition_df = load_dataframe_from_gcs(bucket_name, nutrition_file)
        logger.info(f"Loaded {len(nutrition_df)} nutrition entries from {nutrition_file}")
    except Exception as e:
        logger.error(f"Failed to load nutrition file: {e}")
        raise
    
    # Find nutrition name columns
    nutrition_name_cols = [col for col in nutrition_df.columns if 'product_name' in col]
    if not nutrition_name_cols:
        # Try to find alternative name columns
        for col in nutrition_df.columns:
            if 'name' in col.lower() or 'nombre' in col.lower() or 'product' in col.lower():
                nutrition_name_cols.append(col)
        
        if not nutrition_name_cols:
            logger.error(f"No product name columns found in {nutrition_file}")
            raise ValueError(f"Could not identify product name columns in {nutrition_file}")
    
    logger.info(f"Using nutrition name columns: {nutrition_name_cols}")
    
    # Create enriched dataframe
    enriched_df = products_df.copy()
    
    # Add matching columns
    enriched_df['match_product_name'] = None
    enriched_df['match_index'] = None
    enriched_df['match_score'] = None
    
    # Add nutrition columns
    nutrition_columns = [
        'energy-kcal_value', 'fat_value', 'saturated-fat_value', 
        'carbohydrates_value', 'sugars_value', 'proteins_value', 
        'salt_value', 'fiber_value', 'brands', 'categories_tags',
        'off:nova_groups', 'off:nutriscore_grade'
    ]
    
    existing_nutrition_cols = [col for col in nutrition_columns if col in nutrition_df.columns]
    for col in existing_nutrition_cols:
        enriched_df[col] = None
    
    # Perform matching between products and nutrition data
    logger.info("Starting product matching process...")
    match_count = 0
    
    # Optimize for large datasets: Sample nutrition data for faster processing
    # For very large nutrition datasets, consider sampling a subset
    nutrition_sample_size = min(50000, len(nutrition_df))
    if nutrition_sample_size < len(nutrition_df):
        nutrition_sample = nutrition_df.sample(nutrition_sample_size, random_state=42)
        logger.info(f"Using {nutrition_sample_size} random samples from nutrition data for initial matching")
    else:
        nutrition_sample = nutrition_df
    
    # Process in batches to handle memory constraints
    batch_size = 500
    total_batches = (len(products_df) + batch_size - 1) // batch_size
    
    for batch_idx in range(total_batches):
        start_idx = batch_idx * batch_size
        end_idx = min(start_idx + batch_size, len(products_df))
        
        logger.info(f"Processing batch {batch_idx + 1}/{total_batches} (products {start_idx}-{end_idx})")
        
        batch_matches = 0
        for idx in range(start_idx, end_idx):
            product_name = products_df.iloc[idx][product_name_col]
            if not isinstance(product_name, str) or not product_name.strip():
                continue
            
            # Clean product name
            clean_product_name = clean_text(product_name)
            
            # Find best match
            best_score = 0
            best_match_idx = None
            best_match_name = None
            
            # First try with the sample (faster)
            for n_idx, n_row in nutrition_sample.iterrows():
                for name_col in nutrition_name_cols:
                    if not pd.isna(n_row[name_col]) and isinstance(n_row[name_col], str):
                        n_name = n_row[name_col]
                        clean_n_name = clean_text(n_name)
                        
                        similarity = difflib.SequenceMatcher(None, clean_product_name, clean_n_name).ratio()
                        if similarity > best_score:
                            best_score = similarity
                            best_match_idx = n_idx
                            best_match_name = n_name
            
            # If good match found, add to enriched dataframe
            if best_score >= 0.6:
                enriched_df.loc[idx, 'match_product_name'] = best_match_name
                enriched_df.loc[idx, 'match_index'] = best_match_idx
                enriched_df.loc[idx, 'match_score'] = best_score
                
                # Add nutrition data
                for col in existing_nutrition_cols:
                    enriched_df.loc[idx, col] = nutrition_df.loc[best_match_idx, col]
                
                match_count += 1
                batch_matches += 1
        
        logger.info(f"Batch {batch_idx + 1} complete: {batch_matches} matches in this batch, {match_count} total matches so far")
    
    # Filter only matched products for BigQuery export
    matched_df = enriched_df[enriched_df['match_score'] >= 0.6].copy()
    logger.info(f"Total matches: {len(matched_df)} out of {len(products_df)} products ({len(matched_df)/len(products_df)*100:.1f}%)")
    
    if len(matched_df) > 0:
        # Upload to BigQuery
        try:
            upload_to_bigquery(matched_df, bq_dataset, bq_table, project_id)
            logger.info(f"Successfully uploaded {len(matched_df)} matched products to BigQuery")
        except Exception as e:
            logger.error(f"Error uploading to BigQuery: {e}")
    else:
        logger.warning("No matches found, skipping BigQuery upload")
    
    # Optionally save to GCS (can be useful for debugging or as backup)
    if result_file:
        try:
            # Create a client
            storage_client = storage.Client()
            bucket = storage_client.bucket(bucket_name)
            
            # Convert to CSV
            csv_data = enriched_df.to_csv(index=False, encoding='utf-8')
            
            # Upload to GCS
            blob = bucket.blob(result_file)
            blob.upload_from_string(csv_data, content_type='text/csv')
            
            logger.info(f"Saved results to gs://{bucket_name}/{result_file}")
        except Exception as e:
            logger.error(f"Error saving results to GCS: {e}")
    
    return f"Processed {len(products_df)} products and found {match_count} matches"