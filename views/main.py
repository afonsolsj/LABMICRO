import streamlit as st
from datetime import datetime
import requests
import base64
import pytz
import json

# --- CONFIGURAÇÕES DO GITHUB ---
GITHUB_TOKEN = st.secrets["github"]["token"]
REPO_OWNER = "afonsolsj"
REPO_NAME = "LABMICRO"
FILE_PATH = "assets/files/notice_board.json" 
API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FILE_PATH}"

def get_post_it_content():
    response = requests.get(API_URL, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    if response.status_code == 200:
        content = response.json()
        decoded = base64.b64decode(content['content']).decode('utf-8')
        try:
            return json.loads(decoded), content['sha']
        except:
            return [], content['sha']
    return [], None
def update_github(data_list, sha):
    json_string = json.dumps(data_list, indent=4, ensure_ascii=False)
    content_encoded = base64.b64encode(json_string.encode('utf-8')).decode('utf-8')
    payload = {
        "message": "Atualizando mural",
        "content": content_encoded,
        "sha": sha
    }
    response = requests.put(API_URL, json=payload, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    return response.status_code in [200, 201]
def get_fortaleza_time():
    fuso = pytz.timezone('America/Fortaleza')
    return datetime.now(fuso).strftime("%d/%m/%Y %H:%M")

st.markdown("""
    <style>
    /* Estiliza especificamente o botão de excluir */
    div[data-testid="stColumn"] button {
        background: none !important;
        border: none !important;
        padding: 0 !important;
        color: #2e9aff !important;
        text-decoration: underline !important;
        font-weight: normal !important;
        font-size: 14px !important;
        height: auto !important;
        min-height: 0 !important;
        line-height: 1.5 !important;
        display: inline !important;
    }
    div[data-testid="stColumn"] button:hover {
        color: #ff4b4b !important;
        text-decoration: none !important;
        background: none !important;
    }
    div[data-testid="stColumn"] button:active {
        color: #ff4b4b !important;
        background: none !important;
    }
    /* Ajuste de espaçamento para as colunas do mural */
    [data-testid="stHorizontalBlock"] {
        align-items: baseline;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("Estagiários Lab Microbiologia")
st.markdown(f"Bem-vindo, **{st.session_state.username}** 👋")

col1, col2 = st.columns([1, 2.5])
with col1:
    if st.button("Compilação de amostras", use_container_width=True):
        st.switch_page("views/process_samples.py")
    if st.button("Remoção de duplicatas", use_container_width=True):
        st.switch_page("views/remove_duplicate.py")
with col2:
    st.markdown('📌 **Mural de avisos**')
    avisos, sha = get_post_it_content()
    
    with st.container(height=450, border=True):
        if not avisos:
            st.caption("Nenhum aviso no momento.")
        else:
            for i, item in enumerate(avisos):
                # Layout de linha única para cabeçalho: Nome - Data | Link Excluir
                c_info, c_del = st.columns([0.8, 0.2])
                
                with c_info:
                    st.markdown(f"**{item['user']}** — *{item['date']}*")
                
                with c_del:
                    # O botão agora parece um link devido ao CSS acima
                    if st.button("Excluir", key=f"del_{i}"):
                        avisos.pop(i)
                        if update_github(avisos, sha):
                            st.rerun()
                
                # Texto do aviso logo abaixo do cabeçalho
                st.markdown(f"{item['text']}")
                st.divider()

    # Lógica para adicionar novo aviso
    if "adding_new" not in st.session_state:
        st.session_state.adding_new = False

    if not st.session_state.adding_new:
        c_empty, c_add = st.columns([8, 1])
        with c_add:
            if st.button("➕", use_container_width=True):
                st.session_state.adding_new = True
                st.rerun()
    else:
        new_entry = st.text_area("Nova entrada:", height=100)
        c_empty, c_save, c_cancel = st.columns([6, 1.2, 1.2])
        with c_save:
            # Botão de salvar (usei o ícone mas pode ser texto)
            if st.button("💾 Salvar", use_container_width=True):
                if new_entry.strip():
                    novo_aviso = {
                        "user": st.session_state.username,
                        "date": get_fortaleza_time(),
                        "text": new_entry
                    }
                    avisos.insert(0, novo_aviso)
                    if update_github(avisos, sha):
                        st.session_state.adding_new = False
                        st.rerun()
        with c_cancel:
            if st.button("❌", use_container_width=True):
                st.session_state.adding_new = False
                st.rerun()