from rdkit import Chem
from rdkit.Chem import Descriptors, Lipinski, Crippen

def calculate_descriptors(smiles: str):
    mol = Chem.MolFromSmiles(smiles)

    if mol is None:
        raise ValueError("Invalid SMILES string")

    descriptors = {
        "MolecularWeight": Descriptors.MolWt(mol),
        "HBD": Lipinski.NumHDonors(mol),
        "HBA": Lipinski.NumHAcceptors(mol),
        "TPSA": Descriptors.TPSA(mol),
        "LogP": Crippen.MolLogP(mol),
        "RotatableBonds": Lipinski.NumRotatableBonds(mol),
        "RingCount": Lipinski.RingCount(mol)
    }

    return descriptors