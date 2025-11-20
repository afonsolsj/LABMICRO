import streamlit as st

st.title("Estagiários Lab Microbiologia")
st.markdown(f"Bem-vindo, **{st.session_state.username}** 👋")
col1, col2 = st.columns(2)
if col1.button("Amostras negativas"):
    st.switch_page("views/negative.py")
if col2.button("Compilação de amostras"):
    st.switch_page("views/process_samples.py")