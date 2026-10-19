"""
3D structure, exact-product verification and viewers for dapagliflozin.

Open-source stack used here
---------------------------
* RDKit      - SMILES parsing, stereochemistry (CIP), ETKDG conformer
               generation, MMFF94s force-field optimization, InChI
* 3Dmol.js   - interactive WebGL viewer, embedded in a standalone HTML page
               (loaded from the 3Dmol.org CDN; needs internet when opened)
* matplotlib - static ball-and-stick PNG for reports
* tblite/ASE - OPTIONAL GFN2-xTB geometry refinement, used only if installed

Dependencies: rdkit, matplotlib (numpy). tblite and ase are optional.
"""

import json

import numpy as np
from rdkit import Chem
from rdkit.Chem import AllChem, Descriptors, rdMolDescriptors

# Dapagliflozin (free compound), isomeric SMILES taken from the stereo record
# of dapagliflozin propanediol monohydrate (the marketed form).
# Expected: C21H25ClO6, MW ~408.87, IUPAC (2S,3R,4R,5S,6R).
DAPAGLIFLOZIN_SMILES = (
    "C1=CC(OCC)=CC=C1CC1=CC([C@H]2[C@@H]([C@@H](O)[C@H](O)[C@@H](CO)O2)O)=CC=C1Cl"
)
DAPAGLIFLOZIN_FORMULA = "C21H25ClO6"

# Aryl-bearing, ring-oxygen-bearing sp3 CH: the C-glycoside anomeric carbon.
_ANOMERIC_SMARTS = Chem.MolFromSmarts("[CX4;H1;R]([c])([O;R])[C;R]")

_CPK = {
    "H": "#e8e8e8", "C": "#4a4a4a", "O": "#e03a3a", "N": "#3a5fe0",
    "Cl": "#2ca02c", "S": "#d4b21a", "P": "#e08a1e", "F": "#7fbf3f",
    "Br": "#a0522d",
}
_RADIUS = {"H": 0.25, "C": 0.45, "O": 0.42, "N": 0.42, "Cl": 0.60, "S": 0.55}


# ---------------------------------------------------------------------------
# Identity and exact-product verification
# ---------------------------------------------------------------------------

def _mol(smiles):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Invalid SMILES: {smiles!r}")
    return mol


def inchikey(smiles):
    return Chem.MolToInchiKey(_mol(smiles))


def cip_labels(mol):
    """Return {atom_index: 'R'|'S'} using RDKit's CIP labeler when available."""
    try:
        from rdkit.Chem import rdCIPLabeler
        rdCIPLabeler.AssignCIPLabels(mol)
        return {
            a.GetIdx(): a.GetProp("_CIPCode")
            for a in mol.GetAtoms() if a.HasProp("_CIPCode")
        }
    except Exception:
        return {i: c for i, c in Chem.FindMolChiralCenters(mol, useLegacyImplementation=False)}


def _invert_atoms(mol, atom_ids):
    out = Chem.RWMol(mol)
    for i in atom_ids:
        out.GetAtomWithIdx(i).InvertChirality()
    result = out.GetMol()
    Chem.SanitizeMol(result)
    return result


def anomer_partner(smiles):
    """SMILES with only the anomeric carbon inverted (the alpha/beta partner)."""
    mol = _mol(smiles)
    hits = mol.GetSubstructMatches(_ANOMERIC_SMARTS)
    if not hits:
        raise ValueError("No C-aryl glycoside anomeric carbon found")
    return Chem.MolToSmiles(_invert_atoms(mol, [hits[0][0]]))


