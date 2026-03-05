def delta_pka_score(pka_base: float, pka_acid: float):
    """
    Calculates ΔpKa and gives preliminary salt/co-crystal prediction.
    """

    delta = pka_base - pka_acid

    if delta > 3:
        classification = "Salt Likely"
        probability = 0.85
    elif 0 <= delta <= 3:
        classification = "Co-crystal Possible"
        probability = 0.60
    else:
        classification = "Neutral Co-crystal Likely"
        probability = 0.75

    return {
        "delta_pKa": delta,
        "classification": classification,
        "confidence": probability
    }