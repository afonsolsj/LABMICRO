import streamlit as st

st.title("Estagiários MicroHUWC")
st.markdown(f"Bem-vindo, **{st.session_state.username}** 👋")
col1, col2, col3 = st.columns(3)
if col1.button("Amostras negativas"):
    st.switch_page("views/negative.py")
if col2.button("Compilação de amostras"):
    st.switch_page("views/process_samples.py")
if col3.button("Dividir relatório"):
    st.switch_page("views/structuring_reports.py")