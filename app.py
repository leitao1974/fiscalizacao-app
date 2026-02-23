import streamlit as st
import geopandas as gpd
import pandas as pd
import leafmap.foliumap as leafmap
from fpdf import FPDF
import google.generativeai as genai
import matplotlib.pyplot as plt
import contextily as cx
import os
from datetime import date

# 1. Configuração da Página
st.set_page_config(layout="wide", page_title="Fiscalização IA SIG", page_icon="🤖")

# --- SIDEBAR: CONFIGURAÇÃO DA IA ---
st.sidebar.title("🔑 Configuração IA")
api_key = st.sidebar.text_input("Insere a tua Google API Key", type="password")

modelo_selecionado = "gemini-1.5-flash" # Default inicial

if api_key:
    try:
        genai.configure(api_key=api_key)
        # Obter modelos disponíveis que suportam geração de conteúdo
        available_models = [m.name.replace('models/', '') for m in genai.list_models() 
                            if 'generateContent' in m.supported_generation_methods]
        
        modelo_selecionado = st.sidebar.selectbox(
            "Escolhe o Modelo Gemini",
            options=available_models,
            index=available_models.index("gemini-1.5-flash") if "gemini-1.5-flash" in available_models else 0
        )
        st.sidebar.success("IA configurada com sucesso!")
    except Exception as e:
        st.sidebar.error(f"Erro na chave ou modelos: {e}")
else:
    st.sidebar.warning("Aguardando API Key para ativar o motor IA.")

# --- MOTOR DE ANÁLISE IA ---
def redigir_parecer_ia(dados_analise, modelo_name):
    try:
        model = genai.GenerativeModel(modelo_name)
        prompt = f"""
        Age como um fiscal do territorio em Portugal. Elabora um parecer tecnico detalhado com base nestes dados:
        {dados_analise}
        
        O relatorio deve incluir:
        1. Analise da Ocupacao do Solo (compara o uso oficial COS2023 com o detetado no terreno).
        2. Enquadramento Juridico (cita especificamente o DL 73/2009 para RAN e o DL 166/2008 para REN).
        3. Molduras das Coimas (valores para pessoas singulares e coletivas).
        4. Conclusao e Medidas de Tutela (Auto de noticia, Embargo, Reposicao).
        
        Usa um tom formal. IMPORTANTE: Nao uses caracteres especiais ou acentos para garantir compatibilidade com o PDF.
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Erro na geração do parecer: {e}"

# --- FUNÇÃO CARTOGRÁFICA ---
def gerar_mapa_estatico(user_gdf):
    plt.switch_backend('Agg')
    fig, ax = plt.subplots(figsize=(10, 8), dpi=120)
    user_gdf_web = user_gdf.to_crs(epsg=3857)
    
    try:
        cx.add_basemap(ax, source=cx.providers.Esri.WorldImagery, zorder=0)
    except:
        ax.set_facecolor('#f0f0f0')
        
    user_gdf_web.plot(ax=ax, facecolor="red", alpha=0.4, edgecolor="red", linewidth=2, zorder=1)
    
    bounds = user_gdf_web.total_bounds
    ax.set_xlim([bounds[0] - 150, bounds[2] + 150])
    ax.set_ylim([bounds[1] - 150, bounds[3] + 150])
    ax.set_axis_off()
    
    mapa_path = "mapa_relatorio.png"
    plt.savefig(mapa_path, bbox_inches='tight')
    plt.close(fig)
    return mapa_path

# --- GERAÇÃO DE PDF ---
def exportar_pdf_ia(texto_ia, mapa_path):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Relatorio Tecnico de Fiscalizacao IA", 0, 1, 'C')
    pdf.ln(5)
    
    if os.path.exists(mapa_path):
        pdf.image(mapa_path, x=15, y=None, w=180)
        pdf.ln(5)
    
    pdf.set_font("Arial", '', 10)
    # Limpeza de caracteres para evitar erros de encoding no FPDF
    txt_limpo = texto_ia.encode('latin-1', 'ignore').decode('latin-1')
    pdf.multi_cell(0, 6, txt_limpo)
    
    pdf_name = "Relatorio_Fiscalizacao_IA.pdf"
    pdf.output(pdf_name)
    return pdf_name

# --- INTERFACE PRINCIPAL ---
st.title("🛡️ Sistema de Fiscalização SIG Inteligente")
file = st.sidebar.file_uploader("Carregar Polígono (GeoJSON)", type=['geojson'])

if file:
    user_gdf = gpd.read_file(file).to_crs(epsg=3763)
    area = user_gdf.area.sum()
    
    # Simulação dos dados extraídos do SIG (Baseado no teu exemplo anterior [cite: 3, 5])
    # Na versão final, podes automatizar esta extração das tuas camadas GeoJSON
    dados_para_ia = {
        "data_analise": date.today().strftime('%d/%m/%Y'),
        "area_total": f"{area:.2f} m2 [cite: 3]",
        "uso_oficial_cos": "Culturas temporarias de sequeiro e regadio [cite: 5]",
        "uso_detetado": "Aterro + Construcao de infraestrutura [cite: 5]",
        "servidao_detetada": "RAN - Reserva Agricola Nacional (100% de sobreposicao) [cite: 15, 22]"
    }
    
    col_map, col_ia = st.columns([2, 1])
    
    with col_map:
        m = leafmap.Map(google_map="HYBRID")
        m.add_gdf(user_gdf, layer_name="Alvo")
        m.zoom_to_gdf(user_gdf)
        m.to_streamlit(height=600)
        
    with col_res:
        st.subheader("📋 Resumo SIG")
        st.write(f"**Área Alvo:** {area:.2f} m² [cite: 3]")
        
        if not api_key:
            st.info("Insere a API Key na barra lateral para redigir o parecer.")
        else:
            if st.button("🤖 Redigir Parecer e Gerar PDF"):
                with st.spinner(f'O modelo {modelo_selecionado} está a analisar os dados...'):
                    texto_parecer = redigir_parecer_ia(dados_para_ia, modelo_selecionado)
                    mapa_img = gerar_mapa_estatico(user_gdf)
                    pdf_path = exportar_pdf_ia(texto_parecer, mapa_img)
                    
                    st.markdown("### Parecer Técnico Gerado")
                    st.write(texto_parecer)
                    
                    with open(pdf_path, "rb") as f:
                        st.download_button("📥 Baixar Relatório PDF", f, file_name=pdf_path)
