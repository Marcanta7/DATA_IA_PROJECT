from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver
from states import DietState
from intolerancias import intolerance_search
from mensaje_intolerancias import mensaje_intolerancias
from intolerancias_router import intolerancias_router
from listacompra import generar_lista_compra_csv
from assistant import router
from expertoendietas import buscar_info_dietas
from crear_dieta import crear_dieta
from convertidor import poner_precio
from otros import otros
from typing import List, Dict, Annotated, Any, Optional
from langchain_core.messages import BaseMessage
import operator
from google.cloud import firestore
import json
import pickle
import base64
import traceback
import datetime
import uuid
import copy

# Implementación personalizada del saver para Firestore
class FirestoreSaver:
    """Implementación de guardado de estado en Firestore para LangGraph."""
    
    def __init__(self, 
                 collection_name: str = "conversations", 
                 project_id: str = "diap3-458416",
                 database_id: str = "agente-context-prueba"
                ):
        """
        Inicializa el saver de Firestore.
        
        Args:
            collection_name: Nombre de la colección en Firestore
            project_id: ID del proyecto de Google Cloud
            database_id: ID de la base de datos de Firestore
        """
        self.collection_name = collection_name
        self.db = firestore.Client(project=project_id, database=database_id)
        # Diccionario para cache en memoria
        self._cache = {}
        print(f"🔌 Conectado a Firestore (base de datos: {database_id}, colección: {collection_name})")
    
    def get(self, key: str) -> Optional[Dict]:
        """
        Recupera un estado guardado por su clave.
        
        Args:
            key: Clave del estado (normalmente thread_id o session_id)
            
        Returns:
            El estado guardado o None si no existe
        """
        # Primero intenta obtenerlo de la caché
        if key in self._cache:
            return self._cache[key]
        
        # Si no está en caché, intenta obtenerlo de Firestore
        doc_ref = self.db.collection(self.collection_name).document(key)
        doc = doc_ref.get()
        
        if not doc.exists:
            return None
        
        data = doc.to_dict()
        
        # Si hay campos serializados como binarios, deserializarlos
        if "pickled_data" in data:
            pickled_data = base64.b64decode(data["pickled_data"])
            state = pickle.loads(pickled_data)
        else:
            state = data
            
            # Restaurar claves numéricas en la estructura de datos
            if "diet" in state and "diet_serialized" in state:
                try:
                    state["diet"] = json.loads(state["diet_serialized"])
                    del state["diet_serialized"]
                except:
                    print("⚠️ Error al deserializar diet")
        
        # Actualiza la caché
        self._cache[key] = state
        return state
    
    def put(self, key: str, value: Dict) -> None:
        """
        Guarda un estado.
        
        Args:
            key: Clave del estado (normalmente thread_id o session_id)
            value: Estado a guardar
        """
        # Guarda en caché
        self._cache[key] = value
        
        # Crea una copia para no modificar el original
        firestore_value = copy.deepcopy(value)
        
        # Preprocesa los datos para que sean compatibles con Firestore
        # Firestore no acepta claves numéricas en mapas
        if "diet" in firestore_value and isinstance(firestore_value["diet"], dict):
            # Convierte y guarda la dieta como JSON
            try:
                firestore_value["diet_serialized"] = json.dumps(firestore_value["diet"])
                # Guarda una versión simplificada en el objeto diet para visualización
                diet_simple = {}
                for day, meals in firestore_value["diet"].items():
                    # Convierte los días a strings
                    day_str = f"día_{day}" if isinstance(day, int) else str(day)
                    diet_simple[day_str] = {}
                    for meal_name, items in meals.items():
                        # Guarda sólo los nombres de los alimentos
                        diet_simple[day_str][meal_name] = list(items.keys()) if isinstance(items, dict) else "Info no disponible"
                
                firestore_value["diet"] = diet_simple
            except Exception as e:
                print(f"⚠️ Error al serializar diet: {e}")
                # Si falla, guardamos un diccionario vacío
                firestore_value["diet"] = {}
                firestore_value["diet_serialized"] = "{}"
        
        # Guarda en Firestore
        doc_ref = self.db.collection(self.collection_name).document(key)
        
        try:
            # Intenta guardar directamente
            doc_ref.set(firestore_value)
        except TypeError as e:
            print(f"⚠️ Error al guardar en Firestore: {e}")
            print("Intentando serializar todo con pickle...")
            # Si hay objetos que no son JSON serializables, usa pickle
            pickled_data = pickle.dumps(value)
            encoded_data = base64.b64encode(pickled_data).decode('utf-8')
            doc_ref.set({"pickled_data": encoded_data})
    
    def delete(self, key: str) -> None:
        """
        Elimina un estado guardado.
        
        Args:
            key: Clave del estado a eliminar
        """
        # Elimina de la caché
        if key in self._cache:
            del self._cache[key]
        
        # Elimina de Firestore
        self.db.collection(self.collection_name).document(key).delete()
    
    def list_sessions(self):
        """
        Lista todas las sesiones existentes en la colección.
        
        Returns:
            Lista de IDs de sesiones
        """
        try:
            return [doc.id for doc in self.db.collection(self.collection_name).list_documents()]
        except Exception as e:
            print(f"Error al listar sesiones: {e}")
            return []

