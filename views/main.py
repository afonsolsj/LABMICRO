import streamlit as st

st.title("Estagiários Lab Microbiologia")
st.markdown(f"Bem-vindo, **{st.session_state.username}** 👋")
if st.button("Compilação de amostras"):
    st.switch_page("views/process_samples.py")