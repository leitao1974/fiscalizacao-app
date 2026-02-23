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

# --- FUNÇÃO CARTOGRÁFICA (FORÇAR CARREGAMENTO DO MAPA) ---
def gerar_mapa_tecnico_robusto(user_gdf):
    plt.switch_backend('Agg')
    fig, ax = plt.subplots(figsize=(12, 10), dpi=100)
    
    # Converter para Web Mercator
    user_gdf_web = user_gdf.to_crs(epsg=3857)
    
    # 1. Definição de Estilos e Legenda (Recuperado)
    estilos = {
        "REN": {"cor": "#2ecc71", "hatch": "////", "label": "Reserva Ecologica Nacional (REN)"},
        "RAN": {"cor": "#f1c40f", "hatch": "\\\\\\\\", "label": "Reserva Agricola Nacional (RAN)"}
    }
    legend_elements = []

    # 2. TENTATIVA DE CARREGAMENTO COM RETRY (O segredo para não ficar branco)
    mapa_sucesso = False
    # URLs diretas são mais rápidas que chamar a biblioteca cx.providers
    fontes = [
        "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", # Google Satellite Hybrid
        "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}" # Esri
    ]
    
    for fonte in fontes:
        for tentativa in range(3): # Tenta 3 vezes cada fonte
            try:
                cx.add_basemap(ax, source=fonte, zorder=0, attribution=False)
                mapa_sucesso = True
                break
            except:
                time.sleep(1) # Espera 1 segundo antes de tentar novamente
        if mapa_sucesso: break

    # 3. Desenho das Servidões (Hatches e Cores)
    for nome, estilo in estilos.items():
        path = f"data/{nome.lower()}_amostra.geojson"
        if os.path.exists(path):
            try:
                camada = gpd.read_file(path).to_crs(epsg=3857)
                inter = gpd.overlay(camada, user_gdf_web, how='intersection')
                if not inter.empty:
                    inter.plot(ax=ax, facecolor=estilo["cor"], alpha=0.4, 
                               hatch=estilo["hatch"], edgecolor=estilo["cor"], zorder=1)
                    legend_elements.append(mpatches.Patch(facecolor=estilo["cor"], alpha=0.6, 
                                                          hatch=estilo["hatch"], label=estilo["label"]))
            except: pass

    # 4. Contorno da Área Fiscalizada
    user_gdf_web.plot(ax=ax, facecolor="none", edgecolor="red", linewidth=3, zorder=2)
    legend_elements.append(Line2D([0], [0], color='red', linewidth=3, label='Area Alvo'))

    # 5. Legenda e Enquadramento
    bounds = user_gdf_web.total_bounds
    ax.set_xlim([bounds[0] - 300, bounds[2] + 300]) # Margem maior para carregar tiles
    ax.set_ylim([bounds[1] - 300, bounds[3] + 300])
    
    if legend_elements:
        ax.legend(handles=legend_elements, loc='upper right', frameon=True, facecolor='white', framealpha=0.9)
    
    ax.set_axis_off()
    
    mapa_path = "mapa_tecnico_v3.png"
    plt.savefig(mapa_path, bbox_inches='tight', pad_inches=0.1)
    plt.close(fig)
    return mapa_path

# --- GERAÇÃO DE PDF E INTERFACE (Simplificado para o teste) ---
def exportar_pdf(texto_ia, mapa_path):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "RELATORIO TECNICO DE FISCALIZACAO", 0, 1, 'C')
    if os.path.exists(mapa_path):
        pdf.image(mapa_path, x=10, y=30, w=190)
        pdf.set_y(180)
    pdf.set_font("Arial", '', 10)
    txt = texto_ia.encode('latin-1', 'ignore').decode('latin-1')
    pdf.multi_cell(0, 6, txt)
    pdf_name = "Relatorio_Final_Corrigido.pdf"
    pdf.output(pdf_name)
    return pdf_name

st.title("🛡️ Fiscalização SIG (Fix Imagem)")
file = st.sidebar.file_uploader("Upload GeoJSON", type=['geojson'])

if file:
    user_gdf = gpd.read_file(file).to_crs(epsg=3763)
    if st.sidebar.button("🤖 Gerar Relatório Com Mapa"):
        with st.spinner('A forçar carregamento do Satélite...'):
            # Simulação de texto IA para teste
            texto = "Parecer: Detetada infracao em area RAN (15591 m2). Uso de solo incompativel (Aterro)."
            mapa = gerar_mapa_tecnico_robusto(user_gdf)
            time.sleep(1) # Pausa técnica para escrita em disco
            pdf = exportar_pdf(texto, mapa)
            st.success("Relatório gerado!")
            with open(pdf, "rb") as f:
                st.download_button("📥 Baixar PDF", f, file_name=pdf)
