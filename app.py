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

# --- MOTOR DE ANÁLISE GEOSPACIAL ---
def realizar_analise(user_gdf):
    area_total = user_gdf.area.sum()
    resultados = []
    analise_uso_solo = "Ficheiro COS não encontrado na pasta data/."
    
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
                        "REN": {
                            "lei": "Regime Jurídico da REN (DL n.º 166/2008).",
                            "art": "Artigo 20.º (Interdições). Proibição de obras e alteração de relevo.",
                            "coima": "Singulares: €2.000 a €3.700 | Coletivas: €15.000 a €44.800."
                        },
                        "RAN": {
                            "lei": "Regime Jurídico da RAN (DL n.º 73/2009).",
                            "art": "Artigo 22.º (Utilizações Proibidas). Solo de proteção agrícola.",
                            "coima": "Singulares: €500 a €3.700 | Coletivas: €2.500 a €44.800."
                        },
                        "Rede Natura": {
                            "lei": "Lei n.º 50/2006 (Contraordenações Ambientais).",
                            "art": "Proteção de Habitats. Requer parecer do ICNF.",
                            "coima": "Muito Graves (Coletivas): €24.000 a €5.000.000."
                        }
                    }
                    resultados.append({
                        "Regime": nome, "Area": round(area_int, 2), "Perc": round(perc, 1),
                        "Lei": info_jur[nome]["lei"], "Artigo": info_jur[nome]["art"], "Coima": info_jur[nome]["coima"]
                    })
    return resultados, analise_uso_solo, area_total

# --- FUNÇÃO DO MAPA PARA O WORD (SATÉLITE) ---
def criar_mapa_imagem(user_gdf, resultados):
    fig, ax = plt.subplots(figsize=(10, 8), dpi=150)
    user_gdf_web = user_gdf.to_crs(epsg=3857)
    
    # 1. Adicionar Mapa Base (ZORDER 0)
    try:
        cx.add_basemap(ax, source=cx.providers.Esri.WorldImagery, zorder=0)
    except:
        pass

    estilos = {
        "REN": {"cor": "#2ecc71", "hatch": "////", "label": "REN"},
        "RAN": {"cor": "#f1c40f", "hatch": "\\\\\\\\", "label": "RAN"},
        "Rede Natura": {"cor": "#8B4513", "hatch": "----", "label": "Natura 2000"}
    }
    legend_elements = []

    # 2. Desenhar Servidões (ZORDER 1)
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

    # 3. Contorno Vermelho (ZORDER 2)
    user_gdf_web.plot(ax=ax, facecolor="none", edgecolor="red", linewidth=3, zorder=2)
    legend_elements.append(Line2D([0], [0], color='red', linewidth=3, label='Área Fiscalizada'))

    # Zoom focado
    bounds = user_gdf_web.total_bounds
    ax.set_xlim([bounds[0] - 120, bounds[2] + 120])
    ax.set_ylim([bounds[1] - 120, bounds[3] + 120])
    
    if legend_elements:
        ax.legend(handles=legend_elements, loc='upper right', frameon=True, facecolor='white', framealpha=0.8)
    
    ax.set_axis_off()
    temp_img = "mapa_export.png"
    plt.savefig(temp_img, bbox_inches='tight', pad_inches=0.1)
    plt.close()
    return temp_img

# --- INTERFACE STREAMLIT ---
st.title("🛡️ Sistema de Fiscalização SIG")
uploaded_file = st.sidebar.file_uploader("Upload do ficheiro GeoJSON", type=['geojson'])

col_map, col_res = st.columns([2, 1])

with col_map:
    m = leafmap.Map(google_map="HYBRID")
    if uploaded_file:
        user_gdf = gpd.read_file(uploaded_file).to_crs(epsg=3763)
        m.add_gdf(user_gdf, layer_name="Fiscalização", style={'color': 'red', 'weight': 3})
        
        # ZOOM INTERATIVO
        centroid = user_gdf.to_crs(epsg=4326).centroid.iloc[0]
        m.set_center(centroid.x, centroid.y, zoom=16)
        m.zoom_to_gdf(user_gdf)
    m.to_streamlit(height=650)

with col_res:
    if uploaded_file:
        res, uso_txt, a_total = realizar_analise(user_gdf)
        st.subheader("📊 Painel de Análise")
        st.metric("Área Total", f"{a_total:.2f} m²")
        st.info(uso_txt)
        
        if st.button("📝 Gerar Relatório Word"):
            with st.spinner('A capturar mapa e dados...'):
                doc = Document()
                doc.add_heading('Relatório Técnico de Fiscalização Territorial', 0)
                
                # Inserir Imagem do Mapa
                img_path = criar_mapa_imagem(user_gdf, res)
                doc.add_picture(img_path, width=Inches(5.8))
                os.remove(img_path)
                
                doc.add_paragraph(f"Data da análise: {date.today().strftime('%d/%m/%Y')} | Área: {a_total:.2f} m²")
                
                doc.add_heading('1. Ocupação do Solo (COS 2023)', level=1)
                doc.add_paragraph(uso_txt)

                doc.add_heading('2. Enquadramento Jurídico e Servidões', level=1)
                if not res:
                    doc.add_paragraph("Não foram detetadas servidões administrativas.")
                else:
                    for r in res:
                        doc.add_heading(f"Regime: {r['Regime']}", level=2)
                        p = doc.add_paragraph()
                        p.add_run(f"Sobreposição: {r['Area']} m² ({r['Perc']}%)\n").bold = True
                        p.add_run(f"Lei: {r['Lei']}\nArtigo: {r['Artigo']}\nCoima: {r['Coima']}")

                doc.save("Relatorio_Final.docx")
                with open("Relatorio_Final.docx", "rb") as f:
                    st.download_button("📥 Descarregar Word", f, file_name="Relatorio_Final.docx")
