import streamlit as st
import geopandas as gpd
import pandas as pd
import leafmap.foliumap as leafmap
from docx import Document
from datetime import date
import os

# Configuração da Página
st.set_page_config(layout="wide", page_title="Fiscalização SIG Portugal", page_icon="🛡️")

def realizar_analise(user_gdf):
    area_total = user_gdf.area.sum()
    resultados = []
    analise_uso_solo = "Ficheiro COS não encontrado na pasta /data."
    
    # Caminhos dos ficheiros no GitHub
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
                    # Lógica da COS com as tuas colunas específicas
                    uso_oficial = inter['COS23_n4_L'].iloc[0]
                    uso_fiscal = inter['tipo_obra'].iloc[0] if 'tipo_obra' in inter.columns else "Atributo 'tipo_obra' ausente"
                    
                    if str(uso_oficial).strip() != str(uso_fiscal).strip():
                        analise_uso_solo = f"⚠️ DIVERGÊNCIA detetada: A COS classifica como '{uso_oficial}', mas o levantamento indica '{uso_fiscal}'."
                    else:
                        analise_uso_solo = f"✅ COERENTE: O uso '{uso_fiscal}' coincide com a classificação da COS."
                else:
                    parecer = ""
                    if nome == "REN": parecer = "Restrição REN (DL 166/2008). Interdição de construção ou alteração de relevo."
                    elif nome == "RAN": parecer = "Restrição RAN (DL 73/2009). Solo de alta aptidão agrícola."
                    elif nome == "Rede Natura": parecer = "Sítio Protegido (DL 142/2008). Requer parecer do ICNF."
                    
                    resultados.append({
                        "Regime": nome,
                        "Área (m2)": round(area_int, 2),
                        "Percentagem": round(perc, 1),
                        "Parecer Jurídico": parecer
                    })
    
    return resultados, analise_uso_solo, area_total

def gerar_word(resultados, analise_uso, area_total):
    doc = Document()
    doc.add_heading('Relatório de Fiscalização Territorial', 0)
    
    doc.add_heading('1. Identificação e Área', level=1)
    doc.add_paragraph(f"Data: {date.today().strftime('%d/%m/%Y')}")
    doc.add_paragraph(f"Área Total Analisada: {area_total:.2f} m²")

    doc.add_heading('2. Verificação de Uso do Solo (COS 2023)', level=1)
    doc.add_paragraph(analise_uso)

    doc.add_heading('3. Cruzamento com Servidões e Restrições', level=1)
    if not resultados:
        doc.add_paragraph("Não foram detetadas sobreposições com REN, RAN ou Rede Natura 2000.")
    else:
        for res in resultados:
            p = doc.add_paragraph(style='List Bullet')
            p.add_run(f"{res['Regime']}: ").bold = True
            p.add_run(f"{res['Área (m2)']} m² ({res['Percentagem']}%)")
            doc.add_paragraph(f"Enquadramento: {res['Parecer Jurídico']}")

    fname = "Relatorio_Fiscalizacao.docx"
    doc.save(fname)
    return fname

# --- INTERFACE ---
st.title("🛡️ Sistema de Apoio à Fiscalização")
uploaded_file = st.sidebar.file_uploader("Carregue o polígono de localização (GeoJSON)", type=['geojson'])

col1, col2 = st.columns([2, 1])

with col1:
    m = leafmap.Map(center=[39.5, -8.0], zoom=7, google_map="HYBRID")
    if uploaded_file:
        user_gdf = gpd.read_file(uploaded_file).to_crs(epsg=3763)
        m.add_gdf(user_gdf, layer_name="Área a Analisar")
        m.zoom_to_gdf(user_gdf)
    m.to_streamlit(height=600)

with col2:
    if uploaded_file:
        res, uso_txt, a_total = realizar_analise(user_gdf)
        st.subheader("📊 Resultados")
        st.write(f"**Área:** {a_total:.2f} m²")
        st.info(uso_txt)
        
        if res:
            st.table(pd.DataFrame(res)[['Regime', 'Percentagem']])
        
        if st.button("📝 Gerar Relatório em Word"):
            path_doc = gerar_word(res, uso_txt, a_total)
            with open(path_doc, "rb") as f:
                st.download_button("Baixar Relatório", f, file_name=path_doc)
    else:
        st.info("Por favor, carregue um ficheiro GeoJSON no menu lateral.")

