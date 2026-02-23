import streamlit as st
import geopandas as gpd
import pandas as pd
import leafmap.foliumap as leafmap
from docx import Document
from docx.shared import Pt, Inches
from datetime import date
import os
import matplotlib.pyplot as plt
import contextily as cx

# 1. Configuração de Interface
st.set_page_config(layout="wide", page_title="Fiscalização SIG Portugal", page_icon="🛡️")

# --- MOTOR DE ANÁLISE GEOSPACIAL E JURÍDICA ---

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
                        analise_uso_solo = f"⚠️ DIVERGÊNCIA: COS indica '{uso_oficial}', detetado '{uso_fiscal}'."
                    else:
                        analise_uso_solo = f"✅ COERENTE: Uso '{uso_fiscal}' coincide com a COS."
                else:
                    info_jur = {
                        "REN": {"lei": "DL 166/2008", "art": "Art. 20.º", "coima": "€2.000 a €44.800"},
                        "RAN": {"lei": "DL 73/2009", "art": "Art. 22.º", "coima": "€500 a €44.800"},
                        "Rede Natura": {"lei": "Lei 50/2006", "art": "DL 142/2008", "coima": "Até €5.000.000"}
                    }
                    resultados.append({
                        "Regime": nome, "Area": round(area_int, 2), "Perc": round(perc, 1),
                        "Lei": info_jur[nome]["lei"], "Artigo": info_jur[nome]["art"], "Coima": info_jur[nome]["coima"]
                    })
    
    return resultados, analise_uso_solo, area_total

# --- FUNÇÃO PARA GERAR O MAPA IMAGEM ---

def criar_mapa_imagem(user_gdf):
    fig, ax = plt.subplots(figsize=(10, 8))
    # Projetar para Web Mercator para o contextily (fundo de satélite)
    user_gdf_web = user_gdf.to_crs(epsg=3857)
    user_gdf_web.plot(ax=ax, facecolor="none", edgecolor="red", linewidth=2.5)
    
    try:
        cx.add_basemap(ax, source=cx.providers.Esri.WorldImagery)
    except:
        st.warning("Não foi possível carregar o mapa de fundo para o relatório.")
    
    ax.set_axis_off()
    temp_img = "mapa_relatorio.png"
    plt.savefig(temp_img, bbox_inches='tight', dpi=150)
    plt.close()
    return temp_img

# --- MOTOR DO RELATÓRIO WORD ---

def gerar_word(user_gdf, resultados, analise_uso, area_total):
    doc = Document()
    doc.add_heading('Relatório Técnico de Fiscalização Territorial', 0)
    
    # 1. Mapa e Localização
    doc.add_heading('1. Localização e Enquadramento Visual', level=1)
    img_path = criar_mapa_imagem(user_gdf)
    doc.add_picture(img_path, width=Inches(5.8))
    os.remove(img_path)
    
    doc.add_paragraph(f"Área Total Fiscalizada: {area_total:.2f} m²")

    # 2. Análise COS
    doc.add_heading('2. Verificação de Ocupação do Solo (COS 2023)', level=1)
    doc.add_paragraph(analise_uso)

    # 3. Análise Jurídica
    doc.add_heading('3. Servidões e Molduras Contraordenacionais', level=1)
    if not resultados:
        doc.add_paragraph("Sem restrições detetadas.")
    else:
        for res in resultados:
            doc.add_heading(f"Regime: {res['Regime']}", level=2)
            p = doc.add_paragraph()
            p.add_run(f"Sobreposição: {res['Area']} m² ({res['Perc']}%)\n").bold = True
            p.add_run(f"Base Legal: {res['Lei']} ({res['Artigo']})\n")
            p.add_run(f"Coima Prevista: {res['Coima']}")

    # 4. Medidas de Tutela
    doc.add_heading('4. Conclusões e Recomendações', level=1)
    medidas = ["Levantamento de Auto de Notícia;", "Embargo de obra (se aplicável);", "Notificação para reposição."]
    for m in medidas:
        doc.add_paragraph(m, style='List Number')

    fname = "Relatorio_Final_Fiscalizacao.docx"
    doc.save(fname)
    return fname

# --- INTERFACE ---

st.title("🛡️ Fiscalização SIG 2026")
uploaded_file = st.sidebar.file_uploader("Upload GeoJSON", type=['geojson'])

col1, col2 = st.columns([2, 1])

with col1:
    m = leafmap.Map(center=[39.5, -8.0], zoom=7, google_map="HYBRID")
    if uploaded_file:
        user_gdf = gpd.read_file(uploaded_file).to_crs(epsg=3763)
        m.add_gdf(user_gdf, layer_name="Fiscalização")
        m.zoom_to_gdf(user_gdf)
    m.to_streamlit(height=600)

with col2:
    if uploaded_file:
        res, uso_txt, a_total = realizar_analise(user_gdf)
        st.info(uso_txt)
        if st.button("📝 Gerar Relatório com Mapa"):
            with st.spinner('A gerar relatório e mapa de satélite...'):
                doc_path = gerar_word(user_gdf, res, uso_txt, a_total)
                with open(doc_path, "rb") as f:
                    st.download_button("📥 Baixar Relatório Word", f, file_name=doc_path)
    else:
        st.info("Aguardando ficheiro...")

