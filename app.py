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

# 1. Configuracao de Interface
st.set_page_config(layout="wide", page_title="Fiscalizacao IA SIG", page_icon="🛡️")

# --- SIDEBAR: CONFIGURACAO DINAMICA DA IA ---
st.sidebar.title("🔑 Configuracao IA")
api_key = st.sidebar.text_input("Insere a tua Google API Key", type="password")

modelo_selecionado = None
if api_key:
    try:
        genai.configure(api_key=api_key)
        models = genai.list_models()
        available_models = [m.name.replace('models/', '') for m in models 
                            if 'generateContent' in m.supported_generation_methods]
        if available_models:
            modelo_selecionado = st.sidebar.selectbox("Modelos Disponiveis", options=available_models)
    except:
        st.sidebar.error("Erro ao listar modelos.")

# --- MOTOR DE REDACAO IA ---
def redigir_parecer_ia(dados, api_key, modelo):
    model = genai.GenerativeModel(f"models/{modelo}")
    prompt = f"""
    Age como um fiscal do territorio em Portugal. Redigi um parecer tecnico formal:
    DADOS: Area de {dados['area']} m2.
    DIVERGENCIA: Ocupacao por aterro em zona de Reserva Agricola Nacional (RAN).
    LEGISLACAO: Cita o Decreto-Lei n.o 73/2009 (RAN).
    IMPORTANTE: Nao uses acentos ou cedilhas para evitar erros no PDF.
    """
    return model.generate_content(prompt).text

# --- FUNCAO DE MAPA (RESOLUCAO DE COORDENADAS E FUNDO) ---
def gerar_mapa_tecnico(user_gdf):
    plt.switch_backend('Agg')
    fig, ax = plt.subplots(figsize=(12, 10), dpi=150)
    
    # Forcar ETRS89 / PT-TM06 (EPSG:3763)
    if user_gdf.crs is None:
        user_gdf.set_crs(epsg=3763, inplace=True)
    
    # Converter para Web Mercator (EPSG:3857) para o mapa base
    user_gdf_web = user_gdf.to_crs(epsg=3857)
    
    # Renderizacao do Mapa Base (Google Hybrid)
    try:
        cx.add_basemap(ax, source="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", 
                       attribution=False, alpha=1.0)
    except:
        cx.add_basemap(ax, source=cx.providers.Esri.WorldImagery, attribution=False)

    # Estilos de Servidões (RAN / REN)
    estilos = {
        "REN": {"cor": "#2ecc71", "hatch": "////", "label": "REN"},
        "RAN": {"cor": "#f1c40f", "hatch": "\\\\\\\\", "label": "RAN"}
    }
    legend_elements = []

    for nome, estilo in estilos.items():
        path = f"data/{nome.lower()}_amostra.geojson"
        if os.path.exists(path):
            camada = gpd.read_file(path).to_crs(epsg=3857)
            inter = gpd.overlay(camada, user_gdf_web, how='intersection')
            if not inter.empty:
                inter.plot(ax=ax, facecolor=estilo["cor"], alpha=0.4, 
                           hatch=estilo["hatch"], edgecolor=estilo["cor"], zorder=1)
                legend_elements.append(mpatches.Patch(facecolor=estilo["cor"], alpha=0.6, 
                                                      hatch=estilo["hatch"], label=nome))

    # Desenho do Alvo (Linha Vermelha)
    user_gdf_web.plot(ax=ax, facecolor="none", edgecolor="red", linewidth=3, zorder=5)
    legend_elements.append(Line2D([0], [0], color='red', linewidth=3, label='Alvo'))

    # Zoom de Seguranca (350m)
    bounds = user_gdf_web.total_bounds
    ax.set_xlim([bounds[0] - 350, bounds[2] + 350])
    ax.set_ylim([bounds[1] - 350, bounds[3] + 350])
    
    if legend_elements:
        ax.legend(handles=legend_elements, loc='upper right', frameon=True, facecolor='white')
    
    ax.set_axis_off()
    
    mapa_path = "mapa_export_final.png"
    fig.canvas.draw()
    plt.savefig(mapa_path, bbox_inches='tight', pad_inches=0.1)
    plt.close(fig)
    time.sleep(2)
    return mapa_path

# --- INTERFACE ---
st.title("🛡️ Fiscalizacao SIG Territorial")
file = st.sidebar.file_uploader("Upload GeoJSON (PT-TM06)", type=['geojson'])

if file:
    user_gdf = gpd.read_file(file, engine="pyogrio")
    if user_gdf.crs is None: user_gdf.set_crs(epsg=3763, inplace=True)
    
    area_m2 = 15591.67 # Valor fixo do parecer tecnico
    
    col_map, col_res = st.columns([2, 1])
    with col_map:
        user_gdf_4326 = user_gdf.to_crs(epsg=4326)
        centro = user_gdf_4326.geometry.centroid.iloc[0]
        m = leafmap.Map(center=[centro.y, centro.x], zoom=17, google_map="HYBRID")
        m.add_gdf(user_gdf_4326, layer_name="Divergencia")
        m.to_streamlit(height=600)
        
    with col_res:
        st.subheader("📋 Painel")
        st.write(f"Area Afetada: **{area_m2} m2**")
        
        if st.button("🤖 Gerar Relatorio PDF"):
            if api_key and modelo_selecionado:
                with st.spinner('A gerar relatorio...'):
                    texto = redigir_parecer_ia({"area": area_m2}, api_key, modelo_selecionado)
                    mapa = gerar_mapa_tecnico(user_gdf)
                    
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", 'B', 16)
                    pdf.cell(0, 10, "PARECER TECNICO DE FISCALIZACAO", 0, 1, 'C')
                    
                    if os.path.exists(mapa):
                        pdf.image(mapa, x=10, y=35, w=190)
                        pdf.set_y(185)
                    
                    pdf.set_font("Arial", '', 10)
                    pdf.multi_cell(0, 6, texto.encode('latin-1', 'ignore').decode('latin-1'))
                    
                    pdf_out = "Relatorio_Fiscalizacao.pdf"
                    pdf.output(pdf_out)
                    with open(pdf_out, "rb") as f:
                        st.download_button("📥 Baixar PDF", f, file_name=pdf_out)
            else:
                st.error("Configura a IA na barra lateral.")

