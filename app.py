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
st.set_page_config(layout="wide", page_title="Fiscalização SIG Portugal", page_icon="🛡️")

# --- MOTOR DE ANÁLISE GEOSPACIAL E JURÍDICA ---

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
                        analise_uso_solo = f"⚠️ DIVERGÊNCIA: COS indica '{uso_oficial}', detetado '{uso_fiscal}'."
                    else:
                        analise_uso_solo = f"✅ COERENTE: Uso '{uso_fiscal}' coincide com a COS."
                else:
                    info_jur = {
                        "REN": {
                            "lei": "DL n.º 166/2008 (Regime da REN)",
                            "art": "Artigo 20.º (Interdições)",
                            "coima": "Singulares: €2.000 a €3.700 | Coletivas: €15.000 a €44.800"
                        },
                        "RAN": {
                            "lei": "DL n.º 73/2009 (Regime da RAN)",
                            "art": "Artigo 22.º (Utilizações Proibidas)",
                            "coima": "Singulares: €500 a €3.700 | Coletivas: €2.500 a €44.800"
                        },
                        "Rede Natura": {
                            "lei": "Lei n.º 50/2006 e DL n.º 142/2008",
                            "art": "Proteção de Habitats e Espécies",
                            "coima": "Muito Graves (Coletivas): €24.000 a €5.000.000"
                        }
                    }
                    resultados.append({
                        "Regime": nome, "Area": round(area_int, 2), "Perc": round(perc, 1),
                        "Lei": info_jur[nome]["lei"], "Artigo": info_jur[nome]["art"], "Coima": info_jur[nome]["coima"]
                    })
    
    return resultados, analise_uso_solo, area_total

# --- FUNÇÃO CARTOGRÁFICA COM TRAMAS E LEGENDA ---

def criar_mapa_imagem(user_gdf, resultados):
    fig, ax = plt.subplots(figsize=(10, 8))
    user_gdf_web = user_gdf.to_crs(epsg=3857)
    
    # Configuração de Estilos Visuais
    estilos = {
        "REN": {"cor": "#2ecc71", "hatch": "///", "label": "REN (Diagonais Verdes)"},
        "RAN": {"cor": "#f1c40f", "hatch": None, "label": "RAN (Amarelo Sólido)"},
        "Rede Natura": {"cor": "#8B4513", "hatch": "---", "label": "Rede Natura (Horizontais Castanhas)"}
    }
    
    legend_elements = []

    # 1. Desenhar Manchas das Servidões
    for res in resultados:
        nome = res['Regime']
        path = f"data/{nome.lower().replace(' ', '_')}_amostra.geojson"
        
        if os.path.exists(path):
            camada = gpd.read_file(path).to_crs(epsg=3857)
            patch = gpd.overlay(camada, user_gdf_web, how='intersection')
            
            if not patch.empty:
                estilo = estilos.get(nome, {"cor": "gray", "hatch": None, "label": nome})
                patch.plot(ax=ax, facecolor="none", edgecolor=estilo["cor"], hatch=estilo["hatch"], linewidth=1.5, alpha=0.9)
                
                # Adicionar à legenda
                legend_elements.append(mpatches.Patch(facecolor="none", edgecolor=estilo["cor"], 
                                                      hatch=estilo["hatch"], label=estilo["label"]))

    # 2. Desenhar Contorno da Fiscalização (Vermelho)
    user_gdf_web.plot(ax=ax, facecolor="none", edgecolor="red", linewidth=2.5)
    legend_elements.append(Line2D([0], [0], color='red', linewidth=2.5, label='Área Fiscalizada (Contorno)'))
    
    # 3. Adicionar Fundo de Satélite
    try:
        cx.add_basemap(ax, source=cx.providers.Esri.WorldImagery)
    except:
        st.warning("Aviso: Falha ao carregar satélite. Verifique a ligação.")
    
    # 4. Finalizar Legenda e Imagem
    if legend_elements:
        ax.legend(handles=legend_elements, loc='upper right', frameon=True, facecolor='white', framealpha=0.9)
    
    ax.set_axis_off()
    temp_img = "mapa_temp.png"
    plt.savefig(temp_img, bbox_inches='tight', dpi=150)
    plt.close()
    return temp_img

# --- GERAÇÃO DO DOCUMENTO WORD ---

def gerar_word(user_gdf, resultados, analise_uso, area_total):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)

    doc.add_heading('Relatório Técnico de Fiscalização Territorial', 0)
    
    # 1. Mapa e Dados
    doc.add_heading('1. Localização e Enquadramento Cartográfico', level=1)
    img_path = criar_mapa_imagem(user_gdf, resultados)
    doc.add_picture(img_path, width=Inches(5.8))
    os.remove(img_path)
    doc.add_paragraph(f"Data: {date.today().strftime('%d/%m/%Y')} | Área Fiscalizada: {area_total:.2f} m²")

    # 2. Análise COS
    doc.add_heading('2. Verificação de Ocupação do Solo (COS 2023)', level=1)
    doc.add_paragraph(analise_uso)

    # 3. Análise Jurídica Completa
    doc.add_heading('3. Servidões Administrativas e Molduras Penais', level=1)
    if not resultados:
        doc.add_paragraph("Não foram detetadas sobreposições com servidões protegidas.")
    else:
        for res in resultados:
            doc.add_heading(f"Regime: {res['Regime']}", level=2)
            p = doc.add_paragraph()
            p.add_run(f"Sobreposição: {res['Area']} m² ({res['Perc']}%)\n").bold = True
            p.add_run(f"Base Legal: {res['Lei']}\n")
            p.add_run(f"Artigo: {res['Artigo']}\n")
            p.add_run(f"Coima: {res['Coima']}").font.color.rgb = None

    # 4. Tutela
    doc.add_heading('4. Conclusões e Recomendações', level=1)
    for m in ["Levantamento de Auto de Notícia;", "Embargo de obra;", "Notificação para reposição da legalidade."]:
        doc.add_paragraph(m, style='List Number')

    doc.add_paragraph("\n\n__________________________________________\nAssinatura do Técnico Responsável")
    
    fname = "Relatorio_Fiscalizacao_Oficial.docx"
    doc.save(fname)
    return fname

# --- INTERFACE STREAMLIT ---

st.title("🛡️ Fiscalização SIG: REN, RAN e Natura 2000")
uploaded_file = st.sidebar.file_uploader("Upload polígono GeoJSON", type=['geojson'])

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
        if st.button("📝 Gerar Relatório Final"):
            with st.spinner('A processar cartografia e parecer jurídico...'):
                doc_path = gerar_word(user_gdf, res, uso_txt, a_total)
                with open(doc_path, "rb") as f:
                    st.download_button("📥 Baixar Relatório Word", f, file_name=doc_path)
    else:
        st.info("Carregue um ficheiro GeoJSON para iniciar.")
