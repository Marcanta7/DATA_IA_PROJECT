import pandas as pd
import math
from typing import Tuple
from fuzzywuzzy import fuzz, process
from states import DietState

def buscar_precio(lista_compra_row, bbdd_df):
    producto_lc = str(lista_compra_row['Producto'])
    cantidad_lc = float(lista_compra_row['Cantidad'])
    unidad_lc = str(lista_compra_row['Unidades'])
    producto_coincidente = None
    unidades_necesarias = None

    def calcular_precio_y_unidades(fila_producto):
        cantidad_disponible = fila_producto['Cantidad_real']
        precio_unitario = fila_producto['Precio']
        nombre_producto = fila_producto['Nombre']
        unidad_producto = str(fila_producto['Unidad_medida'])

        if unidad_producto.lower() != unidad_lc.lower():
            return None, None, None

        unidades = math.ceil(cantidad_lc / cantidad_disponible)
        precio_total = precio_unitario * unidades
        return precio_total, nombre_producto, unidades

    bbdd_df['Nombre'] = bbdd_df['Nombre'].astype(str)
    bbdd_df['Unidad_medida'] = bbdd_df['Unidad_medida'].astype(str)

    coincidencia_exacta = bbdd_df[
        (bbdd_df['Nombre'].str.lower() == producto_lc.lower()) &
        (bbdd_df['Unidad_medida'].str.lower() == unidad_lc.lower())
    ]
    if not coincidencia_exacta.empty:
        fila = coincidencia_exacta.iloc[0]
        return calcular_precio_y_unidades(fila)

    nombres_bbdd = bbdd_df['Nombre'].tolist()
    similares = process.extract(producto_lc, nombres_bbdd, scorer=fuzz.token_sort_ratio, limit=5)

    for resultado in similares:
        nombre_similar = resultado[0]
        fila_similar = bbdd_df[bbdd_df['Nombre'].str.lower() == nombre_similar.lower()]
        if not fila_similar.empty:
            fila = fila_similar.iloc[0]
            return calcular_precio_y_unidades(fila)

    return None, None, None

# ✅ NODO: función para el workflow
def poner_precio(state: DietState) -> DietState:
    # Cargar la base de datos de precios
    bbdd_df = pd.read_csv(r'nodes/precios.csv')

    # Convertir grocery_list en DataFrame
    lista_df = pd.read_csv(r'lista_compra.csv')
    lista_df['Cantidad'] = lista_df['Cantidad'].astype(float)

    # Aplicar búsqueda de precios
    lista_df[['Precio_Estimado', 'Producto_Coincidente', 'Unidades_Necesarias']] = lista_df.apply(
        buscar_precio,
        axis=1,
        bbdd_df=bbdd_df,
        result_type='expand'
    )

    # Guardar CSV (opcional, o puedes quitar esta parte si no quieres escribir archivos)
    lista_df.to_csv('lista_compra_con_precio.csv', index=False, encoding='utf-8')
    print("✅ Se ha generado el archivo lista_compra_con_precio.csv con precios estimados.")

    # Opcional: almacenar el resultado en el estado si lo necesitas después
    state.grocery_list = lista_df.to_dict(orient='records')

    return state
