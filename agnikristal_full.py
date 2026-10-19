import os
import streamlit as st
import numpy as np
from rdkit import Chem
from rdkit.Chem import Descriptors, Draw
import plotly.graph_objects as go

st.set_page_config(
    page_title="AgniKristal - AI Cocrystal Predictor",
    page_icon="🔥",
    layout="wide"
)

st.title("AgniKristal - AI Cocrystal Predictor")

def validate_smiles(smiles):
    mol = Chem.MolFromSmiles(smiles)
    return mol is not None, mol

def calculate_descriptors(mol):
    return {
        "MolWt": Descriptors.MolWt(mol),
        "HDonors": Descriptors.NumHDonors(mol),
        "HAcceptors": Descriptors.NumHAcceptors(mol),
        "TPSA": Descriptors.TPSA(mol),
        "LogP": Descriptors.MolLogP(mol)
    }

def show_molecule(smiles):
    mol = Chem.MolFromSmiles(smiles)
    if mol:
        img = Draw.MolToImage(mol, size=(300,200))
        st.image(img)

api = st.text_input("API SMILES")
co = st.text_input("Coformer SMILES")
solv = st.text_input("Solvent SMILES")

if api:
    show_molecule(api)

if co:
    show_molecule(co)

if solv:
    show_molecule(solv)

if st.button("Predict"):
    valid_api, api_mol = validate_smiles(api)
    valid_co, co_mol = validate_smiles(co)

    if valid_api and valid_co:
        api_desc = calculate_descriptors(api_mol)
        co_desc = calculate_descriptors(co_mol)

        hbond_score = (
            min(api_desc["HDonors"], co_desc["HAcceptors"]) +
            min(api_desc["HAcceptors"], co_desc["HDonors"])
        )

        st.subheader("Hydrogen Bond Complementarity Score")
        st.success(f"Score: {hbond_score}")

        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=hbond_score,
            gauge={'axis': {'range':[0,10]}}
        ))

        st.plotly_chart(fig)

    else:
        st.error("Invalid SMILES")

# =========================
# PROCESS ALTERNATIVES (DAPAGLIFLOZIN)
# =========================

st.divider()
st.header("Case Study: Dapagliflozin Process Alternatives")

from core.process_alternatives import (
    get_alternatives, list_steps, DISCLAIMER
)

step_choice = st.selectbox("Step", ["All"] + list_steps())
maturity_choice = st.selectbox(
    "Minimum maturity",
    ["Any", "Industrial", "Patent/literature", "Academic"]
)

cheaper_only = st.checkbox("Only options cheaper than the baseline route", value=True)

rows = get_alternatives(
    step=None if step_choice == "All" else step_choice,
    max_maturity=None if maturity_choice == "Any" else maturity_choice
)
if cheaper_only:
    rows = [r for r in rows if r["cost"] == "Lower"]
rows = sorted(rows, key=lambda r: r["likelihood"], reverse=True)

st.dataframe(
    [
        {
            "Step": r["step"],
            "Reagent / option": r["reagent"],
            "Conditions": r["conditions"],
            "Pros": r["pros"],
            "Cons": r["cons"],
            "Maturity": r["maturity"],
            "Cost vs baseline": r["cost"],
            "Product risk": r["product_risk"],
            "Likelihood (heuristic)": r["likelihood"],
        }
        for r in rows
    ],
    use_container_width=True
)
st.caption(DISCLAIMER)


# =========================
# COMPANY EXPERIMENTAL DATA ANALYSIS
# =========================

st.divider()
st.header("Company Experimental Data - Best Route")

from core.experimental_data import (
    load_experiments, rank_routes, best_of_all, company_summary
)

st.caption(
    "Upload step-level results from any company (CSV or Excel). "
    "Columns: company, route_id, step_no, step_name, yield_pct (required); "
    "reagents, solvent, temp_c, purity_pct, alpha_anomer_pct, n_runs, "
    "n_runs_in_spec, step_cost_usd_per_kg, hazards (optional)."
)

