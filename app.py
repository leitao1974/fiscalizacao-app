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

# --- FUNÇÃO CARTOGRÁFICA (FORÇAR RENDERIZAÇÃO) ---
def gerar_mapa_estatico(user_gdf):
    plt.switch_backend('Agg')
    # Aumentar o tamanho da figura para forçar o download dos tiles
    fig, ax = plt.subplots(figsize=(12, 10), dpi=100)
    
    # Converter para Web Mercator (EPSG:3857)
    user_gdf_web = user_gdf.to_crs(epsg=3857)
    
    # Desenhar o polígono primeiro com cor sólida para ser visível
    user_gdf_web.plot(ax=ax, facecolor="red", alpha=0.5, edgecolor="darkred", linewidth=3, zorder=2)
    
    # TENTATIVA DE MAPA BASE COM TIMEOUT E MULTIPLOS PROVEDORES
    mapa_sucesso = False
    # Lista de URLs diretas para evitar falhas de bibliotecas intermédias
    fontes = [
        "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", # Google Hybrid
        cx.providers.Esri.WorldImagery,                       # Esri Satellite
        cx.providers.OpenStreetMap.Mapnik                     # OSM (Fallback)
    ]
    
    for fonte in fontes:
        try:
            cx.add_basemap(ax, source=fonte, zorder=0, attribution=False)
            mapa_sucesso = True
            break
        except:
            continue
            
    if not mapa_sucesso:
        ax.set_facecolor('#cccccc') # Fundo cinza se falhar
    
    # Ajustar limites com margem generosa
    bounds = user_gdf_web.total_bounds
    ax.set_xlim([bounds[0] - 250, bounds[2] + 250])
    ax.set_ylim([bounds[1] - 250, bounds[3] + 250])
    ax.set_axis_off()
    
    mapa_path = "mapa_final.png"
    # Guardar com alta qualidade
    plt.savefig(mapa_path, bbox_inches='tight', pad_inches=0.2)
    plt.close(fig)
    return mapa_path

# --- GERAÇÃO DE PDF ---
def exportar_pdf(texto_ia, mapa_path):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "RELATORIO TECNICO DE FISCALIZACAO", 0, 1, 'C')
    pdf.ln(5)
    
    # Inserção da Imagem com garantia de posicionamento
    if os.path.exists(mapa_path):
        # x=10, y=30, w=190 (Largura quase total da folha A4)
        pdf.image(mapa_path, x=10, y=30, w=190)
        # Movemos o texto para a página 2 ou muito abaixo para não haver sobreposição
        pdf.set_y(175) 
    
    pdf.set_font("Arial", '', 10)
    # Codificação para evitar caracteres "estranhos"
    txt_fpdf = texto_ia.encode('latin-1', 'ignore').decode('latin-1')
    pdf.multi_cell(0, 6, txt_fpdf)
    
    pdf_name = "Relatorio_Final_IA.pdf"
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
        m.add_tile_layer(url='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', name='Google Satellite', attribution='Google')
        m.add_gdf(user_gdf, layer_name="Parcela")
        m.to_streamlit(height=600)
        
    with col_res:
        st.subheader("📋 Painel de Controle")
        st.write(f"**Área Detetada:** {area:.2f} m² ")
        
        if api_key:
            if st.button("🤖 Gerar Relatório IA"):
                with st.spinner('A capturar cartografia e redigir parecer técnico...'):
                    # Dados contextuais para a IA
                    dados_ia = {
                        "area": f"{area:.2f} m2",
                        "divergencia": "Aterro detetado em zona de culturas temporarias [cite: 40, 55]",
                        "regime": "RAN (Reserva Agricola Nacional) [cite: 41, 64]"
                    }
                    
                    texto_parecer = redigir_parecer_ia(dados_ia, modelo_selecionado)
                    # Gerar a imagem do mapa
                    mapa_img = gerar_mapa_estatico(user_gdf)
                    
                    # Pausa para garantir escrita no disco
                    time.sleep(1)
                    
                    pdf_final = exportar_pdf(texto_parecer, mapa_img)
                    
                    st.success("Relatório gerado com sucesso!")
                    with open(pdf_final, "rb") as f:
                        st.download_button("📥 Descarregar PDF", f, file_name=pdf_final)
                    st.markdown(texto_parecer)
        else:
            st.warning("Insere a API Key para redigir o relatório.")

