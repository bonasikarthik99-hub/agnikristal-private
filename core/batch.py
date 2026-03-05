import csv
from core.descriptors import calculate_descriptors
from core.delta_pka import delta_pka_score
from core.hbond import hbond_score
from core.synthon import synthon_detection
from core.scoring import final_prediction
def batch_screen(api_smiles, coformer_list, pka_base=5.2, pka_acid=3.0):

    results = []

    # Calculate API descriptors once
    api_desc = calculate_descriptors(api_smiles)

    for coformer_name, coformer_smiles in coformer_list:

        try:
            coformer_desc = calculate_descriptors(coformer_smiles)

            # ΔpKa
            pka_result = delta_pka_score(pka_base=pka_base, pka_acid=pka_acid)

            # Hydrogen Bond
            hbond_result = hbond_score(api_desc, coformer_desc)

            # Synthon
            synthon_result = synthon_detection(api_smiles, coformer_smiles)

            # Final scientific prediction
            final_result = final_prediction(
                pka_result,
                hbond_result,
                synthon_result,
                api_desc,
                coformer_desc
            )

            results.append({
                "Coformer": coformer_name,
                "Final Score": final_result["final_score"],
                "Prediction": final_result["prediction"]
            })

        except Exception as e:
            results.append({
                "Coformer": coformer_name,
                "Final Score": 0,
                "Prediction": f"Error: {str(e)}"
            })

    # Sort by score descending
        results.sort(key=lambda x: x["Final Score"], reverse=True)

    # Export to CSV
    import csv
    with open("batch_results.csv", mode="w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["Coformer", "Final Score", "Prediction"])
        writer.writeheader()
        writer.writerows(results)

    return results