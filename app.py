import streamlit as st
import geopandas as gpd
import pandas as pd
import leafmap.foliumap as leafmap
from fpdf import FPDF
import google.generativeai as genai
import matplotlib.pyplot as plt
import contextily as cx
import os
import time

# 1. Configuração Base
st.set_page_config(layout="wide", page_title="Fiscalização SIG")

# --- MOTOR IA ---
def redigir_parecer_ia(area, api_key, modelo):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(f"models/{modelo}")
    prompt = f"Escreve um parecer técnico de fiscalização para uma área de {area} m2 em zona RAN (DL 73/2009) onde foi detetado um aterro ilegal. Não uses acentos."
    return model.generate_content(prompt).text

# --- CARTOGRAFIA (FIX PARA MAPA BASE) ---
def gerar_mapa_final(user_gdf):
    plt.switch_backend('Agg')
    fig, ax = plt.subplots(figsize=(10, 8), dpi=150)
    
    # Garantir coordenadas PT-TM06 (EPSG:3763)
    if user_gdf.crs is None:
        user_gdf.set_crs(epsg=3763, inplace=True)
    
    # Reprojeção para Web Mercator (Necessário para o Satélite)
    user_gdf_web = user_gdf.to_crs(epsg=3857)
    
    # Desenho do Alvo
    user_gdf_web.plot(ax=ax, facecolor="red", alpha=0.3, edgecolor="red", linewidth=3, zorder=5)

    # Forçar download do Mapa Base
    try:
        # Google Hybrid via URL direta
        cx.add_basemap(ax, source="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", attribution=False)
    except:
        cx.add_basemap(ax, source=cx.providers.Esri.WorldImagery)

    ax.set_axis_off()
    
    mapa_path = "mapa_saida.png"
    # O SEGREDO: Forçar o desenho da moldura antes de guardar
    fig.canvas.draw()
    plt.savefig(mapa_path, bbox_inches='tight', pad_inches=0.1)
    plt.close(fig)
    return mapa_path

# --- INTERFACE ---
st.title("🛡️ Fiscalização SIG: Relatório Técnico")
api_key = st.sidebar.text_input("Google API Key", type="password")
file = st.sidebar.file_uploader("Upload GeoJSON (PT-TM06)", type=['geojson'])

if file:
    # Motor pyogrio evita dependências de sistema
    user_gdf = gpd.read_file(file, engine="pyogrio")
    area_valor = 15591.67 # Valor fixo do relatório carregado

    col1, col2 = st.columns([2, 1])
    with col1:
        user_gdf_4326 = user_gdf.to_crs(epsg=4326)
        centro = user_gdf_4326.geometry.centroid.iloc[0]
        m = leafmap.Map(center=[centro.y, centro.x], zoom=17, google_map="HYBRID")
        m.add_gdf(user_gdf_4326)
        m.to_streamlit(height=500)

    with col2:
        if st.button("🤖 Gerar Relatório PDF"):
            if api_key:
                with st.spinner('A capturar satélite e IA...'):
                    mapa_img = gerar_mapa_final(user_gdf)
                    texto = redigir_parecer_ia(area_valor, api_key, "gemini-1.5-flash")
                    
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", "B", 16)
                    pdf.cell(0, 10, "PARECER TECNICO FORMAL", 0, 1, "C")
                    
                    if os.path.exists(mapa_img):
                        pdf.image(mapa_img, x=10, y=35, w=190)
                    
                    pdf_out = "Relatorio_Fiscalizacao.pdf"
                    pdf.output(pdf_out)
                    with open(pdf_out, "rb") as f:
                        st.download_button("📥 Baixar PDF", f, file_name=pdf_out)


