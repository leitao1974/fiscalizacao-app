import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
from datetime import date
import re

# Configuração da Página
st.set_page_config(page_title="Fiscalização Pro", layout="wide", page_icon="🛡️")

# Estilo CSS para leveza da interface
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #007bff; color: white; }
    </style>
    """, unsafe_allow_stdio=True)

# --- SIDEBAR CONFIG ---
st.sidebar.header("⚙️ Configuração do Sistema")
api_key = st.sidebar.text_input("Google API Key", type="password")

modelo_nome = "gemini-1.5-flash"
if api_key:
    genai.configure(api_key=api_key)
    try:
        models = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        modelo_nome = st.sidebar.selectbox("Modelo", models)
    except:
        st.sidebar.error("Chave API inválida.")

# --- LISTAS DE APOIO ---
tipos_ren = ["Estrutura de Proteção de Encostas", "Áreas de Infiltração Máxima", "Zonas Adjacentes", "Cabeceiras de Linhas de Água", "Zonas Ameaçadas pelas Cheias"]
tipos_zec = ["ZEC - Serra de Aire e Candeeiros", "ZEC - Paul de Arzila", "ZEC - Serra da Estrela", "ZEC - Sicó/Alvaiázere", "ZPE - Paul de Taipal / Arzila"]

# --- INTERFACE PRINCIPAL ---
st.title("🛡️ Gerador de Relatórios de Fiscalização")
st.info("Preencha os dados abaixo para gerar o Relatório e o Auto de Notícia em formato Word.")

tab1, tab2 = st.tabs(["📍 Dados e Enquadramento", "⚖️ Contraordenação"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        local = st.text_input("Localização / Concelho", "Alenquer")
        area = st.number_input("Área Afetada (m²)", value=15591.67)
        ocupacao = st.text_area("Ação Detetada", "Aterro de materiais inertes com alteração da morfologia do solo.")
    with col2:
        st.write("**Regimes Jurídicos Ativos:**")
        r_ran = st.checkbox("RAN (DL 73/2009)")
        r_ren = st.checkbox("REN (DL 166/2008)")
        r_zec = st.checkbox("Rede Natura 2000 (ZEC/ZPE)")
        
        t_ren = st.multiselect("Tipologias REN:", tipos_ren) if r_ren else []
        t_zec = st.multiselect("Zonas Especiais (ZEC/ZPE):", tipos_zec) if r_zec else []

with tab2:
    col3, col4 = st.columns(2)
    with col3:
        infrator = st.text_input("Identificação do Infrator", "Em averiguação")
    with col4:
        gravidade = st.select_slider("Gravidade Proposta", options=["Leve", "Grave", "Muito Grave"])

# --- MOTOR DE FORMATAÇÃO WORD ---
def gerar_docx(texto_ia):
    doc = Document()
    
    # Configuração de Margens
    for section in doc.sections:
        section.top_margin = Cm(2.5)
        section.bottom_margin = Cm(2.5)
        section.left_margin = Cm(3.0)
        section.right_margin = Cm(2.5)

    # Limpeza de asteriscos e caracteres especiais da IA
    texto_limpo = texto_ia.replace('*', '').replace('#', '')
    linhas = texto_limpo.split('\n')

    for linha in linhas:
        linha = linha.strip()
        if not linha:
            continue
            
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.space_after = Pt(6)
        
        # Identificação de Capítulos (ex: 1. INTRODUÇÃO ou RELATÓRIO)
        if re.match(r'^(\d+\.|RELATÓRIO|PROPOSTA|AUTO|CONCLUSÃO|FUNDAMENTAÇÃO)', linha.upper()):
            run = p.add_run(linha)
            run.bold = True
            run.font.name = 'Arial'
            run.font.size = Pt(12)
        # Identificação de Subcapítulos (ex: 1.1. Localização)
        elif re.match(r'^\d+\.\d+\.', linha):
            run = p.add_run(linha)
            run.bold = True
            run.font.name = 'Arial'
            run.font.size = Pt(11)
        # Texto Normal
        else:
            run = p.add_run(linha)
            run.font.name = 'Arial'
            run.font.size = Pt(11)

    output = BytesIO()
    doc.save(output)
    output.seek(0)
    return output

# --- EXECUÇÃO ---
if st.button("🚀 Gerar Documentação Final"):
    if not api_key:
        st.warning("Introduza a sua Google API Key para continuar.")
    else:
        with st.spinner("A redigir relatório justificado e auto de notícia..."):
            model = genai.GenerativeModel(modelo_nome)
            prompt = f"""
            Age como Fiscal e Jurista Sénior. Elabora um Relatório de Fiscalização e uma Proposta de Auto de Notícia.
            PORTUGUÊS FORMAL COM ACENTOS. SEM ASTERISCOS OU MARCADORES MD.
            
            ESTRUTURA OBRIGATÓRIA:
            1. RELATÓRIO DE FISCALIZAÇÃO (Título)
            1.1. Introdução
            1.2. Descrição dos Factos (Local: {local}, Área: {area} m2, Ação: {ocupacao})
            1.3. Enquadramento Jurídico (RAN: {r_ran}, REN: {t_ren}, ZEC/ZPE: {t_zec})
            1.4. Conclusão
            
            2. PROPOSTA DE AUTO DE NOTÍCIA (Título)
            2.1. Identificação da Infração
            2.2. Moldura Contraordenacional (Gravidade: {gravidade}. Indica coimas mín/máx para pessoas singulares e coletivas)
            2.3. Medidas de Reposição
            """
            
            res = model.generate_content(prompt).text
            docx_file = gerar_docx(res)
            
            st.success("Documento gerado com sucesso!")
            st.download_button(
                label="📥 Descarregar Relatório de Fiscalização (.docx)",
                data=docx_file,
                file_name=f"Relatorio_{local}_{date.today()}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            st.markdown("### Pré-visualização do Texto")
            st.write(res.replace('*', ''))
