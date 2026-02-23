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
                    uso_fiscal = inter['tipo_obra'].iloc[0] if 'tipo_obra' in inter.columns else "Atributo 'tipo_obra' ausente"
                    if str(uso_oficial).strip().lower() != str(uso_fiscal).strip().lower():
                        analise_uso_solo = f"⚠️ DIVERGÊNCIA: A COS classifica como '{uso_oficial}', mas detetado '{uso_fiscal}'."
                    else:
                        analise_uso_solo = f"✅ COERENTE: O uso '{uso_fiscal}' coincide com a classificação da COS."
                else:
                    # Definições Jurídicas e Coimas
                    info_juridica = {
                        "REN": {
                            "lei": "Regime Jurídico da REN (DL n.º 166/2008).",
                            "artigo": "Artigo 20.º (Interdições). Proibidas obras e alteração do relevo.",
                            "coima": "Singulares: €2.000 a €3.700 | Coletivas: €15.000 a €44.800."
                        },
                        "RAN": {
                            "lei": "Regime Jurídico da RAN (DL n.º 73/2009).",
                            "artigo": "Artigo 22.º (Utilizações Proibidas). Solo de proteção agrícola.",
                            "coima": "Singulares: €500 a €3.700 | Coletivas: €2.500 a €44.800."
                        },
                        "Rede Natura": {
                            "lei": "DL n.º 142/2008 e Lei n.º 50/2006.",
                            "artigo": "Proteção de Habitats. Sujeito a AIA junto do ICNF.",
                            "coima": "Muito Graves (Coletivas): €24.000 a €5.000.000."
                        }
                    }
                    resultados.append({
                        "Regime": nome, "Area": round(area_int, 2), "Perc": round(perc, 1),
                        "Lei": info_juridica[nome]["lei"], "Artigo": info_juridica[nome]["artigo"], 
                        "Coima": info_juridica[nome]["coima"]
                    })
    return resultados, analise_uso_solo, area_total

# --- FUNÇÃO CARTOGRÁFICA (TRAMAS E LEGENDA) ---

def criar_mapa_imagem(user_gdf, resultados):
    fig, ax = plt.subplots(figsize=(10, 8))
    user_gdf_web = user_gdf.to_crs(epsg=3857)
    
    estilos = {
        "REN": {"cor": "#2ecc71", "hatch": "////", "label": "REN (Diagonais Verdes)"},
        "RAN": {"cor": "#f1c40f", "hatch": "\\\\\\\\", "label": "RAN (Amarelo Sólido)"},
        "Rede Natura": {"cor": "#8B4513", "hatch": "----", "label": "Rede Natura (Horizontais Castanhas)"}
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
                                                      hatch=estilo["hatch"], label=estilo["label"], alpha=0.7))

    user_gdf_web.plot(ax=ax, facecolor="none", edgecolor="red", linewidth=2.5, zorder=2)
    legend_elements.append(Line2D([0], [0], color='red', linewidth=2.5, label='Área Fiscalizada (Contorno)'))
    
    if legend_elements:
        ax.legend(handles=legend_elements, loc='upper right', frameon=True, facecolor='white', framealpha=0.9)
    
    ax.set_axis_off()
    bounds = user_gdf_web.total_bounds
    ax.set_xlim([bounds[0] - 60, bounds[2] + 60])
    ax.set_ylim([bounds[1] - 60, bounds[3] + 60])
    
    temp_img = "mapa_temp.png"
    plt.savefig(temp_img, bbox_inches='tight', dpi=150)
    plt.close()
    return temp_img

# --- GERAÇÃO DO WORD ---

def gerar_word(user_gdf, resultados, analise_uso, area_total):
    doc = Document()
    doc.add_heading('Relatório Técnico de Fiscalização Territorial', 0)
    
    doc.add_heading('1. Enquadramento Geográfico', level=1)
    img_path = criar_mapa_imagem(user_gdf, resultados)
    doc.add_picture(img_path, width=Inches(5.8))
    os.remove(img_path)
    doc.add_paragraph(f"Data: {date.today().strftime('%d/%m/%Y')} | Área Total: {area_total:.2f} m²")

    doc.add_heading('2. Ocupação do Solo (COS 2023)', level=1)
    doc.add_paragraph(analise_uso)

    doc.add_heading('3. Análise Jurídica e Coimas', level=1)
    if not resultados:
        doc.add_paragraph("Nenhuma servidão detetada.")
    else:
        for res in resultados:
            doc.add_heading(f"Regime: {res['Regime']}", level=2)
            p = doc.add_paragraph()
            p.add_run(f"Sobreposição: {res['Area']} m² ({res['Perc']}%)\n").bold = True
            p.add_run(f"Lei: {res['Lei']}\nArtigo: {res['Artigo']}\nCoima: {res['Coima']}")

    doc.add_heading('4. Medidas de Tutela', level=1)
    for m in ["Levantamento de Auto de Notícia;", "Embargo de obra;", "Notificação para reposição."]:
        doc.add_paragraph(m, style='List Number')

    fname = "Relatorio_Fiscalizacao.docx"
    doc.save(fname)
    return fname

# --- INTERFACE STREAMLIT COM AUTO-ZOOM ---

st.sidebar.title("📁 Dados")
uploaded_file = st.sidebar.file_uploader("Upload GeoJSON", type=['geojson'])

st.title("🛡️ Fiscalização SIG Territorial")

col_map, col_res = st.columns([2, 1])

with col_map:
    # Definimos o mapa com Google Hybrid
    m = leafmap.Map(google_map="HYBRID")
    
    if uploaded_file:
        user_gdf = gpd.read_file(uploaded_file).to_crs(epsg=3763)
        m.add_gdf(user_gdf, layer_name="Fiscalização", style={'color': 'red', 'weight': 3})
        
        # FORÇAR ZOOM NO MAPA INTERATIVO
        m.zoom_to_gdf(user_gdf)
    
    m.to_streamlit(height=600)

with col_res:
    if uploaded_file:
        res, uso_txt, a_total = realizar_analise(user_gdf)
        st.subheader("📊 Painel")
        st.metric("Área", f"{a_total:.1f} m²")
        st.info(uso_txt)
        
        if st.button("📝 Gerar Word Final"):
            with st.spinner('A gerar relatório...'):
                doc_path = gerar_word(user_gdf, res, uso_txt, a_total)
                with open(doc_path, "rb") as f:
                    st.download_button("📥 Descarregar", f, file_name=doc_path)
    else:
        st.info("Carregue um GeoJSON para começar.")