# Función para validar el estado antes de guardarlo
def validate_state(state):
    """
    Valida que el estado no contenga valores inválidos antes de guardarlo.
    Corrige problemas comunes como None en lugar de cadenas vacías.
    """
    if not isinstance(state, dict):
        print(f"⚠️ Estado no es un diccionario: {type(state)}")
        return False
    
    # Asegúrate de que messages sea una lista
    if "messages" in state and not isinstance(state["messages"], list):
        print(f"⚠️ 'messages' no es una lista: {type(state['messages'])}")
        return False
    
    # Verifica cada mensaje
    if "messages" in state:
        for i, msg in enumerate(state["messages"]):
            if not isinstance(msg, dict):
                print(f"⚠️ Mensaje {i} no es un diccionario: {type(msg)}")
                return False
            
            if "role" not in msg or "content" not in msg:
                print(f"⚠️ Mensaje {i} no tiene 'role' o 'content': {msg.keys()}")
                return False
            
            # Asegúrate de que content sea una cadena
            if not isinstance(msg["content"], str):
                print(f"⚠️ Content del mensaje {i} no es una cadena: {type(msg['content'])}")
                if msg["content"] is None:
                    print("   Corrigiendo: cambiando None a cadena vacía")
                    msg["content"] = ""
                else:
                    try:
                        msg["content"] = str(msg["content"])
                        print(f"   Corrigiendo: convertido a cadena: {msg['content']}")
                    except:
                        print("   No se pudo convertir a cadena")
                        return False
    
    # Verifica otros campos comunes
    for field in ["intolerances", "forbidden_foods", "grocery_list"]:
        if field in state and not isinstance(state[field], list):
            print(f"⚠️ Campo '{field}' no es una lista: {type(state[field])}")
            if state[field] is None:
                state[field] = []
                print(f"   Corrigiendo: cambiando None a lista vacía")
    
    # Verifica que budget sea un número o None
    if "budget" in state and state["budget"] is not None:
        if not isinstance(state["budget"], (int, float)):
            try:
                state["budget"] = float(state["budget"])
                print(f"   Corrigiendo: convertido budget a número: {state['budget']}")
            except:
                print(f"⚠️ 'budget' no es un número y no se puede convertir: {state['budget']}")
                state["budget"] = None
    
    # Verifica que info_dietas sea una cadena
    if "info_dietas" in state and not isinstance(state["info_dietas"], str):
        if state["info_dietas"] is None:
            state["info_dietas"] = ""
            print("   Corrigiendo: cambiando info_dietas None a cadena vacía")
        else:
            try:
                state["info_dietas"] = str(state["info_dietas"])
                print(f"   Corrigiendo: convertido info_dietas a cadena")
            except:
                print(f"⚠️ 'info_dietas' no es una cadena y no se puede convertir")
                state["info_dietas"] = ""
    
    # Verifica que diet sea un diccionario
    if "diet" in state and not isinstance(state["diet"], dict):
        print(f"⚠️ 'diet' no es un diccionario: {type(state['diet'])}")
        if state["diet"] is None:
            state["diet"] = {}
            print("   Corrigiendo: cambiando diet None a diccionario vacío")
    
    return True

