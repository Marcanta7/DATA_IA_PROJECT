def output(state: DietState) -> DietState:
    """Imprime la información relevante encontrada."""
    info = state.get("info_dietas", None)
    if info:
        print(f"\nInformación relevante encontrada:\n{info}")
    return state