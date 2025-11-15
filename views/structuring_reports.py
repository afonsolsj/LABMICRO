import streamlit as st
from pypdf import PdfReader, PdfWriter
import io
import zipfile

st.title("Dividir PDF e Baixar em ZIP")
uploaded_file = st.file_uploader("Envie um PDF:", type=["pdf"])
MAX_PAGES = 400

if uploaded_file is not None:
    st.info("Lendo PDF...")
    pdf_reader = PdfReader(uploaded_file)
    total_pages = len(pdf_reader.pages)
    st.write(f"📄 Total de páginas: **{total_pages}**")
    part_number = 1
    start_page = 0
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        while start_page < total_pages:
            end_page = min(start_page + MAX_PAGES, total_pages)
            writer = PdfWriter()
            for i in range(start_page, end_page):
                writer.add_page(pdf_reader.pages[i])
            output_pdf = io.BytesIO()
            writer.write(output_pdf)
            output_pdf.seek(0)
            zipf.writestr(f"parte_{part_number}.pdf", output_pdf.getvalue())
            start_page = end_page
            part_number += 1
    zip_buffer.seek(0)
    st.success("PDF dividido e compactado!")
    st.download_button(label="⬇️ Baixar ZIP com todas as partes", data=zip_buffer, file_name="relatorio_dividido.zip", mime="application/zip")