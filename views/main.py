import streamlit as st
import requests
import base64

# --- CONFIGURAÇÕES DO GITHUB ---
GITHUB_TOKEN = st.secrets["github"]["token"] # Guarde seu token no st.secrets por segurança
REPO_OWNER = "afonsolsj"
REPO_NAME = "LABMICRO"
FILE_PATH = "assets/files/notice_board.txt"
API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"

def get_post_it_content():
    response = requests.get(API_URL, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    if response.status_code == 200:
        content = response.json()
        return base64.b64decode(content['content']).decode('utf-8'), content['sha']
    return "", None
def update_post_it_github(new_text, sha):
    content_encoded = base64.b64encode(new_text.encode('utf-8')).decode('utf-8')
    data = {
        "message": "Atualizando post-it via Streamlit",
        "content": content_encoded,
        "sha": sha
    }
    response = requests.put(API_URL, json=data, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    return response.status_code == 200

st.title("Estagiários Lab Microbiologia")
st.markdown(f"Bem-vindo, **{st.session_state.username}** 👋")

col1, col2 = st.columns([1, 2.5])
with col1:
    if st.button("Compilação de amostras", use_container_width=True):
        st.switch_page("views/process_samples.py")
    if st.button("Remoção de duplicatas", use_container_width=True):
        st.switch_page("views/remove_duplicate.py")
with col2:
    st.markdown('<p style="font-size: 14px; margin-bottom: 5px;">📌 Mural de avisos</p>', unsafe_allow_html=True)
    current_text, sha = get_post_it_content()
    if "editing" not in st.session_state:
        st.session_state.editing = False
    if not st.session_state.editing:
        st.info(current_text if current_text else "Nenhum aviso no momento.")
        if st.button("✏️"):
            st.session_state.editing = True
            st.rerun()
    else:
        new_content = st.text_area("Escreva o aviso:", value=current_text, height=150)
        if st.button("💾"):
            if update_post_it_github(new_content, sha):
                st.success("Salvo!")
                st.session_state.editing = False
                st.rerun()
            else:
                st.error("Erro ao salvar no GitHub.")