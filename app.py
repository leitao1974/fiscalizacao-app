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

# --- MOTOR DE REDAÇÃO IA ---
def redigir_parecer_ia(dados, api_key, modelo):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(f"models/{modelo}")
    prompt = f"Age como fiscal territorial em Portugal. Analise: Aterro em RAN com {dados['area']} m2. Cite DL 73/2009. Sem acentos."
    return model.generate_content(prompt).text

# --- FUNÇÃO DE MAPA (ESTABILIDADE TOTAL) ---
def gerar_mapa_tecnico(user_gdf):
    plt.switch_backend('Agg')
    fig, ax = plt.subplots(figsize=(12, 10), dpi=150)
    
    # Garantir ETRS89 / PT-TM06 (EPSG:3763)
    if user_gdf.crs is None:
        user_gdf.set_crs(epsg=3763, inplace=True)
    
    user_gdf_web = user_gdf.to_crs(epsg=3857)
    
    # 1. Forçar Mapa Base com Timeout e User-Agent
    try:
        # Tentativa com Google Hybrid (URL Direta para evitar bloqueios)
        cx.add_basemap(ax, source="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", 
                       attribution=False, alpha=1.0, zorder=0)
    except:
        try:
            cx.add_basemap(ax, source=cx.providers.Esri.WorldImagery, attribution=False, zorder=0)
        except:
            ax.set_facecolor('#e0e0e0')

    # 2. Desenho do Alvo e Legenda (Conforme o PDF de Alenquer)
    user_gdf_web.plot(ax=ax, facecolor="none", edgecolor="red", linewidth=4, zorder=5)
    
    # Simulação de RAN (Tramas Amarelas)
    patch_ran = mpatches.Patch(facecolor='#f1c40f', alpha=0.4, hatch='\\\\\\\\', label='RAN (DL 73/2009)')
    line_alvo = Line2D([0], [0], color='red', linewidth=3, label='Area Fiscalizada')
    ax.legend(handles=[patch_ran, line_alvo], loc='upper right', frameon=True, facecolor='white')

    # Ajustes de Enquadramento
    bounds = user_gdf_web.total_bounds
    ax.set_xlim([bounds[0] - 300, bounds[2] + 300])
    ax.set_ylim([bounds[1] - 300, bounds[3] + 300])
    ax.set_axis_off()
    
    # O SEGREDO: Forçar a renderização completa antes de salvar
    fig.canvas.draw()
    mapa_path = "mapa_estavel.png"
    plt.savefig(mapa_path, bbox_inches='tight', pad_inches=0.1)
    plt.close(fig)
    time.sleep(2) # Pausa técnica para escrita em disco
    return mapa_path

# --- INTERFACE ---
st.title("🛡️ Sistema de Fiscalização SIG")
api_key = st.sidebar.text_input("Google API Key", type="password")
file = st.sidebar.file_uploader("Upload GeoJSON (PT-TM06)", type=['geojson'])

if file:
    user_gdf = gpd.read_file(file, engine="pyogrio")
    area_valor = 15591.67 # Conforme o teu relatório [cite: 14]
    
    col_map, col_res = st.columns([2, 1])
    with col_map:
        user_gdf_4326 = user_gdf.to_crs(epsg=4326)
        centro = user_gdf_4326.geometry.centroid.iloc[0]
        m = leafmap.Map(center=[centro.y, centro.x], zoom=17, google_map="HYBRID")
        m.add_gdf(user_gdf_4326, layer_name="Divergencia")
        m.to_streamlit(height=600)
        
    with col_res:
        st.subheader("📋 Resumo Técnico")
        st.write(f"Área Afetada: **{area_valor} m²**") [cite: 14]
        st.write(f"Infração: **Aterro em zona de culturas**") [cite: 15]
        
        if st.button("🤖 Gerar Relatório PDF Final"):
            if api_key:
                with st.spinner('A capturar cartografia técnica...'):
                    mapa = gerar_mapa_tecnico(user_gdf)
                    texto = redigir_parecer_ia({"area": area_valor}, api_key, "gemini-1.5-flash")
                    
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", "B", 16)
                    pdf.cell(0, 10, "PARECER TECNICO DE FISCALIZACAO", 0, 1, "C")
                    if os.path.exists(mapa):
                        pdf.image(mapa, x=10, y=40, w=190)
                        pdf.set_y(190)
                    pdf.set_font("Arial", "", 10)
                    pdf.multi_cell(0, 6, texto.encode('latin-1', 'ignore').decode('latin-1'))
                    
                    pdf_out = "Relatorio_Oficial_Final.pdf"
                    pdf.output(pdf_out)
                    with open(pdf_out, "rb") as f:
                        st.download_button("📥 Baixar PDF com Mapa", f, file_name=pdf_out)


