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

# --- FUNÇÃO CARTOGRÁFICA (FORÇAR MAPA BASE) ---
def gerar_mapa_tecnico(user_gdf):
    plt.switch_backend('Agg')
    # Aumentamos o tamanho para forçar o sistema a capturar os tiles
    fig, ax = plt.subplots(figsize=(12, 10), dpi=150)
    
    # Converter para Web Mercator (EPSG:3857)
    user_gdf_web = user_gdf.to_crs(epsg=3857)
    
    # 1. TENTATIVA DE MAPA BASE COM MÚLTIPLOS PROVEDORES E TIMEOUT
    mapa_carregado = False
    # Google Hybrid é o mais estável para detetar ocupação do solo
    fontes = [
        "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", # Google Hybrid
        cx.providers.Esri.WorldImagery,                       # Esri Satellite
        cx.providers.OpenStreetMap.Mapnik                     # OSM (Fallback final)
    ]
    
    for fonte in fontes:
        try:
            # Adicionamos o mapa base ANTES de qualquer outro desenho
            cx.add_basemap(ax, source=fonte, zorder=0, attribution=False, alpha=1.0)
            mapa_carregado = True
            break
        except:
            continue
    
    if not mapa_carregado:
        ax.set_facecolor('#e0e0e0') # Fundo cinza se a internet do servidor bloquear tudo

    # 2. Estilos por Servidão (Tramas e Cores)
    estilos = {
        "REN": {"cor": "#2ecc71", "hatch": "////", "label": "Reserva Ecologica Nacional (REN)"},
        "RAN": {"cor": "#f1c40f", "hatch": "\\\\\\\\", "label": "Reserva Agricola Nacional (RAN)"}
    }
    legend_elements = []

    # 3. Desenho das Servidões (data/)
    for nome, estilo in estilos.items():
        path = f"data/{nome.lower()}_amostra.geojson"
        if os.path.exists(path):
            camada = gpd.read_file(path).to_crs(epsg=3857)
            inter = gpd.overlay(camada, user_gdf_web, how='intersection')
            if not inter.empty:
                inter.plot(ax=ax, facecolor=estilo["cor"], alpha=0.5, 
                           hatch=estilo["hatch"], edgecolor=estilo["cor"], zorder=1)
                legend_elements.append(mpatches.Patch(facecolor=estilo["cor"], alpha=0.6, 
                                                      hatch=estilo["hatch"], label=estilo["label"]))

    # 4. Área Fiscalizada (Contorno Vermelho)
    user_gdf_web.plot(ax=ax, facecolor="none", edgecolor="red", linewidth=4, zorder=2)
    legend_elements.append(Line2D([0], [0], color='red', linewidth=4, label='Area Alvo (15591 m2)'))

    # 5. Ajustes de Enquadramento
    bounds = user_gdf_web.total_bounds
    # Margem generosa de 400m para obrigar o download de mais tiles em redor
    ax.set_xlim([bounds[0] - 400, bounds[2] + 400])
    ax.set_ylim([bounds[1] - 400, bounds[3] + 400])
    
    if legend_elements:
        ax.legend(handles=legend_elements, loc='upper right', frameon=True, facecolor='white', framealpha=0.9)
    
    ax.set_axis_off()
    
    mapa_path = "mapa_tecnico_oficial.png"
    # O comando bbox_inches='tight' às vezes corta o mapa base, vamos removê-lo ou suavizá-lo
    plt.savefig(mapa_path, dpi=150, pad_inches=0.1)
    plt.close(fig)
    
    # Aguardar 2 segundos para o sistema de ficheiros consolidar a imagem
    time.sleep(2)
    return mapa_path

# --- GERAÇÃO DE PDF ---
def exportar_pdf(texto_ia, mapa_path):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "RELATORIO TECNICO DE FISCALIZACAO TERRITORIAL", 0, 1, 'C')
    pdf.ln(5)
    
    if os.path.exists(mapa_path):
        # x=10, y=30, w=190
        pdf.image(mapa_path, x=10, y=30, w=190)
        pdf.set_y(185) # Garantir que o texto começa bem abaixo do mapa
    
    pdf.set_font("Arial", '', 10)
    txt_fpdf = texto_ia.encode('latin-1', 'ignore').decode('latin-1')
    pdf.multi_cell(0, 6, txt_fpdf)
    
    pdf_name = "Relatorio_Final_Consolidado.pdf"
    pdf.output(pdf_name)
    return pdf_name

# --- INTERFACE ---
st.title("🛡️ Sistema de Fiscalização SIG")
file = st.sidebar.file_uploader("Upload GeoJSON", type=['geojson'])

if file:
    user_gdf = gpd.read_file(file).to_crs(epsg=3763)
    area_valor = user_gdf.area.sum()
    
    col_map, col_res = st.columns([2, 1])
    
    with col_map:
        user_gdf_4326 = user_gdf.to_crs(epsg=4326)
        centro = user_gdf_4326.geometry.centroid.iloc[0]
        m = leafmap.Map(center=[centro.y, centro.x], zoom=17)
        m.add_tile_layer(url='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', 
                         name='Google Hybrid', attribution='Google')
        m.add_gdf(user_gdf, layer_name="Alvo")
        m.to_streamlit(height=600)
        
    with col_res:
        st.subheader("📊 Info Parcela")
        st.write(f"**Área:** {area_valor:.2f} m²")
        
        if api_key:
            if st.button("🤖 Gerar Relatório Completo"):
                with st.spinner('A capturar cartografia e redigir parecer...'):
                    dados_ia = {
                        "area": f"{area_valor:.2f} m2", 
                        "divergencia": "Aterro e construcao em zona de culturas (COS2023)", 
                        "regime": "RAN (DL 73/2009)"
                    }
                    texto = redigir_parecer_ia(dados_ia, modelo_selecionado)
                    mapa = gerar_mapa_tecnico(user_gdf)
                    pdf = exportar_pdf(texto, mapa)
                    
                    st.success("Relatório pronto!")
                    with open(pdf, "rb") as f:
                        st.download_button("📥 Baixar PDF", f, file_name=pdf)
                    st.markdown(texto)


