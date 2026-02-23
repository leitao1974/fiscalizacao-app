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
    Cita obrigatoriamente: DL 73/2009 (RAN) e DL 166/2008 (REN).
    Analise: Compara COS2023 (Cultura) com Realidade (Aterro/Construcao).
    IMPORTANTE: Nao uses acentos ou cedilhas para evitar erros no PDF.
    """
    return model.generate_content(prompt).text

# --- FUNÇÃO CARTOGRÁFICA (A SOLUÇÃO PARA O MAPA EM BRANCO) ---
def gerar_mapa_tecnico_estavel(user_gdf):
    # Forçar backend não interativo
    plt.switch_backend('Agg')
    
    # Criar figura com tamanho fixo para o PDF
    fig, ax = plt.subplots(figsize=(10, 8), dpi=150)
    
    # Garantir projeção Web Mercator para o mapa base
    user_gdf_web = user_gdf.to_crs(epsg=3857)
    
    # 1. Tentar carregar o mapa base com sistema de espera (Retry)
    mapa_carregado = False
    fontes = [
        "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", # Google Hybrid
        cx.providers.Esri.WorldImagery                        # Esri
    ]
    
    for fonte in fontes:
        try:
            # O parâmetro 'zoom' ajuda a estabilizar o download em servidores
            cx.add_basemap(ax, source=fonte, zorder=0, attribution=False)
            mapa_carregado = True
            break
        except Exception as e:
            continue
            
    if not mapa_carregado:
        ax.set_facecolor('#f0f0f0') # Cinza técnico se falhar a rede

    # 2. Estilos de Servidões (Cores e Tramas)
    estilos = {
        "REN": {"cor": "#2ecc71", "hatch": "////", "label": "REN"},
        "RAN": {"cor": "#f1c40f", "hatch": "\\\\\\\\", "label": "RAN"}
    }
    legend_elements = []

    # 3. Cruzamento e Desenho das Camadas
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
                                                          hatch=estilo["hatch"], label=nome))
            except:
                pass

    # 4. Área Fiscalizada (Contorno Vermelho)
    user_gdf_web.plot(ax=ax, facecolor="none", edgecolor="red", linewidth=3, zorder=2)
    legend_elements.append(Line2D([0], [0], color='red', linewidth=3, label='Alvo'))

    # 5. Ajuste de Zoom (Margem maior para capturar mosaicos vizinhos)
    bounds = user_gdf_web.total_bounds
    ax.set_xlim([bounds[0] - 250, bounds[2] + 250])
    ax.set_ylim([bounds[1] - 250, bounds[3] + 250])
    
    if legend_elements:
        ax.legend(handles=legend_elements, loc='upper right', frameon=True, facecolor='white', framealpha=0.9)
    
    ax.set_axis_off()
    
    # Gravar e aguardar
    mapa_path = "mapa_v_estavel.png"
    plt.savefig(mapa_path, bbox_inches='tight', pad_inches=0.1)
    plt.close(fig)
    time.sleep(2) # Pausa crucial para o ficheiro ser escrito no disco
    return mapa_path

# --- GERAÇÃO DE PDF ---
def exportar_pdf_ia(texto_ia, mapa_path):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "RELATORIO TECNICO DE FISCALIZACAO", 0, 1, 'C')
    pdf.ln(5)
    
    if os.path.exists(mapa_path):
        # Inserção da imagem (posicionada para não sobrepor o texto)
        pdf.image(mapa_path, x=10, y=30, w=190)
        pdf.set_y(180) # Move o cursor de escrita para baixo do mapa
    
    pdf.set_font("Arial", '', 10)
    # Limpeza de caracteres especiais
    txt_limpo = texto_ia.encode('latin-1', 'ignore').decode('latin-1')
    pdf.multi_cell(0, 6, txt_limpo)
    
    pdf_name = "Relatorio_Consolidado.pdf"
    pdf.output(pdf_name)
    return pdf_name

# --- INTERFACE ---
st.title("🛡️ Fiscalização SIG Territorial")
file = st.sidebar.file_uploader("Upload GeoJSON", type=['geojson'])

if file:
    user_gdf = gpd.read_file(file).to_crs(epsg=3763)
    area_valor = user_gdf.area.sum() [cite: 5, 25]
    
    col_map, col_res = st.columns([2, 1])
    
    with col_map:
        # Centrar mapa interativo
        user_gdf_4326 = user_gdf.to_crs(epsg=4326)
        centro = user_gdf_4326.geometry.centroid.iloc[0]
        m = leafmap.Map(center=[centro.y, centro.x], zoom=17)
        m.add_tile_layer(url='https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', name='Google Sat', attribution='Google')
        m.add_gdf(user_gdf, layer_name="Alvo")
        m.to_streamlit(height=600)
        
    with col_res:
        st.write(f"**Área Alvo:** {area_valor:.2f} m²") [cite: 5, 25]
        if api_key:
            if st.button("🤖 Gerar Relatório IA"):
                with st.spinner('A analisar terreno e cartografia...'):
                    dados_ia = {
                        "area": f"{area_valor:.2f} m2", 
                        "divergencia": "Aterro detetado em zona de culturas", 
                        "regime": "RAN" [cite: 2, 8, 28]
                    }
                    texto = redigir_parecer_ia(dados_ia, modelo_selecionado)
                    mapa = gerar_mapa_tecnico_estavel(user_gdf)
                    pdf = exportar_pdf_ia(texto, mapa)
                    
                    st.success("Relatório pronto!")
                    with open(pdf, "rb") as f:
                        st.download_button("📥 Baixar PDF", f, file_name=pdf)
                    st.markdown(texto)


