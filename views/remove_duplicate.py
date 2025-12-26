import streamlit as st
import pandas as pd
import io
import os

st.title("Limpeza de duplicatas")

file_complete = st.file_uploader("1️⃣ Base de dados completa (.xlsx)", type=["xlsx"])
file_removal = st.file_uploader("2️⃣ Dados extraídos do relatório (.xlsx)", type=["xlsx"])
arquivos_faltando = not (file_complete and file_removal)

if st.button("Iniciar limpeza", disabled=arquivos_faltando):
    try:
        df_completa = pd.read_excel(file_complete)
        df_remocao = pd.read_excel(file_removal)
        possiveis_colunas = ["n_mero_do_pedido", "numero_pedido"]
        col_comp = next((c for c in possiveis_colunas if c in df_completa.columns), None)
        col_rem = next((c for c in possiveis_colunas if c in df_remocao.columns), None)
        if col_comp and col_rem:
            serie_completa = df_completa[col_comp].astype(str).str.strip()
            df_remocao_limpo = df_remocao.copy()
            df_remocao_limpo[col_rem] = df_remocao_limpo[col_rem].astype(str).str.strip()
            df_final = df_remocao[~df_remocao_limpo[col_rem].isin(serie_completa)]
            removidos = len(df_remocao) - len(df_final)
            if removidos > 0:
                st.success(f"✅ {removidos} registros duplicados removidos!")
            else:
                st.info("ℹ️ Nenhum pedido repetido foi encontrado.")
            nome_base = os.path.splitext(file_removal.name)[0] 
            nome_arquivo_novo = f"{nome_base}_atualizado.xlsx"
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df_final.to_excel(writer, index=False, sheet_name='Dados_Limpos')
            st.download_button(
                label="Baixar (.xlsx)", 
                data=output.getvalue(), 
                file_name=nome_arquivo_novo, 
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            if not col_comp:
                st.error(f"❌ A coluna de pedido não foi encontrada na 'Base Completa'.")
            if not col_rem:
                st.error(f"❌ A coluna de pedido não foi encontrada nos 'Dados para Remoção'.")  
    except Exception as e:
        st.error(f"⚠️ Ocorreu um erro inesperado: {e}")

if arquivos_faltando:
    st.info("💡 Por favor, carregue os dois arquivos acima para liberar o botão de limpeza.")