import streamlit as st

users = st.secrets["users"]
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if not st.session_state.logged_in:
    st.title("🔒 Login obrigatório")
    login = st.text_input("Usuário:")
    password = st.text_input("Senha:", type="password")
    if st.button("Entrar"):
        if login in users and users[login] == password:
            st.session_state.logged_in = True
            st.session_state.username = login
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos. Tente novamente.")
    st.stop()

st.sidebar.markdown(f"""<div style="text-align: center; font-size: 12px;">{"Feito por Saraiva."}</div>""", unsafe_allow_html=True)
main_page = st.Page(page='views/main.py', title="Página principal", icon=':material/home:')
process_samples_page = st.Page(page='views/process_samples.py', title="Compilação de amostras", icon=':material/biotech:')
remove_duplicates_page = st.Page(page='views/remove_duplicate.py', title="Remoção de duplicatas", icon=':material/delete:')
info_page = st.Page(page='views/info.py', title="Informações", icon=':material/info:')
pg = st.navigation(pages=[main_page, process_samples_page, remove_duplicates_page, info_page])

pg.run()