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