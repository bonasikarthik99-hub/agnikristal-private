import math

def ideal_pka_score(delta_pka):
    # Bell-shaped scoring centered at 2.0
    optimal = 2.0
    width = 1.5
    score = math.exp(-((delta_pka - optimal) ** 2) / (2 * width ** 2))
    return min(score, 1.0)

def flexibility_penalty(api_desc, coformer_desc):
    total_rot = api_desc["RotatableBonds"] + coformer_desc["RotatableBonds"]
    if total_rot > 8:
        return 0.2
    elif total_rot > 4:
        return 0.1
    return 0.0

def logp_compatibility(api_desc, coformer_desc):
    diff = abs(api_desc["LogP"] - coformer_desc["LogP"])
    if diff < 1:
        return 1.0
    elif diff < 2:
        return 0.7
    else:
        return 0.4

def final_prediction(pka_result, hbond_result, synthon_result, api_desc, coformer_desc):

    # 1️⃣ ΔpKa scientific score
    pka_component = ideal_pka_score(pka_result["delta_pKa"])

    # 2️⃣ Hydrogen bonding
    hbond_component = hbond_result["normalized_score"]

    # 3️⃣ Synthon structural boost
    synthon_component = 1.0 if synthon_result["synthon_detected"] else 0.0

    # 4️⃣ LogP compatibility
    lipophilicity_component = logp_compatibility(api_desc, coformer_desc)

    # Base score
    base_score = (
        0.35 * pka_component +
        0.25 * hbond_component +
        0.25 * synthon_component +
        0.15 * lipophilicity_component
    )

    # 5️⃣ Flexibility penalty
    penalty = flexibility_penalty(api_desc, coformer_desc)

    final_score = max(base_score - penalty, 0)

    if final_score >= 0.7:
        prediction = "High Probability Co-crystal"
    elif final_score >= 0.5:
        prediction = "Moderate Probability"
    else:
        prediction = "Low Probability"

    return {
        "final_score": round(final_score, 3),
        "prediction": prediction,
        "components": {
            "pka_score": round(pka_component, 3),
            "hbond_score": round(hbond_component, 3),
            "synthon_score": synthon_component,
            "logp_match": round(lipophilicity_component, 3),
            "flexibility_penalty": penalty
        }
    }