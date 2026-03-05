from openbabel import pybel

smiles = "CCO"

mol = pybel.readstring("smi", smiles)

print("Formula:", mol.formula)
print("Molecular Weight:", mol.molwt)