import streamlit as st
import geopandas as gpd
import leafmap.foliumap as leafmap
from docx import Document
from datetime import date
import os

st.set_page_config(layout="wide", page_title="Fiscalização SIG Portugal")

# --- FUNÇÕES DE APOIO ---

def gerar_relatorio_word(resultados, area_total):
    doc = Document()
    doc.add_heading('Relatório de Fiscalização Territorial', 0)
    
    doc.add_heading('1. Resumo da Análise', level=1)
    doc.add_paragraph(f"Data: {date.today().strftime('%d/%m/%Y')}")
    doc.add_paragraph(f"Área Total do Polígono: {area_total:.2f} m²")

    doc.add_heading('2. Interseções Detetadas', level=1)
    if not resultados:
        doc.add_paragraph("Nenhuma sobreposição detetada com as camadas de restrição.")
    else:
        for res in resultados:
            p = doc.add_paragraph(style='List Bullet')
            p.add_run(f"{res['Regime']}: ").bold = True
            p.add_run(f"{res['Área Afetada (m2)']} m² ({res['%']}%)")
            doc.add_paragraph(f"Parecer: {res['Parecer']}")

    filename = "Relatorio_Fiscalizacao.docx"
    doc.save(filename)
    return filename

# --- INTERFACE STREAMLIT ---

st.sidebar.title("🛡️ Painel de Controlo")
uploaded_file = st.sidebar.file_uploader("Carregar polígono (GeoJSON/KML)", type=['geojson', 'kml'])

st.title("Sistema de Fiscalização: REN / RAN / Natura 2000")

col1, col2 = st.columns([2, 1])

with col1:
    m = leafmap.Map(center=[39.5, -8.0], zoom=7)
    # Camadas WMS oficiais (Visualização)
    m.add_wms_layer(url="https://sig.dgterritorio.gov.pt/geoserver/wms", layers="REN_Continente", name="REN", transparent=True)
    
    if uploaded_file:
        user_gdf = gpd.read_file(uploaded_file).to_crs(epsg=3763)
        m.add_gdf(user_gdf, layer_name="Área em Análise")
        m.zoom_to_gdf(user_gdf)
    m.to_streamlit(height=600)

with col2:
    if uploaded_file:
        st.subheader("📊 Resultados da Interseção")
        area_total = user_gdf.area.sum()
        
        # Simulação de base de dados (Caminhos para os teus ficheiros no GitHub)
        camadas = {
            "REN": "data/ren_amostra.geojson",
            "RAN": "data/ran_amostra.geojson",
            "Rede Natura": "data/rede_natura.geojson"
        }
        
        resultados_finais = []
        
        for nome, path in camadas.items():
            if os.path.exists(path):
                camada_gdf = gpd.read_file(path).to_crs(epsg=3763)
                inter = gpd.overlay(user_gdf, camada_gdf, how='intersection')
                if not inter.empty:
                    area_int = inter.area.sum()
                    perc = (area_int / area_total) * 100
                    
                    parecer = "Carece de autorização específica."
                    if nome == "REN": parecer = "Interdição de construção (Art. 20º DL 166/2008)."
                    
                    resultados_finais.append({
                        "Regime": nome, "Área Afetada (m2)": round(area_int, 2),
                        "%": round(perc, 1), "Parecer": parecer
                    })
                    st.error(f"⚠️ {nome}: {round(perc,1)}% de sobreposição")
            else:
                st.info(f"Ficheiro {nome} não encontrado na pasta /data.")

        if st.button("📝 Gerar Relatório Word"):
            fname = gerar_relatorio_word(resultados_finais, area_total)
            with open(fname, "rb") as f:
                st.download_button("Download Relatório", f, file_name=fname)