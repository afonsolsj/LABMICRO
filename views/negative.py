import streamlit as st
import pypdf
from pypdf import PdfReader, PdfWriter
import re
from datetime import datetime
import pytz
import xlsxwriter
import pandas as pd
from io import BytesIO
import zipfile

#Carregamento de dados
departments_df = pd.read_csv("assets/files/departments.csv")
substitution_departments = dict(zip(departments_df["Unidade/Ambulatório"].str.upper(), departments_df["Código"]))
materials_general_df = pd.read_csv("assets/files/materials_general.csv")
materials_general = dict(zip(materials_general_df["Material"].str.lower(), materials_general_df["Código"]))
materials_vigilance_df = pd.read_csv("assets/files/materials_vigilance.csv")
materials_vigilance = dict(zip(materials_vigilance_df["Material"].str.lower(), materials_vigilance_df["Código"]))
materials_smear_df = pd.read_csv("assets/files/materials_smear_microscopy.csv")
materials_smear_microscopy = dict(zip(materials_smear_df["Material"].str.lower(), materials_smear_df["Código"]))

#Funções
def merge_pdfs(pdf_files):
    writer = PdfWriter()
    for uploaded_file in pdf_files:
        reader = PdfReader(uploaded_file)
        for page in reader.pages:
            writer.add_page(page)
    output_buffer = BytesIO()
    writer.write(output_buffer)
    output_buffer.seek(0)
    return output_buffer

