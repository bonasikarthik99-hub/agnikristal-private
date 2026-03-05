from rdkit import Chem

def synthon_detection(api_smiles: str, coformer_smiles: str):
    api = Chem.MolFromSmiles(api_smiles)
    cof = Chem.MolFromSmiles(coformer_smiles)

    # Define SMARTS patterns
    amide_pattern = Chem.MolFromSmarts("C(=O)N")
    pyridine_pattern = Chem.MolFromSmarts("n1ccccc1")

    api_has_amide = api.HasSubstructMatch(amide_pattern)
    cof_has_pyridine = cof.HasSubstructMatch(pyridine_pattern)

    synthon_found = False
    synthon_type = None

    if api_has_amide and cof_has_pyridine:
        synthon_found = True
        synthon_type = "Amide–Pyridine (R2^2(8) candidate)"

    return {
        "amide_present_API": api_has_amide,
        "pyridine_present_Coformer": cof_has_pyridine,
        "synthon_detected": synthon_found,
        "synthon_type": synthon_type
    }