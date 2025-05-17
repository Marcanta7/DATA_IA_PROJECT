from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver
from states import DietState
from intolerancias import intolerance_search
from listacompra import generar_lista_compra_csv
from assistant import router
from expertoendietas import buscar_info_dietas
from crear_dieta import crear_dieta
from convertidor import poner_precio
from otros import otros
from typing import List, Dict, Annotated, Any
from langchain_core.messages import BaseMessage
import operator

# Definición del estado del grafo
# Usa la clase DietState importada de states.py, que ya tiene el campo 'messages' correctamente definido como una lista de diccionarios.
# Elimina la definición redundante y errónea aquí.

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
    lambda x: getattr(x, "next", "otros"),
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
workflow.add_edge("poner_precio",END)
workflow.add_edge("otros",END)

# Usa InMemorySaver de LangGraph para la memoria de conversación
checkpointer = InMemorySaver()
graph = workflow.compile(checkpointer=checkpointer)

if __name__ == "__main__":
    session_id = "usuario_1"
    print("Bienvenido al asistente de dietas. Escribe 'salir' para terminar.")
    # Inicializa el estado solo una vez
    state = {
        "messages": [],
        "intolerances": [],
        "forbidden_foods": [],
        "diet": {},
        "budget": None,
        "info_dietas": "",
        "grocery_list": []
    }
    while True:
        user_input = input("\nTú: ")
        if user_input.lower() in ["salir", "exit"]:
            print("Asistente: ¡Hasta pronto!")
            break
        # Añade el mensaje del usuario al historial
        state["messages"].append({"role": "user", "content": user_input})
        try:
            result = graph.invoke(state, config={"configurable": {"thread_id": session_id}})
            state = result  # Mantén el estado actualizado
        except Exception as e:
            print(f" Hubo un problema ejecutando el asistente: {e}")
            continue

        assistant_msgs = [m for m in reversed(state['messages']) if m.get("role") == "assistant"]
        if assistant_msgs:
            print(f"Asistente: {assistant_msgs[-1]['content']}")
        else:
            print("Asistente: (No hay respuesta del asistente en este turno)")