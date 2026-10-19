# agnikristal-private
Private R&D project for AI-assisted cocrystal screening.

## Setup

```
pip install rdkit matplotlib pandas numpy streamlit openpyxl
```

- Desktop app: `python gui.py`
- Web app: `streamlit run agnikristal_full.py`
- Tests (no RDKit needed): `python tests/test_experimental_data.py` and `python tests/test_substitutions.py`

## Process-route tools

### 1. Company experimental data analysis (`core/experimental_data.py`)
Load step-level results from any company (CSV or Excel). The tool ranks routes
on yield, cost, safety and the probability of getting the exact product, and
assembles a "best of all companies" route. That combined route is a
projection: the exact combination has not been run, so confirm that
intermediates and solvents carry over.

The probability of the exact product comes from replicate counts per step
(`n_runs`, `n_runs_in_spec`) with a 90% interval. Without replicate counts the
probability is shown as n/a, not guessed. Edit `DEFAULT_SPEC` in the module
for your own purity and impurity limits.

CSV columns (see `data/experimental_template.csv`; its rows are fictional DEMO
data, not real results):

| Column | Required | Meaning |
|---|---|---|
| company, route_id, step_no, step_name, yield_pct | yes | Who, which route, step order, step type, step yield (0-100) |
| reagents, solvent, temp_c, time_h | no | Conditions; feeds the substitution screen |
| purity_pct, alpha_anomer_pct | no | Checked against the spec |
| n_runs, n_runs_in_spec | no | Replicates; needed for probability |
| scale_kg, step_cost_usd_per_kg | no | Route cost per kg of final product |
| hazards | no | Comma-separated: pyrophoric, cryogenic, corrosive, chlorinated_solvent, toxic, high_pressure |
| source, is_demo | no | Provenance; `true` marks fictional rows |

End each route with a `purification` or `final_crystallization` step so routes
compare fairly. Duplicate (company, route_id, step_no) rows, yields outside
0-100 and `n_runs_in_spec` above `n_runs` are rejected with a message naming
the row.

### 2. Alternative reagents, solvents and steps for any drug (`core/substitutions.py`)
A knowledge base of 32 entries (hazardous or costly solvents, reagents and
process steps) with safer/cheaper alternatives, a cost direction, a maturity
rating and what to re-check after swapping. It screens an uploaded route and
also answers free-text lookups. To add an entry, append to `KNOWLEDGE_BASE`.

The entries are literature-level guidance, not validated procedures. A swap
can change selectivity and the impurity profile, so confirm each one
experimentally for your drug. The tool does not discover new routes; a
retrosynthesis engine (for example AiZynthFinder or ASKCOS) would be needed
for that.

`core/process_alternatives.py` holds a dapagliflozin-specific case study.

### 3. 3D structure and exact-product check (`core/molecule3d.py`)
Builds a low-energy 3D structure (RDKit ETKDG + MMFF94s), writes an
interactive 3Dmol.js viewer page and a PNG, and compares a structure with a
reference drug by InChIKey: exact product, alpha-anomer (C-aryl glycosides),
enantiomer, other stereoisomer or a different compound. The default
reference is dapagliflozin; pass any other drug's SMILES to check it instead.
The viewer page loads 3Dmol.js from a CDN and needs internet access.

Status: this module needs RDKit and was not run during development, so test it
on your machine first.
