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
    except:
        st.sidebar.error("Erro na IA.")

# --- MOTOR DE REDAÇÃO IA ---
def redigir_parecer_ia(dados_analise, modelo_name):
    model = genai.GenerativeModel(modelo_name)
    prompt = f"Age como um fiscal em Portugal. Dados: {dados_analise}. Cita DL 73/2009 (RAN). Sem acentos."
    return model.generate_content(prompt).text

# --- FUNÇÃO CARTOGRÁFICA (AJUSTE EPSG:3763 -> EPSG:3857) ---
def gerar_mapa_tecnico(user_gdf):
    plt.switch_backend('Agg')
    fig, ax = plt.subplots(figsize=(10, 8), dpi=150)
    
    # FORÇAR DEFINIÇÃO DO SISTEMA DE ENTRADA (PT-TM06) E CONVERTER PARA WEB MERCATOR
    if user_gdf.crs is None:
        user_gdf.set_crs(epsg=3763, inplace=True)
    
    user_gdf_web = user_gdf.to_crs(epsg=3857)
    
    # 1. Desenhar Servidões com Tramas
    estilos = {
        "REN": {"cor": "#2ecc71", "hatch": "////", "label": "REN"},
        "RAN": {"cor": "#f1c40f", "hatch": "\\\\\\\\", "label": "RAN"}
    }
    legend_elements = []

    # 2. Mapa Base Google Hybrid (URL Direta para evitar erros de biblioteca)
    try:
        cx.add_basemap(ax, source="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", zorder=0)
    except:
        cx.add_basemap(ax, source=cx.providers.Esri.WorldImagery, zorder=0)

    # 3. Cruzamento Geospacial
    for nome, estilo in estilos.items():
        path = f"data/{nome.lower()}_amostra.geojson"
        if os.path.exists(path):
            camada = gpd.read_file(path)
            if camada.crs is None: camada.set_crs(epsg=3763, inplace=True)
            camada_web = camada.to_crs(epsg=3857)
            
            inter = gpd.overlay(camada_web, user_gdf_web, how='intersection')
            if not inter.empty:
                inter.plot(ax=ax, facecolor=estilo["cor"], alpha=0.4, hatch=estilo["hatch"], edgecolor=estilo["cor"], zorder=1)
                legend_elements.append(mpatches.Patch(facecolor=estilo["cor"], alpha=0.6, hatch=estilo["hatch"], label=nome))

    # 4. Desenho do Alvo (Vermelho)
    user_gdf_web.plot(ax=ax, facecolor="none", edgecolor="red", linewidth=3, zorder=2)
    legend_elements.append(Line2D([0], [0], color='red', linewidth=3, label='Alvo (15591 m2)'))

    # Ajuste de Enquadramento
    bounds = user_gdf_web.total_bounds
    ax.set_xlim([bounds[0] - 250, bounds[2] + 250])
    ax.set_ylim([bounds[1] - 250, bounds[3] + 250])
    
    if legend_elements:
        ax.legend(handles=legend_elements, loc='upper right', frameon=True, facecolor='white')
    
    ax.set_axis_off()
    mapa_path = "mapa_coordenadas_fix.png"
    plt.savefig(mapa_path, bbox_inches='tight', pad_inches=0.1)
    plt.close(fig)
    time.sleep(2)
    return mapa_path

# --- GERAÇÃO DE PDF ---
def exportar_pdf(texto_ia, mapa_path):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "RELATORIO DE FISCALIZACAO - COORDINATE FIX", 0, 1, 'C')
    if os.path.exists(mapa_path):
        pdf.image(mapa_path, x=10, y=30, w=190)
        pdf.set_y(180)
    pdf.set_font("Arial", '', 10)
    txt = texto_ia.encode('latin-1', 'ignore').decode('latin-1')
    pdf.multi_cell(0, 6, txt)
    pdf_name = "Relatorio_Final_SIG.pdf"
    pdf.output(pdf_name)
    return pdf_name

# --- INTERFACE ---
st.title("🛡️ Fiscalização SIG (PT-TM06 Fix)")
file = st.sidebar.file_uploader("Upload GeoJSON (PT-TM06)", type=['geojson'])

if file:
    user_gdf = gpd.read_file(file)
    # FORÇAR EPSG:3763 NO CARREGAMENTO
    if user_gdf.crs is None:
        user_gdf.set_crs(epsg=3763, inplace=True)
    
    area_m2 = user_gdf.area.sum()
    
    col_map, col_res = st.columns([2, 1])
    with col_map:
        # Converter para WGS84 para o Leafmap
        user_gdf_4326 = user_gdf.to_crs(epsg=4326)
        centro = user_gdf_4326.geometry.centroid.iloc[0]
        m = leafmap.Map(center=[centro.y, centro.x], zoom=17)
        m.add_tile_layer(url='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', name='Google Sat', attribution='Google')
        m.add_gdf(user_gdf_4326, layer_name="Alvo")
        m.to_streamlit(height=600)
        
    with col_res:
        st.write(f"**Área Detetada:** {area_m2:.2f} m²")
        if api_key and st.button("🤖 Gerar Relatório"):
            with st.spinner('A converter coordenadas e gerar mapa...'):
                parecer = redigir_parecer_ia({"area": area_m2, "regime": "RAN"}, modelo_selecionado)
                mapa = gerar_mapa_tecnico(user_gdf)
                pdf = exportar_pdf(parecer, mapa)
                st.success("Relatório pronto!")
                with open(pdf, "rb") as f:
                    st.download_button("📥 Baixar PDF", f, file_name=pdf)
