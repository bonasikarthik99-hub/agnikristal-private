def hbond_score(api_desc: dict, coformer_desc: dict):
    api_hbd = api_desc["HBD"]
    api_hba = api_desc["HBA"]

    cof_hbd = coformer_desc["HBD"]
    cof_hba = coformer_desc["HBA"]

    # Donor → Acceptor matching
    forward_pairs = min(api_hbd, cof_hba)
    reverse_pairs = min(api_hba, cof_hbd)

    total_pairs = forward_pairs + reverse_pairs

    # Maximum theoretical pairs
    max_possible = (
        max(api_hbd, cof_hba) +
        max(api_hba, cof_hbd)
    )

    if max_possible == 0:
        normalized = 0
    else:
        normalized = total_pairs / max_possible

    return {
        "forward_pairs": forward_pairs,
        "reverse_pairs": reverse_pairs,
        "total_pairs": total_pairs,
        "normalized_score": round(normalized, 3)
    }