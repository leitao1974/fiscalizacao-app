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
        st.sidebar.success("Motor IA Ativo")
    except Exception as e:
        st.sidebar.error(f"Erro na configuração: {e}")

# --- MOTOR DE REDAÇÃO IA ---
def redigir_parecer_ia(dados_analise, modelo_name):
    try:
        model = genai.GenerativeModel(modelo_name)
        prompt = f"""
        Age como um fiscal do territorio em Portugal. Escreve um parecer tecnico formal com base nestes dados:
        {dados_analise}
        
        O relatorio deve incluir:
        1. Analise da Ocupacao do Solo (Divergencia COS2023 vs Realidade).
        2. Enquadramento Juridico (Cita DL 73/2009 para RAN e DL 166/2008 para REN).
        3. Medidas de Tutela (Auto de noticia, Embargo, Reposicao).
        
        IMPORTANTE: Nao uses acentos ou cedilhas para evitar erros de geracao no PDF.
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Erro na geracao do parecer: {e}"

# --- FUNÇÃO CARTOGRÁFICA TÉCNICA (ESTABILIDADE TOTAL) ---
def gerar_mapa_tecnico(user_gdf):
    plt.switch_backend('Agg')
    # DPI elevado para forçar o carregamento detalhado do satélite
    fig, ax = plt.subplots(figsize=(12, 10), dpi=150)
    user_gdf_web = user_gdf.to_crs(epsg=3857)
    
    # 1. Estilos por Servidão (Cores e Tramas)
    estilos = {
        "REN": {"cor": "#2ecc71", "hatch": "////", "label": "Reserva Ecologica Nacional (REN)"},
        "RAN": {"cor": "#f1c40f", "hatch": "\\\\\\\\", "label": "Reserva Agricola Nacional (RAN)"}
    }
    legend_elements = []

    # 2. Mapa Base (Google Hybrid com Redundância)
    mapa_carregado = False
    fontes = ["https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", cx.providers.Esri.WorldImagery]
    
    for fonte in fontes:
        try:
            cx.add_basemap(ax, source=fonte, zorder=0, attribution=False)
            mapa_carregado = True
            break
        except:
            continue
    if not mapa_carregado:
        ax.set_facecolor('#d3d3d3')

    # 3. Desenho das Servidões (Cruzamento de ficheiros na pasta data/)
    for nome, estilo in estilos.items():
        path = f"data/{nome.lower()}_amostra.geojson"
        if os.path.exists(path):
            camada = gpd.read_file(path).to_crs(epsg=3857)
            inter = gpd.overlay(camada, user_gdf_web, how='intersection')
            if not inter.empty:
                inter.plot(ax=ax, facecolor=estilo["cor"], alpha=0.4, 
                           hatch=estilo["hatch"], edgecolor=estilo["cor"], zorder=1)
                legend_elements.append(mpatches.Patch(facecolor=estilo["cor"], alpha=0.6, 
                                                      hatch=estilo["hatch"], label=estilo["label"]))

    # 4. Área Fiscalizada (Linha Vermelha)
    user_gdf_web.plot(ax=ax, facecolor="none", edgecolor="red", linewidth=3, zorder=2)
    legend_elements.append(Line2D([0], [0], color='red', linewidth=3, label='Area Alvo'))

    # 5. Ajustes de Layout e Legenda
    bounds = user_gdf_web.total_bounds
    ax.set_xlim([bounds[0] - 350, bounds[2] + 350]) # Margem de segurança para satélite
    ax.set_ylim([bounds[1] - 350, bounds[3] + 350])
    
    if legend_elements:
        ax.legend(handles=legend_elements, loc='upper right', frameon=True, facecolor='white', framealpha=0.9)
    
    ax.set_axis_off()
    mapa_path = "mapa_tecnico_relatorio.png"
    plt.savefig(mapa_path, bbox_inches='tight', pad_inches=0.1)
    plt.close(fig)
    time.sleep(2) # Pausa técnica para o sistema de ficheiros
    return mapa_path

# --- GERAÇÃO DE PDF ---
def exportar_pdf(texto_ia, mapa_path):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "RELATORIO TECNICO DE FISCALIZACAO", 0, 1, 'C')
    pdf.ln(5)
    
    if os.path.exists(mapa_path):
        pdf.image(mapa_path, x=10, y=30, w=190)
        pdf.set_y(180) # Inicia texto abaixo do mapa
    
    pdf.set_font("Arial", '', 10)
    txt_fpdf = texto_ia.encode('latin-1', 'ignore').decode('latin-1')
    pdf.multi_cell(0, 6, txt_fpdf)
    
    pdf_name = "Relatorio_Final_Consolidado.pdf"
    pdf.output(pdf_name)
    return pdf_name

# --- INTERFACE ---
st.title("🛡️ Sistema de Fiscalização SIG Inteligente")
file = st.sidebar.file_uploader("Upload Polígono de Fiscalização", type=['geojson'])

if file:
    user_gdf = gpd.read_file(file).to_crs(epsg=3763)
    area_calc = user_gdf.area.sum()
    
    col_map, col_res = st.columns([2, 1])
    
    with col_map:
        # Focar localização dinâmica
        user_gdf_4326 = user_gdf.to_crs(epsg=4326)
        centro = user_gdf_4326.geometry.centroid.iloc[0]
        
        m = leafmap.Map(center=[centro.y, centro.x], zoom=17)
        m.add_tile_layer(url='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', 
                         name='Google Hybrid', attribution='Google')
        m.add_gdf(user_gdf, layer_name="Alvo")
        m.to_streamlit(height=600)
        
    with col_res:
        st.subheader("📊 Análise do SIG")
        st.write(f"**Área Detetada:** {area_calc:.2f} m²") [cite: 9, 25]
        
        if api_key:
            if st.button("🤖 Gerar Relatório e Parecer IA"):
                with st.spinner('A processar mapa e parecer jurídico...'):
                    dados_ia = {
                        "area": f"{area_calc:.2f} m2", 
                        "divergencia": "Aterro e construcao detetados em zona de culturas (COS2023)", [cite: 6, 27]
                        "regime": "RAN (Reserva Agricola Nacional)" [cite: 8, 28]
                    }
                    parecer = redigir_parecer_ia(dados_ia, modelo_selecionado)
                    mapa_img = gerar_mapa_tecnico(user_gdf)
                    pdf_path = exportar_pdf(parecer, mapa_img)
                    
                    st.success("Relatório concluído!")
                    with open(pdf_path, "rb") as f:
                        st.download_button("📥 Baixar PDF Consolidado", f, file_name=pdf_path)
                    st.markdown(parecer)
        else:
            st.warning("Insere a API Key para redigir o relatório.")

