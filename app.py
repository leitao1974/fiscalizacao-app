import streamlit as st
import geopandas as gpd
import pandas as pd
import leafmap.foliumap as leafmap
from docx import Document
from docx.shared import Pt
from datetime import date
import os

# 1. Configuração de Interface
st.set_page_config(layout="wide", page_title="Fiscalização Territorial SIG", page_icon="🛡️")

# --- MOTOR DE ANÁLISE GEOSPACIAL E JURÍDICA ---

def realizar_analise(user_gdf):
    area_total = user_gdf.area.sum()
    resultados = []
    analise_uso_solo = "Ficheiro COS não encontrado para comparação."
    
    # Mapeamento de ficheiros e Regimes
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
                    # Lógica de cruzamento de atributos COS23 vs tipo_obra
                    uso_oficial = inter['COS23_n4_L'].iloc[0]
                    uso_fiscal = inter['tipo_obra'].iloc[0] if 'tipo_obra' in inter.columns else "Atributo 'tipo_obra' ausente"
                    
                    if str(uso_oficial).strip().lower() != str(uso_fiscal).strip().lower():
                        analise_uso_solo = f"⚠️ DIVERGÊNCIA DETETADA: A COS 2023 classifica como '{uso_oficial}', mas o levantamento indica '{uso_fiscal}'."
                    else:
                        analise_uso_solo = f"✅ COERENTE: O uso '{uso_fiscal}' coincide com a classificação oficial da COS."
                else:
                    # Definição jurídica detalhada
                    info_jur = {
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
                            "lei": "DL n.º 142/2008 e Lei n.º 50/2006",
                            "artigo": "Proteção de Habitats e Espécies",
                            "coima": "Muito Graves (Coletivas): €24.000 a €5.000.000"
                        }
                    }
                    
                    resultados.append({
                        "Regime": nome,
                        "Area": round(area_int, 2),
                        "Perc": round(perc, 1),
                        "Lei": info_jur[nome]["lei"],
                        "Artigo": info_jur[nome]["artigo"],
                        "Coima": info_jur[nome]["coima"]
                    })
    
    return resultados, analise_uso_solo, area_total

# --- MOTOR DE GERAÇÃO DO RELATÓRIO WORD ---

def gerar_word(resultados, analise_uso, area_total):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)

    doc.add_heading('Relatório Técnico de Fiscalização Territorial', 0)
    
    # Secção 1
    doc.add_heading('1. Identificação da Área e Metodologia', level=1)
    doc.add_paragraph(f"Data da Análise: {date.today().strftime('%d/%m/%Y')}")
    doc.add_paragraph(f"Área Total do Polígono: {area_total:.2f} m²")
    doc.add_paragraph("Metodologia: Cruzamento geospacial automático com base em dados oficiais da DGT e SNIG.")

    # Secção 2
    doc.add_heading('2. Análise de Ocupação do Solo (COS 2023)', level=1)
    p_cos = doc.add_paragraph()
    p_cos.add_run("Resultado: ").bold = True
    p_cos.add_run(analise_uso)
    if "DIVERGÊNCIA" in analise_uso:
        doc.add_paragraph("Nota: A discrepância detetada constitui indício de infração por alteração ilícita do uso do solo.")

    # Secção 3
    doc.add_heading('3. Análise Jurídica de Servidões e Restrições', level=1)
    if not resultados:
        doc.add_paragraph("Não foram detetadas sobreposições com regimes de proteção ambiental ou agrícola.")
    else:
        for res in resultados:
            doc.add_heading(f"Regime: {res['Regime']}", level=2)
            p = doc.add_paragraph()
            p.add_run(f"Sobreposição: {res['Area']} m² ({res['Perc']}% da área total)\n").bold = True
            p.add_run(f"Citação Legal: {res['Lei']}\n")
            p.add_run(f"Artigo Aplicável: {res['Artigo']}\n")
            p.add_run(f"Moldura Contraordenacional: {res['Coima']}").font.color.rgb = None

    # Secção 4
    doc.add_heading('4. Conclusões e Medidas de Tutela', level=1)
    p_tutela = doc.add_paragraph()
    p_tutela.add_run("Medidas de Tutela Recomendadas:").bold = True
    
    medidas = [
        "Verificação imediata de licenciamento nos serviços municipais;",
        "Levantamento do respetivo Auto de Notícia caso não exista título autorizativo;",
        "Avaliação de medida cautelar de embargo para evitar agravamento do dano;",
        "Notificação para reposição da situação anterior à infração."
    ]
    for medida in medidas:
        doc.add_paragraph(medida, style='List Number')

    doc.add_paragraph("\n\n__________________________________________\nAssinatura do Técnico Responsável")

    fname = "Relatorio_Fiscalizacao_Final.docx"
    doc.save(fname)
    return fname

# --- INTERFACE STREAMLIT ---

st.sidebar.title("📁 Configuração")
uploaded_file = st.sidebar.file_uploader("Upload polígono de fiscalização (GeoJSON)", type=['geojson'])

st.title("🛡️ Sistema de Apoio à Fiscalização (REN/RAN/COS)")

col1, col2 = st.columns([2, 1])

with col1:
    m = leafmap.Map(center=[39.5, -8.0], zoom=7, google_map="HYBRID")
    if uploaded_file:
        try:
            user_gdf = gpd.read_file(uploaded_file).to_crs(epsg=3763)
            m.add_gdf(user_gdf, layer_name="Área Fiscalizada", fill_colors=["red"])
            m.zoom_to_gdf(user_gdf)
            st.success("Polígono carregado e projetado (EPSG:3763).")
        except Exception as e:
            st.error(f"Erro no processamento SIG: {e}")
    m.to_streamlit(height=600)

with col2:
    st.subheader("📋 Painel de Conformidade")
    if uploaded_file:
        res, uso_txt, a_total = realizar_analise(user_gdf)
        
        st.metric("Área Total", f"{a_total:.2f} m²")
        st.info(uso_txt)
        
        if res:
            st.warning(f"Detetadas {len(res)} condicionantes legais.")
            for r in res:
                with st.expander(f"Ver Detalhes: {r['Regime']}"):
                    st.write(f"**Sobreposição:** {r['Perc']}%")
                    st.write(f"**Coima:** {r['Coima']}")
            
            if st.button("📝 Gerar Relatório Word Final"):
                path_doc = gerar_word(res, uso_txt, a_total)
                with open(path_doc, "rb") as f:
                    st.download_button("📥 Descarregar Documento", f, file_name=path_doc)
        else:
            st.success("Nenhuma restrição detetada.")
    else:
        st.info("Aguardando ficheiro para análise.")