def process_general(uploaded_files, start_id, st):
    valid_files = []
    ignored_files_summary = []
    st.info("Iniciando pré-análise dos arquivos...")
    progress_bar = st.progress(0)
    status_text = st.empty()
    for idx, f in enumerate(uploaded_files, 1):
        status_text.text(f"Verificando arquivo {idx}/{len(uploaded_files)}: {f.name}")
        try:
            reader = pypdf.PdfReader(f)
            text_content = reader.pages[0].extract_text() or ""
            fname = f.name.replace(".pdf", "")
            match_proc = re.search(r"Proced[êe]ncia\.\s*:\s*([^|]+)", text_content, re.IGNORECASE)
            if match_proc and "MEAC" in match_proc.group(1).upper():
                ignored_files_summary.append(f"{fname}: Pertence à MEAC")
                continue
            text_lower = text_content.lower()
            motivo_ignorar = ""
            if "bacterioscopia" in text_lower:
                motivo_ignorar = "Contém o termo 'bacterioscopia'"
            elif "swab retal" in text_lower or "reto" in text_lower:
                motivo_ignorar = "Contém o termo 'swab retal'"
            elif "baar" in text_lower:
                motivo_ignorar = "Contém o termo 'BAAR'"
            if motivo_ignorar:
                ignored_files_summary.append(f"{fname}: {motivo_ignorar}")
                continue
            valid_files.append(f)
        except Exception as e:
            ignored_files_summary.append(f"{fname}: Erro ({e})")
        progress_bar.progress(idx / len(uploaded_files))
    st.success(f"Pré-análise concluída: {len(valid_files)} arquivos válidos, {len(ignored_files_summary)} ignorados.")
    if valid_files:
        found_data = []
        current_id = start_id
        brazil_tz = pytz.timezone('America/Sao_Paulo')
        data_agora = datetime.now(brazil_tz).strftime("%Y-%m-%d %H:%M:%S")
        progress_bar = st.progress(0)
        status_text = st.empty()
        for idx, f in enumerate(valid_files, 1):
            status_text.text(f"Processando {idx}/{len(valid_files)}: {f.name}")
            try:
                reader = pypdf.PdfReader(f)
                full_text = "".join([p.extract_text() or "" for p in reader.pages])
                record = {col: "" for col in st.secrets["columns"]["general"]}
                record.update({
                    "id": current_id,
                    "hospital": "1",
                    "faz_parte_projeto_cdc_rfa": "2",
                    "dados_microbiologia_complete": "2",
                    "desfecho_do_paciente": "3",
                    "data_agora": data_agora
                })
                try:
                    record["n_mero_do_pedido"] = int(f.name.replace(".pdf", ""))
                except ValueError:
                    record["n_mero_do_pedido"] = f.name.replace(".pdf", "")
                match_proc = re.search(r"Proced[êe]ncia\.\s*:\s*([^|]+)", full_text, re.IGNORECASE)
                record['setor_nao_padronizado'] = False
                if match_proc:
                    setor = match_proc.group(1).strip()
                    if setor.upper() in substitution_departments:
                        record["setor_de_origem"] = substitution_departments[setor.upper()]
                    else:
                        record["setor_de_origem"] = setor
                        record['setor_nao_padronizado'] = True
                match_mat = re.search(r"material\s*:(.*)", full_text, re.IGNORECASE)
                if match_mat:
                    raw_material = match_mat.group(1).strip()
                    low_material = raw_material.lower()
                    material_encontrado = False
                    if "sangue" in low_material:
                        record["qual_tipo_de_material"] = 5
                        material_encontrado = True
                    if not material_encontrado:
                        for mat in materials_general:
                            if low_material == mat.lower():
                                record["qual_tipo_de_material"] = materials_general[mat]
                                material_encontrado = True
                                break
                    if not material_encontrado:
                        record["qual_tipo_de_material"] = 10
                        record["outro_tipo_de_material"] = raw_material
                m_pront = re.search(r"Prontuário\.\.:\s*(\S+)\s*([\s\S]*?)\s*Sexo\.\.", full_text, re.IGNORECASE)
                if m_pront:
                    record["n_mero_do_prontu_rio"] = m_pront.group(1).strip()
                    nome_bruto = m_pront.group(2).strip()
                    nome_limpo = " ".join(nome_bruto.split()) 
                    record["column_aux"] = nome_limpo
                m_idade = re.search(r"Idade:\s*(\d+)", full_text, re.IGNORECASE)
                if m_idade:
                    record["idade"] = m_idade.group(1)
                m_sexo = re.search(r"Sexo\.\.\.\.\.\.\.\.:\s*(\S+)", full_text, re.IGNORECASE)
                if m_sexo:
                    sx = m_sexo.group(1).strip().upper()
                    record["sexo"] = 1 if sx == "MASCULINO" else 0 if sx == "FEMININO" else sx
                def parse_date(text, default_time="00:00"):
                    text = text.strip()
                    if ":" not in text:
                        text += f" {default_time}"
                    for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S"):
                        try:
                            dt_obj = datetime.strptime(text, fmt)
                            return dt_obj.strftime("%Y-%m-%d %H:%M")
                        except ValueError:
                            continue
                    return text
                m_rec = re.search(r"Dt\.Recebimento:\s*([\d/]+\s*\d{0,2}:?\d{0,2})", full_text)
                if m_rec:
                    record["data_de_entrada"] = parse_date(m_rec.group(1))
                m_lib = re.search(r"Dt\.Libera[çc][aã]o:\s*([\d/]+\s*\d{0,2}:?\d{0,2})", full_text)
                if m_lib:
                    record["data_da_libera_o"] = parse_date(m_lib.group(1))
                record["tempo_de_libera_o_dias"] = ""
                record["cat_tempo_de_libera_o_dias"] = ""
                record["resultado"] = "0"
                if record.get("qual_tipo_de_material") == 7 and "SUGESTIVO DE CONTAMINAÇÃO" in full_text.upper():
                    record["resultado"] = "2"
                elif record.get("qual_tipo_de_material") != 7 and "SUGESTIVO DE CONTAMINAÇÃO" in full_text.upper():
                    record["resultado"] = "3"
                found_data.append(record)
                current_id += 1
            except Exception as e:
                ignored_files_summary.append(f"{f.name}: erro ({e})")
                continue
            progress_bar.progress(idx / len(valid_files))
        status_text.text("Processamento concluído!")
        excel_buffer = None
        if uploaded_report is not None:
            reader = PdfReader(uploaded_report)
            pdf_text = ""
            for page in reader.pages:
                content = page.extract_text()
                if content:
                    pdf_text += content
            pdf_lines = pdf_text.split('\n')
            if found_data:
                df = pd.DataFrame(found_data)
                df['pdf_data_1'] = pd.NaT
                df['pdf_data_2'] = pd.NaT
                date_regex = re.compile(r'(\d{2}/\d{2}/\d{4})')
                for i, row in df.iterrows():
                    nome = str(row.get('column_aux', '')).strip() 
                    data_entrada_str = str(row.get('data_de_entrada', '')).strip()
                    if not nome:
                        continue 
                    data_entrada = pd.to_datetime(data_entrada_str, errors='coerce') 
                    if pd.isna(data_entrada):
                        continue 
                    found_patient = False
                    nome_pattern = r'\b' + re.escape(nome) + r'\b'
                    for line in pdf_lines:
                        if re.search(nome_pattern, line, re.IGNORECASE):
                            found_patient = True
                            dates_found = date_regex.findall(line)
                            if len(dates_found) >= 2:
                                date_str_1 = dates_found[-2]
                                date_str_2 = dates_found[-1]
                                pdf_data_1 = pd.to_datetime(date_str_1, format='%d/%m/%Y', errors='coerce')
                                pdf_data_2 = pd.to_datetime(date_str_2, format='%d/%m/%Y', errors='coerce')
                                if pd.isna(pdf_data_1) or pd.isna(pdf_data_2):
                                    continue
                                start_date = min(pdf_data_1, pdf_data_2)
                                end_date = max(pdf_data_1, pdf_data_2) + pd.Timedelta(days=1) 
                                if start_date <= data_entrada < end_date: 
                                    df.at[i, 'pdf_data_1'] = start_date
                                    df.at[i, 'pdf_data_2'] = end_date - pd.Timedelta(days=1)
                                    break 
                                else:
                                    pass
                            else:
                                pass
                excel_buffer = BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                    df_export = df.drop(columns=['setor_nao_padronizado', 'column_aux', 'pdf_data_1', 'pdf_data_2','column_aux1',
            'column_aux2', 'column_aux3'], errors='ignore')
                    df_export.to_excel(writer, index=False, sheet_name='Dados')
                    wb = writer.book
                    ws = writer.sheets['Dados']
                    violet = wb.add_format({'bg_color': "#D296E3"})
                    blue = wb.add_format({'bg_color': '#ADD8E6'})
                    green = wb.add_format({'bg_color': '#90EE90'})
                    red = wb.add_format({'bg_color': '#FF7F7F'})
                    col_setor = df_export.columns.get_loc('setor_de_origem')
                    col_mat = df_export.columns.get_loc('qual_tipo_de_material')
                    col_cx = df_export.columns.get_loc('desfecho_do_paciente')
                    code_to_unit = dict(zip(departments_df["Código"], departments_df["Unidade/Ambulatório"].str.upper()))
                    for i, row in df.iterrows():
                        if row['setor_nao_padronizado']:
                            ws.write(i + 1, col_setor, row['setor_de_origem'], violet)
                        if row['qual_tipo_de_material'] == 10:
                            ws.write(i + 1, col_mat, row['qual_tipo_de_material'], blue)
                    for i, row in df.iterrows():
                        nome = str(row['column_aux']).strip()
                        if not nome:
                            continue
                        setor_cod = row['setor_de_origem']
                        setor_nome = ""
                        if isinstance(setor_cod, (int, float)) and setor_cod in code_to_unit:
                            setor_nome = code_to_unit[setor_cod]
                        elif isinstance(setor_cod, str):
                            setor_nome = setor_cod.upper()
                        pdf1_val = row.get('pdf_data_1')
                        pdf2_val = row.get('pdf_data_2')
                        if pd.isna(pdf1_val) or pd.isna(pdf2_val):
                            ws.write(i + 1, col_cx, 3, blue)
                        else:
                            match = re.search(rf"(\bO\s+)?\b{re.escape(nome)}\b", pdf_text, re.IGNORECASE)
                            if match and match.group(1):
                                ws.write(i + 1, col_cx, 2, red)
                            else:
                                ws.write(i + 1, col_cx, row['desfecho_do_paciente'], blue)
                        if "AMB" in setor_nome:
                            ws.write(i + 1, col_cx, row['desfecho_do_paciente'], green)
                            continue
                excel_buffer.seek(0)
    return excel_buffer, ignored_files_summary

