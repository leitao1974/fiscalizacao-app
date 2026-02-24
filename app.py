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

# --- SIDEBAR: CONFIGURAÇÃO DINÂMICA DA IA ---
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
            modelo_selecionado = st.sidebar.selectbox("Modelos Gemini Disponíveis", options=available_models)
            st.sidebar.success(f"Motor Ativo: {modelo_selecionado}")
    except Exception as e:
        st.sidebar.error("Erro ao validar API Key.")

# --- MOTOR DE REDAÇÃO IA ---
def redigir_parecer_ia(dados, api_key, modelo):
    if not api_key or not modelo: return "Configuração IA incompleta."
    model = genai.GenerativeModel(f"models/{modelo}")
    prompt = f"""
    Age como um fiscal do territorio em Portugal. Redigi um parecer tecnico formal:
    DADOS: Area afetada de {dados['area']} m2.
    DIVERGENCIA: Aterro detetado em zona de culturas (COS2023).
    ENQUADRAMENTO: Solo integrado em Reserva Agricola Nacional (RAN).
    LEGISLACAO: Cita obrigatoriamente o Decreto-Lei n.o 73/2009.
    IMPORTANTE: Nao uses acentos ou cedilhas para evitar erros de encoding no PDF.
    """
    try:
        return model.generate_content(prompt).text
    except Exception as e:
        return f"Erro na geracao: {str(e)}"

# --- FUNÇÃO DE MAPA (FIX DO MAPA BASE E COORDENADAS) ---
def gerar_mapa_tecnico(user_gdf):
    plt.switch_backend('Agg')
    fig, ax = plt.subplots(figsize=(12, 10), dpi=150)
    
    # Forçar ETRS89 / PT-TM06 (EPSG:3763)
    if user_gdf.crs is None:
        user_gdf.set_crs(epsg=3763, inplace=True)
    
    # Converter para Web Mercator (EPSG:3857) para o satélite
    user_gdf_web = user_gdf.to_crs(epsg=3857)
    
    # 1. Mapa Base (Google Hybrid / Esri)
    try:
        cx.add_basemap(ax, source="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", attribution=False)
    except:
        try:
            cx.add_basemap(ax, source=cx.providers.Esri.WorldImagery, attribution=False)
        except:
            ax.set_facecolor('#dcdcdc')

    # 2. Estilos de Servidões (RAN / REN) - Tenta carregar da pasta data/
    estilos = {
        "REN": {"cor": "#2ecc71", "hatch": "////", "label": "REN (DL 166/2008)"},
        "RAN": {"cor": "#f1c40f", "hatch": "\\\\\\\\", "label": "RAN (DL 73/2009)"}
    }
    legend_elements = []

    for nome, estilo in estilos.items():
        path = f"data/{nome.lower()}_amostra.geojson"
        if os.path.exists(path):
            try:
                camada = gpd.read_file(path)
                if camada.crs is None: camada.set_crs(epsg=3763, inplace=True)
                camada_web = camada.to_crs(epsg=3857)
                
                inter = gpd.overlay(camada_web, user_gdf_web, how='intersection')
                if not inter.empty:
                    inter.plot(ax=ax, facecolor=estilo["cor"], alpha=0.4, hatch=estilo["hatch"])
                    legend_elements.append(mpatches.Patch(facecolor=estilo["cor"], alpha=0.6, 
                                                          hatch=estilo["hatch"], label=estilo["label"]))
            except:
                pass

    # 3. Desenho do Alvo (Polígono Vermelho)
    user_gdf_web.plot(ax=ax, facecolor="none", edgecolor="red", linewidth=3, zorder=10)
    legend_elements.append(Line2D([0], [0], color='red', linewidth=3, label='Area Fiscalizada'))

    # Zoom e Finalização
    bounds = user_gdf_web.total_bounds
    ax.set_xlim([bounds[0] - 300, bounds[2] + 300])
    ax.set_ylim([bounds[1] - 300, bounds[3] + 300])
    
    if legend_elements:
        ax.legend(handles=legend_elements, loc='upper right', frameon=True, facecolor='white')
    
    ax.set_axis_off()
    
    mapa_path = "mapa_final_report.png"
    fig.canvas.draw()
    plt.savefig(mapa_path, bbox_inches='tight', pad_inches=0.1)
    plt.close(fig)
    return mapa_path

# --- INTERFACE PRINCIPAL ---
st.title("🛡️ Sistema de Fiscalização SIG Territorial")
uploaded_file = st.sidebar.file_uploader("Upload GeoJSON (ETRS89 / PT-TM06)", type=['geojson'])

if uploaded_file:
    # Motor pyogrio para evitar dependências de sistema
    user_gdf = gpd.read_file(uploaded_file, engine="pyogrio")
    if user_gdf.crs is None: user_gdf.set_crs(epsg=3763, inplace=True)
    
    area_fiscalizada = user_gdf.area.sum()
    
    col1, col2 = st.columns([2, 1])
    with col1:
        # Mapa Interativo WGS84
        user_gdf_4326 = user_gdf.to_crs(epsg=4326)
        centro = user_gdf_4326.geometry.centroid.iloc[0]
        m = leafmap.Map(center=[centro.y, centro.x], zoom=17, google_map="HYBRID")
        m.add_gdf(user_gdf_4326, layer_name="Divergencia Detetada")
        m.to_streamlit(height=600)
        
    with col2:
        st.subheader("📋 Resumo do Processo")
        st.write(f"**Área Detetada:** {area_fiscalizada:.2f} m²")
        st.write(f"**Localização:** {centro.y:.5f}, {centro.x:.5f}")
        
        if st.button("🤖 Gerar Relatório PDF"):
            if api_key and modelo_selecionado:
                with st.spinner('A processar cartografia e parecer...'):
                    mapa_img = gerar_mapa_tecnico(user_gdf)
                    dados_parecer = {"area": f"{area_fiscalizada:.2f}"}
                    texto_ia = redigir_parecer_ia(dados_parecer, api_key, modelo_selecionado)
                    
                    # Geração do PDF
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Helvetica", "B", 16)
                    pdf.cell(0, 10, "PARECER TECNICO DE FISCALIZACAO", 0, 1, "C")
                    pdf.set_font("Helvetica", "", 10)
                    pdf.cell(0, 10, f"Data: {date.today().strftime('%d/%m/%Y')}", 0, 1, "R")
                    
                    if os.path.exists(mapa_img):
                        pdf.image(mapa_img, x=10, y=40, w=190)
                        pdf.set_y(190)
                    
                    pdf.multi_cell(0, 6, texto_ia.encode('latin-1', 'ignore').decode('latin-1'))
                    
                    pdf_output = "Relatorio_Fiscalizacao_SIG.pdf"
                    pdf.output(pdf_output)
                    
                    with open(pdf_output, "rb") as f:
                        st.download_button("📥 Baixar Relatório PDF", f, file_name=pdf_output)
            else:
                st.warning("Configura a API Key e o Modelo Gemini na barra lateral.")

