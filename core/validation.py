from core.descriptors import calculate_descriptors
from core.delta_pka import delta_pka_score
from core.hbond import hbond_score
from core.synthon import synthon_detection
from core.scoring import final_prediction


def evaluate_pair(api_smiles, coformer_smiles):

    api_desc = calculate_descriptors(api_smiles)
    coformer_desc = calculate_descriptors(coformer_smiles)

    pka_result = delta_pka_score(pka_base=5.2, pka_acid=3.0)
    hbond_result = hbond_score(api_desc, coformer_desc)
    synthon_result = synthon_detection(api_smiles, coformer_smiles)

    final_result = final_prediction(
        pka_result,
        hbond_result,
        synthon_result,
        api_desc,
        coformer_desc
    )

    return final_result["final_score"]


def compute_metrics(dataset, threshold):

    TP = TN = FP = FN = 0

    for api_smiles, coformer_smiles, true_label in dataset:

        score = evaluate_pair(api_smiles, coformer_smiles)
        predicted = 1 if score >= threshold else 0

        if predicted == 1 and true_label == 1:
            TP += 1
        elif predicted == 0 and true_label == 0:
            TN += 1
        elif predicted == 1 and true_label == 0:
            FP += 1
        elif predicted == 0 and true_label == 1:
            FN += 1

    total = TP + TN + FP + FN

    accuracy = (TP + TN) / total if total else 0
    precision = TP / (TP + FP) if (TP + FP) else 0
    recall = TP / (TP + FN) if (TP + FN) else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0

    return {
        "Threshold": threshold,
        "Accuracy": round(accuracy, 3),
        "Precision": round(precision, 3),
        "Recall": round(recall, 3),
        "F1 Score": round(f1, 3)
    }


def optimize_threshold(dataset):

    thresholds = [0.5, 0.6, 0.65, 0.7, 0.75, 0.8]

    results = []

    for t in thresholds:
        metrics = compute_metrics(dataset, t)
        results.append(metrics)

    return results