import os
import json
import math
import ast
import re
from google.cloud import firestore
from google.cloud import bigquery
from google.oauth2 import service_account

# --- CONFIGURATION ---
SERVICE_ACCOUNT_FILE = "/Users/joaquin/Documents/GitHub/DATA_IA_PROJECT/diap3-458416-e2b338560b68.json"
PROJECT_ID = "diap3-458416"
COLLECTION_NAME = "diet_conversations"
BQ_DATASET = "analytics"

# --- AUTHENTICATION ---
credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE)
db = firestore.Client(project=PROJECT_ID, credentials=credentials, database="agente-context-prueba")
bq_client = bigquery.Client(project=PROJECT_ID, credentials=credentials)

# --- CREATE DATASET IF NEEDED ---
dataset_ref = bq_client.dataset(BQ_DATASET)
try:
    bq_client.get_dataset(dataset_ref)
    print(f"Dataset {BQ_DATASET} already exists")
except Exception:
    print(f"Creating dataset {BQ_DATASET}...")
    dataset = bigquery.Dataset(dataset_ref)
    bq_client.create_dataset(dataset)

# --- UTILITY FUNCTIONS ---
def json_serializable(obj):
    """Convert special values to JSON-serializable format"""
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj

def clean_string(s):
    """Clean strings of any problematic characters"""
    if not isinstance(s, str):
        return s
    # Replace any non-printable characters
    return re.sub(r'[^\x20-\x7E]', '', s)