def process_vigilance(uploaded_files, start_id, st):
    valid_files = []
    ignored_files_summary = []
    st.info("Iniciando pré-análise dos arquivos de vigilância...")
    progress_bar = st.progress(0)
    status_text = st.empty()
    for idx, f in enumerate(uploaded_files, 1):
        status_text.text(f"Verificando arquivo {idx}/{len(uploaded_files)}: {f.name}")
        fname = f.name.replace(".pdf", "")
        try:
            reader = pypdf.PdfReader(f)
            text_content = reader.pages[0].extract_text() or ""
            text_lower = text_content.lower()
            motivo_ignorar = ""
            match_procedencia = re.search(r"Proced[êe]ncia\.\s*:\s*([^|]+)", text_content, re.IGNORECASE)
            if match_procedencia and "MEAC" in match_procedencia.group(1).strip().upper():
                ignored_files_summary.append(f"{fname}: Pertence à MEAC")
                continue
            if not ("swab retal" in text_lower or "reto" in text_lower):
                ignored_files_summary.append(f"{fname}: Não contém 'swab retal' ou 'reto'")
                continue
            if "bacterioscopia" in text_lower:
                motivo_ignorar = "Contém o termo 'bacterioscopia'"
            elif "baar" in text_lower:
                motivo_ignorar = "Contém o termo 'BAAR'"
            if motivo_ignorar:
                ignored_files_summary.append(f"{fname}: {motivo_ignorar}")
                continue                
            valid_files.append(f)
        except Exception as e:
            ignored_files_summary.append(f"{fname}: Erro na pré-análise ({e})")
        progress_bar.progress(idx / len(uploaded_files))
    st.success(f"Pré-análise concluída: {len(valid_files)} arquivos válidos, {len(ignored_files_summary)} ignorados.")
    excel_buffer = None
    found_data = []
    if valid_files:
        current_id = start_id
        brazil_tz = pytz.timezone('America/Sao_Paulo')
        data_agora = datetime.now(brazil_tz).strftime("%Y-%m-%d %H:%M:%S")
        progress_bar = st.progress(0)
        status_text = st.empty()
        for idx, f in enumerate(valid_files, 1):
            status_text.text(f"Processando {idx}/{len(valid_files)}: {f.name}")
            try:
                reader = pypdf.PdfReader(f)
                full_text = "".join(page.extract_text() or "" for page in reader.pages)
                record = {col: "" for col in st.secrets["columns"]["vigilance"]}
                record.update({
                    "record_id": current_id,
                    "hospital_de_origem": "1",
                    "faz_parte_projeto_cdc_rfa_ck21_2104": "2",
                    "formulrio_complete": "2",
                    "desfecho_do_paciente": "3",
                    "data_agora": data_agora,
                    "se_positivo_para_qual_agente": "",
                    "se_negativo_para_qual_agente": ""
                })
                try:
                    record["n_mero_do_pedido"] = int(f.name.replace(".pdf", ""))
                except ValueError:
                    record["n_mero_do_pedido"] = f.name.replace(".pdf", "")
                match_proc = re.search(r"Proced[êe]ncia\.\s*:\s*([^|]+)", full_text, re.IGNORECASE)
                record['setor_nao_padronizado'] = False
                if match_proc:
                    setor = match_proc.group(1).strip()
                    if setor.upper() in substitution_departments:
                        record["setor_de_origem"] = substitution_departments[setor.upper()]
                    else:
                        record["setor_de_origem"] = setor
                        record['setor_nao_padronizado'] = True
                match_mat = re.search(r"material\s*:(.*)", full_text, re.IGNORECASE)
                if match_mat:
                    raw_material = match_mat.group(1).strip()
                    low_material = raw_material.lower()
                    material_encontrado = False
                    for material_valido in materials_vigilance.keys():
                        if low_material == material_valido.lower():
                            record["qual_tipo_de_material"] = materials_vigilance[material_valido]
                            material_encontrado = True
                            break
                    if not material_encontrado:
                        record["qual_tipo_de_material"] = 2
                        record["outro_tipo_de_material"] = raw_material
                m_pront = re.search(r"Prontuário\.\.:\s*(\S+)\s*([\s\S]*?)\s*Sexo\.\.", full_text, re.IGNORECASE)
                if m_pront:
                    record["n_mero_do_prontu_rio"] = m_pront.group(1).strip()
                    aux_text = m_pront.group(2)
                    if aux_text:
                        nome_limpo = " ".join(aux_text.split())
                        record["column_aux"] = nome_limpo
                    else:
                        record["column_aux"] = ""
                m_idade = re.search(r"Idade:\s*(\d+)", full_text, re.IGNORECASE)
                if m_idade:
                    record["idade_anos"] = m_idade.group(1)
                m_sexo = re.search(r"Sexo\.\.\.\.\.\.\.\.:\s*(\S+)", full_text, re.IGNORECASE)
                if m_sexo:
                    sx = m_sexo.group(1).strip().upper()
                    record["sexo"] = 2 if sx == "MASCULINO" else 1 if sx == "FEMININO" else sx
                def parse_date(text, default_time="00:00"):
                    text = text.strip()
                    if ":" not in text:
                        text += f" {default_time}"
                    for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S"):
                        try:
                            dt_obj = datetime.strptime(text, fmt)
                            return dt_obj.strftime("%Y-%m-%d %H:%M")
                        except ValueError:
                            continue
                    return text
                m_rec = re.search(r"Dt\.Recebimento:\s*([\d/]+\s*\d{0,2}:?\d{0,2})", full_text)
                if m_rec:
                    record["data_de_entrada"] = parse_date(m_rec.group(1))
                m_lib = re.search(r"Dt\.Libera[çc][aã]o:\s*([\d/]+\s*\d{0,2}:?\d{0,2})", full_text)
                if m_lib:
                    record["data_da_libera_o"] = parse_date(m_lib.group(1))
                record["tempo_de_libera_o_dias"] = ""
                record["categoriza_o_do_tempo_de_libera_o_dias"] = ""
                record["resultado"] = "2"
                full_text_upper = full_text.upper().replace("\n", " ")
                if "NÃO HOUVE CRESCIMENTO DE ENTEROBACTÉRIAS RESISTENTES AOS CARBAPENÊMICOS" in full_text_upper and \
                   "ENTEROCOCOS RESISTENTES À VANCOMICINA" in full_text_upper:
                    record["se_negativo_para_qual_agente"] = "3"
                elif "NÃO HOUVE CRESCIMENTO DE ENTEROBACTÉRIAS RESISTENTES AOS CARBAPENÊMICOS" in full_text_upper:
                     record["se_negativo_para_qual_agente"] = "1"
                found_data.append(record)
                current_id += 1  
            except Exception as e:
                ignored_files_summary.append(f"{f.name}: erro durante processamento ({e})")
                continue
            progress_bar.progress(idx / len(valid_files))
        status_text.text("Processamento concluído!")
        excel_buffer = None
        if uploaded_report is not None:
            reader = PdfReader(uploaded_report)
            pdf_text = ""
            for page in reader.pages:
                content = page.extract_text()
                if content:
                    pdf_text += content
            pdf_lines = pdf_text.split('\n')
            if found_data:
                df = pd.DataFrame(found_data)
                df['pdf_data_1'] = pd.NaT
                df['pdf_data_2'] = pd.NaT
                date_regex = re.compile(r'(\d{2}/\d{2}/\d{4})')
                for i, row in df.iterrows():
                    nome = str(row.get('column_aux', '')).strip() 
                    data_entrada_str = str(row.get('data_de_entrada', '')).strip()
                    if not nome:
                        continue 
                    data_entrada = pd.to_datetime(data_entrada_str, errors='coerce') 
                    if pd.isna(data_entrada):
                        continue 
                    found_patient = False
                    nome_pattern = r'\b' + re.escape(nome) + r'\b'
                    for line in pdf_lines:
                        if re.search(nome_pattern, line, re.IGNORECASE):
                            found_patient = True
                            dates_found = date_regex.findall(line)
                            if len(dates_found) >= 2:
                                date_str_1 = dates_found[-2]
                                date_str_2 = dates_found[-1]
                                pdf_data_1 = pd.to_datetime(date_str_1, format='%d/%m/%Y', errors='coerce')
                                pdf_data_2 = pd.to_datetime(date_str_2, format='%d/%m/%Y', errors='coerce')
                                if pd.isna(pdf_data_1) or pd.isna(pdf_data_2):
                                    continue
                                start_date = min(pdf_data_1, pdf_data_2)
                                end_date = max(pdf_data_1, pdf_data_2) + pd.Timedelta(days=1) 
                                if start_date <= data_entrada < end_date: 
                                    df.at[i, 'pdf_data_1'] = start_date
                                    df.at[i, 'pdf_data_2'] = end_date - pd.Timedelta(days=1)
                                    break 
                                else:
                                    pass
                            else:
                                pass
                excel_buffer = BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                    df_export = df.drop(columns=['setor_nao_padronizado', 'column_aux', 'pdf_data_1', 'pdf_data_2','column_aux1',
            'column_aux2', 'column_aux3'], errors='ignore')
                    df_export.to_excel(writer, index=False, sheet_name='Dados')
                    wb = writer.book
                    ws = writer.sheets['Dados']
                    violet = wb.add_format({'bg_color': '#D296E3'})
                    blue = wb.add_format({'bg_color': '#ADD8E6'})
                    green = wb.add_format({'bg_color': '#90EE90'})
                    red = wb.add_format({'bg_color': '#FF7F7F'})
                    col_setor = df_export.columns.get_loc('setor_de_origem')
                    col_mat = df_export.columns.get_loc('qual_tipo_de_material')
                    col_cx = df_export.columns.get_loc('desfecho_do_paciente')
                    code_to_unit = dict(zip(departments_df["Código"], departments_df["Unidade/Ambulatório"].str.upper()))
                    for i, row in df.iterrows():
                        if row['setor_nao_padronizado']:
                            ws.write(i + 1, col_setor, row['setor_de_origem'], violet)
                        if row['qual_tipo_de_material'] == 10:
                            ws.write(i + 1, col_mat, row['qual_tipo_de_material'], blue)
                    for i, row in df.iterrows():
                        nome = str(row['column_aux']).strip()
                        if not nome:
                            continue
                        setor_cod = row['setor_de_origem']
                        setor_nome = ""
                        if isinstance(setor_cod, (int, float)) and setor_cod in code_to_unit:
                            setor_nome = code_to_unit[setor_cod]
                        elif isinstance(setor_cod, str):
                            setor_nome = setor_cod.upper()
                        pdf1_val = row.get('pdf_data_1')
                        pdf2_val = row.get('pdf_data_2')
                        if pd.isna(pdf1_val) or pd.isna(pdf2_val):
                            ws.write(i + 1, col_cx, 3, blue)
                        else:
                            match = re.search(rf"(\bO\s+)?\b{re.escape(nome)}\b", pdf_text, re.IGNORECASE)
                            if match and match.group(1):
                                ws.write(i + 1, col_cx, 2, red)
                            else:
                                ws.write(i + 1, col_cx, row['desfecho_do_paciente'], blue)
                        if "AMB" in setor_nome:
                            ws.write(i + 1, col_cx, row['desfecho_do_paciente'], green)
                            continue
                excel_buffer.seek(0)
    return excel_buffer, ignored_files_summary

