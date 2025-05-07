import csv
import json
import time
import logging
import os
import pandas as pd
import requests
from io import StringIO
import chardet # You might need to run: pip install chardet pandas requests
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
# Using v1 search (cgi/search.pl) as documentation suggests it has better full-text search
OFF_API_SEARCH_V1_URL = "https://world.openfoodfacts.org/cgi/search.pl"
OFF_API_PRODUCT_V2_URL_TEMPLATE = "https://world.openfoodfacts.org/api/v2/product/{barcode}.json"

SLEEP_TIME = 6
USER_AGENT = "MercadonaProductEnricher/1.2 (your_email@example.com)" # PLEASE CHANGE THIS
OUTPUT_CSV = "mercadona_enriched_v3_v1api.csv"
OUTPUT_JSON = "mercadona_enriched_v3_v1api.json"
MERCADONA_BRANDS = ["hacendado"] # Add other Mercadona specific brands if needed, lowercase

def detect_encoding(file_path):
    with open(file_path, 'rb') as file:
        raw_data = file.read(10000)
        result = chardet.detect(raw_data)
        encoding = result['encoding']
        confidence = result['confidence']
        logger.info(f"Detected encoding: {encoding} with confidence: {confidence}")
        return encoding

def clean_product_name_for_search(product_name, brand_to_remove=None):
    if not isinstance(product_name, str):
        return ""
    name = product_name.lower()
    if brand_to_remove: # Remove the brand if it's handled by a separate filter
        name = name.replace(brand_to_remove.lower(), "")

    name = re.sub(r'\b\d+\s*bricks?\s*x\s*\d+\s*g\b', '', name, flags=re.IGNORECASE).strip()
    name = re.sub(r'\bp(ie|aquete|ieza)\s*\d+\s*g\s*(aprox\.?)?\b', '', name, flags=re.IGNORECASE).strip()
    name = re.sub(r'\b(paquete|bolsa|tarrina|bandeja|brick)\b', '', name, flags=re.IGNORECASE).strip()
    name = re.sub(r'\b\d+\s*ud(s)?\.?\b', '', name, flags=re.IGNORECASE).strip()
    name = re.sub(r'\b\d+x\d+\s*g\b', '', name, flags=re.IGNORECASE).strip()
    name = re.sub(r'\b\d+(\.\d+)?\s*(g|kg|l|ml)\b', '', name, flags=re.IGNORECASE).strip()
    name = re.sub(r'\baprox\.?\b', '', name, flags=re.IGNORECASE).strip()
    name = re.sub(r'\s+', ' ', name).strip()
    
    if not name or len(name.split()) < 1: # Allow even single word search terms if brand is specified
        name = product_name.lower() # Fallback slightly
        if brand_to_remove:
             name = name.replace(brand_to_remove.lower(), "").strip()
        name = " ".join(name.split()[:3]) # Take first few words if cleaning resulted in empty
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
                logger.info(f"No product found for barcode {sanitized_barcode} or status not 1 (v2 product API). Status: {data.get('status_verbose', 'N/A')}")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404: logger.warning(f"Product with barcode {sanitized_barcode} not found (404) via v2 product API.")
            else: logger.warning(f"HTTP error during barcode lookup (v2 product API) for {sanitized_barcode}: {e}")
        except Exception as e: logger.warning(f"Error during barcode lookup (v2 product API) for {sanitized_barcode}: {e}")
    elif barcode:
        logger.warning(f"Invalid barcode format provided: {barcode}. Skipping barcode search.")

    # 2. Fall back to search by name using v1 search API (cgi/search.pl)
    if not search_terms or not search_terms.strip():
        logger.warning("Empty product name provided for search. Skipping name search.")
        return None

    params_v1 = {
        'action': 'process',
        'search_terms': search_terms,
        'search_simple': 1, # Use simple search
        'json': 1,          # Request JSON response
        'page_size': 5,     # Get a few results to check brand match locally
        'fields': common_fields
    }

    if target_brand:
        # For v1 (cgi/search.pl), brand filtering is typically done with tagtype/tag_contains/tag
        params_v1['tagtype_0'] = 'brands'
        params_v1['tag_contains_0'] = 'contains' # Search for the brand within the brands field
        params_v1['tag_0'] = target_brand.lower() # API often expects lowercase for tags
        logger.info(f"Attempting v1 API name search for '{search_terms}' with brand filter '{target_brand}'")
    else:
        logger.info(f"Attempting v1 API name search for '{search_terms}' (no brand filter)")
        
    try:
        response = requests.get(OFF_API_SEARCH_V1_URL, params=params_v1, headers=headers)
        response.raise_for_status()
        data = response.json()

        if data.get('count', 0) > 0 and data.get('products'):
            products_found = data.get('products')
            logger.info(f"Found {len(products_found)} product(s) via v1 API for '{search_terms}' (brand filter: {target_brand}).")

            # Prioritize results matching the target_brand if specified
            if target_brand:
                for product in products_found:
                    product_brands_str = product.get('brands', '').lower()
                    # Check if the target brand is wholly present in the product's brands string
                    # e.g., target_brand "hacendado" should match "hacendado" or "hacendado, other brand"
                    if any(b.strip() == target_brand.lower() for b in product_brands_str.split(',')):
                        logger.info(f"Prioritized v1 match for brand '{target_brand}': {product.get('product_name', 'N/A')}")
                        return product
                logger.info(f"No exact brand match for '{target_brand}' in top {len(products_found)} v1 results. Considering first result.")
            
            # If no brand prioritization or no match after prioritization, return the first result
            if products_found:
                 logger.info(f"V1 API top match (after any brand check): {products_found[0].get('product_name', 'N/A')} (Brands: {products_found[0].get('brands', 'N/A')})")
                 return products_found[0]
        else:
            logger.info(f"No products found via v1 API for '{search_terms}' (brand filter: {target_brand}). Count: {data.get('count', 0)}")
            
    except requests.exceptions.HTTPError as e:
        logger.warning(f"HTTP error during v1 API name search for '{search_terms}': {e}")
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

    logger.info(f"Original Name: '{full_product_name}', Cleaned Search Terms: '{search_name_cleaned}', Brand Filter: {detected_brand_for_filter}, Barcode: {barcode if barcode else 'N/A'}")
    
    off_product = search_product_openfoodfacts(search_name_cleaned, target_brand=detected_brand_for_filter, barcode=barcode)
    
    logger.info(f"Sleeping for {SLEEP_TIME} seconds...")
    time.sleep(SLEEP_TIME)
    
    enriched_product = product_row.copy()
    if off_product:
        nutriments = off_product.get('nutriments', {})
        logger.info(f"Match selected: {off_product.get('product_name', '')} (Barcode: {off_product.get('code','')}, Brands: {off_product.get('brands', 'N/A')}, Qty: {off_product.get('quantity','N/A')})")
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
        logger.warning(f"No match from OFF for: '{search_name_cleaned}' (Orig: '{full_product_name}', Brand: {detected_brand_for_filter})")
        keys_to_add = ['off_product_name', 'off_barcode', 'off_brands', 'off_quantity', 'nutriscore_grade', 
                       'ecoscore_grade', 'nova_group', 'ingredients_text', 'energy_kcal_100g', 
                       'fat_100g', 'saturated_fat_100g', 'carbohydrates_100g', 'sugars_100g', 
                       'fiber_100g', 'proteins_100g', 'salt_100g', 'sodium_100g']
        for key in keys_to_add: enriched_product[key] = 'N/A'
    return enriched_product

