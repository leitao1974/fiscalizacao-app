import streamlit as st
import geopandas as gpd
import pandas as pd
import leafmap.foliumap as leafmap
from fpdf import FPDF
import google.generativeai as genai
import matplotlib.pyplot as plt
import contextily as cx
import os
from datetime import date

# 1. Configuração da Página
st.set_page_config(layout="wide", page_title="Fiscalização IA SIG", page_icon="🤖")

# --- SIDEBAR: CONFIGURAÇÃO DA IA ---
st.sidebar.title("🔑 Configuração IA")
api_key = st.sidebar.text_input("Insere a tua Google API Key", type="password")

modelo_selecionado = "gemini-1.5-flash"

if api_key:
    try:
        genai.configure(api_key=api_key)
        available_models = [m.name.replace('models/', '') for m in genai.list_models() 
                            if 'generateContent' in m.supported_generation_methods]
        modelo_selecionado = st.sidebar.selectbox("Escolhe o Modelo Gemini", options=available_models, index=0)
        st.sidebar.success("IA Pronta")
    except Exception as e:
        st.sidebar.error(f"Erro: {e}")

# --- MOTOR DE REDAÇÃO IA ---
def redigir_parecer_ia(dados_analise, modelo_name):
    model = genai.GenerativeModel(modelo_name)
    prompt = f"""
    Age como um fiscal do territorio em Portugal. Escreve um parecer tecnico formal:
    Dados: {dados_analise}
    Cita: DL 73/2009 (RAN) e DL 166/2008 (REN).
    Inclui: Analise de divergencia COS2023 vs Realidade, Coimas e Medidas de Tutela.
    IMPORTANTE: Nao uses acentos ou caracteres especiais (cedilhas, etc) para evitar erros no PDF.
    """
    return model.generate_content(prompt).text

# --- FUNÇÃO CARTOGRÁFICA COM ZOOM E FALLBACK ---
def gerar_mapa_estatico(user_gdf):
    plt.switch_backend('Agg')
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Converter para Web Mercator para o mapa base
    user_gdf_web = user_gdf.to_crs(epsg=3857)
    
    try:
        # Tenta carregar satélite (Esri)
        cx.add_basemap(ax, source=cx.providers.Esri.WorldImagery, zorder=0)
    except:
        # Se falhar, usa um fundo cinza técnico para o relatório não ficar em branco
        ax.set_facecolor('#e0e0e0')
        ax.grid(True, linestyle='--', alpha=0.5)
        
    user_gdf_web.plot(ax=ax, facecolor="red", alpha=0.4, edgecolor="darkred", linewidth=2, zorder=1)
    
    # Ajustar a vista exatamente ao polígono com uma margem de 100 metros
    bounds = user_gdf_web.total_bounds
    ax.set_xlim([bounds[0] - 100, bounds[2] + 100])
    ax.set_ylim([bounds[1] - 100, bounds[3] + 100])
    ax.set_axis_off()
    
    mapa_path = "mapa_export.png"
    plt.savefig(mapa_path, bbox_inches='tight', pad_inches=0.1)
    plt.close()
    return mapa_path

# --- GERAÇÃO DE PDF ---
def exportar_pdf(texto_ia, mapa_path):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Relatorio de Fiscalizacao Territorial IA", 0, 1, 'C')
    pdf.ln(5)
    
    if os.path.exists(mapa_path):
        pdf.image(mapa_path, x=15, y=None, w=180)
        pdf.ln(5)
    
    pdf.set_font("Arial", '', 10)
    txt_limpo = texto_ia.encode('latin-1', 'ignore').decode('latin-1')
    pdf.multi_cell(0, 6, txt_limpo)
    
    pdf_name = "Relatorio_Final_IA.pdf"
    pdf.output(pdf_name)
    return pdf_name

# --- INTERFACE ---
st.title("🛡️ Fiscalização SIG Inteligente")
file = st.sidebar.file_uploader("Upload GeoJSON", type=['geojson'])

if file:
    # 1. Carregar e calcular área
    user_gdf = gpd.read_file(file).to_crs(epsg=3763)
    area = user_gdf.area.sum()
    
    col_map, col_res = st.columns([2, 1])
    
    with col_map:
        # CORREÇÃO DO ZOOM: Converter para 4326 para o leafmap centrar
        user_gdf_4326 = user_gdf.to_crs(epsg=4326)
        centro = user_gdf_4326.geometry.centroid.iloc[0]
        
        m = leafmap.Map(center=[centro.y, centro.x], zoom=17, google_map="HYBRID")
        m.add_gdf(user_gdf, layer_name="Parcela Fiscalizada")
        m.to_streamlit(height=600)
        
    with col_res:
        st.subheader("📋 Dados da Parcela")
        st.metric("Área Total", f"{area:.2f} m²")
        
        # Contexto para a IA
        dados_ia = {
            "area": f"{area:.2f} m2",
            "detetado": "Aterro e Construcao de infraestrutura",
            "oficial_cos": "Culturas temporarias",
            "concelho": "Alenquer" # Podes automatizar isto
        }
        
        if api_key:
            if st.button("🤖 Gerar Relatório Completo"):
                with st.spinner('A processar mapa e parecer...'):
                    parecer = redigir_parecer_ia(dados_ia, modelo_selecionado)
                    mapa_img = gerar_mapa_estatico(user_gdf)
                    pdf_path = exportar_pdf(parecer, mapa_img)
                    
                    st.success("Relatório Gerado!")
                    with open(pdf_path, "rb") as f:
                        st.download_button("📥 Baixar PDF", f, file_name=pdf_path)
                    st.markdown(parecer)
        else:
            st.warning("Insere a API Key para ativar a redação do relatório.")

