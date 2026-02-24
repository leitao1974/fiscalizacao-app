import streamlit as st
import geopandas as gpd
import pandas as pd
import leafmap.foliumap as leafmap
from fpdf import FPDF
import google.generativeai as genai
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
import contextily as cx
import os
import time
from datetime import date

# 1. Configuração de Interface
st.set_page_config(layout="wide", page_title="Fiscalização IA SIG", page_icon="🛡️")

# --- MOTOR IA DINÂMICO ---
st.sidebar.title("🔑 Configuração IA")
api_key = st.sidebar.text_input("Insere a tua Google API Key", type="password")

modelo_selecionado = None
if api_key:
    try:
        genai.configure(api_key=api_key)
        models = genai.list_models()
        available_models = [m.name.replace('models/', '') for m in models 
                            if 'generateContent' in m.supported_generation_methods]
        if available_models:
            modelo_selecionado = st.sidebar.selectbox("Escolhe o Modelo Gemini", options=available_models)
    except:
        st.sidebar.error("Verifica a tua API Key.")

# --- FUNÇÃO CARTOGRÁFICA (A SOLUÇÃO PARA O MAPA BRANCO) ---
def gerar_mapa_tecnico(user_gdf):
    plt.switch_backend('Agg')
    fig, ax = plt.subplots(figsize=(10, 8), dpi=150)
    
    # Forçar ETRS89 / PT-TM06 (EPSG:3763)
    if user_gdf.crs is None:
        user_gdf.set_crs(epsg=3763, inplace=True)
    
    # Converter para Web Mercator (EPSG:3857) para o satélite
    user_gdf_web = user_gdf.to_crs(epsg=3857)
    
    # 1. Tentar Mapa Base com URL direta (evita bloqueios de sistema)
    try:
        cx.add_basemap(ax, source="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", zorder=0)
    except:
        try:
            cx.add_basemap(ax, source=cx.providers.Esri.WorldImagery, zorder=0)
        except:
            ax.set_facecolor('#dcdcdc')

    # 2. Desenho do Alvo e Legenda Técnica
    user_gdf_web.plot(ax=ax, facecolor="red", alpha=0.3, edgecolor="red", linewidth=3, zorder=5)
    
    patch_ran = mpatches.Patch(facecolor='#f1c40f', alpha=0.4, hatch='\\\\\\\\', label='Zona RAN (DL 73/2009)')
    ax.legend(handles=[patch_ran], loc='upper right', frameon=True, facecolor='white')

    # Enquadramento (300m de margem)
    bounds = user_gdf_web.total_bounds
    ax.set_xlim([bounds[0] - 300, bounds[2] + 300])
    ax.set_ylim([bounds[1] - 300, bounds[3] + 300])
    ax.set_axis_off()
    
    # FORÇAR RENDERIZAÇÃO ANTES DE SALVAR
    mapa_path = "mapa_fiscalizacao_final.png"
    fig.canvas.draw()
    plt.savefig(mapa_path, bbox_inches='tight', pad_inches=0.1)
    plt.close(fig)
    time.sleep(1)
    return mapa_path

# --- INTERFACE PRINCIPAL ---
st.title("🛡️ Fiscalização SIG: Relatório de Divergência")
file = st.sidebar.file_uploader("Upload GeoJSON (PT-TM06)", type=['geojson'])

if file:
    # Usamos pyogrio para evitar o erro de instalação dpkg do sistema
    user_gdf = gpd.read_file(file, engine="pyogrio")
    if user_gdf.crs is None: user_gdf.set_crs(epsg=3763, inplace=True)
    
    # Área exata do teu relatório: 15591.67 m2
    area_valor = user_gdf.area.sum() 
    
    col1, col2 = st.columns([2, 1])
    with col1:
        # Visualização interativa no ecrã
        user_gdf_4326 = user_gdf.to_crs(epsg=4326)
        centro = user_gdf_4326.geometry.centroid.iloc[0]
        m = leafmap.Map(center=[centro.y, centro.x], zoom=17, google_map="HYBRID")
        m.add_gdf(user_gdf_4326)
        m.to_streamlit(height=550)
        
    with col2:
        st.subheader("📋 Resumo da Ocorrência")
        st.write(f"Área Afetada: **{area_valor:.2f} m²**")
        st.write(f"Natureza: **Aterro detetado em zona RAN**")
        
        if st.button("🤖 Gerar Relatório PDF"):
            if api_key and modelo_selecionado:
                with st.spinner('A capturar satélite e redigir parecer...'):
                    mapa_img = gerar_mapa_tecnico(user_gdf)
                    
                    # Motor de IA Gemini
                    model = genai.GenerativeModel(f"models/{modelo_selecionado}")
                    prompt = f"Escreve um parecer tecnico. Area {area_valor:.2f} m2 em RAN (DL 73/2009). Aterro detetado. Sem acentos."
                    texto = model.generate_content(prompt).text
                    
                    # Geração do PDF
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", "B", 16)
                    pdf.cell(0, 10, "PARECER TECNICO DE FISCALIZACAO", 0, 1, "C")
                    
                    if os.path.exists(mapa_img):
                        pdf.image(mapa_img, x=10, y=35, w=190)
                        pdf.set_y(190)
                    
                    pdf.set_font("Arial", "", 10)
                    pdf.multi_cell(0, 6, texto.encode('latin-1', 'ignore').decode('latin-1'))
                    
                    pdf_out = "Relatorio_Fiscalizacao_Final.pdf"
                    pdf.output(pdf_out)
                    with open(pdf_out, "rb") as f:
                        st.download_button("📥 Baixar PDF com Mapa", f, file_name=pdf_out)
            else:
                st.warning("Configura a IA na barra lateral.")
