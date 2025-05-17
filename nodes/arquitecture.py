from langgraph.graph import StateGraph, END
from states import DietState
from intolerancias import intolerance_search
from listacompra import generar_lista_compra_csv
from assistant import router
from expertoendietas import buscar_info_dietas
from crear_dieta import crear_dieta
from convertidor import poner_precio
from otros import otros


# Definición del grafo según el diagrama
workflow = StateGraph(DietState)
workflow.add_node("input_usuario", router)
workflow.add_node("intolerancias", intolerance_search)
workflow.add_node("experto_dietas", buscar_info_dietas)
workflow.add_node("hacer_lista_compra", generar_lista_compra_csv)
workflow.add_node("crear_dieta", crear_dieta)
workflow.add_node("poner_precio", poner_precio)
workflow.add_node("otros", otros)

# Transiciones
workflow.set_entry_point("input_usuario")
workflow.add_conditional_edges(
    "input_usuario",
    lambda x: x["next"],
    {
        "intolerancias": "intolerancias",
        "experto_dietas": "experto_dietas",
        "otros": "otros"
    }
)
workflow.add_edge("intolerancias", "input_usuario")
workflow.add_edge("experto_dietas", "crear_dieta")
workflow.add_edge("crear_dieta", "hacer_lista_compra")
workflow.add_edge("hacer_lista_compra","poner_precio")
workflow.add_edge("otros", END)
workflow.add_edge("poner_precio",END)

graph = workflow.compile()

if __name__ == "__main__":
    # Estado inicial vacío
    state = DietState(
        intolerances=[],
        forbidden_foods=[],
        diet={},
        budget=None,
        grocery_list=[],
        messages=[]
    )
    print("Bienvenido al asistente de dietas. Escribe 'salir' para terminar.")
    while True:
        user_input = input("\nTu pregunta o instrucción: ")
        if user_input.lower() in ["salir", "exit"]:
            print("¡Hasta pronto!")
            break
        # Asegurar que 'messages' existe y es lista
        if not hasattr(state, 'messages') or state["messages"] is None:
            state["messages"] = []
        # Añadir el mensaje del usuario al historial
        try:
            state["messages"].append({"role": "user", "content": user_input})
        except Exception as e:
            print(f"[DEBUG] Error añadiendo mensaje al historial: {e}")
            print(f"[DEBUG] state: {state}")
            continue
        # Ejecutar el grafo y capturar posibles errores
        try:
            state = graph.invoke(state)
        except Exception as e:
            print(f"[ERROR] Hubo un problema ejecutando el grafo: {e}")
            print(f"[DEBUG] state: {state}")
            continue
        # Mostrar la información relevante encontrada (si existe)
        info = state.get("info_dietas", None)
        if info:
            # print(f"\nInformación relevante encontrada:\n{info}")
            pass
        #else:
            #print("\n(No se encontró información relevante en esta iteración)")
