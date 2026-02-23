import streamlit as st
import geopandas as gpd
import pandas as pd
import leafmap.foliumap as leafmap
from docx import Document
from docx.shared import Pt, Inches
from datetime import date
import os
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
import contextily as cx

# 1. Configuração da Página
st.set_page_config(layout="wide", page_title="Fiscalização Territorial SIG", page_icon="🛡️")

# --- FUNÇÕES DE APOIO ---

def realizar_analise(user_gdf):
    area_total = user_gdf.area.sum()
    resultados = []
    analise_uso_solo = "Ficheiro COS não encontrado."
    
    camadas = {
        "REN": "data/ren_amostra.geojson",
        "RAN": "data/ran_amostra.geojson",
        "Rede Natura": "data/rede_natura.geojson",
        "COS": "data/cos_amostra.geojson" 
    }

    for nome, path in camadas.items():
        if os.path.exists(path):
            camada_gdf = gpd.read_file(path).to_crs(epsg=3763)
            inter = gpd.overlay(user_gdf, camada_gdf, how='intersection')
            
            if not inter.empty:
                area_int = inter.area.sum()
                perc = (area_int / area_total) * 100
                
                if nome == "COS":
                    uso_oficial = inter['COS23_n4_L'].iloc[0]
                    uso_fiscal = inter['tipo_obra'].iloc[0] if 'tipo_obra' in inter.columns else "Não definido"
                    analise_uso_solo = f"Análise COS: Oficial '{uso_oficial}' vs Detetado '{uso_fiscal}'."
                else:
                    resultados.append({
                        "Regime": nome, "Area": round(area_int, 2), "Perc": round(perc, 1),
                        "Lei": "DL n.º 166/2008" if nome == "REN" else "DL n.º 73/2009",
                        "Artigo": "Artigo 20.º" if nome == "REN" else "Artigo 22.º",
                        "Coima": "Consultar anexo jurídico completo."
                    })
    return resultados, analise_uso_solo, area_total

def criar_mapa_imagem(user_gdf, resultados):
    fig, ax = plt.subplots(figsize=(10, 8))
    user_gdf_web = user_gdf.to_crs(epsg=3857)
    estilos = {
        "REN": {"cor": "#2ecc71", "hatch": "////", "label": "REN"},
        "RAN": {"cor": "#f1c40f", "hatch": "\\\\\\\\", "label": "RAN"},
        "Rede Natura": {"cor": "#8B4513", "hatch": "----", "label": "Natura 2000"}
    }
    legend_elements = []
    
    try:
        cx.add_basemap(ax, source=cx.providers.Esri.WorldImagery, zorder=0)
    except:
        pass

    for res in resultados:
        nome = res['Regime']
        path = f"data/{nome.lower().replace(' ', '_')}_amostra.geojson"
        if os.path.exists(path):
            camada = gpd.read_file(path).to_crs(epsg=3857)
            patch = gpd.overlay(camada, user_gdf_web, how='intersection')
            if not patch.empty:
                estilo = estilos.get(nome, {"cor": "gray", "hatch": None})
                patch.plot(ax=ax, facecolor=estilo["cor"], edgecolor=estilo["cor"], hatch=estilo["hatch"], alpha=0.4, zorder=1)
                legend_elements.append(mpatches.Patch(facecolor=estilo["cor"], edgecolor=estilo["cor"], hatch=estilo["hatch"], label=estilo["label"], alpha=0.7))

    user_gdf_web.plot(ax=ax, facecolor="none", edgecolor="red", linewidth=2.5, zorder=2)
    legend_elements.append(Line2D([0], [0], color='red', linewidth=2.5, label='Área Fiscalizada'))
    
    if legend_elements:
        ax.legend(handles=legend_elements, loc='upper right', frameon=True, facecolor='white', framealpha=0.9)
    
    ax.set_axis_off()
    bounds = user_gdf_web.total_bounds
    ax.set_xlim([bounds[0] - 80, bounds[2] + 80])
    ax.set_ylim([bounds[1] - 80, bounds[3] + 80])
    
    temp_img = "mapa_temp.png"
    plt.savefig(temp_img, bbox_inches='tight', dpi=150)
    plt.close()
    return temp_img

# --- INTERFACE E LÓGICA DE ZOOM ---

st.title("🛡️ Fiscalização SIG Territorial")
uploaded_file = st.sidebar.file_uploader("Carregar GeoJSON de Fiscalização", type=['geojson'])

# Colunas para visualização
col_map, col_data = st.columns([2, 1])

with col_map:
    # Criar o mapa base
    m = leafmap.Map(google_map="HYBRID")
    
    if uploaded_file:
        # 1. Ler o ficheiro e converter coordenadas
        user_gdf = gpd.read_file(uploaded_file).to_crs(epsg=3763)
        
        # 2. Adicionar ao mapa interactivo
        m.add_gdf(user_gdf, layer_name="Área de Fiscalização", info_mode=None)
        
        # 3. FORÇAR O ZOOM IMEDIATO (O que estava a faltar)
        m.zoom_to_gdf(user_gdf)
    
    m.to_streamlit(height=650)

with col_data:
    if uploaded_file:
        res, uso_txt, a_total = realizar_analise(user_gdf)
        st.subheader("📊 Resultados Rápidos")
        st.metric("Área Fiscalizada", f"{a_total:.1f} m²")
        st.write(uso_txt)
        
        if st.button("📝 Gerar Relatório Jurídico"):
            # Lógica de geração de Word (omitida aqui por brevidade, mantém a anterior)
            st.success("Relatório pronto para download!")
    else:
        st.info("Por favor, carregue um polígono GeoJSON para navegar até à zona.")
