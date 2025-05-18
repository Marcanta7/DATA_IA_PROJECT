# prepare_embeddings.py

import spacy

nlp = spacy.load("es_core_news_sm")

def append_message(state, message, max_messages=10):
    """
    Añade un mensaje al historial solo si no es duplicado consecutivo y limita el historial a los últimos max_messages. Marca cada mensaje assistant con turn_id.
    """
    # Inicializa turn_id si no existe
    if not hasattr(state, 'turn_id'):
        state.turn_id = 0
    # Marca los mensajes del assistant con el turn_id actual
    if message.get('role') == 'assistant':
        message = dict(message)
        message['turn_id'] = state.turn_id
    if not (state.messages and state.messages[-1].get("role") == message["role"] and state.messages[-1].get("content") == message["content"]):
        state.messages.append(message)
        if len(state.messages) > max_messages:
            state.messages = state.messages[-max_messages:]
        if message.get('role') == 'assistant':
            assistant_msgs = [m for m in state.messages if m.get('role') == 'assistant']
            if len(assistant_msgs) > 2:
                keep = set(id(m) for m in assistant_msgs[-2:])
                state.messages = [m for m in state.messages if m.get('role') != 'assistant' or id(m) in keep]


def identify_removed_intolerances(user_prompt: str, current_intolerances: list) -> list:
    """
    Identifica las intolerancias que el usuario menciona que ya no tiene.
    """
    removed = []
    doc = nlp(user_prompt.lower())
    negations = set([token.head.text for token in doc if token.dep_ == 'neg'])

    for intolerance in current_intolerances:
        intolerance_doc = nlp(intolerance.lower())
        for neg in negations:
            # Buscar si la intolerancia aparece después de una negación
            for token in intolerance_doc:
                if token.text in doc.text and token.i > [t.i for t in doc if t.text == neg][0]:
                    removed.append(intolerance)
                    break # Si se encuentra una negación, pasar a la siguiente intolerancia
            if removed and intolerance in removed:
                break # Evitar añadir la misma intolerancia varias veces

        # Buscar frases explícitas como "ya no soy intolerante a la ..."
        if f"no soy intolerante a {intolerance.lower()}" in doc.text:
            if intolerance not in removed:
                removed.append(intolerance)

    return list(set(removed))