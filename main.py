from core.validation import optimize_threshold


if __name__ == "__main__":

    dataset = [
        ("CNC(=O)Nc1ccc(Cl)cc1", "NC(=O)c1cccnc1", 1),
        ("CNC(=O)Nc1ccc(Cl)cc1", "C1=CC=NC=C1", 1),
        ("CNC(=O)Nc1ccc(Cl)cc1", "NC(=O)N", 0),
        ("CNC(=O)Nc1ccc(Cl)cc1", "Oc1ccccc1", 0),
        ("CNC(=O)Nc1ccc(Cl)cc1", "OC(=O)c1ccccc1", 0)
    ]

    results = optimize_threshold(dataset)

    print("\n=== Threshold Optimization Results ===\n")

    for r in results:
        print(r)