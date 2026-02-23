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
                    uso_fiscal = inter['tipo_obra'].iloc[0] if 'tipo_obra' in inter.columns else "Atributo 'tipo_obra' ausente"
                    if str(uso_oficial).strip().lower() != str(uso_fiscal).strip().lower():
                        analise_uso_solo = f"⚠️ DIVERGÊNCIA DETETADA: A COS 2023 classifica como '{uso_oficial}', mas o levantamento indica '{uso_fiscal}'."
                    else:
                        analise_uso_solo = f"✅ COERENTE: O uso '{uso_fiscal}' coincide com a classificação oficial da COS."
                else:
                    # REINTEGRAÇÃO DA ANÁLISE JURÍDICA COMPLETA
                    info_juridica = {
                        "REN": {
                            "lei": "Regime Jurídico da Reserva Ecológica Nacional (DL n.º 166/2008, de 22 de agosto).",
                            "artigo": "Artigo 20.º (Interdições). São proibidas ações de loteamento, obras de urbanização, construção e alteração do relevo natural.",
                            "coima": "Singulares: € 2.000,00 a € 3.700,00 | Coletivas: € 15.000,00 a € 44.800,00 (Art. 25.º)."
                        },
                        "RAN": {
                            "lei": "Regime Jurídico da Reserva Agrícola Nacional (DL n.º 73/2009, de 31 de março).",
                            "artigo": "Artigo 22.º (Utilizações Proibidas). Os solos da RAN destinam-se exclusivamente à exploração agrícola.",
                            "coima": "Singulares: € 500,00 a € 3.700,00 | Coletivas: € 2.500,00 a € 44.800,00 (Art. 43.º)."
                        },
                        "Rede Natura": {
                            "lei": "DL n.º 142/2008 (Conservação da Natureza) e Lei n.º 50/2006 (Contraordenações Ambientais).",
                            "artigo": "Proteção de Habitats e Espécies. Requer Avaliação de Incidências Ambientais (AIA) junto do ICNF.",
                            "coima": "Contraordenações Muito Graves (Coletivas): € 24.000,00 a € 5.000.000,00."
                        }
                    }
                    
                    resultados.append({
                        "Regime": nome,
                        "Area": round(area_int, 2),
                        "Perc": round(perc, 1),
                        "Lei": info_juridica[nome]["lei"],
                        "Artigo": info_juridica[nome]["artigo"],
                        "Coima": info_juridica[nome]["coima"]
                    })
    
    return resultados, analise_uso_solo, area_total

# --- FUNÇÃO DE MAPA ESTÁTICO COM SERVIDÕES ---

def criar_mapa_imagem(user_gdf, resultados):
    fig, ax = plt.subplots(figsize=(10, 8))
    user_gdf_web = user_gdf.to_crs(epsg=3857)
    cores = {"REN": "#2ecc71", "RAN": "#f1c40f", "Rede Natura": "#3498db"}
    
    for res in resultados:
        nome = res['Regime']
        path = f"data/{nome.lower().replace(' ', '_')}_amostra.geojson"
        if os.path.exists(path):
            camada = gpd.read_file(path).to_crs(epsg=3857)
            patch = gpd.overlay(camada, user_gdf_web, how='intersection')
            if not patch.empty:
                patch.plot(ax=ax, color=cores.get(nome, "gray"), alpha=0.5, label=f"Zona em {nome}")

    user_gdf_web.plot(ax=ax, facecolor="none", edgecolor="red", linewidth=2.5, label="Área de Intervenção")
    
    try:
        cx.add_basemap(ax, source=cx.providers.Esri.WorldImagery)
    except:
        pass
    
    ax.legend(loc='upper right', prop={'size': 10})
    ax.set_axis_off()
    temp_img = "mapa_temp.png"
    plt.savefig(temp_img, bbox_inches='tight', dpi=150)
    plt.close()
    return temp_img

# --- MOTOR DE RELATÓRIO WORD JURÍDICO ---