upload = st.file_uploader("Experimental data", type=["csv", "xlsx", "xls"])
use_demo = st.checkbox("Use the fictional demo template instead", value=upload is None)

exp_source = upload
if exp_source is None and use_demo:
    exp_source = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "data", "experimental_template.csv"
    )

if exp_source is not None:
    try:
        exp_df = load_experiments(exp_source)
    except Exception as err:
        st.error(str(err))
        exp_df = None

    if exp_df is not None:
        for warning in exp_df.attrs.get("warnings", []):
            st.warning(warning)

        st.subheader("Route ranking")
        st.dataframe(rank_routes(exp_df), use_container_width=True)

        st.subheader("Company comparison")
        st.dataframe(company_summary(exp_df), use_container_width=True)

        st.subheader("Best of all companies (projection)")
        best = best_of_all(exp_df)
        st.dataframe(best["steps"], use_container_width=True)
        p_best = best["projected_p_exact_product"]
        st.metric("Projected overall yield (%)", best["projected_overall_yield_pct"])
        st.metric(
            "Projected P(exact product)",
            "n/a" if p_best != p_best else f"{p_best:.2f}"
        )
        for note in best["notes"]:
            st.info(note)

        st.subheader("Hazard and substitution screen (any drug)")
        from core.substitutions import screen_route
        screen = screen_route(exp_df)
        if screen.empty:
            st.success("No known hazardous or costly reagents/solvents found in these steps.")
        else:
            st.dataframe(screen, use_container_width=True)


# =========================
# 3D STRUCTURE + EXACT-PRODUCT CHECK
# =========================

st.divider()
st.header("3D Structure and Exact-Product Check")

try:
    from core import molecule3d
    import streamlit.components.v1 as components
    _have_3d = True
except ImportError:
    _have_3d = False
    st.error("RDKit is required for 3D structures: pip install rdkit matplotlib")

if _have_3d:
    reference_3d = st.text_input(
        "Target drug (reference SMILES, with stereochemistry)",
        value=molecule3d.DAPAGLIFLOZIN_SMILES
    )
    smiles_3d = st.text_input(
        "Structure to check and view (SMILES)",
        value=reference_3d
    )
    show_alpha = st.checkbox(
        "Show the alpha-anomer partner (C-aryl glycosides only)", value=True
    )

    if st.button("Build 3D structure"):
        try:
            check = molecule3d.verify_product(smiles_3d, reference_smiles=reference_3d)
            if check["is_exact_product"]:
                st.success("Exact product: matches dapagliflozin (stereochemistry included).")
            else:
                st.warning(f"Not the exact product - verdict: {check['verdict']}")
            st.json(check)

            entries = [("Structure", smiles_3d)]
            if show_alpha and check["verdict"] in ("exact_product", "alpha_anomer"):
                try:
                    entries.append(("Anomer partner", molecule3d.anomer_partner(smiles_3d)))
                except ValueError:
                    pass  # not a C-aryl glycoside: no alpha/beta partner

            components.html(
                molecule3d.viewer_html(entries), height=760, scrolling=True
            )

            import tempfile
            png = molecule3d.export_3d_png(
                os.path.join(tempfile.gettempdir(), "agnikristal_3d.png"), smiles_3d
            )
            st.image(png, caption="Static 3D render (MMFF94s optimized)")
        except Exception as err:
            st.error(str(err))


# =========================
# ALTERNATIVE REAGENTS / SOLVENTS FOR ANY DRUG
# =========================

st.divider()
st.header("Alternative Reagents and Solvents (any drug)")

from core.substitutions import lookup_table

st.caption(
    "Type the reagents, solvents or process steps of any route (for example: "
    "n-BuLi, DCM, LiAlH4, DMF, column chromatography). Suggestions are "
    "literature-level guidance; confirm each swap experimentally for your drug."
)

sub_text = st.text_input("Reagents / solvents / steps", key="sub_text")
if sub_text:
    sub_table = lookup_table(sub_text)
    if sub_table.empty:
        st.info("Nothing in the knowledge base matches that text yet.")
    else:
        st.dataframe(sub_table, use_container_width=True)
