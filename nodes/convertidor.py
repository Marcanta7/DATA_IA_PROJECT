import pandas as pd
import math
from typing import List, Dict, Tuple, Optional, Any
from states import DietState
from sentence_transformers import SentenceTransformer, util
from google.cloud import bigquery
import re
import logging
import traceback
import os

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('convertidor')

class BigQueryProductMatcher:
    def __init__(
        self, 
        project_id: str = "diap3-458416",
        dataset_id: str = "food_data", 
        table_id: str = "mercadona_enriched_products_clean"
    ):
        """Initialize the product matcher with BigQuery connection details."""
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.table_id = table_id
        
        logger.info(f"Initializing BigQuery connection to {project_id}.{dataset_id}.{table_id}")
        # Try to initialize the client with explicit project and more error handling
        try:
            # Ensure we have the project ID in environment variables
            os.environ['GOOGLE_CLOUD_PROJECT'] = project_id
            
            # Initialize BigQuery client with explicit project ID
            self.client = bigquery.Client(project=project_id)
            
            # Test the connection immediately
            self.client.list_datasets(max_results=1)
            logger.info("✅ Successfully connected to BigQuery")
        except Exception as e:
            logger.error(f"❌ Failed to connect to BigQuery: {e}")
            logger.error(f"Error details: {traceback.format_exc()}")
            # Continue initialization, we'll check for client before queries
            self.client = None
        
        logger.info("Loading sentence transformer model")
        self.model = SentenceTransformer('intfloat/multilingual-e5-large')
        
        self.precios_df = None
        self.productos_embeddings = None
        self.productos = None
        
        # Load data from BigQuery if client was initialized successfully
        if self.client:
            self.load_data()
        else:
            logger.error("BigQuery client initialization failed. Cannot load data.")
    
    def load_data(self) -> None:
        """Load product data from BigQuery and prepare embeddings."""
        try:
            # First check if the table exists
            try:
                dataset_ref = self.client.dataset(self.dataset_id)
                table_ref = dataset_ref.table(self.table_id)
                self.client.get_table(table_ref)
                logger.info(f"✅ Table {self.project_id}.{self.dataset_id}.{self.table_id} exists")
            except Exception as e:
                logger.error(f"❌ Table {self.project_id}.{self.dataset_id}.{self.table_id} does not exist: {e}")
                logger.error(f"Error details: {traceback.format_exc()}")
                return
                
            logger.info("Executing BigQuery query to retrieve product data...")
            query = f"""
                SELECT
                    Nombre,
                    Precio,
                    Descripcion_del_producto,
                    off_product_name
                FROM
                    `{self.project_id}.{self.dataset_id}.{self.table_id}`
                WHERE
                    Nombre IS NOT NULL AND Precio IS NOT NULL 
                LIMIT 1000  /* Limiting to 1000 rows for faster processing */
            """
            
            # Execute query with timeout (FIXED: changed timeout_ms to timeout)
            job_config = bigquery.QueryJobConfig()
            # Set timeout as a property (60 seconds)
            job_config.timeout = 60  # Timeout in seconds
            
            query_job = self.client.query(query, job_config=job_config)
            logger.info(f"BigQuery job {query_job.job_id} started")
            
            self.precios_df = query_job.to_dataframe()
            logger.info(f"Query complete. Retrieved {len(self.precios_df)} rows")
            
            if self.precios_df.empty:
                logger.warning("No products found in the BigQuery table")
                return
            
            # Fill missing values with defaults
            text_columns = ['Nombre', 'Descripcion_del_producto', 'off_product_name']
            for col in text_columns:
                if col in self.precios_df.columns:
                    self.precios_df[col] = self.precios_df[col].fillna('').astype(str)
                
            # Combine product information for better semantic matching
            logger.info("Creating combined product descriptions for semantic matching...")
            self.productos = (
                self.precios_df['Nombre'] + " " +
                self.precios_df['Descripcion_del_producto'] + " " +
                self.precios_df['off_product_name']
            ).tolist()
            
            # Pre-compute embeddings for all products
            logger.info("Computing embeddings for all products (this may take a moment)...")
            self.productos_embeddings = self.model.encode(self.productos, convert_to_tensor=True)
            logger.info(f"✅ Successfully loaded {len(self.productos)} products from BigQuery")
            
        except Exception as e:
            logger.error(f"Error loading data from BigQuery: {e}")
            logger.error(f"Error details: {traceback.format_exc()}")
            logger.warning("Could not load product data from BigQuery. Product matching will not work.")
    
    def buscar_producto(self, prompt_usuario: str, unidad_requerida: str = None, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Find the top_k most similar products to the user prompt.
        Optionally filter by unit of measurement.
        Returns a list of dictionaries with product details and similarity scores.
        """
        if self.precios_df is None or self.productos_embeddings is None:
            logger.warning("No product data available. BigQuery query may have failed.")
            return []
            
        try:
            # Standardize unit names if provided
            if unidad_requerida:
                unidad_requerida = self._normalizar_unidad(unidad_requerida)
                
            # Encode the user prompt
            prompt_emb = self.model.encode(prompt_usuario, convert_to_tensor=True)
            
            # Calculate similarity scores
            similitudes = util.cos_sim(prompt_emb, self.productos_embeddings)[0]
            
            # Get top_k indices
            top_valores, top_indices = similitudes.topk(min(top_k * 3, len(similitudes)))
            
            resultados = []
            for i, idx in enumerate(top_indices.cpu().numpy()):
                score = similitudes[idx].item()
                fila = self.precios_df.iloc[idx]
                
                resultados.append({
                    'Nombre': fila['Nombre'],
                    'Precio': fila['Precio'],
                    'Descripcion': fila.get('Descripcion_del_producto', ''),
                    'Score': score,
                })
                
                # Stop once we have enough results
                if len(resultados) >= top_k:
                    break
                
            return resultados
            
        except Exception as e:
            logger.error(f"Error searching for products: {e}")
            logger.error(f"Error details: {traceback.format_exc()}")
            return []
    
    def _normalizar_unidad(self, unidad: str) -> str:
        """Normalize unit names for better matching."""
        unidad = unidad.lower().strip()
        
        # Mapping of common unit variations
        unidades_map = {
            # Weight units
            'g': 'gramos', 'gr': 'gramos', 'gram': 'gramos', 'gramo': 'gramos', 'grs': 'gramos',
            'kg': 'kilogramos', 'kilo': 'kilogramos', 'kilos': 'kilogramos', 'kilogramo': 'kilogramos',
            
            # Volume units
            'l': 'litros', 'lt': 'litros', 'ltr': 'litros', 'litro': 'litros',
            'ml': 'mililitros', 'mililitro': 'mililitros',
            
            # Count units
            'ud': 'unidad', 'und': 'unidad', 'unid': 'unidad', 'u': 'unidad',
            'uds': 'unidades', 'unds': 'unidades', 'unids': 'unidades',
            'pza': 'unidad', 'pzas': 'unidades', 'pieza': 'unidad', 'piezas': 'unidades',
        }
        
        # Return mapped unit or original if not in map
        return unidades_map.get(unidad, unidad)
    
    def parse_grocery_item(self, item: str) -> Optional[Dict[str, Any]]:
        """
        Parse a grocery list item in format "product: quantity unit".
        Returns a dictionary with parsed information or None if format is invalid.
        """
        match = re.match(r"^(.+?):\s*([\d\.]+)\s*(\w+)$", item)
        if not match:
            logger.warning(f"Unrecognized format: '{item}'")
            return None
            
        articulo = match.group(1).strip()
        cantidad = float(match.group(2).replace(",", "."))
        unidad = match.group(3).strip()
        
        return {
            'Producto': articulo,
            'Cantidad': cantidad,
            'Unidades': unidad
        }


def buscar_precio_bigquery(lista_compra_row, matcher):
    """
    Find price information for a product in the grocery list using the matcher.
    Returns the exact price from BigQuery without any multiplication.
    """
    try:
        producto_lc = str(lista_compra_row['Producto'])
        cantidad_lc = float(lista_compra_row['Cantidad'])
        unidad_lc = str(lista_compra_row['Unidades'])
        
        logger.info(f"Buscando precio para: {cantidad_lc} {unidad_lc} de '{producto_lc}'")
        
        # Get the best match using semantic search
        matches = matcher.buscar_producto(producto_lc, top_k=1)
        
        if not matches:
            logger.info(f"No matching products found for '{producto_lc}'")
            return None, None
            
        match = matches[0]
        
        # Skip if score is too low
        similarity_threshold = 0.3  # Adjust as needed
        if match['Score'] < similarity_threshold:
            logger.info(f"Match found for '{producto_lc}' but score too low: {match['Score']:.2f}")
            return None, None
            
        precio = match['Precio']
        nombre_producto = match['Nombre']
        
        # No multiplication, return the exact price from BigQuery
        logger.info(f"Producto encontrado: {nombre_producto} (score: {match['Score']:.2f})")
        logger.info(f"Precio: €{precio:.2f}")
        
        return precio, nombre_producto
        
    except Exception as e:
        logger.error(f"Error al buscar precio para {lista_compra_row.get('Producto', 'unknown')}: {e}")
        logger.error(f"Error details: {traceback.format_exc()}")
        return None, None


# ✅ NODO: función para el workflow
def poner_precio(state: DietState,
                 project_id: str = "diap3-458416",
                 dataset_id: str = "food_data",
                 table_id: str = "mercadona_enriched_products_clean") -> DietState:
    """
    Process the grocery list in the state, find product matches and prices using BigQuery.
    This function is designed to work with LangGraph workflows.
    """
    logger.info("Starting price estimation process with BigQuery")
    
    try:
        # Initialize the product matcher with BigQuery
        matcher = BigQueryProductMatcher(
            project_id=project_id,
            dataset_id=dataset_id,
            table_id=table_id
        )
        
        # Check if the client was initialized successfully
        if matcher.client is None:
            logger.error("BigQuery client initialization failed. Cannot continue with price estimation.")
            return state
        
        # Check if we have product data
        if matcher.precios_df is None or matcher.productos_embeddings is None:
            logger.error("Product data not loaded from BigQuery. Cannot continue with price estimation.")
            return state
        
        # Check if we have a grocery list in the state
        if not state.grocery_list:
            logger.warning("La lista de la compra está vacía en el estado.")
            return state
        
        # Process grocery list items
        items_to_process = []
        
        # Check if the grocery list contains strings or dictionaries
        if all(isinstance(item, str) for item in state.grocery_list):
            # Parse string items (format: "product: quantity unit")
            for item in state.grocery_list:
                parsed = matcher.parse_grocery_item(item)
                if parsed:
                    items_to_process.append(parsed)
                else:
                    logger.warning(f"Could not parse item: '{item}'")
        else:
            # Assume already parsed items
            items_to_process = state.grocery_list
        
        if not items_to_process:
            logger.warning("No valid items to process in the grocery list.")
            return state
        
        # Create DataFrame from items
        lista_df = pd.DataFrame(items_to_process)
        
        # Apply price search to each row
        results = []
        for _, row in lista_df.iterrows():
            precio, producto_coincidente = buscar_precio_bigquery(row, matcher)
            
            result_row = row.to_dict()
            result_row.update({
                'Precio_Unitario': precio,
                'Producto_Coincidente': producto_coincidente
            })
            
            results.append(result_row)
        
        # Convert results to DataFrame
        result_df = pd.DataFrame(results)
        
        # Log match statistics
        matched_count = result_df['Precio_Unitario'].notna().sum()
        total_count = len(result_df)
        match_percentage = (matched_count/total_count*100) if total_count > 0 else 0
        logger.info(f"Matched {matched_count} of {total_count} products ({match_percentage:.1f}%)")
        
        # Save results to CSV
        try:
            result_df.to_csv('lista_compra_con_precio.csv', index=False, encoding='utf-8')
            logger.info("✅ Se ha generado el archivo lista_compra_con_precio.csv con precios unitarios.")
        except Exception as e:
            logger.error(f"Error saving results to CSV: {e}")
            logger.error(f"Error details: {traceback.format_exc()}")
        
        # Update the state with the results
        state.grocery_list = result_df.to_dict(orient='records')
        
        return state
        
    except Exception as e:
        logger.error(f"Error in poner_precio: {e}")
        logger.error(f"Error details: {traceback.format_exc()}")
        # Return the original state in case of error
        return state


# Example usage for testing
if __name__ == "__main__":
    class MockDietState:
        def __init__(self):
            self.grocery_list = [
                "Leche: 2 litros",
                "Pan: 1 unidad", 
                "Manzanas: 1.5 kg",
                "Yogur natural: 6 unidades"
            ]
    
    print("BigQuery Product Matcher Test")
    print("-----------------------------")
    
    # Create a mock state
    mock_state = MockDietState()
    
    # Run the price estimation
    updated_state = poner_precio(mock_state)
    
    # Print the results
    if updated_state.grocery_list:
        print("\nProcessed grocery list with prices:")
        for item in updated_state.grocery_list:
            producto = item.get('Producto', '?')
            precio = item.get('Precio_Unitario', None)
            coincidente = item.get('Producto_Coincidente', 'No encontrado')
            
            if precio:
                print(f"✅ {producto}: €{precio:.2f} ({coincidente})")
            else:
                print(f"❌ {producto}: No encontrado")
    else:
        print("No results found")