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
                    uso_fiscal = inter['tipo_obra'].iloc[0] if 'tipo_obra' in inter.columns else "Atributo 'tipo_obra' ausente"
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

# --- FUNÇÃO CARTOGRÁFICA (CORREÇÃO DA LEGENDA) ---

def criar_mapa_imagem(user_gdf, resultados):
    fig, ax = plt.subplots(figsize=(10, 8))
    user_gdf_web = user_gdf.to_crs(epsg=3857)
    
    # Estilos Visuais
    estilos = {
        "REN": {"cor": "#2ecc71", "hatch": "////", "label": "Reserva Ecológica Nacional (REN)"},
        "RAN": {"cor": "#f1c40f", "hatch": None, "label": "Reserva Agrícola Nacional (RAN)"},
        "Rede Natura": {"cor": "#8B4513", "hatch": "----", "label": "Rede Natura 2000"}
    }
    
    # Criamos manualmente os elementos da legenda
    legend_elements = []

    # 1. Desenhar Manchas e Guardar para a Legenda
    for res in resultados:
        nome = res['Regime']
        path = f"data/{nome.lower().replace(' ', '_')}_amostra.geojson"
        
        if os.path.exists(path):
            camada = gpd.read_file(path).to_crs(epsg=3857)
            patch = gpd.overlay(camada, user_gdf_web, how='intersection')
            
            if not patch.empty:
                estilo = estilos.get(nome)
                # Desenhar a mancha no mapa
                patch.plot(ax=ax, facecolor="none", edgecolor=estilo["cor"], hatch=estilo["hatch"], linewidth=1.5, alpha=0.9)
                
                # CRIAR O SÍMBOLO DA LEGENDA
                proxy = mpatches.Patch(facecolor="none", edgecolor=estilo["cor"], hatch=estilo["hatch"], label=estilo["label"])
                legend_elements.append(proxy)

    # 2. Contorno da Fiscalização
    user_gdf_web.plot(ax=ax, facecolor="none", edgecolor="red", linewidth=2.5)
    line_proxy = Line2D([0], [0], color='red', linewidth=2.5, label='Área Fiscalizada (Contorno)')
    legend_elements.append(line_proxy)
    
    # 3. Adicionar Fundo de Satélite
    try:
        cx.add_basemap(ax, source=cx.providers.Esri.WorldImagery)
    except:
        pass
    
    # 4. FORÇAR A LEGENDA A APARECER
    if legend_elements:
        ax.legend(handles=legend_elements, loc='upper right', frameon=True, facecolor='white', framealpha=0.9, fontsize='small')
    
    ax.set_axis_off()
    temp_img = "mapa_relatorio.png"
    plt.savefig(temp_img, bbox_inches='tight', dpi=150)
    plt.close()
    return temp_img

# --- RELATÓRIO E INTERFACE ---

def gerar_word(user_gdf, resultados, analise_uso, area_total):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)

    doc.add_heading('Relatório de Fiscalização Territorial', 0)
    
    # Secção Mapa
    doc.add_heading('1. Enquadramento Cartográfico', level=1)
    img_path = criar_mapa_imagem(user_gdf, resultados)
    doc.add_picture(img_path, width=Inches(5.5))
    os.remove(img_path)
    
    doc.add_paragraph(f"Área Total Analisada: {area_total:.2f} m²")

    # Secção Jurídica (Mantendo a análise completa anterior)
    doc.add_heading('2. Análise Jurídica e Servidões', level=1)
    doc.add_paragraph(analise_uso)
    
    for res in resultados:
        doc.add_heading(f"Regime: {res['Regime']}", level=2)
        p = doc.add_paragraph()
        p.add_run(f"Área afetada: {res['Area']} m²\n").bold = True
        p.add_run(f"Base Legal: {res['Lei']}\n")
        p.add_run(f"Coima: {res['Coima']}")

    doc.add_heading('3. Conclusões', level=1)
    doc.add_paragraph("Recomenda-se o levantamento de Auto de Notícia e Embargo.", style='List Bullet')

    fname = "Relatorio_Fiscalizacao.docx"
    doc.save(fname)
    return fname

st.title("🛡️ Sistema de Fiscalização SIG")
uploaded_file = st.sidebar.file_uploader("Upload GeoJSON", type=['geojson'])

if uploaded_file:
    user_gdf = gpd.read_file(uploaded_file).to_crs(epsg=3763)
    res, uso_txt, a_total = realizar_analise(user_gdf)
    
    m = leafmap.Map(center=[39.5, -8.0], zoom=7, google_map="HYBRID")
    m.add_gdf(user_gdf)
    m.to_streamlit(height=500)
    
    if st.button("📝 Gerar Relatório"):
        doc_path = gerar_word(user_gdf, res, uso_txt, a_total)
        with open(doc_path, "rb") as f:
            st.download_button("Descarregar Word", f, file_name=doc_path)
