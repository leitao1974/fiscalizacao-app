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

# 1. Configuração da Página
st.set_page_config(layout="wide", page_title="Fiscalização Territorial SIG", page_icon="🛡️")

# --- MOTOR DE ANÁLISE GEOSPACIAL ---

def realizar_analise(user_gdf):
    area_total = user_gdf.area.sum()
    resultados = []
    analise_uso_solo = "Ficheiro COS não encontrado para análise."
    
    # Mapeamento de ficheiros na pasta data/
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
                        analise_uso_solo = f"⚠️ DIVERGÊNCIA: COS indica '{uso_oficial}', detetado '{uso_fiscal}'."
                    else:
                        analise_uso_solo = f"✅ COERENTE: Uso '{uso_fiscal}' coincide com a COS."
                else:
                    # Dados Jurídicos e Coimas
                    info_jur = {
                        "REN": {"lei": "DL 166/2008", "art": "Art. 20.º", "coima": "Singulares: €2k-€3.7k | Coletivas: €15k-€44.8k"},
                        "RAN": {"lei": "DL 73/2009", "art": "Art. 22.º", "coima": "Singulares: €500-€3.7k | Coletivas: €2.5k-€44.8k"},
                        "Rede Natura": {"lei": "Lei 50/2006", "art": "Habitats", "coima": "Até €5.000.000 (P. Coletivas)"}
                    }
                    resultados.append({
                        "Regime": nome, "Area": round(area_int, 2), "Perc": round(perc, 1),
                        "Lei": info_jur[nome]["lei"], "Artigo": info_jur[nome]["art"], "Coima": info_jur[nome]["coima"]
                    })
    
    return resultados, analise_uso_solo, area_total

# --- FUNÇÃO PARA GERAR O MAPA COM SERVIDÕES E LEGENDA ---

def criar_mapa_imagem(user_gdf, resultados):
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Projetar para Web Mercator para o fundo de satélite
    user_gdf_web = user_gdf.to_crs(epsg=3857)
    
    # Cores para as servidões
    cores = {"REN": "#2ecc71", "RAN": "#f1c40f", "Rede Natura": "#3498db"}
    
    # 1. Desenhar manchas das servidões que foram intersetadas
    for res in resultados:
        nome = res['Regime']
        path = f"data/{nome.lower().replace(' ', '_')}_amostra.geojson"
        if os.path.exists(path):
            camada = gpd.read_file(path).to_crs(epsg=3857)
            # Clip da servidão apenas para a área de interesse
            patch = gpd.overlay(camada, user_gdf_web, how='intersection')
            if not patch.empty:
                patch.plot(ax=ax, color=cores.get(nome, "gray"), alpha=0.5, label=f"Área em {nome}")

    # 2. Desenhar o contorno da área fiscalizada
    user_gdf_web.plot(ax=ax, facecolor="none", edgecolor="red", linewidth=2.5, label="Área Fiscalizada")
    
    # 3. Adicionar fundo de satélite
    try:
        cx.add_basemap(ax, source=cx.providers.Esri.WorldImagery)
    except:
        pass # Mantém sem fundo se falhar a net
    
    # 4. Legenda e Estética
    ax.legend(loc='upper right', title="Legenda Técnica")
    ax.set_axis_off()
    
    temp_img = "mapa_relatorio.png"
    plt.savefig(temp_img, bbox_inches='tight', dpi=150)
    plt.close()
    return temp_img

# --- MOTOR DO RELATÓRIO WORD ---

def gerar_word(user_gdf, resultados, analise_uso, area_total):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(10)

    doc.add_heading('Relatório Técnico de Fiscalização Territorial', 0)
    
    # Secção 1: Mapa
    doc.add_heading('1. Enquadramento Geográfico e Servidões', level=1)
    img_path = criar_mapa_imagem(user_gdf, resultados)
    doc.add_picture(img_path, width=Inches(5.8))
    os.remove(img_path)
    doc.add_paragraph(f"Área Total Analisada: {area_total:.2f} m²")

    # Secção 2: COS
    doc.add_heading('2. Ocupação do Solo (COS 2023)', level=1)
    doc.add_paragraph(analise_uso)

    # Secção 3: Jurídica
    doc.add_heading('3. Análise Jurídica e Coimas', level=1)
    if not resultados:
        doc.add_paragraph("Não foram detetadas sobreposições.")
    else:
        for res in resultados:
            doc.add_heading(f"Regime: {res['Regime']}", level=2)
            p = doc.add_paragraph()
            p.add_run(f"Sobreposição: {res['Area']} m² ({res['Perc']}%)\n").bold = True
            p.add_run(f"Base Legal: {res['Lei']} ({res['Artigo']})\n")
            p.add_run(f"Moldura Contraordenacional: {res['Coima']}")

    # Secção 4: Medidas
    doc.add_heading('4. Medidas de Tutela', level=1)
    for m in ["Levantamento de Auto de Notícia;", "Embargo de obra;", "Reposição da legalidade."]:
        doc.add_paragraph(m, style='List Number')

    fname = "Relatorio_Fiscalizacao_Final.docx"
    doc.save(fname)
    return fname

# --- INTERFACE ---

st.title("🛡️ Fiscalização SIG: Análise Automática")
uploaded_file = st.sidebar.file_uploader("Upload do polígono (GeoJSON)", type=['geojson'])

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
        st.subheader("📊 Resultados")
        st.write(f"**Área:** {a_total:.2f} m²")
        st.info(uso_txt)
        
        if st.button("📝 Gerar Relatório Completo"):
            with st.spinner('A processar mapa e texto jurídico...'):
                doc_path = gerar_word(user_gdf, res, uso_txt, a_total)
                with open(doc_path, "rb") as f:
                    st.download_button("📥 Descarregar Word", f, file_name=doc_path)
    else:
        st.info("Carregue um GeoJSON para começar.")

