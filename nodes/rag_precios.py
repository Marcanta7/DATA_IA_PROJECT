import pandas as pd
import re
from typing import List, Dict, Tuple, Optional, Any
from sentence_transformers import SentenceTransformer, util
from google.cloud import bigquery

class ProductMatcher:
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
        self.client = bigquery.Client(project=project_id)
        self.model = SentenceTransformer('intfloat/multilingual-e5-large')
        self.precios_df = None
        self.productos_embeddings = None
        self.productos = None
        
        # Load data from BigQuery
        self.load_data()
    
    def load_data(self) -> None:
        """Load product data from BigQuery and prepare embeddings."""
        try:
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
                    AND Descripcion_del_producto IS NOT NULL AND off_product_name IS NOT NULL
            """
            
            self.precios_df = self.client.query(query).to_dataframe()
            
            if self.precios_df.empty:
                print(f"Warning: No products found in the BigQuery table")
                return
                
            # Combine product information for better semantic matching
            self.productos = (
                self.precios_df['Nombre'].astype(str) + " " +
                self.precios_df['Descripcion_del_producto'].astype(str) + " " +
                self.precios_df['off_product_name'].astype(str)
            ).tolist()
            
            # Pre-compute embeddings for all products (this improves performance for multiple searches)
            self.productos_embeddings = self.model.encode(self.productos, convert_to_tensor=True)
            print(f"Loaded {len(self.productos)} products from BigQuery")
            
        except Exception as e:
            print(f"Error loading data from BigQuery: {e}")
    
    def buscar_producto(self, prompt_usuario: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Find the top_k most similar products to the user prompt.
        Returns a list of dictionaries with product details and similarity scores.
        """
        if self.precios_df is None or self.productos_embeddings is None:
            print("No product data available. Please check BigQuery connection.")
            return []
            
        try:
            # Encode the user prompt
            prompt_emb = self.model.encode(prompt_usuario, convert_to_tensor=True)
            
            # Calculate similarity scores
            similitudes = util.cos_sim(prompt_emb, self.productos_embeddings)[0]
            
            # Get top_k indices
            top_valores, top_indices = similitudes.topk(top_k)
            
            resultados = []
            for i, idx in enumerate(top_indices.cpu().numpy()):
                score = similitudes[idx].item()
                fila = self.precios_df.iloc[idx]
                
                resultados.append({
                    'Nombre': fila['Nombre'],
                    'Precio': fila['Precio'],
                    'Descripcion': fila['Descripcion_del_producto'],
                    'OFF_Name': fila['off_product_name'],
                    'Score': score,
                    'Index': idx
                })
                
            return resultados
            
        except Exception as e:
            print(f"Error searching for products: {e}")
            return []
    
    def parse_grocery_list_item(self, item: str) -> Optional[Dict[str, Any]]:
        """
        Parse a grocery list item in format "product: quantity unit".
        Returns a dictionary with parsed information or None if format is invalid.
        """
        match = re.match(r"^(.+?):\s*([\d\.]+)\s*(\w+)$", item)
        if not match:
            print(f"Unrecognized format: '{item}'")
            return None
            
        articulo = match.group(1).strip()
        cantidad = float(match.group(2).replace(",", "."))
        unidad = match.group(3).strip()
        
        return {
            'Articulo': articulo,
            'Cantidad': cantidad,
            'Unidad': unidad
        }
    
    def process_grocery_list(self, grocery_list: List[str], 
                             resultado_file: str = "lista_compra_con_precios.csv") -> pd.DataFrame:
        """
        Process a list of grocery items, match them with products, and calculate prices.
        Optionally save the results to a CSV file.
        """
        resultados = []
        
        if not grocery_list:
            print("The grocery list is empty.")
            return pd.DataFrame(resultados)
            
        for entrada in grocery_list:
            parsed_item = self.parse_grocery_list_item(entrada)
            if not parsed_item:
                continue
                
            articulo = parsed_item['Articulo']
            cantidad = parsed_item['Cantidad']
            unidad = parsed_item['Unidad']
            
            # Get the best match for this item
            matches = self.buscar_producto(articulo, top_k=1)
            
            if matches and matches[0]['Score'] > 0.3:  # Apply a similarity threshold
                match = matches[0]
                precio_unitario = match['Precio']
                precio_total = precio_unitario * cantidad if precio_unitario else None
                
                resultados.append({
                    'Artículo': articulo,
                    'Cantidad': cantidad,
                    'Unidad': unidad,
                    'Producto Encontrado': match['Nombre'],
                    'Precio Unitario (€)': precio_unitario,
                    'Precio Total (€)': precio_total,
                    'Score': match['Score']
                })
            else:
                resultados.append({
                    'Artículo': articulo,
                    'Cantidad': cantidad,
                    'Unidad': unidad,
                    'Producto Encontrado': 'No encontrado',
                    'Precio Unitario (€)': None,
                    'Precio Total (€)': None,
                    'Score': None
                })
        
        df_resultados = pd.DataFrame(resultados)
        
        # Save results to CSV if requested
        if resultado_file and not df_resultados.empty:
            df_resultados.to_csv(resultado_file, index=False, encoding='utf-8')
            print(f"Results saved to '{resultado_file}'.")
            
        return df_resultados

# Example usage
if __name__ == "__main__":
    # Initialize the product matcher
    matcher = ProductMatcher()
    
    # Interactive search mode
    def interactive_search():
        while True:
            prompt = input("\nWhat product are you looking for? (or 'q' to quit): ")
            if prompt.lower() in ('q', 'quit', 'exit'):
                break
                
            resultados = matcher.buscar_producto(prompt, top_k=5)
            
            if not resultados:
                print("No matching products found.")
                continue
                
            print(f"\nTop 5 products similar to: '{prompt}'\n")
            for i, producto in enumerate(resultados, 1):
                print(f"{i}. {producto['Nombre']} (score: {producto['Score']:.2f})")
                print(f"   Price: €{producto['Precio']}")
                print(f"   Description: {producto['Descripcion']}")
                print("-" * 60)
    
    # Process grocery list mode
    def process_list_example():
        example_list = [
            "Leche: 2 litros",
            "Pan: 1 unidad", 
            "Manzanas: 1.5 kg",
            "Yogur natural: 6 unidades"
        ]
        
        print("\nProcessing example grocery list:")
        for item in example_list:
            print(f"- {item}")
            
        results_df = matcher.process_grocery_list(example_list)
        
        print("\nResults:")
        print(results_df.to_string(index=False))
        
        # Calculate total cost
        total_cost = results_df['Precio Total (€)'].sum()
        print(f"\nTotal estimated cost: €{total_cost:.2f}")
    
    # Choose which mode to run
    print("BigQuery Product Matcher")
    print("1. Interactive product search")
    print("2. Process example grocery list")
    
    choice = input("Choose an option (1 or 2): ")
    
    if choice == "1":
        interactive_search()
    elif choice == "2":
        process_list_example()
    else:
        print("Invalid choice. Exiting.")