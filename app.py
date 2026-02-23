import streamlit as st
import geopandas as gpd
import pandas as pd
import leafmap.foliumap as leafmap
from fpdf import FPDF
import google.generativeai as genai
import matplotlib.pyplot as plt
import contextily as cx
import os
from datetime import date

# 1. Configuração da Página
st.set_page_config(layout="wide", page_title="Fiscalização IA SIG", page_icon="🤖")

# --- SIDEBAR: CONFIGURAÇÃO DA IA ---
st.sidebar.title("🔑 Configuração IA")
api_key = st.sidebar.text_input("Insere a tua Google API Key", type="password")

if api_key:
    try:
        genai.configure(api_key=api_key)
        available_models = [m.name.replace('models/', '') for m in genai.list_models() 
                            if 'generateContent' in m.supported_generation_methods]
        modelo_selecionado = st.sidebar.selectbox("Escolhe o Modelo Gemini", options=available_models, index=0)
    except Exception as e:
        st.sidebar.error(f"Erro na IA: {e}")

# --- MOTOR DE REDAÇÃO IA ---
def redigir_parecer_ia(dados_analise, modelo_name):
    model = genai.GenerativeModel(modelo_name)
    prompt = f"""
    Age como um fiscal do territorio em Portugal. Escreve um parecer tecnico formal:
    Dados: {dados_analise}
    Cita: DL 73/2009 (RAN) e DL 166/2008 (REN).
    Analise: Compara COS2023 (Cultura) com Realidade (Aterro/Construcao).
    IMPORTANTE: Nao uses acentos ou cedilhas para evitar erros no PDF.
    """
    return model.generate_content(prompt).text

# --- FUNÇÃO CARTOGRÁFICA (GOOGLE MAPS) ---
def gerar_mapa_estatico(user_gdf):
    plt.switch_backend('Agg')
    fig, ax = plt.subplots(figsize=(10, 8))
    user_gdf_web = user_gdf.to_crs(epsg=3857)
    
    # Google Satellite Tiles via URL (Método mais robusto)
    google_url = 'https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}'
    try:
        cx.add_basemap(ax, source=google_url, zorder=0)
    except:
        cx.add_basemap(ax, source=cx.providers.Esri.WorldImagery, zorder=0)
        
    user_gdf_web.plot(ax=ax, facecolor="red", alpha=0.3, edgecolor="red", linewidth=2, zorder=1)
    
    bounds = user_gdf_web.total_bounds
    ax.set_xlim([bounds[0] - 150, bounds[2] + 150])
    ax.set_ylim([bounds[1] - 150, bounds[3] + 150])
    ax.set_axis_off()
    
    mapa_path = "mapa_export.png"
    plt.savefig(mapa_path, bbox_inches='tight', pad_inches=0.1)
    plt.close(fig)
    return mapa_path

# --- GERAÇÃO DE PDF ---
def exportar_pdf(texto_ia, mapa_path):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Relatorio de Fiscalizacao (Google Satellite + IA)", 0, 1, 'C')
    pdf.ln(5)
    
    if os.path.exists(mapa_path):
        pdf.image(mapa_path, x=15, y=None, w=180)
        pdf.ln(5)
    
    pdf.set_font("Arial", '', 10)
    txt_limpo = texto_ia.encode('latin-1', 'ignore').decode('latin-1')
    pdf.multi_cell(0, 6, txt_limpo)
    
    pdf_name = "Relatorio_IA_Google.pdf"
    pdf.output(pdf_name)
    return pdf_name

# --- INTERFACE ---
st.title("🛡️ Sistema de Fiscalização SIG")
file = st.sidebar.file_uploader("Upload GeoJSON", type=['geojson'])

if file:
    user_gdf = gpd.read_file(file).to_crs(epsg=3763)
    area = user_gdf.area.sum()
    
    col_map, col_res = st.columns([2, 1])
    
    with col_map:
        user_gdf_4326 = user_gdf.to_crs(epsg=4326)
        centro = user_gdf_4326.geometry.centroid.iloc[0]
        
        # Correção do Erro: Usar add_tile_layer para o Google Maps
        m = leafmap.Map(center=[centro.y, centro.x], zoom=17)
        m.add_tile_layer(
            url='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
            name='Google Satellite',
            attribution='Google'
        )
        m.add_gdf(user_gdf, layer_name="Alvo")
        m.to_streamlit(height=600)
        
    with col_res:
        st.subheader("📋 Resumo")
        st.write(f"**Area:** {area:.2f} m²")
        
        if api_key:
            if st.button("🤖 Gerar Relatório IA"):
                with st.spinner('A redigir...'):
                    dados_ia = {
                        "area": f"{area:.2f} m2",
                        "divergencia": "Aterro detetado em zona de culturas",
                        "regime": "RAN"
                    }
                    texto = redigir_parecer_ia(dados_ia, modelo_selecionado)
                    mapa = gerar_mapa_estatico(user_gdf)
                    pdf = exportar_pdf(texto, mapa)
                    
                    st.success("Relatório pronto!")
                    with open(pdf, "rb") as f:
                        st.download_button("📥 Baixar PDF", f, file_name=pdf)
                    st.write(texto)
