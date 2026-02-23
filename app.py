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
                    info_juridica = {
                        "REN": {
                            "lei": "Regime Jurídico da REN (DL n.º 166/2008).",
                            "artigo": "Artigo 20.º (Interdições). Proibidas obras e alteração do relevo natural.",
                            "coima": "Singulares: €2.000 a €3.700 | Coletivas: €15.000 a €44.800."
                        },
                        "RAN": {
                            "lei": "Regime Jurídico da RAN (DL n.º 73/2009).",
                            "artigo": "Artigo 22.º (Utilizações Proibidas). Uso exclusivo agrícola.",
                            "coima": "Singulares: €500 a €3.700 | Coletivas: €2.500 a €44.800."
                        },
                        "Rede Natura": {
                            "lei": "DL n.º 142/2008 e Lei n.º 50/2006.",
                            "artigo": "Proteção de Habitats. Requer AIA junto do ICNF.",
                            "coima": "Muito Graves (Coletivas): €24.000 a €5.000.000."
                        }
                    }
                    
                    resultados.append({
                        "Regime": nome, "Area": round(area_int, 2), "Perc": round(perc, 1),
                        "Lei": info_juridica[nome]["lei"], "Artigo": info_juridica[nome]["artigo"], 
                        "Coima": info_juridica[nome]["coima"]
                    })
    
    return resultados, analise_uso_solo, area_total

# --- FUNÇÃO CARTOGRÁFICA (PINTURA E TRAMAS) ---

def criar_mapa_imagem(user_gdf, resultados):
    fig, ax = plt.subplots(figsize=(10, 8))
    user_gdf_web = user_gdf.to_crs(epsg=3857)
    
    # Estilos: Cor, Trama e Label para Legenda
    estilos = {
        "REN": {"cor": "#2ecc71", "hatch": "////", "label": "Reserva Ecológica Nacional (REN)"},
        "RAN": {"cor": "#f1c40f", "hatch": "\\\\\\\\", "label": "Reserva Agrícola Nacional (RAN)"},
        "Rede Natura": {"cor": "#8B4513", "hatch": "----", "label": "Rede Natura 2000"}
    }
    
    legend_elements = []

    # 1. Base Map (Satélite)
    try:
        cx.add_basemap(ax, source=cx.providers.Esri.WorldImagery, zorder=0)
    except:
        pass

    # 2. Desenhar Manchas das Servidões (Pintadas e com Tramas)
    for res in resultados:
        nome = res['Regime']
        path = f"data/{nome.lower().replace(' ', '_')}_amostra.geojson"
        
        if os.path.exists(path):
            camada = gpd.read_file(path).to_crs(epsg=3857)
            patch = gpd.overlay(camada, user_gdf_web, how='intersection')
            
            if not patch.empty:
                estilo = estilos.get(nome, {"cor": "gray", "hatch": None, "label": nome})
                
                # Pintar o polígono com transparência e trama
                patch.plot(
                    ax=ax, 
                    facecolor=estilo["cor"], 
                    edgecolor=estilo["cor"], 
                    hatch=estilo["hatch"], 
                    linewidth=1.5, 
                    alpha=0.4, 
                    zorder=1
                )
                
                # Adicionar à lista da legenda
                proxy = mpatches.Patch(
                    facecolor=estilo["cor"], 
                    edgecolor=estilo["cor"], 
                    hatch=estilo["hatch"], 
                    label=estilo["label"],
                    alpha=0.7
                )
                legend_elements.append(proxy)

    # 3. Desenhar Contorno da Área Fiscalizada (Sempre visível no topo)
    user_gdf_web.plot(ax=ax, facecolor="none", edgecolor="red", linewidth=2.5, zorder=2)
    legend_elements.append(Line2D([0], [0], color='red', linewidth=2.5, label='Área de Intervenção (Contorno)'))
    
    # 4. Configurar Legenda e Zoom
    if legend_elements:
        ax.legend(handles=legend_elements, loc='upper right', frameon=True, facecolor='white', framealpha=0.9)
    
    ax.set_axis_off()
    
    # Zoom focado no polígono com margem de 50 metros
    bounds = user_gdf_web.total_bounds
    ax.set_xlim([bounds[0] - 50, bounds[2] + 50])
    ax.set_ylim([bounds[1] - 50, bounds[3] + 50])

    temp_img = "mapa_relatorio.png"
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
    
    # 1. Mapa e Localização
    doc.add_heading('1. Enquadramento Cartográfico e Localização', level=1)
    img_path = criar_mapa_imagem(user_gdf, resultados)
    doc.add_picture(img_path, width=Inches(5.8))
    os.remove(img_path)
    doc.add_paragraph(f"Data: {date.today().strftime('%d/%m/%Y')} | Área Total: {area_total:.2f} m²")

    # 2. COS
    doc.add_heading('2. Verificação de Ocupação do Solo (COS 2023)', level=1)
    doc.add_paragraph(analise_uso)

    # 3. Jurídico
    doc.add_heading('3. Servidões Administrativas e Análise Jurídica', level=1)
    if not resultados:
        doc.add_paragraph("Nenhuma servidão intersetada.")
    else:
        for res in resultados:
            doc.add_heading(f"Regime: {res['Regime']}", level=2)
            p = doc.add_paragraph()
            p.add_run(f"Sobreposição: {res['Area']} m² ({res['Perc']}%)\n").bold = True
            p.add_run(f"Base Legal: {res['Lei']}\n")
            p.add_run(f"Norma: {res['Artigo']}\n")
            p.add_run(f"Coima: {res['Coima']}")

    # 4. Conclusão
    doc.add_heading('4. Medidas de Tutela e Conclusão', level=1)
    medidas = ["Verificação de licenciamento;", "Levantamento de Auto de Notícia;", "Medida cautelar de embargo."]
    for m in medidas:
        doc.add_paragraph(m, style='List Number')

    doc.add_paragraph("\n\n__________________________________________\nAssinatura do Técnico Responsável")
    
    fname = "Relatorio_Fiscalizacao_Final.docx"
    doc.save(fname)
    return fname

# --- INTERFACE ---

st.title("🛡️ Sistema de Fiscalização SIG")
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
        st.subheader("📊 Painel de Conformidade")
        st.info(uso_txt)
        if st.button("📝 Gerar Relatório Word Final"):
            with st.spinner('A gerar relatório com cartografia técnica...'):
                doc_path = gerar_word(user_gdf, res, uso_txt, a_total)
                with open(doc_path, "rb") as f:
                    st.download_button("📥 Descarregar Word", f, file_name=doc_path)
    else:
        st.info("Aguardando ficheiro...")
