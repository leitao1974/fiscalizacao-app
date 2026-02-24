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

# 1. Configuração da Página
st.set_page_config(layout="wide", page_title="Fiscalização IA SIG", page_icon="🛡️")

# --- SIDEBAR: GESTÃO DINÂMICA DE MODELOS ---
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
        st.sidebar.error("Erro ao validar API Key.")

# --- MOTOR DE REDAÇÃO IA ---
def redigir_parecer_ia(dados, api_key, modelo):
    model = genai.GenerativeModel(f"models/{modelo}")
    prompt = f"""
    Age como um fiscal do territorio em Portugal. Redigi um parecer tecnico formal:
    DADOS: Area de {dados['area']} m2.
    DIVERGENCIA: Aterro detetado em zona de culturas (RAN).
    LEGISLACAO: Cita o Decreto-Lei n.o 73/2009.
    IMPORTANTE: Nao uses acentos ou cedilhas no texto para evitar erros no PDF.
    """
    return model.generate_content(prompt).text

# --- FUNÇÃO CARTOGRÁFICA (A SOLUÇÃO PARA O MAPA BRANCO) ---
def gerar_mapa_tecnico(user_gdf):
    # Forçar backend não interativo
    plt.switch_backend('Agg')
    fig, ax = plt.subplots(figsize=(10, 8), dpi=150)
    
    # Garantir Projeção PT-TM06 -> Web Mercator
    if user_gdf.crs is None:
        user_gdf.set_crs(epsg=3763, inplace=True)
    user_gdf_web = user_gdf.to_crs(epsg=3857)
    
    # 1. Tentar Mapa Base (Google ou Esri)
    try:
        # Usamos uma URL direta para evitar bloqueios de User-Agent
        cx.add_basemap(ax, source="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", zorder=0)
    except:
        cx.add_basemap(ax, source=cx.providers.Esri.WorldImagery, zorder=0)

    # 2. Desenho do Alvo (Vermelho)
    user_gdf_web.plot(ax=ax, facecolor="none", edgecolor="red", linewidth=3, zorder=5)
    
    # 3. Legenda Técnica (conforme o teu PDF)
    patch_ran = mpatches.Patch(facecolor='#f1c40f', alpha=0.4, hatch='\\\\\\\\', label='RAN (DL 73/2009)')
    line_alvo = Line2D([0], [0], color='red', linewidth=2, label='Area Fiscalizada')
    ax.legend(handles=[patch_ran, line_alvo], loc='upper right', frameon=True, facecolor='white')

    # Zoom e Limites
    bounds = user_gdf_web.total_bounds
    ax.set_xlim([bounds[0] - 250, bounds[2] + 250])
    ax.set_ylim([bounds[1] - 250, bounds[3] + 250])
    ax.set_axis_off()
    
    # --- O PASSO CRÍTICO: FORÇAR RENDERIZAÇÃO ---
    mapa_path = "mapa_renderizado.png"
    fig.canvas.draw() # Desenha o mapa na memória
    plt.savefig(mapa_path, bbox_inches='tight', pad_inches=0.1)
    plt.close(fig)
    time.sleep(1) # Aguarda escrita do ficheiro
    return mapa_path

# --- INTERFACE PRINCIPAL ---
st.title("🛡️ Fiscalização SIG: Relatórios Automáticos")
file = st.sidebar.file_uploader("Upload GeoJSON (PT-TM06)", type=['geojson'])

if file:
    # Usamos o motor pyogrio para estabilidade
    user_gdf = gpd.read_file(file, engine="pyogrio")
    if user_gdf.crs is None: user_gdf.set_crs(epsg=3763, inplace=True)
    
    area_valor = user_gdf.area.sum()
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Mapa Interativo WGS84
        user_gdf_4326 = user_gdf.to_crs(epsg=4326)
        centro = user_gdf_4326.geometry.centroid.iloc[0]
        m = leafmap.Map(center=[centro.y, centro.x], zoom=17, google_map="HYBRID")
        m.add_gdf(user_gdf_4326, layer_name="Alvo")
        m.to_streamlit(height=600)
        
    with col2:
        st.subheader("📋 Dados da Ocorrência")
        st.write(f"Área Calculada: **{area_valor:.2f} m²**")
        st.info("Divergência: Solo RAN vs Aterro de Materiais")
        
        if st.button("🤖 Gerar Relatório PDF Final"):
            if api_key and modelo_selecionado:
                with st.spinner('A capturar cartografia e redigir parecer...'):
                    mapa_img = gerar_mapa_tecnico(user_gdf)
                    texto = redigir_parecer_ia({"area": f"{area_valor:.2f}"}, api_key, modelo_selecionado)
                    
                    # Gerar PDF
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", "B", 16)
                    pdf.cell(0, 10, "PARECER TECNICO DE FISCALIZACAO", 0, 1, "C")
                    
                    if os.path.exists(mapa_img):
                        pdf.image(mapa_img, x=10, y=35, w=190)
                        pdf.set_y(185)
                    
                    pdf.set_font("Arial", "", 10)
                    pdf.multi_cell(0, 6, texto.encode('latin-1', 'ignore').decode('latin-1'))
                    
                    pdf_path = "Relatorio_Final_Consolidado.pdf"
                    pdf.output(pdf_path)
                    
                    with open(pdf_path, "rb") as f:
                        st.download_button("📥 Baixar PDF Oficial", f, file_name=pdf_path)
            else:
                st.warning("Verifica a configuração da IA na barra lateral.")



