def output(state: DietState) -> DietState:
    """Imprime la información relevante encontrada."""
    info = getattr(state, 'info_dietas')
    if info:
        print(f"\nInformación relevante encontrada:\n{info}")
    return state