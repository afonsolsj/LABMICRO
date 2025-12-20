import streamlit as st
import pandas as pd
import io

st.title("Limpador de Base: Remoção de Pedidos")
st.markdown("""
Esta ferramenta remove das suas planilhas novas os pedidos que já constam na sua **Base de dados completa**.
    """)

# 1. Upload dos arquivos
col1, col2 = st.columns(2)
with col1:
    file_complete = st.file_uploader("1️⃣ Base de dados completa (.xlsx)", type=["xlsx"])
with col2:
    file_removal = st.file_uploader("2️⃣ Dados para remoção/conferência (.xlsx)", type=["xlsx"])

# 2. Processamento
if st.button("Executar Limpeza"):
    if file_complete and file_removal:
        with st.spinner("Processando..."):
            try:
                # Carregar planilhas
                df_completa = pd.read_excel(file_complete)
                df_remocao = pd.read_excel(file_removal)

                # Nome da coluna conforme sua estrutura
                col_pedido = "n_mero_do_pedido"

                if col_pedido in df_completa.columns and col_pedido in df_remocao.columns:
                    # Limpeza básica: converter para string e remover espaços
                    # Isso evita que o Python ache que "123" é diferente de "123 "
                    df_completa[col_pedido] = df_completa[col_pedido].astype(str).str.strip()
                    df_remocao[col_pedido] = df_remocao[col_pedido].astype(str).str.strip()

                    # Lógica: Manter no df_remocao apenas o que NÃO está no df_completa
                    initial_count = len(df_remocao)
                    df_final = df_remocao[~df_remocao[col_pedido].isin(df_completa[col_pedido])]
                    final_count = len(df_final)
                    removidos = initial_count - final_count

                    if removidos > 0:
                        st.success(f"Sucesso! {removidos} pedidos encontrados na base completa e removidos da nova lista.")
                            
                        # Preparar arquivo para download
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                            df_final.to_excel(writer, index=False, sheet_name='Dados_Atualizados')
                            
                        st.download_button(
                            label="⬇️ Baixar Planilha Atualizada",
                            data=output.getvalue(),
                            file_name="dados_para_remocao_atualizado.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    else:
                        st.info("Nenhum pedido da lista nova foi encontrado na base completa. Nada foi removido.")
                    
                else:
                    st.error(f"Erro: A coluna '{col_pedido}' não foi encontrada em um dos arquivos. Verifique os nomes das colunas.")

            except Exception as e:
                st.error(f"Ocorreu um erro ao processar: {e}")
    else:
        st.warning("Por favor, anexe os dois arquivos para continuar.")