def safe_json_dump(obj):
    """Convert object to JSON safely, cleaning strings and handling special values"""
    if isinstance(obj, dict):
        return {k: safe_json_dump(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [safe_json_dump(item) for item in obj]
    elif isinstance(obj, str):
        return clean_string(obj)
    elif isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    else:
        return obj

# --- FETCH DOCUMENTS ---
print("Fetching Firestore documents...")
docs = db.collection(COLLECTION_NAME).stream()

# --- PREPARE EXPORT DIRECTORY ---
export_dir = "bq_export"
os.makedirs(export_dir, exist_ok=True)

# --- EXPORT CONVERSATIONS ---
print("Exporting conversation metadata...")
with open(f"{export_dir}/conversations.jsonl", "w") as f:
    for doc in docs:
        data = doc.to_dict()
        doc_id = doc.id
        
        # Create a simplified conversation record
        record = {
            "document_id": doc_id,
            "has_diet": "diet" in data,
            "has_grocery_list": "grocery_list" in data,
            "budget": str(data.get("budget", "")) if data.get("budget") is not None else "",
            "intolerances": json.dumps(data.get("intolerances", [])) if isinstance(data.get("intolerances"), list) else str(data.get("intolerances", "")),
            "forbidden_foods": json.dumps(data.get("forbidden_foods", [])) if isinstance(data.get("forbidden_foods"), list) else str(data.get("forbidden_foods", ""))
        }
        
        # Clean and write as a single JSON line
        clean_record = safe_json_dump(record)
        try:
            json_line = json.dumps(clean_record)
            f.write(json_line + "\n")
        except Exception as e:
            print(f"Error serializing conversation for doc {doc_id}: {e}")

# --- EXPORT GROCERY ITEMS ---
print("Exporting grocery items...")
docs = db.collection(COLLECTION_NAME).stream()

with open(f"{export_dir}/grocery_items.jsonl", "w") as f:
    for doc in docs:
        data = doc.to_dict()
        doc_id = doc.id
        
        grocery_list = data.get("grocery_list", [])
        
        if not grocery_list:
            continue
            
        if isinstance(grocery_list, list):
            for item_index, item in enumerate(grocery_list):
                try:
                    # Handle dictionary items
                    if isinstance(item, dict):
                        record = {
                            "document_id": doc_id,
                            "product": str(item.get("Producto", "")) if item.get("Producto") is not None else "",
                            "quantity": float(item.get("Cantidad")) if item.get("Cantidad") is not None and not (isinstance(item.get("Cantidad"), float) and math.isnan(item.get("Cantidad"))) else None,
                            "units": str(item.get("Unidades", "")) if item.get("Unidades") is not None else "",
                            "matching_product": str(item.get("Producto_Coincidente", "")) if item.get("Producto_Coincidente") is not None else "",
                            "estimated_price": float(item.get("Precio_Estimado")) if item.get("Precio_Estimado") is not None and not (isinstance(item.get("Precio_Estimado"), float) and math.isnan(item.get("Precio_Estimado"))) else None,
                            "units_needed": float(item.get("Unidades_Necesarias")) if item.get("Unidades_Necesarias") is not None and not (isinstance(item.get("Unidades_Necesarias"), float) and math.isnan(item.get("Unidades_Necesarias"))) else None
                        }
                        
                        # Clean and write as a single JSON line
                        clean_record = safe_json_dump(record)
                        json_line = json.dumps(clean_record)
                        f.write(json_line + "\n")
                    
                    # Handle string items (format: "Product: quantity unit")
                    elif isinstance(item, str) and ":" in item:
                        parts = item.split(":", 1)
                        if len(parts) == 2:
                            product = parts[0].strip()
                            qty_part = parts[1].strip().split(" ", 1)
                            
                            if len(qty_part) >= 1:
                                try:
                                    quantity = float(qty_part[0])
                                    unit = qty_part[1] if len(qty_part) > 1 else ""
                                    
                                    record = {
                                        "document_id": doc_id,
                                        "product": product,
                                        "quantity": quantity,
                                        "units": unit,
                                        "matching_product": "",
                                        "estimated_price": None,
                                        "units_needed": None
                                    }
                                    
                                    # Clean and write as a single JSON line
                                    clean_record = safe_json_dump(record)
                                    json_line = json.dumps(clean_record)
                                    f.write(json_line + "\n")
                                except ValueError:
                                    print(f"Could not parse quantity from: {item}")
                except Exception as e:
                    print(f"Error with grocery item {item_index} in doc {doc_id}: {e}")

# --- EXPORT DIET MEALS ---
print("Exporting meal data...")
docs = db.collection(COLLECTION_NAME).stream()

with open(f"{export_dir}/meals.jsonl", "w") as f:
    for doc in docs:
        data = doc.to_dict()
        doc_id = doc.id
        
        # Function to process diet dictionaries
        def process_diet_dict(diet_dict, doc_id):
            meals_found = 0
            try:
                # Process each day's meals
                for day, day_meals in diet_dict.items():
                    for meal_type, meal_items in day_meals.items():
                        for food_item, food_details in meal_items.items():
                            # Extract quantity and unit from tuple
                            if isinstance(food_details, tuple) and len(food_details) == 2:
                                quantity, unit = food_details
                                record = {
                                    "document_id": doc_id,
                                    "day": int(day),
                                    "meal_type": str(meal_type),
                                    "food_item": str(food_item),
                                    "quantity": float(quantity),
                                    "unit": str(unit)
                                }
                                
                                # Clean and write as a single JSON line
                                clean_record = safe_json_dump(record)
                                json_line = json.dumps(clean_record)
                                f.write(json_line + "\n")
                                meals_found += 1
            except Exception as e:
                print(f"Error processing meals in doc {doc_id}: {e}")
            return meals_found
        
        # First try to find diet in the assistant messages
        if "assistant_messages" in data:
            for msg in data.get("assistant_messages", []):
                if isinstance(msg, str) and "¡Aquí tienes tu dieta" in msg:
                    try:
                        # Find the diet dictionary in the string
                        diet_str = msg.split("\n", 1)[1] if "\n" in msg else ""
                        if diet_str:
                            # Try to parse the diet dictionary
                            try:
                                diet_dict = ast.literal_eval(diet_str)
                                meals_found = process_diet_dict(diet_dict, doc_id)
                                if meals_found > 0:
                                    print(f"Found {meals_found} meals in assistant_messages for doc {doc_id}")
                            except (SyntaxError, ValueError) as e:
                                print(f"Could not parse diet in assistant_messages for doc {doc_id}: {e}")
                    except Exception as e:
                        print(f"Error processing assistant message in doc {doc_id}: {e}")
        
        # Check messages array
        if "messages" in data:
            for msg in data.get("messages", []):
                if isinstance(msg, dict) and msg.get("role") == "assistant" and "¡Aquí tienes tu dieta" in msg.get("content", ""):
                    try:
                        # Find the diet dictionary in the string
                        diet_str = msg.get("content", "").split("\n", 1)[1] if "\n" in msg.get("content", "") else ""
                        if diet_str:
                            # Try to parse the diet dictionary
                            try:
                                diet_dict = ast.literal_eval(diet_str)
                                meals_found = process_diet_dict(diet_dict, doc_id)
                                if meals_found > 0:
                                    print(f"Found {meals_found} meals in messages for doc {doc_id}")
                            except (SyntaxError, ValueError) as e:
                                print(f"Could not parse diet in messages for doc {doc_id}: {e}")
                    except Exception as e:
                        print(f"Error processing message in doc {doc_id}: {e}")
        
        # Check conversation array
        if "conversation" in data:
            for msg in data.get("conversation", []):
                if isinstance(msg, dict) and msg.get("role") == "assistant" and "¡Aquí tienes tu dieta" in msg.get("content", ""):
                    try:
                        # Find the diet dictionary in the string
                        diet_str = msg.get("content", "").split("\n", 1)[1] if "\n" in msg.get("content", "") else ""
                        if diet_str:
                            # Try to parse the diet dictionary
                            try:
                                diet_dict = ast.literal_eval(diet_str)
                                meals_found = process_diet_dict(diet_dict, doc_id)
                                if meals_found > 0:
                                    print(f"Found {meals_found} meals in conversation for doc {doc_id}")
                            except (SyntaxError, ValueError) as e:
                                print(f"Could not parse diet in conversation for doc {doc_id}: {e}")
                    except Exception as e:
                        print(f"Error processing conversation in doc {doc_id}: {e}")

# --- VALIDATE EXPORTED FILES ---
print("Validating exported JSONL files...")

def validate_jsonl_file(file_path):
    """Validate each line in the JSONL file to ensure it's valid JSON"""
    if not os.path.exists(file_path):
        print(f"File does not exist: {file_path}")
        return False
    
    print(f"Validating {file_path}...")
    valid_lines = []
    line_count = 0
    
    with open(file_path, "r") as f:
        for i, line in enumerate(f):
            line_count += 1
            try:
                # Attempt to parse the JSON
                json.loads(line)
                valid_lines.append(line)
            except json.JSONDecodeError as e:
                print(f"Invalid JSON at line {i+1}: {e}")
                print(f"Problematic line: {line[:100]}...")
    
    # Write back only the valid lines
    with open(file_path, "w") as f:
        for line in valid_lines:
            f.write(line)
    
    print(f"Validated {file_path}: {len(valid_lines)} valid lines out of {line_count}")
    return len(valid_lines) > 0

# Validate all files
conversations_valid = validate_jsonl_file(f"{export_dir}/conversations.jsonl")
grocery_items_valid = validate_jsonl_file(f"{export_dir}/grocery_items.jsonl")
meals_valid = validate_jsonl_file(f"{export_dir}/meals.jsonl")

# --- DEFINE TABLE SCHEMAS ---
conversations_schema = [
    bigquery.SchemaField("document_id", "STRING"),
    bigquery.SchemaField("has_diet", "BOOLEAN"),
    bigquery.SchemaField("has_grocery_list", "BOOLEAN"),
    bigquery.SchemaField("budget", "STRING"),
    bigquery.SchemaField("intolerances", "STRING"),
    bigquery.SchemaField("forbidden_foods", "STRING")
]

grocery_items_schema = [
    bigquery.SchemaField("document_id", "STRING"),
    bigquery.SchemaField("product", "STRING"),
    bigquery.SchemaField("quantity", "FLOAT"),
    bigquery.SchemaField("units", "STRING"),
    bigquery.SchemaField("matching_product", "STRING"),
    bigquery.SchemaField("estimated_price", "FLOAT"),
    bigquery.SchemaField("units_needed", "FLOAT")
]

meals_schema = [
    bigquery.SchemaField("document_id", "STRING"),
    bigquery.SchemaField("day", "INTEGER"),
    bigquery.SchemaField("meal_type", "STRING"),
    bigquery.SchemaField("food_item", "STRING"),
    bigquery.SchemaField("quantity", "FLOAT"),
    bigquery.SchemaField("unit", "STRING")
]

# --- UPLOAD FILES TO BIGQUERY ---
print("Uploading data to BigQuery...")

# Helper function to load data from file
def load_table_from_file(table_name, schema, file_path):
    if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        print(f"No data to load for {table_name}")
        return
    
    table_id = f"{PROJECT_ID}.{BQ_DATASET}.{table_name}"
    
    # Configure the load job
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        schema=schema,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        max_bad_records=10  # Allow some bad records
    )
    
    print(f"Loading data into {table_name}...")
    
    # Load the file
    with open(file_path, "rb") as source_file:
        job = bq_client.load_table_from_file(
            source_file,
            table_id,
            job_config=job_config
        )
    
    # Wait for the job to complete
    job.result()
    
    # Get loaded rows count
    table = bq_client.get_table(table_id)
    print(f"Loaded {table.num_rows} rows into {table_name}")

# Load all tables
if conversations_valid:
    load_table_from_file("conversations", conversations_schema, f"{export_dir}/conversations.jsonl")
if grocery_items_valid:
    load_table_from_file("grocery_items", grocery_items_schema, f"{export_dir}/grocery_items.jsonl")
if meals_valid:
    load_table_from_file("meals", meals_schema, f"{export_dir}/meals.jsonl")

print("Export process completed successfully!")