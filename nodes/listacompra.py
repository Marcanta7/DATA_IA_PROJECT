import csv
from collections import defaultdict
from typing import Dict, Tuple, List, Optional
from states import DietState

def generar_lista_compra_csv(state: DietState) -> DietState:
    """
    Genera una lista de compra consolidada a partir del objeto DietState y la guarda en un archivo CSV.

    Args:
        state (DietState): Objeto DietState que contiene la información de la dieta.

    Returns:
        DietState: El objeto DietState con la lista de la compra actualizada.
    """
    nombre_archivo_csv = "lista_compra.csv" # Se define el nombre del archivo

    lista_compra = defaultdict(lambda: [0.0, ""])

    if state.diet is None:
        print("La dieta está vacía. No se generará la lista de compra.")
        state.grocery_list = [] # Asegurar que grocery_list está inicializada
        return state

    for dia in state.diet.values():
        for comida in dia.values():
            for alimento, (cantidad, unidad) in comida.items():
                if lista_compra[alimento][1] == "":
                    lista_compra[alimento][1] = unidad
                elif lista_compra[alimento][1] != unidad:
                    print(f"¡Advertencia! Unidad inconsistente para {alimento}. Se usará la primera unidad encontrada.")
                lista_compra[alimento][0] += cantidad

    with open(nombre_archivo_csv, 'w', newline='', encoding='utf-8') as archivo_csv:
        writer = csv.writer(archivo_csv)
        writer.writerow(["Producto", "Cantidad", "Unidades"])  # Escribir encabezado

        for alimento, (cantidad, unidad) in lista_compra.items():
            writer.writerow([alimento, cantidad, unidad])

    print(f"Se ha generado el archivo {nombre_archivo_csv} con la lista de compra.")
    
    # Actualiza el estado con la lista de la compra generada
    state.grocery_list = [f"{alimento}: {cantidad} {unidad}" for alimento, (cantidad, unidad) in lista_compra.items()]
    return state