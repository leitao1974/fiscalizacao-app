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

# 1. Configuração de Interface
st.set_page_config(layout="wide", page_title="Fiscalização Territorial SIG", page_icon="🛡️")

# --- MOTOR DE ANÁLISE ---
def realizar_analise(user_gdf):
    area_total = user_gdf.area.sum() [cite: 3]
    resultados = []
    analise_uso_solo = "Ficheiro COS não encontrado." [cite: 4]
    
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
                    uso_oficial = inter['COS23_n4_L'].iloc[0] [cite: 5]
                    uso_fiscal = inter['tipo_obra'].iloc[0] if 'tipo_obra' in inter.columns else "Não definido" [cite: 5]
                    if str(uso_oficial).strip().lower() != str(uso_fiscal).strip().lower():
                        analise_uso_solo = f"DIVERGENCIA: A COS classifica como '{uso_oficial}', mas detetado '{uso_fiscal}'." [cite: 5]
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
                            "lei": "Regime Juridico da RAN (DL n. 73/2009).", [cite: 8]
                            "art": "Artigo 22. (Utilizacoes Proibidas). Solo de protecao agricola.", [cite: 8, 9]
                            "coima": "Singulares: 500 a 3.700 euros | Coletivas: 2.500 a 44.800 euros." [cite: 9]
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

# --- FUNÇÃO CARTOGRÁFICA REFORÇADA ---
def criar_mapa_imagem(user_gdf, resultados):
    plt.switch_backend('Agg') # Forçar backend sem interface gráfica
    fig, ax = plt.subplots(figsize=(10, 8), dpi=150)
    user_gdf_web = user_gdf.to_crs(epsg=3857)
    
    # 1. Mapa Base (ZORDER 0)
    try:
        cx.add_basemap(ax, source=cx.providers.Esri.WorldImagery, zorder=0)
    except:
        pass

    estilos = {"REN": "#2ecc71", "RAN": "#f1c40f", "Rede Natura": "#8B4513"}
    legend_elements = []

    # 2. Servidões
    for res in resultados:
        nome = res['Regime']
        path = f"data/{nome.lower().replace(' ', '_')}_amostra.geojson"
        if os.path.exists(path):
            camada = gpd.read_file(path).to_crs(epsg=3857)
            patch = gpd.overlay(camada, user_gdf_web, how='intersection')
            if not patch.empty:
                cor = estilos.get(nome, "gray")
                patch.plot(ax=ax, facecolor=cor, alpha=0.4, zorder=1)
                legend_elements.append(mpatches.Patch(facecolor=cor, label=nome, alpha=0.6))

    # 3. Contorno Vermelho
    user_gdf_web.plot(ax=ax, facecolor="none", edgecolor="red", linewidth=3, zorder=2)
    legend_elements.append(Line2D([0], [0], color='red', linewidth=3, label='Area Fiscalizada'))

    bounds = user_gdf_web.total_bounds
    ax.set_xlim([bounds[0] - 100, bounds[2] + 100])
    ax.set_ylim([bounds[1] - 100, bounds[3] + 100])
    if legend_elements:
        ax.legend(handles=legend_elements, loc='upper right')
    
    ax.set_axis_off()
    temp_img = "mapa_export.png"
    plt.savefig(temp_img, bbox_inches='tight', pad_inches=0.1)
    plt.close(fig)
    return temp_img

# --- GERAÇÃO DE PDF ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Relatorio Tecnico de Fiscalizacao Territorial', 0, 1, 'C')
        self.ln(5)

def gerar_pdf(user_gdf, resultados, analise_uso, area_total):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font('Arial', '', 12)
    
    # Inserir Mapa
    img_path = criar_mapa_imagem(user_gdf, resultados)
    pdf.image(img_path, x=10, y=25, w=190)
    os.remove(img_path)
    
    pdf.set_y(170) # Mover cursor para baixo do mapa
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, f"Data: {date.today().strftime('%d/%m/%Y')} | Area: {area_total:.2f} m2", 0, 1) [cite: 3]
    
    # Secção COS
    pdf.set_fill_color(230, 230, 230)
    pdf.cell(0, 10, "1. Ocupacao do Solo (COS 2023)", 1, 1, 'L', fill=True) [cite: 4]
    pdf.set_font('Arial', '', 11)
    pdf.multi_cell(0, 8, analise_uso) [cite: 5]
    pdf.ln(5)

    # Secção Jurídica
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, "2. Analise Juridica e Servidoes", 1, 1, 'L', fill=True) [cite: 6]
    pdf.set_font('Arial', '', 10)
    
    if not resultados:
        pdf.cell(0, 10, "Nenhuma servidao detetada.", 0, 1)
    else:
        for r in resultados:
            pdf.set_font('Arial', 'B', 11)
            pdf.cell(0, 8, f"Regime: {r['Regime']}", 0, 1) [cite: 7]
            pdf.set_font('Arial', '', 10)
            pdf.multi_cell(0, 6, f"Sobreposicao: {r['Area']} m2 ({r['Perc']}%)\nLei: {r['Lei']}\nArtigo: {r['Artigo']}\nCoima: {r['Coima']}") [cite: 8, 9]
            pdf.ln(3)

    # Medidas de Tutela
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, "3. Medidas de Tutela", 1, 1, 'L', fill=True) [cite: 10]
    pdf.set_font('Arial', '', 11)
    pdf.multi_cell(0, 8, "- Levantamento de Auto de Noticia\n- Embargo de obra\n- Notificacao para reposicao") [cite: 11, 12, 13]

    pdf_output = "Relatorio_Fiscalizacao.pdf"
    pdf.output(pdf_output)
    return pdf_output

# --- INTERFACE ---
st.title("🛡️ Fiscalizacao SIG (Versao PDF)")
uploaded_file = st.sidebar.file_uploader("Upload GeoJSON", type=['geojson'])

col_map, col_res = st.columns([2, 1])

with col_map:
    m = leafmap.Map(google_map="HYBRID")
    if uploaded_file:
        user_gdf = gpd.read_file(uploaded_file).to_crs(epsg=3763)
        m.add_gdf(user_gdf, layer_name="Fiscalizacao")
        # Zoom Automático
        centroid = user_gdf.to_crs(epsg=4326).centroid.iloc[0]
        m.set_center(centroid.x, centroid.y, zoom=16)
        m.zoom_to_gdf(user_gdf)
    m.to_streamlit(height=600)

with col_res:
    if uploaded_file:
        res, uso_txt, a_total = realizar_analise(user_gdf)
        st.info(uso_txt)
        if st.button("📝 Gerar Relatorio PDF"):
            with st.spinner('A capturar mapa e fundamentacao...'):
                pdf_path = gerar_pdf(user_gdf, res, uso_txt, a_total)
                with open(pdf_path, "rb") as f:
                    st.download_button("📥 Baixar PDF", f, file_name=pdf_path)
