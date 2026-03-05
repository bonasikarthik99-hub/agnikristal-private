import streamlit as st

st.title("AgniKristal AI Engine")

st.write("Co-crystal Prediction System")

api = st.text_input("Enter API SMILES")
coformer = st.text_input("Enter Coformer SMILES")

if st.button("Predict"):
    st.write("Running analysis...")
    st.success("Prediction complete")