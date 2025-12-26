import streamlit as st
from datetime import datetime
import requests
import base64
import pytz

GITHUB_TOKEN = st.secrets["github"]["token"]
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
def get_fortaleza_time():
    fuso = pytz.timezone('America/Fortaleza')
    return datetime.now(fuso).strftime("%d/%m/%Y %H:%M")

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
    if "adding_new" not in st.session_state:
        st.session_state.adding_new = False
    if not st.session_state.adding_new:
        with st.container(height=250, border=True):
            if current_history:
                st.markdown(current_history)
            else:
                st.caption("Nenhum aviso no momento.")
        c_empty, c_edit = st.columns([8, 1])
        with c_edit:
            if st.button("➕", use_container_width=True):
                st.session_state.adding_new = True
                st.rerun()
    else:
        new_entry = st.text_area("Nova entrada no mural:", height=150, placeholder="Escreva o aviso aqui...")
        c_empty, c_save, c_cancel = st.columns([6, 1.2, 1.2])
        with c_save:
            if st.button("💾", use_container_width=True):
                if new_entry.strip():
                    data_hora = get_fortaleza_time()
                    header = f"**{st.session_state.username}** — *{data_hora}*"
                    new_block = f"{header}\n\n{new_entry}\n\n---\n\n"
                    updated_content = f"{new_block}{current_history}"
                    if update_post_it_github(updated_content, sha):
                        st.session_state.adding_new = False
                        st.rerun()
                else:
                    st.warning("Texto vazio.")
        with c_cancel:
            if st.button("❌", use_container_width=True):
                st.session_state.adding_new = False
                st.rerun()