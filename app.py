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

# --- FUNÇÃO CARTOGRÁFICA TÉCNICA (MAPA BASE, CORES E TRAMAS) ---
def gerar_mapa_tecnico(user_gdf):
    plt.switch_backend('Agg')
    fig, ax = plt.subplots(figsize=(12, 10), dpi=120)
    user_gdf_web = user_gdf.to_crs(epsg=3857)
    
    # 1. Definição de Estilos por Servidão
    estilos = {
        "REN": {"cor": "#2ecc71", "hatch": "////", "label": "Reserva Ecologica Nacional (REN)"},
        "RAN": {"cor": "#f1c40f", "hatch": "\\\\\\\\", "label": "Reserva Agricola Nacional (RAN)"},
        "Rede Natura": {"cor": "#8B4513", "hatch": "----", "label": "Rede Natura 2000"}
    }
    legend_elements = []

    # 2. Forçar Mapa Base (Google Hybrid com Fallback para Esri)
    mapa_sucesso = False
    fontes = ["https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", cx.providers.Esri.WorldImagery]
    
    for fonte in fontes:
        try:
            cx.add_basemap(ax, source=fonte, zorder=0, attribution=False)
            mapa_sucesso = True
            break
        except:
            continue
    
    if not mapa_sucesso:
        ax.set_facecolor('#cccccc')

    # 3. Desenho das Servidões (Cruzamento Geospacial e Tramas)
    for nome, estilo in estilos.items():
        # Assume que os ficheiros existem na pasta data/ com nomes específicos
        path = f"data/{nome.lower().replace(' ', '_')}_amostra.geojson"
        if os.path.exists(path):
            camada = gpd.read_file(path).to_crs(epsg=3857)
            inter = gpd.overlay(camada, user_gdf_web, how='intersection')
            if not inter.empty:
                inter.plot(ax=ax, facecolor=estilo["cor"], alpha=0.4, 
                           hatch=estilo["hatch"], edgecolor=estilo["cor"], zorder=1)
                legend_elements.append(mpatches.Patch(facecolor=estilo["cor"], alpha=0.6, 
                                                      hatch=estilo["hatch"], label=estilo["label"]))

    # 4. Desenho do Contorno da Área Fiscalizada
    user_gdf_web.plot(ax=ax, facecolor="none", edgecolor="red", linewidth=3, zorder=2)
    legend_elements.append(Line2D([0], [0], color='red', linewidth=3, label='Area Alvo'))

    # 5. Ajustes de Enquadramento e Legenda
    bounds = user_gdf_web.total_bounds
    ax.set_xlim([bounds[0] - 200, bounds[2] + 200])
    ax.set_ylim([bounds[1] - 200, bounds[3] + 200])
    
    if legend_elements:
        ax.legend(handles=legend_elements, loc='upper right', frameon=True, facecolor='white', framealpha=0.9)
    
    ax.set_axis_off()
    mapa_path = "mapa_tecnico_final.png"
    plt.savefig(mapa_path, bbox_inches='tight', pad_inches=0.1)
    plt.close(fig)
    return mapa_path

# --- GERAÇÃO DE PDF ---
def exportar_pdf(texto_ia, mapa_path):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Cabeçalho do Relatório
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "RELATORIO TECNICO DE FISCALIZACAO TERRITORIAL", 0, 1, 'C')
    pdf.ln(5)
    
    # Inserção da Imagem Técnica
    if os.path.exists(mapa_path):
        pdf.image(mapa_path, x=10, y=30, w=190)
        pdf.set_y(180) # Posicionamento do parecer abaixo do mapa
    
    pdf.set_font("Arial", '', 10)
    # Codificação Latin-1 para compatibilidade FPDF
    txt_fpdf = texto_ia.encode('latin-1', 'ignore').decode('latin-1')
    pdf.multi_cell(0, 6, txt_fpdf)
    
    pdf_name = "Relatorio_Consolidado_Tecnico.pdf"
    pdf.output(pdf_name)
    return pdf_name

# --- INTERFACE PRINCIPAL ---
st.title("🛡️ Fiscalização SIG Territorial")
file = st.sidebar.file_uploader("Upload GeoJSON", type=['geojson'])

if file:
    user_gdf = gpd.read_file(file).to_crs(epsg=3763)
    area_valor = user_gdf.area.sum()
    
    col_map, col_res = st.columns([2, 1])
    
    with col_map:
        user_gdf_4326 = user_gdf.to_crs(epsg=4326)
        centro = user_gdf_4326.geometry.centroid.iloc[0]
        
        m = leafmap.Map(center=[centro.y, centro.x], zoom=17)
        # Adição de camada Google Satellite na App
        m.add_tile_layer(url='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', 
                         name='Google Satellite', attribution='Google')
        m.add_gdf(user_gdf, layer_name="Parcela Fiscalizada")
        m.to_streamlit(height=600)
        
    with col_res:
        st.subheader("📊 Resultados da Análise")
        st.write(f"**Área Total:** {area_valor:.2f} m²")
        
        if api_key:
            if st.button("🤖 Gerar Relatório IA"):
                with st.spinner('A analisar cartografia e redigir parecer...'):
                    # Dados para o motor de IA
                    dados_ia = {
                        "area": f"{area_valor:.2f} m2", 
                        "divergencia": "Aterro detetado em zona de culturas", 
                        "regime": "RAN (DL 73/2009)"
                    }
                    texto = redigir_parecer_ia(dados_ia, modelo_selecionado)
                    mapa = gerar_mapa_tecnico(user_gdf)
                    
                    time.sleep(1) # Segurança para escrita de ficheiro
                    pdf_final = exportar_pdf(texto, mapa)
                    
                    st.success("Relatório gerado!")
                    with open(pdf_final, "rb") as f:
                        st.download_button("📥 Baixar PDF Consolidado", f, file_name=pdf_final)
                    st.markdown(texto)
        else:
            st.warning("Insere a API Key para redigir o relatório.")
