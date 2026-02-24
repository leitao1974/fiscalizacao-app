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

# 1. Configuração
st.set_page_config(layout="wide", page_title="Fiscalização IA SIG", page_icon="🛡️")

# --- MOTOR DE REDAÇÃO IA (FIX: NOMES DE MODELO) ---
def redigir_parecer_ia(dados, api_key, modelo):
    if not api_key: return "API Key em falta."
    genai.configure(api_key=api_key)
    
    # Adiciona o prefixo 'models/' se não estiver presente
    nome_modelo = modelo if modelo.startswith('models/') else f"models/{modelo}"
    
    try:
        model = genai.GenerativeModel(nome_modelo)
        prompt = f"Age como fiscal em Portugal. Area: {dados['area']}. Infracao: Aterro em RAN (DL 73/2009). Sem acentos."
        return model.generate_content(prompt).text
    except Exception as e:
        return f"Erro ao contactar o modelo {nome_modelo}: {str(e)}"

# --- FUNÇÃO DE MAPA (FIX: FORÇAR RENDERIZAÇÃO DE TILES) ---
def gerar_mapa_tecnico(user_gdf):
    plt.switch_backend('Agg')
    fig, ax = plt.subplots(figsize=(10, 8), dpi=150)
    
    # Garantir ETRS89 / PT-TM06 (EPSG:3763)
    if user_gdf.crs is None:
        user_gdf.set_crs(epsg=3763, inplace=True)
    
    user_gdf_web = user_gdf.to_crs(epsg=3857)
    
    # TENTATIVA ROBUSTA DE MAPA BASE
    try:
        # Usamos o ESRI como primário e forçamos o download dos tiles
        cx.add_basemap(ax, source=cx.providers.Esri.WorldImagery, attribution=False)
    except:
        try:
            # Fallback para Google com URL direta
            cx.add_basemap(ax, source="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", attribution=False)
        except:
            ax.set_facecolor('#e0e0e0')

    # Desenho das Servidões e Alvo
    user_gdf_web.plot(ax=ax, facecolor="none", edgecolor="red", linewidth=4, zorder=10)

    # Definir limites antes de desenhar hachuras para otimizar memória
    bounds = user_gdf_web.total_bounds
    ax.set_xlim([bounds[0] - 300, bounds[2] + 300])
    ax.set_ylim([bounds[1] - 300, bounds[3] + 300])
    ax.set_axis_off()
    
    mapa_path = "mapa_final.png"
    # O segredo: renderizar o mapa antes de guardar
    fig.canvas.draw()
    plt.savefig(mapa_path, bbox_inches='tight', pad_inches=0.1)
    plt.close(fig)
    return mapa_path

# --- INTERFACE ---
st.title("🛡️ Fiscalização SIG Territorial")
api_key = st.sidebar.text_input("Google API Key", type="password")
file = st.sidebar.file_uploader("GeoJSON (PT-TM06)", type=['geojson'])

if file:
    user_gdf = gpd.read_file(file)
    if user_gdf.crs is None: user_gdf.set_crs(epsg=3763, inplace=True)
    
    area_m2 = user_gdf.area.sum()
    
    col_map, col_res = st.columns([2, 1])
    with col_map:
        user_gdf_4326 = user_gdf.to_crs(epsg=4326)
        centro = user_gdf_4326.geometry.centroid.iloc[0]
        m = leafmap.Map(center=[centro.y, centro.x], zoom=17, google_map="HYBRID")
        m.add_gdf(user_gdf_4326, layer_name="Alvo")
        m.to_streamlit(height=500)
        
    with col_res:
        st.write(f"Área: **{area_m2:.2f} m²**")
        
        if st.button("🤖 Gerar Relatório PDF"):
            if api_key:
                with st.spinner('A processar IA e Cartografia...'):
                    # Corrigido: Passamos o nome simples, a função trata o prefixo
                    parecer = redigir_parecer_ia({"area": area_m2}, api_key, "gemini-1.5-flash")
                    mapa_img = gerar_mapa_tecnico(user_gdf)
                    
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", 'B', 16)
                    pdf.cell(0, 10, "RELATORIO DE FISCALIZACAO", 0, 1, 'C')
                    if os.path.exists(mapa_img):
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
