import streamlit as st
import geopandas as gpd
import pandas as pd
import leafmap.foliumap as leafmap
from fpdf import FPDF
import google.generativeai as genai
import matplotlib.pyplot as plt
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
        # Recupera dinamicamente os modelos disponíveis para a tua chave
        models = genai.list_models()
        available_models = [m.name.replace('models/', '') for m in models 
                            if 'generateContent' in m.supported_generation_methods]
        
        if available_models:
            modelo_selecionado = st.sidebar.selectbox("Modelos Disponíveis", options=available_models)
            st.sidebar.success(f"Conectado a: {modelo_selecionado}")
    except Exception as e:
        st.sidebar.error("Erro ao listar modelos. Verifica a tua API Key.")

# --- MOTOR DE REDAÇÃO IA ---
def redigir_parecer_ia(dados, api_key, modelo):
    if not api_key or not modelo: return "Configuração incompleta."
    model = genai.GenerativeModel(f"models/{modelo}")
    # Baseado no Relatório de Fiscalização oficial [cite: 3, 13]
    prompt = f"""
    Age como um fiscal do territorio em Portugal. Redigi um parecer tecnico formal:
    DADOS: Area de {dados['area']} m2 em zona de {dados['natureza']}. [cite: 8, 10]
    DIVERGENCIA: Ocupacao por aterro/construcao em zona de Reserva Agricola Nacional (RAN). [cite: 10, 11]
    LEGISLACAO: Cita o Decreto-Lei n.o 73/2009 (RAN). [cite: 16]
    IMPORTANTE: Nao uses acentos ou cedilhas para evitar erros no PDF.
    """
    return model.generate_content(prompt).text

# --- FUNÇÃO DE MAPA (FIX DO MAPA BASE EM BRANCO) ---
def gerar_mapa_tecnico(user_gdf):
    plt.switch_backend('Agg')
    # Aumentar DPI e tamanho ajuda a forçar o carregamento dos blocos de imagem
    fig, ax = plt.subplots(figsize=(12, 10), dpi=150)
    
    # Garantir ETRS89 / PT-TM06 (EPSG:3763)
    if user_gdf.crs is None:
        user_gdf.set_crs(epsg=3763, inplace=True)
    
    # Converter para Web Mercator (EPSG:3857) para o mapa base
    user_gdf_web = user_gdf.to_crs(epsg=3857)
    
    # Renderização do Mapa Base (Tenta Google, Fallback Esri)
    try:
        cx.add_basemap(ax, source="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", 
                       attribution=False, alpha=1.0)
    except:
        try:
            cx.add_basemap(ax, source=cx.providers.Esri.WorldImagery, attribution=False)
        except:
            ax.set_facecolor('#dcdcdc')

    # Desenho do Alvo (Polígono da Divergência) [cite: 25]
    user_gdf_web.plot(ax=ax, facecolor="red", alpha=0.3, edgecolor="red", linewidth=3, zorder=5)

    # Enquadramento Dinâmico
    bounds = user_gdf_web.total_bounds
    ax.set_xlim([bounds[0] - 350, bounds[2] + 350])
    ax.set_ylim([bounds[1] - 350, bounds[3] + 350])
    ax.set_axis_off()
    
    mapa_path = "mapa_relatorio.png"
    # Forçar o "desenho" completo antes de guardar
    fig.canvas.draw()
    plt.savefig(mapa_path, bbox_inches='tight', pad_inches=0.1)
    plt.close(fig)
    time.sleep(2) # Pausa para escrita em disco
    return mapa_path

# --- INTERFACE ---
st.title("🛡️ Fiscalização SIG Territorial")
file = st.sidebar.file_uploader("Upload GeoJSON (PT-TM06)", type=['geojson'])

if file:
    user_gdf = gpd.read_file(file)
    if user_gdf.crs is None: user_gdf.set_crs(epsg=3763, inplace=True)
    
    # Cálculo da área afetada 
    area_m2 = user_gdf.area.sum()
    
    col_map, col_res = st.columns([2, 1])
    with col_map:
        user_gdf_4326 = user_gdf.to_crs(epsg=4326)
        centro = user_gdf_4326.geometry.centroid.iloc[0]
        m = leafmap.Map(center=[centro.y, centro.x], zoom=17, google_map="HYBRID")
        m.add_gdf(user_gdf_4326, layer_name="Divergencia Detetada")
        m.to_streamlit(height=600)
        
    with col_res:
        st.subheader("📋 Resumo do SIG")
        st.write(f"Área Afetada: **{area_m2:.2f} m²**") [cite: 8]
        st.write(f"Natureza: **Aterro detetado em zona de culturas**") [cite: 10]
        
        if st.button("🤖 Gerar Relatório PDF"):
            if api_key and modelo_selecionado:
                with st.spinner('A capturar cartografia e redigir parecer técnico...'):
                    # Dados do Parecer Técnico Formal [cite: 3, 4]
                    dados_fiscalizacao = {
                        "area": f"{area_m2:.2f}",
                        "natureza": "Cultura / Solo com Aptidao Agricola" [cite: 22]
                    }
                    
                    texto_parecer = redigir_parecer_ia(dados_fiscalizacao, api_key, modelo_selecionado)
                    mapa_img = gerar_mapa_tecnico(user_gdf)
                    
                    # Gerar PDF Consolidado
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Arial", 'B', 16)
                    pdf.cell(0, 10, "PARECER TECNICO FORMAL", 0, 1, 'C') [cite: 3]
                    pdf.set_font("Arial", '', 10)
                    pdf.cell(0, 10, f"DATA: {date.today().strftime('%d de %B de %Y')}", 0, 1, 'R') [cite: 4]
                    
                    if os.path.exists(mapa_img):
                        pdf.image(mapa_img, x=10, y=35, w=190)
                        pdf.set_y(185)
                    
                    pdf.multi_cell(0, 6, texto_parecer.encode('latin-1', 'ignore').decode('latin-1'))
                    
                    pdf_out = "Relatorio_Fiscalizacao_Final.pdf"
                    pdf.output(pdf_out)
                    
                    with open(pdf_out, "rb") as f:
                        st.download_button("📥 Baixar Relatório Oficial", f, file_name=pdf_out)
            else:
                st.error("Verifica a API Key e o Modelo na barra lateral.")