# Definición del grafo según el diagrama
workflow = StateGraph(DietState)
workflow.add_node("input_usuario", router)
workflow.add_node("intolerancias", intolerance_search)
workflow.add_node("intolerancias_router", intolerancias_router)
workflow.add_node("mensaje_intolerancias", mensaje_intolerancias)
workflow.add_node("experto_dietas", buscar_info_dietas)
workflow.add_node("crear_dieta", crear_dieta)
workflow.add_node("hacer_lista_compra", generar_lista_compra_csv)
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
workflow.add_edge("intolerancias", "intolerancias_router")
workflow.add_conditional_edges(
    "intolerancias_router",
    lambda x: getattr(x, "next_after_intolerancias", "mensaje_intolerancias"),
    {
        "mensaje_intolerancias": "mensaje_intolerancias",
        "experto_dietas": "experto_dietas"
    }
)
workflow.add_edge("mensaje_intolerancias", END)
workflow.add_edge("experto_dietas", "crear_dieta")
workflow.add_edge("crear_dieta", "hacer_lista_compra")
workflow.add_edge("hacer_lista_compra", "poner_precio")
workflow.add_edge("poner_precio", END)
workflow.add_edge("otros", END)

# Usar InMemorySaver para LangGraph (mantiene la compatibilidad)
# y nuestro FirestoreSaver personalizado para persistencia
memory_saver = InMemorySaver()
firestore_saver = FirestoreSaver(
    collection_name="diet_conversations",
    project_id="diap3-458416",
    database_id="agente-context-prueba"
)

# Compila el grafo con el guardado en memoria que usa LangGraph
graph = workflow.compile(checkpointer=memory_saver)

def generate_session_id():
    """
    Genera un ID de sesión único basado en los IDs existentes.
    
    Returns:
        ID de sesión generado
    """
    try:
        # Obtener sesiones existentes
        existing_sessions = firestore_saver.list_sessions()
        
        # Extraer números de las sesiones existentes con formato "usuario_X"
        user_numbers = []
        for session in existing_sessions:
            try:
                if session.startswith("usuario_"):
                    num = int(session.split("_")[1])
                    user_numbers.append(num)
            except (ValueError, IndexError):
                continue
        
        # Generar siguiente ID secuencial
        next_number = max(user_numbers, default=0) + 1
        return f"usuario_{next_number}"
    except Exception as e:
        print(f"Error al generar ID de sesión: {e}")
        # Fallback a ID basado en timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"usuario_{timestamp}"

def list_active_sessions():
    """
    Lista las sesiones activas y permite al usuario seleccionar una.
    
    Returns:
        ID de la sesión seleccionada o None para crear una nueva
    """
    sessions = firestore_saver.list_sessions()
    if not sessions:
        print("No hay sesiones existentes.")
        return None
    
    print("\n📝 Sesiones existentes:")
    for i, session_id in enumerate(sessions, 1):
        print(f"  {i}. {session_id}")
    
    print("  0. Crear nueva sesión")
    
    while True:
        try:
            choice = input("\nSelecciona una sesión (número) o 0 para crear nueva: ")
            if choice == "0":
                return None
            
            idx = int(choice) - 1
            if 0 <= idx < len(sessions):
                return sessions[idx]
            
            print("❌ Selección inválida, intenta de nuevo.")
        except ValueError:
            print("❌ Por favor, ingresa un número.")

