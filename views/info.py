import streamlit as st
import pandas as pd
import requests
import base64
from io import StringIO

# Variáveis
GITHUB_TOKEN = st.secrets["github"]["token"]
REPO = "afonsolsj/LABMICRO"
PATHS = {"departments": "assets/files/departments.csv", "material_general": "assets/files/materials_general.csv", "material_vigilance": "assets/files/materials_vigilance.csv", "material_smear_microscopy": "assets/files/materials_smear_microscopy.csv"}

# Funções
def load_csv_from_github(file_path):
    url = f"https://api.github.com/repos/{REPO}/contents/{file_path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        st.error(f"Erro ao carregar {file_path}: {r.status_code}")
        return pd.DataFrame(), None
    data = r.json()
    csv_content = base64.b64decode(data["content"]).decode("utf-8")
    return pd.read_csv(StringIO(csv_content)), data["sha"]

def update_csv_on_github(df, file_path, sha):
    url = f"https://api.github.com/repos/{REPO}/contents/{file_path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    payload = {
        "message": f"Atualização automática de {file_path} pelo Streamlit",
        "content": base64.b64encode(df.to_csv(index=False).encode()).decode(),
        "sha": sha,
    }
    return requests.put(url, headers=headers, json=payload).status_code == 200

def render_editor(title, path_key, color, key_suffix):
    st.badge(title, icon=":material/picture_as_pdf:", color=color)
    df, sha = load_csv_from_github(PATHS[path_key])
    edited = st.data_editor(df, num_rows="dynamic", use_container_width=True, key=f"{key_suffix}_editor")
    if st.button(f"Atualizar {title}", key=f"save_{key_suffix}"):
        if "Código" in edited.columns:
            edited = edited.sort_values("Código").reset_index(drop=True)
        if update_csv_on_github(edited, PATHS[path_key], sha):
            st.success("Base de dados atualizada com sucesso!")
        else:
            st.error("Erro ao atualizar base de dados.")

def render_legend_item(badge_text, icon, color, description):
    col1, col2 = st.columns([2, 8], vertical_alignment="center")
    with col1:
        st.badge(badge_text, icon=icon, color=color)
    with col2:
        st.markdown(f'<p style="font-size:14px;">{description}</p>', unsafe_allow_html=True)

# Código principal da página
st.title("Informações")
tab1, tab2, tab3 = st.tabs(["Setores", "Materiais", "Legendas"])
with tab1:
    st.badge('HUWC', icon=":material/home_health:", color="yellow")
    df, sha = load_csv_from_github(PATHS["departments"])
    edited = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="departments_editor") 
    if st.button("Atualizar setores", key="save_departments"):
        if "Código" in edited.columns:
            edited = edited.sort_values("Código").reset_index(drop=True)
        if update_csv_on_github(edited, PATHS["departments"], sha):
            st.success("Base de dados atualizada com sucesso!")
        else:
            st.error("Erro ao atualizar base de dados.")
with tab2:
    render_editor("Materiais (Geral)", "material_general", "blue", "general")
    render_editor("Materiais (Cultura de vigilância)", "material_vigilance", "red", "vigilance")
    render_editor("Materiais (Baciloscopia)", "material_smear_microscopy", "green", "smear")
with tab3:
    with st.expander("Cores", icon=":material/colors:"):
        render_legend_item("Ambulatório", ":material/check_circle:", "green",
                           "Paciente em ambulatório. Não é necessário verificação.")
        render_legend_item("Vermelho", ":material/skull:", "red",
                           "Óbito do paciente. Não é necessário verificação.")
        render_legend_item("Amarelo", ":material/hotel:", "yellow",
                           "Valor dependente. É necessário verificação e preenchimento manual.")
        render_legend_item("Vazio", ":material/hotel:", "blue",
                           "Valor não encontrado. É necessário verificação e preenchimento manual.")
    with st.expander("Desfecho", icon=":material/health_cross:", expanded=True):
        st.table({"Desfecho": ["Internação", "Óbito", "Alta", "Transferência"], "Código": [1, 2, 3, 4]})