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

# --- FUNÇÕES ---
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

# --- INTERFACE ---
st.set_page_config(page_title="Mural Lab Micro", layout="wide")

# CSS MELHORADO: Ataca diretamente o botão dentro da div específica
st.markdown("""
    <style>
    /* Estilo para o container que envolve o botão de excluir */
    .link-btn {
        display: flex;
        justify-content: flex-end;
    }
    
    /* Remove o estilo de botão e transforma em link azul */
    .link-btn button {
        background: none !important;
        border: none !important;
        padding: 0 !important;
        color: #007bff !important;
        text-decoration: underline !important;
        font-family: inherit !important;
        font-size: 14px !important;
        box-shadow: none !important;
        cursor: pointer !important;
        width: auto !important;
        height: auto !important;
        min-height: 0 !important;
    }
    
    /* Efeito de hover (opcional: mudar para vermelho ou remover sublinhado) */
    .link-btn button:hover {
        color: #ff4b4b !important;
        text-decoration: none !important;
        background: none !important;
    }

    /* Impede que o botão tenha fundo cinza ao ser clicado */
    .link-btn button:active, .link-btn button:focus {
        background: none !important;
        outline: none !important;
        color: #ff4b4b !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("Estagiários Lab Microbiologia")
st.markdown(f"Bem-vindo, **{st.session_state.username}** 👋")

col1, col2 = st.columns([1, 2.5])

with col1:
    # Botões normais (NÃO serão afetados pelo CSS acima)
    if st.button("Compilação de amostras", use_container_width=True):
        st.switch_page("views/process_samples.py")
    if st.button("Remoção de duplicatas", use_container_width=True):
        st.switch_page("views/remove_duplicate.py")

with col2:
    st.markdown('📌 **Mural de avisos**')
    avisos, sha = get_post_it_content()
    
    with st.container(height=400, border=True):
        if not avisos:
            st.caption("Nenhum aviso no momento.")
        else:
            for i, item in enumerate(avisos):
                # Usamos colunas para o cabeçalho
                c_head, c_del = st.columns([0.8, 0.2])
                
                with c_head:
                    st.markdown(f"**{item['user']}** — *{item['date']}*")
                
                with c_del:
                    # Div 'link-btn' força o estilo de link apenas aqui
                    st.markdown('<div class="link-btn">', unsafe_allow_html=True)
                    if st.button("Excluir", key=f"del_{i}"):
                        avisos.pop(i)
                        if update_github(avisos, sha):
                            st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                
                st.markdown(f"{item['text']}")
                st.divider()

    # Adição de novo aviso
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
            # Botão normal
            if st.button("💾", use_container_width=True):
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