if __name__ == "__main__":
    print("🍽️ Asistente de Dietas 🍽️")
    print("===========================")
    
    # Ofrecer seleccionar sesión existente o crear nueva
    print("¿Deseas continuar una conversación existente o iniciar una nueva?")
    choice = input("1. Continuar existente\n2. Iniciar nueva\nSelección: ")
    
    if choice == "1":
        selected_session = list_active_sessions()
        if selected_session:
            session_id = selected_session
            print(f"Continuando sesión: {session_id}")
        else:
            session_id = generate_session_id()
            print(f"Creando nueva sesión: {session_id}")
    else:
        session_id = generate_session_id()
        print(f"Creando nueva sesión: {session_id}")
    
    print("\nBienvenido al asistente de dietas. Escribe 'salir' para terminar.")
    
    # Intentar recuperar el estado de una conversación existente de Firestore
    state = firestore_saver.get(session_id)
    
    # Si no hay estado previo, crear uno nuevo
    if state is None:
        state = {
            "messages": [],
            "intolerances": [],
            "forbidden_foods": [],
            "diet": {},
            "budget": None,
            "info_dietas": "",
            "grocery_list": []
        }
    
    # Añadir metadatos de la sesión si es nueva
    if "metadata" not in state:
        state["metadata"] = {
            "created_at": datetime.datetime.now().isoformat(),
            "last_active": datetime.datetime.now().isoformat(),
            "session_id": session_id
        }
    else:
        # Actualizar timestamp de última actividad
        state["metadata"]["last_active"] = datetime.datetime.now().isoformat()
    
    while True:
        user_input = input("\nTú: ")
        if user_input.lower() in ["salir", "exit"]:
            print("Asistente: ¡Hasta pronto!")
            # Actualizar timestamp de última actividad
            if "metadata" in state:
                state["metadata"]["last_active"] = datetime.datetime.now().isoformat()
            # Guardar estado final explícitamente
            if validate_state(state):
                firestore_saver.put(session_id, state)
            break
            
        # Añade el mensaje del usuario al historial
        state["messages"].append({"role": "user", "content": user_input})
        prev_len = len(state["messages"])
        
        try:
            result = graph.invoke(
                state,
                config={"configurable": {"thread_id": session_id}},
            )
            state = result  # Mantén el estado actualizado
            
            # Actualizar timestamp de última actividad
            if "metadata" in state:
                state["metadata"]["last_active"] = datetime.datetime.now().isoformat()
            
            # Imprime SOLO los mensajes nuevos del asistente generados en este turno
            new_msgs = state["messages"][prev_len:]
            assistant_msgs = [m for m in new_msgs if m.get("role") == "assistant"]
            if assistant_msgs:
                print(f"Asistente: {assistant_msgs[-1]['content']}")
            else:
                print("Asistente: (No hay respuesta del asistente en este turno)")
            
            # Validar y guardar explícitamente en Firestore después de cada interacción
            if validate_state(state):
                firestore_saver.put(session_id, state)
            
        except Exception as e:
            print(f" Hubo un problema ejecutando el asistente: {str(e)}")
            print("Detalles del error:")
            traceback.print_exc()
            
            # Intenta guardar el estado actual, incluso si hubo un error
            if "metadata" in state:
                state["metadata"]["last_active"] = datetime.datetime.now().isoformat()
                state["metadata"]["last_error"] = str(e)
            
            if validate_state(state):
                print("Guardando el estado actual a pesar del error...")
                try:
                    firestore_saver.put(session_id, state)
                except Exception as save_error:
                    print(f"Error al guardar el estado: {save_error}")
                    # Último recurso: serializar todo con pickle
                    try:
                        print("Intentando serializar todo con pickle...")
                        pickled_data = pickle.dumps(state)
                        encoded_data = base64.b64encode(pickled_data).decode('utf-8')
                        doc_ref = firestore_saver.db.collection(firestore_saver.collection_name).document(session_id)
                        doc_ref.set({"pickled_data": encoded_data})
                        print("Estado guardado con pickle")
                    except Exception as pickle_error:
                        print(f"Error al serializar con pickle: {pickle_error}")
            continue