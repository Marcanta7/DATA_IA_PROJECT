# prepare_embeddings.py

import spacy

nlp = spacy.load("es_core_news_sm")

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