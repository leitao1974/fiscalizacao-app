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
st.set_page_config(layout="wide", page_title="Fiscalização Técnica SIG", page_icon="🛡️")

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
        st.sidebar.error("Erro na ligação à IA.")

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

# --- FUNÇÃO CARTOGRÁFICA (TRAMAS, CORES E SATÉLITE) ---
def gerar_mapa_tecnico(user_gdf):
    plt.switch_backend('Agg')
    fig, ax = plt.subplots(figsize=(12, 10), dpi=100)
    user_gdf_web = user_gdf.to_crs(epsg=3857)
    
    # 1. Estilos por Servidão
    estilos = {
        "REN": {"cor": "#2ecc71", "hatch": "////", "label": "REN"},
        "RAN": {"cor": "#f1c40f", "hatch": "\\\\\\\\", "label": "RAN"}
    }
    legend_elements = []

    # 2. Carregamento do Mapa Base com Retry
    mapa_sucesso = False
    fontes = [
        "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", # Google
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}" # Esri
    ]
    
    for fonte in fontes:
        for _ in range(3): # 3 tentativas por fonte
            try:
                cx.add_basemap(ax, source=fonte, zorder=0, attribution=False)
                mapa_sucesso = True
                break
            except:
                time.sleep(1)
        if mapa_sucesso: break

    # 3. Desenho das Servidões (Cruzamento data/)
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

    # 4. Contorno Área Fiscalizada
    user_gdf_web.plot(ax=ax, facecolor="none", edgecolor="red", linewidth=3, zorder=2)
    legend_elements.append(Line2D([0], [0], color='red', linewidth=3, label='Area Alvo'))

    bounds = user_gdf_web.total_bounds
    ax.set_xlim([bounds[0] - 250, bounds[2] + 250])
    ax.set_ylim([bounds[1] - 250, bounds[3] + 250])
    
    if legend_elements:
        ax.legend(handles=legend_elements, loc='upper right', frameon=True, facecolor='white')
    
    ax.set_axis_off()
    mapa_path = "mapa_final.png"
    plt.savefig(mapa_path, bbox_inches='tight', pad_inches=0.1)
    plt.close(fig)
    return mapa_path

# --- GERAÇÃO DE PDF ---
def exportar_pdf(texto_ia, mapa_path):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "RELATORIO TECNICO DE FISCALIZACAO", 0, 1, 'C')
    
    if os.path.exists(mapa_path):
        pdf.image(mapa_path, x=10, y=30, w=190)
        pdf.set_y(175) 
    
    pdf.set_font("Arial", '', 10)
    txt_fpdf = texto_ia.encode('latin-1', 'ignore').decode('latin-1')
    pdf.multi_cell(0, 6, txt_fpdf)
    
    pdf_name = "Relatorio_Final_Consolidado.pdf"
    pdf.output(pdf_name)
    return pdf_name

# --- INTERFACE ---
st.title("🛡️ Fiscalização SIG Territorial")
file = st.sidebar.file_uploader("Upload GeoJSON", type=['geojson'])

if file:
    user_gdf = gpd.read_file(file).to_crs(epsg=3763)
    area = user_gdf.area.sum()
    
    col_map, col_res = st.columns([2, 1])
    
    with col_map:
        user_gdf_4326 = user_gdf.to_crs(epsg=4326)
        centro = user_gdf_4326.geometry.centroid.iloc[0]
        m = leafmap.Map(center=[centro.y, centro.x], zoom=17)
        m.add_tile_layer(url='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', name='Google Sat', attribution='Google')
        m.add_gdf(user_gdf, layer_name="Parcela")
        m.to_streamlit(height=600)
        
    with col_res:
        st.write(f"**Area Total:** {area:.2f} m2")
        if api_key:
            if st.button("🤖 Gerar Relatório IA"):
                with st.spinner('A capturar mapa e redigir parecer...'):
                    dados_ia = {
                        "area": f"{area:.2f} m2", 
                        "divergencia": "Aterro detetado em zona de culturas", 
                        "regime": "RAN"
                    }
                    texto = redigir_parecer_ia(dados_ia, modelo_selecionado)
                    mapa = gerar_mapa_tecnico(user_gdf)
                    time.sleep(2) # Pausa para escrita em disco
                    pdf = exportar_pdf(texto, mapa)
                    st.success("Relatório pronto!")
                    with open(pdf, "rb") as f:
                        st.download_button("📥 Baixar PDF", f, file_name=pdf)

