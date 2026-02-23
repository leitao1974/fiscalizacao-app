import streamlit as st
import geopandas as gpd
import pandas as pd
import leafmap.foliumap as leafmap
from docx import Document
from docx.shared import Pt
from datetime import date
import os

# 1. Configuração da Página
st.set_page_config(layout="wide", page_title="Fiscalização Territorial SIG", page_icon="🛡️")

# --- FUNÇÕES DE PROCESSAMENTO GEOSPACIAL ---

def realizar_analise(user_gdf):
    """Cruza o polígono do utilizador com as camadas de referência na pasta data/"""
    area_total = user_gdf.area.sum()
    resultados = []
    analise_uso_solo = "Ficheiro COS (cos_amostra.geojson) não encontrado."
    
    # Caminhos dos ficheiros no GitHub (Pasta data/)
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
                    # Comparação de Atributos: COS23_n4_L vs tipo_obra
                    uso_oficial = inter['COS23_n4_L'].iloc[0]
                    uso_fiscal = inter['tipo_obra'].iloc[0] if 'tipo_obra' in inter.columns else "Atributo 'tipo_obra' ausente"
                    
                    if str(uso_oficial).strip().lower() != str(uso_fiscal).strip().lower():
                        analise_uso_solo = f"⚠️ DIVERGÊNCIA: A COS classifica como '{uso_oficial}', mas o levantamento indica '{uso_fiscal}'."
                    else:
                        analise_uso_solo = f"✅ COERENTE: O uso '{uso_fiscal}' coincide com a classificação oficial da COS."
                else:
                    # Definição jurídica e Coimas
                    info_juridica = {
                        "REN": {
                            "lei": "DL n.º 166/2008 (Regime da REN)",
                            "artigo": "Artigo 20.º (Interdições)",
                            "coima": "Singulares: €2.000 a €3.700 | Coletivas: €15.000 a €44.800"
                        },
                        "RAN": {
                            "lei": "DL n.º 73/2009 (Regime da RAN)",
                            "artigo": "Artigo 22.º (Utilizações Proibidas)",
                            "coima": "Singulares: €500 a €3.700 | Coletivas: €2.500 a €44.800"
                        },
                        "Rede Natura": {
                            "lei": "Lei n.º 50/2006 (Contraordenações Ambientais)",
                            "artigo": "DL n.º 142/2008 (Rede Natura)",
                            "coima": "Muito Graves (Coletivas): €24.000 a €5.000.000"
                        }
                    }
                    
                    resultados.append({
                        "Regime": nome,
                        "Area": round(area_int, 2),
                        "Perc": round(perc, 1),
                        "Lei": info_juridica[nome]["lei"],
                        "Coima": info_juridica[nome]["coima"]
                    })
    
    return resultados, analise_uso_solo, area_total

# --- FUNÇÃO DE GERAÇÃO DE RELATÓRIO WORD ---

def gerar_word(resultados, analise_uso, area_total):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)

    doc.add_heading('Relatório Técnico de Fiscalização Territorial', 0)
    
    # 1. Dados Gerais
    doc.add_heading('1. Identificação da Área', level=1)
    doc.add_paragraph(f"Data da Análise: {date.today().strftime('%d/%m/%Y')}")
    doc.add_paragraph(f"Área Total Fiscalizada: {area_total:.2f} m²")

    # 2. Análise COS
    doc.add_heading('2. Verificação de Ocupação do Solo (COS 2023)', level=1)
    p_cos = doc.add_paragraph(analise_uso)
    if "DIVERGÊNCIA" in analise_uso:
        doc.add_paragraph("Nota: A discrepância de uso constitui indício de infração por alteração ilícita do uso do solo.")

    # 3. Análise de Servidões e Coimas
    doc.add_heading('3. Servidões Administrativas e Restrições', level=1)
    if not resultados:
        doc.add_paragraph("Não foram detetadas sobreposições com regimes protegidos.")
    else:
        for res in resultados:
            doc.add_heading(f"Regime: {res['Regime']}", level=2)
            p = doc.add_paragraph()
            p.add_run(f"Sobreposição: {res['Area']} m² ({res['Perc']}% da área total)\n").bold = True
            p.add_run(f"Enquadramento: {res['Lei']}\n")
            p.add_run(f"Moldura Contraordenacional: {res['Coima']}").font.color.rgb = None # Pode-se personalizar cor aqui

    # 4. Conclusão
    doc.add_heading('4. Medidas de Tutela Recomendadas', level=1)
    doc.add_paragraph(
        "Face às evidências detetadas, recomenda-se o levantamento de Auto de Notícia e a "
        "notificação dos interessados para audição prévia ou reposição da legalidade urbanística."
    )

    fname = "Relatorio_Fiscalizacao.docx"
    doc.save(fname)
    return fname

# --- INTERFACE STREAMLIT ---

st.title("🛡️ Sistema Automático de Fiscalização Territorial")
st.markdown("Análise integrada de **REN, RAN, Rede Natura 2000** e **COS 2023**.")

# Sidebar
st.sidebar.header("📁 Dados de Entrada")
uploaded_file = st.sidebar.file_uploader("Carregue o polígono (GeoJSON)", type=['geojson'])

col1, col2 = st.columns([2, 1])

with col1:
    # Mapa Interativo
    m = leafmap.Map(center=[39.5, -8.0], zoom=7, google_map="HYBRID")
    
    if uploaded_file:
        try:
            # Carregar e projetar para coordenadas métricas de PT
            user_gdf = gpd.read_file(uploaded_file).to_crs(epsg=3763)
            m.add_gdf(user_gdf, layer_name="Área Fiscalizada", fill_colors=["red"])
            m.zoom_to_gdf(user_gdf)
        except Exception as e:
            st.error(f"Erro ao processar ficheiro: {e}")
    
    m.to_streamlit(height=600)

with col2:
    st.subheader("📋 Resultados da Análise")
    if uploaded_file:
        res, uso_txt, a_total = realizar_analise(user_gdf)
        
        st.metric("Área Total", f"{a_total:.2f} m²")
        
        if "⚠️" in uso_txt:
            st.error(uso_txt)
        else:
            st.success(uso_txt)
            
        if res:
            st.warning(f"Detetadas {len(res)} condicionantes legais.")
            for r in res:
                with st.expander(f"Detalhes: {r['Regime']}"):
                    st.write(f"**Área:** {r['Area']} m² ({r['Perc']}%)")
                    st.write(f"**Coima:** {r['Coima']}")
            
            if st.button("📝 Gerar Relatório Word Completo"):
                path_word = gerar_word(res, uso_txt, a_total)
                with open(path_word, "rb") as f:
                    st.download_button("⬇️ Descarregar Relatório", f, file_name=path_word)
        else:
            st.success("Área sem restrições detetadas.")
    else:
        st.info("Aguardando upload do ficheiro GeoJSON para iniciar a análise espacial e jurídica.")

