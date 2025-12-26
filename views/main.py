import streamlit as st
from datetime import datetime
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
    current_history, sha = get_post_it_content()
    with st.container(height=250, border=True):
        if current_history:
            st.markdown(current_history)
        else:
            st.caption("Nenhum aviso registrado.")
    with st.expander("➕"):
        new_entry = st.text_area("Escreva sua mensagem:", key="new_post_it", placeholder="Digite aqui o aviso...")
        if st.button("💾", use_container_width=True):
            if new_entry.strip() != "":
                data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")
                formatted_entry = f"**{st.session_state.username}** - *{data_hora}*\n\n{new_entry}\n\n---\n"
                updated_content = formatted_entry + current_history
                if update_post_it_github(updated_content, sha):
                    st.success("Aviso postado!")
                    st.rerun()
                else:
                    st.error("Erro ao conectar com o GitHub.")
            else:
                st.warning("O campo de texto está vazio.")