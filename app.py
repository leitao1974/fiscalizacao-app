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

# 1. Configuração de Interface
st.set_page_config(layout="wide", page_title="Fiscalização Territorial SIG", page_icon="🛡️")

# --- MOTOR DE ANÁLISE GEOSPACIAL ---
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
                    if str(uso_oficial).strip().lower() != str(uso_fiscal).strip().lower():
                        analise_uso_solo = f"⚠️ DIVERGÊNCIA: A COS classifica como '{uso_oficial}', mas detetado '{uso_fiscal}'."
                    else:
                        analise_uso_solo = f"✅ COERENTE: Uso '{uso_fiscal}' coincide com a classificação da COS."
                else:
                    info_jur = {
                        "REN": {"lei": "DL 166/2008", "art": "Art. 20.º", "coima": "€2.000 a €44.800"},
                        "RAN": {"lei": "DL 73/2009", "art": "Art. 22.º", "coima": "€500 a €3.700 | €2.500 a €44.800"},
                        "Rede Natura": {"lei": "Lei 50/2006", "art": "DL 142/2008", "coima": "Até €5.000.000"}
                    }
                    resultados.append({
                        "Regime": nome, "Area": round(area_int, 2), "Perc": round(perc, 1),
                        "Lei": info_jur[nome]["lei"], "Artigo": info_jur[nome]["art"], "Coima": info_jur[nome]["coima"]
                    })
    return resultados, analise_uso_solo, area_total

# --- FUNÇÃO CARTOGRÁFICA (CORREÇÃO DE MAPA BASE) ---
def criar_mapa_imagem(user_gdf, resultados):
    fig, ax = plt.subplots(figsize=(10, 8), dpi=150)
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
                estilo = estilos.get(nome)
                patch.plot(ax=ax, facecolor=estilo["cor"], edgecolor=estilo["cor"], 
                           hatch=estilo["hatch"], alpha=0.4, zorder=1)
                legend_elements.append(mpatches.Patch(facecolor=estilo["cor"], edgecolor=estilo["cor"], 
                                                      hatch=estilo["hatch"], label=nome, alpha=0.6))

    user_gdf_web.plot(ax=ax, facecolor="none", edgecolor="red", linewidth=2.5, zorder=2)
    legend_elements.append(Line2D([0], [0], color='red', linewidth=2.5, label='Área Fiscalizada'))

    bounds = user_gdf_web.total_bounds
    ax.set_xlim([bounds[0] - 100, bounds[2] + 100])
    ax.set_ylim([bounds[1] - 100, bounds[3] + 100])
    
    if legend_elements:
        ax.legend(handles=legend_elements, loc='upper right', frameon=True, facecolor='white')
    
    ax.set_axis_off()
    temp_img = "mapa_temp.png"
    plt.savefig(temp_img, bbox_inches='tight', pad_inches=0.1)
    plt.close()
    return temp_img

# --- INTERFACE ---
st.title("🛡️ Sistema de Fiscalização SIG")
uploaded_file = st.sidebar.file_uploader("Upload GeoJSON", type=['geojson'])

col_map, col_res = st.columns([2, 1])

with col_map:
    m = leafmap.Map(google_map="HYBRID")
    if uploaded_file:
        user_gdf = gpd.read_file(uploaded_file).to_crs(epsg=3763)
        m.add_gdf(user_gdf, layer_name="Fiscalização", style={'color': 'red', 'weight': 3})
        
        centroid = user_gdf.to_crs(epsg=4326).centroid.iloc[0]
        m.set_center(centroid.x, centroid.y, zoom=16)
        m.zoom_to_gdf(user_gdf)
    m.to_streamlit(height=600)

with col_res:
    if uploaded_file:
        res, uso_txt, a_total = realizar_analise(user_gdf)
        st.subheader("📊 Painel")
        st.metric("Área Fiscalizada", f"{a_total:.2f} m²")
        st.info(uso_txt)
        
        if st.button("📝 Gerar Relatório"):
            doc = Document()
            doc.add_heading('Relatório de Fiscalização Territorial', 0)
            img_path = criar_mapa_imagem(user_gdf, res)
            doc.add_picture(img_path, width=Inches(5.5))
            os.remove(img_path)
            
            doc.add_heading('Análise Jurídica e Coimas', level=1)
            for r in res:
                doc.add_heading(f"Regime: {r['Regime']}", level=2)
                doc.add_paragraph(f"Sobreposição: {r['Area']} m² ({r['Perc']}%)")
                doc.add_paragraph(f"Lei: {r['Lei']} | Artigo: {r['Artigo']}")
                doc.add_paragraph(f"Coima: {r['Coima']}")
            
            doc.add_heading('Medidas de Tutela', level=1)
            for m_tutela in ["Auto de Notícia", "Embargo", "Reposição"]:
                doc.add_paragraph(m_tutela, style='List Bullet')
            
            doc.save("Relatorio_Final.docx")
            with open("Relatorio_Final.docx", "rb") as f:
                st.download_button("📥 Baixar Relatório", f, file_name="Relatorio_Final.docx")