def process_smear_microscopy(uploaded_files, start_id, st):
    valid_files = []
    ignored_files_summary = []
    st.info("Iniciando pré-análise dos arquivos de baciloscopia (BAAR)...")
    progress_bar = st.progress(0)
    status_text = st.empty()
    for idx, f in enumerate(uploaded_files, 1):
        status_text.text(f"Verificando arquivo {idx}/{len(uploaded_files)}: {f.name}")
        fname = f.name.replace(".pdf", "")
        try:
            reader = pypdf.PdfReader(f)
            text_content = reader.pages[0].extract_text() or ""
            text_lower = text_content.lower()
            match_procedencia = re.search(r"Proced[êe]ncia\.\s*:\s*([^|]+)", text_content, re.IGNORECASE)
            if match_procedencia and "MEAC" in match_procedencia.group(1).strip().upper():
                ignored_files_summary.append(f"{fname}: Pertence à MEAC")
                continue
            if "baar" not in text_lower:
                ignored_files_summary.append(f"{fname}: Não contém o termo 'BAAR'")
                continue
            valid_files.append(f)
        except Exception as e:
            ignored_files_summary.append(f"{fname}: Erro na pré-análise ({e})")
        progress_bar.progress(idx / len(uploaded_files))
    st.success(f"Pré-análise concluída: {len(valid_files)} arquivos válidos, {len(ignored_files_summary)} ignorados.")
    excel_buffer = None
    found_data = []
    if valid_files:
        current_id = start_id
        brazil_tz = pytz.timezone('America/Sao_Paulo')
        data_agora = datetime.now(brazil_tz).strftime("%Y-%m-%d %H:%M:%S")
        progress_bar = st.progress(0)
        status_text = st.empty()
        for idx, f in enumerate(valid_files, 1):
            status_text.text(f"Processando {idx}/{len(valid_files)}: {f.name}")
            try:
                reader = pypdf.PdfReader(f)
                full_text = "".join(page.extract_text() or "" for page in reader.pages)
                record = {col: "" for col in st.secrets["columns"]["smear_microscopy"]}
                record.update({
                    "record_id": current_id,
                    "hospital_de_origem": "1",
                    "formulrio_complete": "2",
                    "desfecho_do_paciente": "3",
                    "data_agora": data_agora,
                    "se_positivo_marque": ""
                })
                try:
                    record["n_mero_do_pedido"] = int(f.name.replace(".pdf", ""))
                except ValueError:
                    record["n_mero_do_pedido"] = f.name.replace(".pdf", "")
                match_proc = re.search(r"Proced[êe]ncia\.\s*:\s*([^|]+)", full_text, re.IGNORECASE)
                record['setor_nao_padronizado'] = False
                if match_proc:
                    setor = match_proc.group(1).strip()
                    if setor.upper() in substitution_departments:
                        record["setor_de_origem"] = substitution_departments[setor.upper()]
                    else:
                        record["setor_de_origem"] = setor
                        record['setor_nao_padronizado'] = True
                match_mat = re.search(r"MATERIAL EXAMINADO\s*:\s*(.*)", full_text, re.IGNORECASE)
                if match_mat:
                    raw_material = match_mat.group(1).strip()
                    low_material = raw_material.lower()
                    material_encontrado = False
                    for material_valido in materials_smear_microscopy.keys():
                        if low_material == material_valido.lower():
                            record["tipo_de_material"] = materials_smear_microscopy[material_valido]
                            material_encontrado = True
                            break
                    if not material_encontrado:
                        record["tipo_de_material"] = 2
                        record["se_outro_material"] = raw_material                
                m_pront = re.search(r"Prontuário\.\.:\s*(\S+)\s*([\s\S]*?)\s*Sexo\.\.", full_text, re.IGNORECASE)
                if m_pront:
                    record["n_mero_do_prontu_rio"] = m_pront.group(1).strip()
                    nome_bruto = m_pront.group(2).strip()
                    nome_limpo = " ".join(nome_bruto.split()) 
                    record["column_aux"] = nome_limpo                
                m_idade = re.search(r"Idade:\s*(\d+)", full_text, re.IGNORECASE)
                if m_idade:
                    record["idade_anos"] = m_idade.group(1)
                m_sexo = re.search(r"Sexo\.\.\.\.\.\.\.\.:\s*(\S+)", full_text, re.IGNORECASE)
                if m_sexo:
                    sx = m_sexo.group(1).strip().upper()
                    record["sexo"] = 2 if sx == "MASCULINO" else 1 if sx == "FEMININO" else sx
                def parse_date(text, default_time="00:00"):
                    text = text.strip()
                    if ":" not in text:
                        text += f" {default_time}"
                    for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S"):
                        try:
                            from datetime import datetime
                            dt_obj = datetime.strptime(text, fmt)
                            return dt_obj.strftime("%Y-%m-%d")
                        except ValueError:
                            continue
                    return text
                m_rec = re.search(r"Dt\.Recebimento:\s*([\d/]+\s*\d{0,2}:?\d{0,2})", full_text)
                if m_rec:
                    record["data_da_entrada"] = parse_date(m_rec.group(1))
                m_lib = re.search(r"Dt\.Libera[çc][aã]o:\s*([\d/]+\s*\d{0,2}:?\d{0,2})", full_text)
                if m_lib:
                    record["data_da_libera_o"] = parse_date(m_lib.group(1))
                record["tempo_de_libera_o_dias"] = ""
                record["categoriza_o_do_tempo_de_libera_o"] = ""
                record["resultado"] = "2"
                found_data.append(record)
                current_id += 1
            except Exception as e:
                ignored_files_summary.append(f"{f.name}: erro durante processamento ({e})")
                continue  
            progress_bar.progress(idx / len(valid_files))
        status_text.text("Processamento concluído!")
        excel_buffer = None
        if uploaded_report is not None:
            reader = PdfReader(uploaded_report)
            pdf_text = ""
            for page in reader.pages:
                content = page.extract_text()
                if content:
                    pdf_text += content
            pdf_lines = pdf_text.split('\n')
            if found_data:
                df = pd.DataFrame(found_data)
                df['pdf_data_1'] = pd.NaT
                df['pdf_data_2'] = pd.NaT
                date_regex = re.compile(r'(\d{2}/\d{2}/\d{4})')
                for i, row in df.iterrows():
                    nome = str(row.get('column_aux', '')).strip() 
                    data_entrada_str = str(row.get('data_de_entrada', '')).strip()
                    if not nome:
                        continue 
                    data_entrada = pd.to_datetime(data_entrada_str, errors='coerce') 
                    if pd.isna(data_entrada):
                        continue 
                    found_patient = False
                    nome_pattern = r'\b' + re.escape(nome) + r'\b'
                    for line in pdf_lines:
                        if re.search(nome_pattern, line, re.IGNORECASE):
                            found_patient = True
                            dates_found = date_regex.findall(line)
                            if len(dates_found) >= 2:
                                date_str_1 = dates_found[-2]
                                date_str_2 = dates_found[-1]
                                pdf_data_1 = pd.to_datetime(date_str_1, format='%d/%m/%Y', errors='coerce')
                                pdf_data_2 = pd.to_datetime(date_str_2, format='%d/%m/%Y', errors='coerce')
                                if pd.isna(pdf_data_1) or pd.isna(pdf_data_2):
                                    continue
                                start_date = min(pdf_data_1, pdf_data_2)
                                end_date = max(pdf_data_1, pdf_data_2) + pd.Timedelta(days=1) 
                                if start_date <= data_entrada < end_date: 
                                    df.at[i, 'pdf_data_1'] = start_date
                                    df.at[i, 'pdf_data_2'] = end_date - pd.Timedelta(days=1)
                                    break 
                                else:
                                    pass
                            else:
                                pass
                excel_buffer = BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                    df_export = df.drop(columns=['setor_nao_padronizado', 'column_aux', 'pdf_data_1', 'pdf_data_2','column_aux1',
            'column_aux2', 'column_aux3'], errors='ignore')
                    df_export.to_excel(writer, index=False, sheet_name='Dados')
                    wb = writer.book
                    ws = writer.sheets['Dados']
                    violet = wb.add_format({'bg_color': '#D296E3'})
                    blue = wb.add_format({'bg_color': '#ADD8E6'})
                    green = wb.add_format({'bg_color': '#90EE90'})
                    red = wb.add_format({'bg_color': '#FF7F7F'})
                    col_setor = df_export.columns.get_loc('setor_de_origem')
                    col_mat = df_export.columns.get_loc('tipo_de_material')
                    col_cx = df_export.columns.get_loc('desfecho_do_paciente')
                    code_to_unit = dict(zip(departments_df["Código"], departments_df["Unidade/Ambulatório"].str.upper()))
                    for i, row in df.iterrows():
                        if row['setor_nao_padronizado']:
                            ws.write(i + 1, col_setor, row['setor_de_origem'], violet)
                        if row['tipo_de_material'] == 10:
                            ws.write(i + 1, col_mat, row['tipo_de_material'], blue)
                    for i, row in df.iterrows():
                        nome = str(row['column_aux']).strip()
                        if not nome:
                            continue
                        setor_cod = row['setor_de_origem']
                        setor_nome = ""
                        if isinstance(setor_cod, (int, float)) and setor_cod in code_to_unit:
                            setor_nome = code_to_unit[setor_cod]
                        elif isinstance(setor_cod, str):
                            setor_nome = setor_cod.upper()
                        pdf1_val = row.get('pdf_data_1')
                        pdf2_val = row.get('pdf_data_2')
                        if pd.isna(pdf1_val) or pd.isna(pdf2_val):
                            ws.write(i + 1, col_cx, 3, blue)
                        else:
                            match = re.search(rf"(\bO\s+)?\b{re.escape(nome)}\b", pdf_text, re.IGNORECASE)
                            if match and match.group(1):
                                ws.write(i + 1, col_cx, 2, red)
                            else:
                                ws.write(i + 1, col_cx, row['desfecho_do_paciente'], blue)
                        if "AMB" in setor_nome:
                            ws.write(i + 1, col_cx, row['desfecho_do_paciente'], green)
                            continue
                excel_buffer.seek(0)  
    return excel_buffer, ignored_files_summary