def verify_product(smiles, reference_smiles=None):
    """
    Classify a structure against a target drug (dapagliflozin by default;
    pass reference_smiles to check any other drug).

    Returns a dict with 'verdict', one of:
      exact_product, alpha_anomer (C-aryl glycosides only), enantiomer,
      other_stereoisomer, different_compound
    plus formula, molecular weight and InChIKeys for the record.
    """
    ref_smiles = reference_smiles or DAPAGLIFLOZIN_SMILES
    ref = _mol(ref_smiles)
    cand = _mol(smiles)

    ref_key = Chem.MolToInchiKey(ref)
    cand_key = Chem.MolToInchiKey(cand)
    formula = rdMolDescriptors.CalcMolFormula(cand)
    ref_formula = rdMolDescriptors.CalcMolFormula(ref)

    if cand_key == ref_key:
        verdict = "exact_product"
    elif cand_key.split("-")[0] != ref_key.split("-")[0]:
        verdict = "different_compound"
    else:
        # Same connectivity, different stereochemistry: say which kind.
        enant = Chem.MolFromSmiles(ref_smiles.replace("@@", "!").replace("@", "@@").replace("!", "@"))
        try:
            alpha = Chem.MolFromSmiles(anomer_partner(ref_smiles))
            alpha_key = Chem.MolToInchiKey(alpha)
        except ValueError:
            alpha_key = None  # reference is not a C-aryl glycoside
        if alpha_key is not None and cand_key == alpha_key:
            verdict = "alpha_anomer"
        elif cand_key == Chem.MolToInchiKey(enant):
            verdict = "enantiomer"
        else:
            verdict = "other_stereoisomer"

    return {
        "verdict": verdict,
        "is_exact_product": verdict == "exact_product",
        "formula": formula,
        "formula_matches": formula == ref_formula,
        "molecular_weight": round(Descriptors.MolWt(cand), 2),
        "inchikey": cand_key,
        "reference_inchikey": ref_key,
        "stereocenters": len(Chem.FindMolChiralCenters(cand, includeUnassigned=True, useLegacyImplementation=False)),
    }


# ---------------------------------------------------------------------------
# 3D structure
# ---------------------------------------------------------------------------

def build_3d(smiles, n_confs=60, seed=42):
    """
    Generate a low-energy 3D structure.

    ETKDGv3 conformer search followed by MMFF94s optimization (UFF if MMFF
    parameters are missing). Returns (mol_with_Hs, conf_id, energy_kcal_mol).
    """
    mol = Chem.AddHs(_mol(smiles))

    params = AllChem.ETKDGv3()
    params.randomSeed = seed
    params.pruneRmsThresh = 0.3
    conf_ids = list(AllChem.EmbedMultipleConfs(mol, numConfs=n_confs, params=params))
    if not conf_ids:
        raise RuntimeError("3D embedding failed for " + smiles)

    if AllChem.MMFFHasAllMoleculeParams(mol):
        results = AllChem.MMFFOptimizeMoleculeConfs(
            mol, maxIters=5000, mmffVariant="MMFF94s"
        )
    else:
        results = AllChem.UFFOptimizeMoleculeConfs(mol, maxIters=5000)

    energies = [e for (_, e) in results]
    best = int(np.argmin(energies))
    return mol, conf_ids[best], float(energies[best])


def xtb_refine(mol, conf_id, fmax=0.05, steps=200):
    """
    OPTIONAL: refine one conformer with GFN2-xTB through tblite + ASE.
    Returns True when the coordinates were updated, False when tblite/ASE
    is not installed or the calculation failed.
    """
    try:
        from ase import Atoms
        from ase.optimize import LBFGS
        from tblite.ase import TBLite
    except ImportError:
        return False

    conf = mol.GetConformer(conf_id)
    symbols = [a.GetSymbol() for a in mol.GetAtoms()]
    positions = conf.GetPositions()
    atoms = Atoms(symbols=symbols, positions=positions)
    atoms.calc = TBLite(method="GFN2-xTB", verbosity=0)
    try:
        LBFGS(atoms, logfile=None).run(fmax=fmax, steps=steps)
    except Exception:
        return False
    for i, (x, y, z) in enumerate(atoms.get_positions()):
        conf.SetAtomPosition(i, (float(x), float(y), float(z)))
    return True


def _label_points(mol, conf_id):
    conf = mol.GetConformer(conf_id)
    points = []
    for idx, code in cip_labels(mol).items():
        p = conf.GetAtomPosition(idx)
        points.append({"x": p.x, "y": p.y, "z": p.z, "text": code})
    return points


