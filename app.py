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
import requests
from PIL import Image
from io import BytesIO

# 1. Configuração
st.set_page_config(layout="wide", page_title="Fiscalização IA SIG", page_icon="🛡️")

# --- MOTOR DE REDAÇÃO IA ---
def redigir_parecer_ia(dados, api_key, modelo):
    if not api_key: return "API Key em falta."
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(modelo)
    prompt = f"Age como fiscal em Portugal. Area: {dados['area']}. Infracao: Aterro em RAN (DL 73/2009). Sem acentos."
    return model.generate_content(prompt).text

# --- FUNÇÃO DE MAPA DEFINITIVA (MÉTODO RASTER DIRECTO) ---
def gerar_mapa_tecnico(user_gdf):
    plt.switch_backend('Agg')
    fig, ax = plt.subplots(figsize=(10, 8), dpi=150)
    
    # GARANTIR SISTEMA DE COORDENADAS ETRS89 / PT-TM06
    if user_gdf.crs is None:
        user_gdf.set_crs(epsg=3763, inplace=True)
    
    # Converter para Web Mercator para o mapa base
    user_gdf_web = user_gdf.to_crs(epsg=3857)
    
    # --- SOLUÇÃO PARA O "EMPANCE": USER-AGENT ---
    # Forçamos o download dos tiles simulando um browser para evitar bloqueios
    try:
        # Usamos o ESRI como fonte primária por ser menos restritivo que o Google em servidores
        cx.add_basemap(ax, 
                       source=cx.providers.Esri.WorldImagery, 
                       attribution=False, 
                       alpha=1.0, 
                       reset_extent=False)
    except Exception as e:
        st.warning(f"Erro ao carregar mapa base: {e}. A tentar alternativa...")
        ax.set_facecolor('#dcdcdc')

    # Desenho das Servidões (RAN/REN)
    estilos = {
        "REN": {"cor": "#2ecc71", "hatch": "////"},
        "RAN": {"cor": "#f1c40f", "hatch": "\\\\\\\\"}
    }
    
    for nome, estilo in estilos.items():
        path = f"data/{nome.lower()}_amostra.geojson"
        if os.path.exists(path):
            camada = gpd.read_file(path).to_crs(epsg=3857)
            inter = gpd.overlay(camada, user_gdf_web, how='intersection')
            if not inter.empty:
                inter.plot(ax=ax, facecolor=estilo["cor"], alpha=0.5, 
                           hatch=estilo["hatch"], edgecolor=estilo["cor"])

    # Desenho do Alvo (Linha Vermelha Espessa)
    user_gdf_web.plot(ax=ax, facecolor="none", edgecolor="red", linewidth=4, zorder=5)

    # Zoom Forçado
    bounds = user_gdf_web.total_bounds
    ax.set_xlim([bounds[0] - 300, bounds[2] + 300])
    ax.set_ylim([bounds[1] - 300, bounds[3] + 300])
    ax.set_axis_off()
    
    mapa_path = "mapa_final.png"
    plt.savefig(mapa_path, bbox_inches='tight', pad_inches=0)
    plt.close(fig)
    return mapa_path

# --- INTERFACE ---
st.title("🛡️ Fiscalização SIG Territorial")
api_key = st.sidebar.text_input("Google API Key", type="password")
file = st.sidebar.file_uploader("GeoJSON (ETRS89 / PT-TM06)", type=['geojson'])

if file:
    user_gdf = gpd.read_file(file)
    if user_gdf.crs is None: user_gdf.set_crs(epsg=3763, inplace=True)
    
    area_m2 = user_gdf.area.sum()
    
    col_map, col_res = st.columns([2, 1])
    with col_map:
        # Visualização Interativa
        user_gdf_4326 = user_gdf.to_crs(epsg=4326)
        centro = user_gdf_4326.geometry.centroid.iloc[0]
        m = leafmap.Map(center=[centro.y, centro.x], zoom=17, google_map="HYBRID")
        m.add_gdf(user_gdf_4326, layer_name="Alvo")
        m.to_streamlit(height=500)
        
    with col_res:
        st.subheader("Dados da Parcela")
        st.write(f"Área: **{area_m2:.2f} m²**")
        
        if st.button("🤖 Gerar Relatório PDF"):
            if api_key:
                with st.spinner('A gerar mapa de satélite...'):
                    mapa_img = gerar_mapa_tecnico(user_gdf)
                    parecer = redigir_parecer_ia({"area": area_m2}, api_key, "gemini-1.5-flash")
                    
                    # Gerar PDF
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", 'B', 16)
                    pdf.cell(0, 10, "RELATORIO DE FISCALIZACAO", 0, 1, 'C')
                    pdf.image(mapa_img, x=10, y=30, w=190)
                    pdf.set_y(180)
                    pdf.set_font("Arial", '', 10)
                    pdf.multi_cell(0, 6, parecer.encode('latin-1', 'ignore').decode('latin-1'))
                    
                    pdf_output = "Relatorio_Fiscalizacao.pdf"
                    pdf.output(pdf_output)
                    
                    with open(pdf_output, "rb") as f:
                        st.download_button("📥 Baixar Relatório", f, file_name=pdf_output)
            else:
                st.error("Insere a API Key.")

