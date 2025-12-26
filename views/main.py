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

st.title("Estagiários Lab Microbiologia")
st.markdown(f"Bem-vindo, **{st.session_state.username}** 👋")

col1, col2 = st.columns([1, 2.5])
with col1:
    if st.button("Compilação de amostras", use_container_width=True):
        st.switch_page("views/process_samples.py")
    if st.button("Remoção de duplicatas", use_container_width=True):
        st.switch_page("views/remove_duplicate.py")
Python
# ... (suas funções get_post_it_content, update_github e get_fortaleza_time continuam iguais)

with col2:
    st.markdown('📌 **Mural de avisos**')
    avisos, sha = get_post_it_content()

    # Container de Visualização
    with st.container(height=350, border=True):
        if not avisos:
            st.caption("Nenhum aviso no momento.")
        else:
            for i, item in enumerate(avisos):
                # Usamos uma proporção que dê pouco espaço para o botão (ex: 15 para 1)
                c_text, c_del = st.columns([15, 1])
                
                with c_text:
                    # Exibição do texto formatada
                    st.markdown(f"**{item['user']}** — *{item['date']}*")
                    st.markdown(f"{item['text']}")
                
                with c_del:
                    # Usamos um botão pequeno sem label para a lixeira
                    if st.button("🗑️", key=f"del_{i}", help="Excluir aviso"):
                        avisos.pop(i)
                        if update_github(avisos, sha):
                            st.rerun()
                
                st.markdown("---") # Linha divisória simples

    # Lógica de Botões (➕, 💾, ❌) na Direita
    if not st.session_state.adding_new:
        # Colunas para empurrar o botão ➕ para a direita
        c_empty, c_add = st.columns([0.9, 0.1])
        with c_add:
            if st.button("➕", use_container_width=True):
                st.session_state.adding_new = True
                st.rerun()
    else:
        new_entry = st.text_area("Nova entrada:", height=100, placeholder="Digite o aviso...")
        
        # Alinhamento dos botões de salvar e cancelar
        c_empty, c_save, c_cancel = st.columns([0.76, 0.12, 0.12])
        with c_save:
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