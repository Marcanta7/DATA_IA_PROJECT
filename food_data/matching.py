import duckdb

OFF_DATA_PATH = "openfoodfacts-products.jsonl"  # o .tsv según tu caso

con = duckdb.connect()

query = f"""
SELECT * 
FROM read_csv_auto('{OFF_DATA_PATH}', delim='\t', sample_size=1, all_varchar=true)
LIMIT 1
"""

df = con.execute(query).df()
print("\nColumnas detectadas:")
for i, col in enumerate(df.columns):
    print(f"{i+1}. {col}")