def read_csv_with_encoding(file_path, encoding=None):
    if not encoding: encoding = detect_encoding(file_path)
    common_separators = [',', ';', '\t', '|']
    for sep in common_separators:
        try:
            df = pd.read_csv(file_path, encoding=encoding, sep=sep, engine='python', skip_blank_lines=True)
            logger.info(f"Successfully read CSV with encoding {encoding} and delimiter '{sep}'.")
            if len(df.columns) > 1 or (df.shape[0] > 0): return df
            else: logger.warning(f"Parsed with '{sep}' but resulted in questionable structure. Trying next.")
        except Exception as e: logger.debug(f"Read with '{sep}' failed: {e}")
    try:
        logger.info("Trying with CSV Sniffer...")
        with open(file_path, 'r', encoding=encoding) as f:
            sample = "".join([f.readline() for _ in range(20)])
            if not sample: raise ValueError("File is empty/small.")
            dialect = csv.Sniffer().sniff(sample)
        df = pd.read_csv(file_path, encoding=encoding, sep=dialect.delimiter, engine='python', skip_blank_lines=True)
        logger.info(f"Successfully read CSV with sniffed delimiter '{dialect.delimiter}'.")
        return df
    except Exception as e_sniff: logger.error(f"All read attempts failed for {file_path}: {e_sniff}"); raise

