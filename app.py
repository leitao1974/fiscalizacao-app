import streamlit as st
import geopandas as gpd
import pandas as pd
import leafmap.foliumap as leafmap
from fpdf import FPDF
import google.generativeai as genai
import matplotlib.pyplot as plt
import contextily as cx
import os

# 1. Configuração da IA (Coloca a tua chave aqui ou nos Secrets do Streamlit)
os.environ["GOOGLE_API_KEY"] = "A_TUA_API_KEY_AQUI"
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

st.set_page_config(layout="wide", page_title="Fiscalização IA SIG", page_icon="🤖")

# --- MOTOR DE ANÁLISE IA ---
def redigir_parecer_ia(dados_analise):
    prompt = f"""
    Age como um fiscal do território em Portugal. Elabora um parecer técnico detalhado com base nestes dados:
    {dados_analise}
    
    O relatório deve ter:
    1. Análise da Ocupação do Solo (compara o oficial com o detetado).
    2. Enquadramento Jurídico (cita DL 73/2009 para RAN e DL 166/2008 para REN).
    3. Conclusão e Medidas de Tutela (Auto de notícia, Embargo, Reposição).
    Usa um tom formal e técnico. Não uses acentos especiais para evitar erros no PDF.
    """
    response = model.generate_content(prompt)
    return response.text

# --- FUNÇÃO CARTOGRÁFICA (BACKEND ROBUSTO) ---
def gerar_mapa_estatico(user_gdf, resultados):
    plt.switch_backend('Agg')
    fig, ax = plt.subplots(figsize=(10, 8))
    user_gdf_web = user_gdf.to_crs(epsg=3857)
    
    # Tentativa de Satélite com fallback para mapa simples se a net falhar
    try:
        cx.add_basemap(ax, source=cx.providers.Esri.WorldImagery, zorder=0)
    except:
        ax.set_facecolor('#e0e0e0') # Fundo cinza se falhar satélite
        
    user_gdf_web.plot(ax=ax, facecolor="red", alpha=0.3, edgecolor="red", linewidth=2)
    ax.set_axis_off()
    
    mapa_path = "mapa_ia.png"
    plt.savefig(mapa_path, bbox_inches='tight')
    plt.close()
    return mapa_path

# --- GERAÇÃO DE PDF ---
def exportar_pdf_ia(texto_ia, mapa_path):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Relatorio de Fiscalizacao IA", 0, 1, 'C')
    
    # Mapa
    if os.path.exists(mapa_path):
        pdf.image(mapa_path, x=10, y=25, w=190)
        pdf.set_y(150)
    
    pdf.set_font("Arial", '', 10)
    pdf.multi_cell(0, 6, texto_ia.encode('latin-1', 'ignore').decode('latin-1'))
    
    pdf_name = "Relatorio_IA_Final.pdf"
    pdf.output(pdf_name)
    return pdf_name

# --- INTERFACE ---
st.title("🛡️ Fiscalização Territorial Inteligente")
file = st.sidebar.file_uploader("Ficheiro SIG (GeoJSON)", type=['geojson'])

if file:
    user_gdf = gpd.read_file(file).to_crs(epsg=3763)
    
    # Simulação de dados para a IA (Baseado no teu relatório anterior)
    area = user_gdf.area.sum()
    dados_para_ia = {
        "area_total": f"{area:.2f} m2",
        "divergencia_cos": "Oficial: Culturas temporarias | Detetado: Aterro e Construcao",
        "sobreposicao_ran": "100% da area em Reserva Agricola Nacional"
    }
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        m = leafmap.Map(google_map="HYBRID")
        m.add_gdf(user_gdf)
        m.zoom_to_gdf(user_gdf)
        m.to_streamlit(height=500)
        
    with col2:
        if st.button("🤖 Gerar Parecer com IA"):
            with st.spinner('A IA está a redigir o relatório...'):
                parecer = redigir_parecer_ia(dados_para_ia)
                mapa = gerar_mapa_estatico(user_gdf, [])
                pdf_final = exportar_pdf_ia(parecer, mapa)
                
                st.markdown(parecer)
                with open(pdf_final, "rb") as f:
                    st.download_button("📥 Baixar Relatório PDF", f, file_name=pdf_final)
