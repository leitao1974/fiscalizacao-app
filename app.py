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

if api_key:
    try:
        genai.configure(api_key=api_key)
        available_models = [m.name.replace('models/', '') for m in genai.list_models() 
                            if 'generateContent' in m.supported_generation_methods]
        modelo_selecionado = st.sidebar.selectbox("Escolhe o Modelo Gemini", options=available_models, index=0)
    except Exception as e:
        st.sidebar.error(f"Erro: {e}")

# --- MOTOR DE REDAÇÃO IA ---
def redigir_parecer_ia(dados_analise, modelo_name):
    model = genai.GenerativeModel(modelo_name)
    prompt = f"""
    Age como um fiscal do território em Portugal. Escreve um parecer técnico detalhado:
    Dados: {dados_analise}
    Fundamentação: Cita o DL 73/2009 (RAN) e o DL 166/2008 (REN).
    Divergência: Comenta a alteração de 'Culturas' para 'Aterro/Construção'.
    IMPORTANTE: Não uses acentos ou caracteres especiais para evitar erros no PDF.
    """
    return model.generate_content(prompt).text

# --- FUNÇÃO CARTOGRÁFICA (GOOGLE MAPS) ---
def gerar_mapa_estatico(user_gdf):
    plt.switch_backend('Agg')
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Converter para Web Mercator
    user_gdf_web = user_gdf.to_crs(epsg=3857)
    
    try:
        # Tenta carregar o Google Maps (Satélite) para o relatório
        # Nota: O contextily usa URLs de tiles. Algumas regiões podem exigir API Key do Google Maps Static
        cx.add_basemap(ax, source='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', zorder=0)
    except:
        # Fallback para Esri se o Google bloquear o pedido
        cx.add_basemap(ax, source=cx.providers.Esri.WorldImagery, zorder=0)
        
    user_gdf_web.plot(ax=ax, facecolor="red", alpha=0.3, edgecolor="red", linewidth=2, zorder=1)
    
    bounds = user_gdf_web.total_bounds
    ax.set_xlim([bounds[0] - 150, bounds[2] + 150])
    ax.set_ylim([bounds[1] - 150, bounds[3] + 150])
    ax.set_axis_off()
    
    mapa_path = "mapa_google_export.png"
    plt.savefig(mapa_path, bbox_inches='tight', pad_inches=0.1)
    plt.close()
    return mapa_path

# --- GERAÇÃO DE PDF ---
def exportar_pdf(texto_ia, mapa_path):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Relatorio de Fiscalizacao Territorial (Google Maps + IA)", 0, 1, 'C')
    pdf.ln(5)
    
    if os.path.exists(mapa_path):
        pdf.image(mapa_path, x=15, y=None, w=180)
        pdf.ln(5)
    
    pdf.set_font("Arial", '', 10)
    # Filtro para caracteres latinos básicos
    txt_limpo = texto_ia.encode('latin-1', 'ignore').decode('latin-1')
    pdf.multi_cell(0, 6, txt_limpo)
    
    pdf_name = "Relatorio_Final_IA.pdf"
    pdf.output(pdf_name)
    return pdf_name

# --- INTERFACE ---
st.title("🛡️ Fiscalização SIG com Google Maps")
file = st.sidebar.file_uploader("Upload GeoJSON", type=['geojson'])

if file:
    user_gdf = gpd.read_file(file).to_crs(epsg=3763)
    area = user_gdf.area.sum()
    
    col_map, col_res = st.columns([2, 1])
    
    with col_map:
        # Localização dinâmica
        user_gdf_4326 = user_gdf.to_crs(epsg=4326)
        centro = user_gdf_4326.geometry.centroid.iloc[0]
        
        # DEFINIÇÃO DO GOOGLE MAPS NA INTERFACE
        m = leafmap.Map(center=[centro.y, centro.x], zoom=17)
        m.add_google_map(google_map="HYBRID") # <--- Google Maps Hybrid aqui
        m.add_gdf(user_gdf, layer_name="Alvo da Fiscalização")
        m.to_streamlit(height=600)
        
    with col_res:
        st.subheader("📋 Painel de Controle")
        st.metric("Área da Parcela", f"{area:.2f} m²")
        
        if api_key:
            if st.button("🤖 Gerar Parecer IA e PDF"):
                with st.spinner('A analisar terreno com Google Maps...'):
                    # Dados contextuais baseados no teu caso real
                    dados_ia = {
                        "area": f"{area:.2f} m2",
                        "divergencia": "COS2023 indica agricultura, mas detetado aterro para construção",
                        "regime": "RAN (100% de ocupação)"
                    }
                    
                    texto = redigir_parecer_ia(dados_ia, modelo_selecionado)
                    mapa = gerar_mapa_estatico(user_gdf)
                    pdf = exportar_pdf(texto, mapa)
                    
                    st.success("Relatório pronto!")
                    with open(pdf, "rb") as f:
                        st.download_button("📥 Descarregar Relatório", f, file_name=pdf)
                    st.write(texto)
        else:
            st.warning("Insere a API Key para redigir o relatório.")