def process_csv_file(file_path):
    logger.info(f"Starting CSV processing for file: {file_path}")
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}"); print(f"ERROR: File '{file_path}' not found."); return None
    try:
        df = read_csv_with_encoding(file_path)
        df.dropna(how='all', inplace=True)
        if df.empty: logger.error(f"CSV '{file_path}' is empty/unparsable."); print(f"ERROR: CSV '{file_path}' empty."); return None
        logger.info(f"Parsed CSV: {len(df)} rows, columns: {df.columns.tolist()}")
    except Exception as e: logger.error(f"Failed to read CSV '{file_path}': {e}"); print(f"ERROR: Could not read CSV: {e}"); return None
    
    if 'Nombre' not in df.columns:
        logger.error(f"'Nombre' column not found. Columns: {df.columns.tolist()}")
        # Basic interactive fallback for 'Nombre' column (can be enhanced or removed for full automation)
        product_col_input = input(f"Available columns: {df.columns.tolist()}. Enter product name column or Enter to cancel: ")
        if product_col_input and product_col_input in df.columns:
            df = df.rename(columns={product_col_input: 'Nombre'})
        else:
            logger.error("Product name column not specified or invalid. Aborting."); print("Aborting."); return None
    
    price_col_name = next((col for col in df.columns if 'precio' in col.lower() or 'price' in col.lower()), None)
    if price_col_name:
        try:
            df[price_col_name] = df[price_col_name].astype(str).str.replace('€','',regex=False).str.replace(',','.',regex=False).str.strip()
            df[price_col_name] = df[price_col_name].str.extract(r'(\d+\.?\d*)')[0]
            df[price_col_name] = pd.to_numeric(df[price_col_name], errors='coerce')
            logger.info(f"Standardized price column '{price_col_name}'.")
        except Exception as e: logger.warning(f"Could not fully convert price column '{price_col_name}': {e}.")

    products = df.to_dict('records')
    enriched_products = [enrich_product_data(p) for i, p in enumerate(products, 1)]
    
    enriched_df = pd.DataFrame(enriched_products)
    try:
        enriched_df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
        enriched_df.to_json(OUTPUT_JSON, orient='records', lines=True, force_ascii=False, indent=2)
        logger.info(f"Processing complete. Results: {OUTPUT_CSV}, {OUTPUT_JSON}")
        print(f"\nProcessing complete! Results in '{OUTPUT_CSV}' and '{OUTPUT_JSON}'")
    except Exception as e: logger.error(f"Error saving output: {e}"); print(f"ERROR saving output: {e}")
    return enriched_df

def process_csv_string(csv_string): # Mainly for testing
    logger.info("Starting CSV string processing")
    try:
        df = pd.read_csv(StringIO(csv_string), sep=None, engine='python', skip_blank_lines=True)
        df.dropna(how='all', inplace=True)
        if df.empty: logger.error("CSV string empty."); return None
    except Exception as e: logger.error(f"Failed to parse CSV string: {e}"); return None
    if 'Nombre' not in df.columns: logger.error("CSV string needs 'Nombre' column."); return None
    if 'Precio' in df.columns: # Simplified price conversion for test string
        df['Precio'] = df['Precio'].astype(str).str.replace('€','').str.replace(',','.').str.extract(r'(\d+\.?\d*)')[0]
        df['Precio'] = pd.to_numeric(df['Precio'], errors='coerce')
    products = df.to_dict('records')
    enriched_products = [enrich_product_data(p) for p in products]
    enriched_df = pd.DataFrame(enriched_products)
    logger.info(f"String processing complete. Output to console if main calls, or saved if integrated to save.")
    return enriched_df


def main():
    print("Welcome to the Mercadona Product Data Enricher (v1 API Search)!")
    print(f"USER_AGENT: '{USER_AGENT}' (Change if needed!)")
    print(f"SLEEP_TIME: {SLEEP_TIME}s. Output: {OUTPUT_CSV}, {OUTPUT_JSON}")
    print("\nOptions:\n1. Process built-in example data\n2. Process your own CSV file")
    choice = input("\nEnter choice (1 or 2): ").strip()

    if choice == "1":
        example_csv = """Nombre,Descripcion_del_producto,Precio,Imagen,Barcode
Tomate frito Hacendado 3 bricks x 400 g,Tomate frito en brick.,1.35 €,img1.jpg,8480000123456
Tomate triturado Hacendado Bote 400 g,Tomate triturado natural.,0.65 €,img2.jpg,8480000654321
Agua mineral natural Hacendado botella 1,5 l,Agua mineral.,0.22 €,img3.jpg,8480000987654
"""
        # Added dummy barcodes to test that path too
        results_df = process_csv_string(example_csv)
        if results_df is not None:
            print("\nEnriched example data (first 5 rows):")
            pd.set_option('display.max_columns', None); pd.set_option('display.width', 1000)
            print(results_df.head())
            print(f"\n(Example data also saved to '{OUTPUT_CSV}' and '{OUTPUT_JSON}')")
        else: print("Failed to process example data.")
    elif choice == "2":
        file_path = input("Enter path to your CSV file: ").strip()
        if not file_path: print("No file path. Exiting."); return
        process_csv_file(file_path)
    else: print("Invalid choice.")

if __name__ == "__main__":
    try: import pandas; import requests; import chardet
    except ImportError as e: print(f"Missing package: {e.name}. Pip install it."); exit()
    main()