# Código principal da página
st.title("Amostras negativas")
uploaded_files = st.file_uploader("1️⃣ Envie os arquivos PDF para processar", type="pdf", accept_multiple_files=True)
uploaded_reports = st.file_uploader("2️⃣ Envie o(s) relatório(s) de alta por período", type=["pdf"], accept_multiple_files=True)
uploaded_report = None
if uploaded_reports:
    uploaded_report = merge_pdfs(uploaded_reports)
st.markdown('<p style="font-size: 14px;">3️⃣ Defina os IDs iniciais para cada tipo de formulário</p>', unsafe_allow_html=True)
col1, col2, col3 = st.columns(3)
with col1:
    start_id_general = st.number_input("Geral", value=None, step=1)
with col2:
    start_id_vigilance = st.number_input("Cultura de vigilância", value=None, step=1)
with col3:
    start_id_smear = st.number_input("Baciloscopia", value=None, step=1)
conditions_met = uploaded_files and uploaded_report
is_disabled = not conditions_met
if st.button("Iniciar processamento", disabled=is_disabled):
    st.markdown('<p style="font-size: 14px;">🔄 Realizando processamento</p>', unsafe_allow_html=True)
    etapas = [
        ("🔍 Etapa 1/3: Processando GERAL...", "FORMULÁRIO GERAL", process_general, start_id_general, "negativos_GERAL.xlsx"),
        ("🔬 Etapa 2/3: Processando CULTURA DE VIGILÂNCIA...", "FORMULÁRIO CULTURA DE VIGILÂNCIA", process_vigilance, start_id_vigilance, "negativos_CULTURADEVIGILANCIA.xlsx"),
        ("🧫 Etapa 3/3: Processando BACILOSCOPIA...", "FORMULÁRIO BACILOSCOPIA", process_smear_microscopy, start_id_smear, "negativos_BACILOSCOPIA.xlsx"),
    ]
    resultados = []
    with st.status("Processando...", expanded=False) as status:
        overall_progress = st.progress(0)
        for i, (label, expander_label, func, start_id, filename) in enumerate(etapas, start=1):
            status.write(label)
            with st.expander(expander_label):
                excel_file, ignored = func(uploaded_files, start_id, st)
                resultados.append((filename, excel_file))
            overall_progress.progress(i / len(etapas))
        status.update(label="Processamento concluído!", state="complete", expanded=False)
    st.markdown('<p style="font-size: 14px;">⬇️ Download dos arquivos criados</p>', unsafe_allow_html=True)
    arquivos_validos = [(nome, buf) for nome, buf in resultados if buf]
    if not arquivos_validos:
        st.error("Nenhum arquivo Excel foi gerado em nenhum dos processamentos.")
    else:
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for nome, buf in arquivos_validos:
                buf.seek(0)
                zf.writestr(nome, buf.getvalue())
        st.download_button(
            label="Baixar (.zip)", 
            data=zip_buffer.getvalue(), 
            file_name="processamento_negativos_compilado.zip", 
            mime="application/zip"
        )