# ---------------------------------------------------------------------------
# Interactive 3D viewer (standalone HTML)
# ---------------------------------------------------------------------------

_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>__TITLE__</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://3Dmol.org/build/3Dmol-min.js"></script>
<style>
 body{font-family:Arial,sans-serif;margin:0;background:#f5f6fa;color:#222}
 h2{margin:12px 16px 4px}
 .info{margin:0 16px 8px;font-size:13px;color:#555}
 .grid{display:grid;grid-template-columns:repeat(__COLS__,1fr);gap:12px;padding:0 16px 16px}
 .card{background:#fff;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.12);padding:8px}
 .card h3{margin:4px 8px;font-size:15px}
 .viewer{width:100%;height:520px;position:relative}
 .bar{padding:6px 8px}
 button{background:#1f4aa8;color:#fff;border:0;border-radius:4px;padding:6px 10px;margin:2px;cursor:pointer;font-size:13px}
 button:hover{background:#16397f}
</style></head><body>
<h2>__TITLE__</h2>
<div class="info">Drag to rotate, scroll to zoom. Labels R/S are CIP descriptors at the stereocenters.</div>
<div class="bar">
 <button onclick="setStyle('ballstick')">Ball &amp; stick</button>
 <button onclick="setStyle('stick')">Stick</button>
 <button onclick="setStyle('sphere')">Space-filling</button>
 <button onclick="toggleLabels()">Toggle R/S labels</button>
 <button onclick="toggleSurface()">Toggle surface</button>
 <button onclick="toggleSpin()">Spin</button>
</div>
<div class="grid" id="grid"></div>
<script>
const MODELS = __MODELS__;
const viewers = [];
let labelsOn = true, surfaceOn = false, spinOn = false;

MODELS.forEach((m, i) => {
  const card = document.createElement('div'); card.className = 'card';
  card.innerHTML = '<h3>' + m.title + '</h3><div class="viewer" id="v' + i + '"></div>';
  document.getElementById('grid').appendChild(card);
  const v = $3Dmol.createViewer(document.getElementById('v' + i), {backgroundColor: 'white'});
  v.addModel(m.molblock, 'sdf');
  viewers.push({v: v, m: m, surf: null});
});

function applyStyle(style) {
  viewers.forEach(o => {
    o.v.setStyle({}, {});
    if (style === 'stick') o.v.setStyle({}, {stick: {radius: 0.15, colorscheme: 'Jmol'}});
    else if (style === 'sphere') o.v.setStyle({}, {sphere: {colorscheme: 'Jmol'}});
    else o.v.setStyle({}, {stick: {radius: 0.12, colorscheme: 'Jmol'}, sphere: {scale: 0.28, colorscheme: 'Jmol'}});
    o.v.render();
  });
}
function drawLabels() {
  viewers.forEach(o => {
    o.v.removeAllLabels();
    if (labelsOn) o.m.labels.forEach(l => o.v.addLabel(l.text, {
      position: {x: l.x, y: l.y, z: l.z}, backgroundColor: '#1f4aa8',
      fontColor: 'white', fontSize: 14, backgroundOpacity: 0.85, inFront: true}));
    o.v.render();
  });
}
function setStyle(s) { applyStyle(s); }
function toggleLabels() { labelsOn = !labelsOn; drawLabels(); }
function toggleSurface() {
  surfaceOn = !surfaceOn;
  viewers.forEach(o => {
    if (surfaceOn) { o.surf = o.v.addSurface($3Dmol.SurfaceType.VDW, {opacity: 0.55, color: '#9ec1ff'}); }
    else { o.v.removeAllSurfaces(); }
    o.v.render();
  });
}
function toggleSpin() { spinOn = !spinOn; viewers.forEach(o => o.v.spin(spinOn)); }

applyStyle('ballstick'); drawLabels();
viewers.forEach(o => { o.v.zoomTo(); o.v.render(); });
</script></body></html>
"""


def viewer_html(entries, title="AgniKristal 3D Viewer", n_confs=60):
    """
    Build a standalone interactive 3D page.

    entries -- list of (label, smiles); more than one gives side-by-side
               viewers (for example exact product vs alpha-anomer).
    """
    models = []
    info = []
    for label, smiles in entries:
        mol, conf_id, energy = build_3d(smiles, n_confs=n_confs)
        xtb_refine(mol, conf_id)  # no-op unless tblite and ASE are installed
        block = Chem.MolToMolBlock(mol, confId=conf_id)
        models.append({
            "title": f"{label}  (MMFF94s {energy:.1f} kcal/mol)",
            "molblock": block,
            "labels": _label_points(mol, conf_id),
        })
        info.append(label)

    html = _HTML_TEMPLATE
    html = html.replace("__TITLE__", title)
    html = html.replace("__COLS__", str(min(len(models), 2)))
    html = html.replace("__MODELS__", json.dumps(models))
    return html


def export_3d_html(path, smiles=DAPAGLIFLOZIN_SMILES, label="Dapagliflozin"):
    html = viewer_html([(label, smiles)], title=f"{label} - 3D structure")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path


def export_anomer_comparison_html(path, smiles=DAPAGLIFLOZIN_SMILES):
    """Side-by-side exact product (beta) and its alpha-anomer partner."""
    alpha = anomer_partner(smiles)
    html = viewer_html(
        [("Dapagliflozin (exact product, beta-C-glycoside)", smiles),
         ("Alpha-anomer (process impurity)", alpha)],
        title="Dapagliflozin vs alpha-anomer impurity",
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return path


# ---------------------------------------------------------------------------
# Static 3D image (for reports)
# ---------------------------------------------------------------------------

def export_3d_png(path, smiles=DAPAGLIFLOZIN_SMILES, elev=22, azim=35, dpi=200,
                  show_hydrogens=True):
    """Ball-and-stick PNG rendered from the same optimized 3D coordinates."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    mol, conf_id, energy = build_3d(smiles)
    conf = mol.GetConformer(conf_id)
    pos = conf.GetPositions()
    pos = pos - pos.mean(axis=0)

    keep = [a.GetIdx() for a in mol.GetAtoms()
            if show_hydrogens or a.GetSymbol() != "H"]
    keep_set = set(keep)

    fig = plt.figure(figsize=(8, 7))
    ax = fig.add_subplot(111, projection="3d")

    for b in mol.GetBonds():
        i, j = b.GetBeginAtomIdx(), b.GetEndAtomIdx()
        if i in keep_set and j in keep_set:
            ax.plot([pos[i, 0], pos[j, 0]], [pos[i, 1], pos[j, 1]],
                    [pos[i, 2], pos[j, 2]], color="#8a8a8a", linewidth=2.0,
                    solid_capstyle="round", zorder=1)

    # Painter's order: far atoms first so near atoms draw over them.
    az = np.radians(azim)
    el = np.radians(elev)
    view = np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])
    order = sorted(keep, key=lambda i: float(pos[i] @ view))

    for i in order:
        sym = mol.GetAtomWithIdx(i).GetSymbol()
        ax.scatter(pos[i, 0], pos[i, 1], pos[i, 2],
                   s=(_RADIUS.get(sym, 0.5) * 260) ** 1.0,
                   color=_CPK.get(sym, "#c06aff"), edgecolors="#222222",
                   linewidths=0.4, depthshade=True, zorder=2)

    for idx, code in cip_labels(mol).items():
        ax.text(pos[idx, 0], pos[idx, 1], pos[idx, 2] + 0.45, code,
                color="#1f4aa8", fontsize=10, fontweight="bold", ha="center")

    span = float(np.abs(pos[keep]).max()) * 1.05
    ax.set_xlim(-span, span)
    ax.set_ylim(-span, span)
    ax.set_zlim(-span, span)
    ax.view_init(elev=elev, azim=azim)
    ax.set_axis_off()
    ax.set_title(f"3D structure  |  MMFF94s {energy:.1f} kcal/mol  |  "
                 + rdMolDescriptors.CalcMolFormula(Chem.RemoveHs(mol)),
                 fontsize=11)
    fig.savefig(path, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path
