import streamlit as st
import geopandas as gpd
import pandas as pd
import leafmap.foliumap as leafmap
from fpdf import FPDF
from datetime import date
import os
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
import contextily as cx
import time

# 1. Configuração de Interface
st.set_page_config(layout="wide", page_title="Fiscalização Territorial SIG", page_icon="🛡️")

# --- MOTOR DE ANÁLISE ---
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
                    uso_fiscal = inter['tipo_obra'].iloc[0] if 'tipo_obra' in inter.columns else "Nao definido"
                    if str(uso_oficial).strip().lower() != str(uso_fiscal).strip().lower():
                        analise_uso_solo = f"DIVERGENCIA: A COS classifica como '{uso_oficial}', mas detetado '{uso_fiscal}'."
                    else:
                        analise_uso_solo = f"COERENTE: Uso '{uso_fiscal}' coincide com a COS."
                else:
                    info_jur = {
                        "REN": {
                            "lei": "Regime Juridico da REN (DL n. 166/2008).",
                            "art": "Artigo 20. (Interdicoes). Proibidas obras e alteracao de relevo.",
                            "coima": "Singulares: 2.000 a 3.700 euros | Coletivas: 15.000 a 44.800 euros."
                        },
                        "RAN": {
                            "lei": "Regime Juridico da RAN (DL n. 73/2009).",
                            "art": "Artigo 22. (Utilizacoes Proibidas). Solo de protecao agricola.",
                            "coima": "Singulares: 500 a 3.700 euros | Coletivas: 2.500 a 44.800 euros."
                        },
                        "Rede Natura": {
                            "lei": "Lei n. 50/2006 e DL n. 142/2008.",
                            "art": "Protecao de Habitats. Requer parecer do ICNF.",
                            "coima": "Muito Graves (Coletivas): 24.000 a 5.000.000 euros."
                        }
                    }
                    resultados.append({
                        "Regime": nome, "Area": round(area_int, 2), "Perc": round(perc, 1),
                        "Lei": info_jur[nome]["lei"], "Artigo": info_jur[nome]["art"], "Coima": info_jur[nome]["coima"]
                    })
    return resultados, analise_uso_solo, area_total

# --- FUNÇÃO CARTOGRÁFICA ---
def criar_mapa_imagem(user_gdf, resultados):
    plt.switch_backend('Agg') 
    fig, ax = plt.subplots(figsize=(10, 8), dpi=100) # DPI menor para garantir download rápido
    user_gdf_web = user_gdf.to_crs(epsg=3857)
    
    # Adicionar Mapa Base com Provedor Alternativo (CartoDB é mais estável)
    try:
        cx.add_basemap(ax, source=cx.providers.CartoDB.Positron, zorder=0)
    except:
        try: cx.add_basemap(ax, source=cx.providers.OpenStreetMap.Mapnik, zorder=0)
        except: pass

    estilos = {"REN": "#2ecc71", "RAN": "#f1c40f", "Rede Natura": "#8B4513"}
    legend_elements = []

    for res in resultados:
        nome = res['Regime']
        path = f"data/{nome.lower().replace(' ', '_')}_amostra.geojson"
        if os.path.exists(path):
            camada = gpd.read_file(path).to_crs(epsg=3857)
            patch = gpd.overlay(camada, user_gdf_web, how='intersection')
            if not patch.empty:
                cor = estilos.get(nome, "gray")
                patch.plot(ax=ax, facecolor=cor, alpha=0.5, zorder=1)
                legend_elements.append(mpatches.Patch(facecolor=cor, label=nome))

    user_gdf_web.plot(ax=ax, facecolor="none", edgecolor="red", linewidth=3, zorder=2)
    legend_elements.append(Line2D([0], [0], color='red', linewidth=3, label='Alvo'))

    bounds = user_gdf_web.total_bounds
    ax.set_xlim([bounds[0] - 200, bounds[2] + 200])
    ax.set_ylim([bounds[1] - 200, bounds[3] + 200])
    
    if legend_elements:
        ax.legend(handles=legend_elements, loc='upper right')
    
    ax.set_axis_off()
    temp_img = "mapa_relatorio.png"
    plt.savefig(temp_img, bbox_inches='tight')
    plt.close(fig)
    return temp_img

# --- GERAÇÃO DE PDF ---
def gerar_pdf_final(user_gdf, resultados, analise_uso, area_total):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    # Cabeçalho
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'RELATORIO DE FISCALIZACAO TERRITORIAL', 0, 1, 'C')
    pdf.ln(5)
    
    # Imagem do Mapa
    img_path = criar_mapa_imagem(user_gdf, resultados)
    if os.path.exists(img_path):
        pdf.image(img_path, x=10, y=None, w=190)
        pdf.ln(5)
        os.remove(img_path)
    
    # Dados Gerais
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, f"Data: {date.today().strftime('%d/%m/%Y')} | Area: {area_total:.2f} m2", 0, 1)
    pdf.ln(5)

    # 1. COS
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, "1. OCUPACAO DO SOLO (COS 2023)", 1, 1, 'L', fill=True)
    pdf.set_font('Arial', '', 11)
    pdf.multi_cell(0, 8, str(analise_uso))
    pdf.ln(5)

    # 2. Jurídica
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, "2. ANALISE JURIDICA E SERVIDOES", 1, 1, 'L', fill=True)
    pdf.ln(2)
    
    if not resultados:
        pdf.set_font('Arial', '', 11)
        pdf.cell(0, 10, "Sem condicionantes detetadas.", 0, 1)
    else:
        for r in resultados:
            pdf.set_font('Arial', 'B', 11)
            pdf.cell(0, 8, f"Regime: {r['Regime']}", 0, 1)
            pdf.set_font('Arial', '', 10)
            pdf.multi_cell(0, 6, f"Sobreposicao: {r['Area']} m2 ({r['Perc']}%)\nLei: {r['Lei']}\nArtigo: {r['Artigo']}\nCoima: {r['Coima']}")
            pdf.ln(4)

    # 3. Medidas
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, "3. MEDIDAS DE TUTELA RECOMENDADAS", 1, 1, 'L', fill=True)
    pdf.set_font('Arial', '', 11)
    pdf.multi_cell(0, 8, "- Levantamento de Auto de Noticia imediato\n- Embargo cautelar de obra/aterro\n- Notificacao para reposicao da legalidade")

    output_name = "Relatorio_Oficial.pdf"
    pdf.output(output_name)
    return output_name

# --- INTERFACE ---
st.title("🛡️ Fiscalização SIG (Versão Estabilidade)")
uploaded_file = st.sidebar.file_uploader("Ficheiro GeoJSON", type=['geojson'])

if uploaded_file:
    user_gdf = gpd.read_file(uploaded_file).to_crs(epsg=3763)
    res, uso_txt, a_total = realizar_analise(user_gdf)
    
    col_map, col_res = st.columns([2, 1])
    
    with col_map:
        m = leafmap.Map(google_map="HYBRID")
        m.add_gdf(user_gdf)
        centroid = user_gdf.to_crs(epsg=4326).centroid.iloc[0]
        m.set_center(centroid.x, centroid.y, zoom=16)
        m.to_streamlit(height=500)
        
    with col_res:
        st.info(uso_txt)
        if st.button("📝 Gerar Relatório PDF Oficial"):
            with st.spinner('A processar...'):
                final_pdf = gerar_pdf_final(user_gdf, res, uso_txt, a_total)
                with open(final_pdf, "rb") as f:
                    st.download_button("📥 Baixar PDF", f, file_name=final_pdf)