def gerar_word(user_gdf, resultados, analise_uso, area_total):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)

    doc.add_heading('Relatório Técnico de Fiscalização Territorial', 0)
    
    # 1. Mapa e Dados Gerais
    doc.add_heading('1. Enquadramento Geográfico e Identificação', level=1)
    img_path = criar_mapa_imagem(user_gdf, resultados)
    doc.add_picture(img_path, width=Inches(5.8))
    os.remove(img_path)
    
    doc.add_paragraph(f"Data da Análise: {date.today().strftime('%d/%m/%Y')}")
    doc.add_paragraph(f"Área Total Fiscalizada: {area_total:.2f} m²")

    # 2. Análise COS
    doc.add_heading('2. Verificação de Ocupação do Solo (COS 2023)', level=1)
    p_cos = doc.add_paragraph()
    p_cos.add_run("Resultado: ").bold = True
    p_cos.add_run(analise_uso)
    if "DIVERGÊNCIA" in analise_uso:
        doc.add_paragraph(
            "Fundamentação Jurídica: A discrepância entre o uso cartografado e o uso detetado no terreno constitui indício de "
            "infração ao regime de uso e ocupação do solo, podendo configurar alteração ilícita sem licenciamento municipal."
        )

    # 3. Análise Jurídica Detalhada e Coimas
    doc.add_heading('3. Análise de Servidões Administrativas e Restrições', level=1)
    if not resultados:
        doc.add_paragraph("Não foram detetadas sobreposições com condicionantes de proteção ambiental ou agrícola.")
    else:
        for res in resultados:
            doc.add_heading(f"Regime: {res['Regime']}", level=2)
            p = doc.add_paragraph()
            p.add_run(f"Sobreposição Detetada: {res['Area']} m² ({res['Perc']}% da área total).\n").bold = True
            
            p_jur = doc.add_paragraph()
            p_jur.add_run(f"Enquadramento Legal: ").bold = True
            p_jur.add_run(res['Lei'] + "\n")
            p_jur.add_run(f"Norma Aplicável: ").bold = True
            p_jur.add_run(res['Artigo'] + "\n")
            p_jur.add_run(f"Moldura Contraordenacional: ").bold = True
            p_jur.add_run(res['Coima']).font.color.rgb = None

    # 4. Medidas de Tutela
    doc.add_heading('4. Conclusões e Medidas de Tutela Recomendadas', level=1)
    doc.add_paragraph("Face às evidências colhidas, propõe-se as seguintes medidas executivas:", style='Normal')
    medidas = [
        "Verificação imediata de licenciamento ou autorização administrativa nos serviços municipais;",
        "Levantamento do respetivo Auto de Notícia caso não exista título autorizativo;",
        "Avaliação de medida cautelar de embargo para evitar o agravamento do dano;",
        "Notificação dos infratores para a reposição da situação anterior à infração."
    ]
    for medida in medidas:
        doc.add_paragraph(medida, style='List Number')

    doc.add_paragraph("\n\n__________________________________________\nAssinatura do Técnico/Fiscal Responsável")

    fname = "Relatorio_Fiscalizacao_Completo.docx"
    doc.save(fname)
    return fname

# --- INTERFACE ---

st.title("🛡️ Sistema de Apoio à Fiscalização (SIG + Jurídico)")
uploaded_file = st.sidebar.file_uploader("Carregar Polígono GeoJSON", type=['geojson'])

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
        st.subheader("📊 Painel de Análise")
        st.metric("Área Total", f"{a_total:.2f} m²")
        st.info(uso_txt)
        
        if st.button("📝 Gerar Relatório Jurídico Completo"):
            with st.spinner('A gerar relatório com mapas e fundamentação legal...'):
                doc_path = gerar_word(user_gdf, res, uso_txt, a_total)
                with open(doc_path, "rb") as f:
                    st.download_button("📥 Descarregar Word", f, file_name=doc_path)
    else:
        st.info("Aguardando upload de polígono...")

