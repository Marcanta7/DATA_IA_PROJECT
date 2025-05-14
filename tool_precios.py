import csv
from typing import Dict, Tuple
from collections import defaultdict
from google.cloud import bigquery

def price_tool_csv(diet: Dict[int, Dict[str, Dict[str, Tuple[float, str]]]], nombre_archivo_csv="lista_compra.csv"):
    """
    Genera una lista de compra consolidada y la guarda en un archivo CSV.

    Args:
        dieta (Dict): Un diccionario anidado que representa la dieta. Ten en cuenta que deben incluir desayuno,almuerzo,comida,merienda y cena.
        nombre_archivo_csv (str, opcional): El nombre del archivo CSV a crear.
                                            Por defecto es "lista_compra.csv".
    """
    lista_compra = defaultdict(float)
    unidades = {}
    lista_compra_final = []  # Lista de diccionarios para escribir en el CSV

    for dia, comidas in dieta.items():
        for comida, ingredientes in comidas.items():
            for ingrediente, (cantidad, unidad) in ingredientes.items():
                lista_compra[ingrediente] += cantidad
                if ingrediente not in unidades:
                    unidades[ingrediente] = unidad
                elif unidades[ingrediente] != unidad and unidad:
                    print(f"¡Advertencia! Unidad inconsistente para '{ingrediente}'. Se usará '{unidades[ingrediente]}'.")

    for producto, cantidad_total in lista_compra.items():
        unidad = unidades.get(producto, '')
        lista_compra_final.append({"producto": producto, "cantidad": cantidad_total, "unidad": unidad.strip()})

    try:
        with open(nombre_archivo_csv, 'w', newline='', encoding='utf-8') as archivo_csv:
            nombres_columnas = ["producto", "cantidad", "unidad"]
            writer = csv.DictWriter(archivo_csv, fieldnames=nombres_columnas)

            writer.writeheader()
            writer.writerows(lista_compra_final)

        print(f"\nLista de compra guardada en el archivo '{nombre_archivo_csv}'")

    except Exception as e:
        print(f"Ocurrió un error al escribir el archivo CSV: {e}")