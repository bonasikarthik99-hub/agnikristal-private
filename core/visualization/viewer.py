import py3Dmol
from rdkit import Chem
from rdkit.Chem import AllChem
import webbrowser
import tempfile


def open_view(view):
    html = view._make_html()

    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".html")
    temp.write(html.encode("utf-8"))
    temp.close()

    webbrowser.open(temp.name)


def show_molecule(smiles):

    mol = Chem.MolFromSmiles(smiles)
    mol = Chem.AddHs(mol)

    AllChem.EmbedMolecule(mol)
    AllChem.UFFOptimizeMolecule(mol)

    block = Chem.MolToMolBlock(mol)

    view = py3Dmol.view(width=800, height=500)
    view.addModel(block, "mol")

    view.setStyle({"stick": {}})
    view.addPropertyLabels("atom", "")

    view.zoomTo()

    open_view(view)


def show_pair(api_smiles, coformer_smiles):

    api = Chem.MolFromSmiles(api_smiles)
    coformer = Chem.MolFromSmiles(coformer_smiles)

    api = Chem.AddHs(api)
    coformer = Chem.AddHs(coformer)

    AllChem.EmbedMolecule(api)
    AllChem.EmbedMolecule(coformer)

    AllChem.UFFOptimizeMolecule(api)
    AllChem.UFFOptimizeMolecule(coformer)

    api_block = Chem.MolToMolBlock(api)
    cof_block = Chem.MolToMolBlock(coformer)

    view = py3Dmol.view(width=900, height=600)

    view.addModel(api_block, "mol")
    view.setStyle({'model': 0}, {'stick': {'color': 'blue'}})

    view.addModel(cof_block, "mol")
    view.setStyle({'model': 1}, {'stick': {'color': 'green'}})

    view.addPropertyLabels("atom", "")

    view.zoomTo()

    open_view(view)