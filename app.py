import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
from datetime import date
import re

# 1. Configuração da Página
st.set_page_config(page_title="Fiscalização Pro", layout="wide", page_icon="🛡️")

# Estilo CSS para leveza da interface (Correção do Erro unsafe_allow_html)
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #f0f2f6; border-radius: 5px 5px 0 0; padding: 10px; }
    .stTabs [aria-selected="true"] { background-color: #007bff !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR CONFIG ---
st.sidebar.header("⚙️ Configuração")
api_key = st.sidebar.text_input("Google API Key", type="password")

modelo_nome = "gemini-1.5-flash"
if api_key:
    genai.configure(api_key=api_key)
    try:
        models = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        modelo_nome = st.sidebar.selectbox("Modelo", models)
    except:
        st.sidebar.error("Chave API inválida ou erro de ligação.")

# --- LISTAS DE APOIO ---
tipos_ren = ["Estrutura de Proteção de Encostas", "Áreas de Infiltração Máxima", "Zonas Adjacentes", "Cabeceiras de Linhas de Água", "Zonas Ameaçadas pelas Cheias"]
tipos_zec = ["ZEC - Serra de Aire e Candeeiros", "ZEC - Paul de Arzila", "ZEC - Serra da Estrela", "ZEC - Sicó/Alvaiázere", "ZPE - Paul de Taipal / Arzila"]

# --- INTERFACE PRINCIPAL ---
st.title("🛡️ Sistema de Apoio à Fiscalização")
st.info("Gere Relatórios de Fiscalização e Autos de Notícia profissionais em Word (.docx)")

tab1, tab2 = st.tabs(["📍 Localização e Factos", "⚖️ Enquadramento Legal"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        local = st.text_input("Localização / Concelho", "Alenquer")
        area = st.number_input("Área Afetada (m²)", value=15591.67)
    with col2:
        ocupacao = st.text_area("Ação/Ocupação Detetada", "Realização de aterro com deposição de materiais, alterando a morfologia do solo.")

with tab2:
    col3, col4 = st.columns(2)
    with col3:
        st.write("**Regimes Jurídicos:**")
        r_ran = st.checkbox("RAN (DL 73/2009)")
        r_ren = st.checkbox("REN (DL 166/2008)")
        r_zec = st.checkbox("Rede Natura 2000 (ZEC/ZPE)")
        
        t_ren = st.multiselect("Tipologias REN:", tipos_ren) if r_ren else []
        t_zec = st.multiselect("Zonas Especiais (ZEC/ZPE):", tipos_zec) if r_zec else []
    with col4:
        st.write("**Parâmetros do Auto:**")
        infrator = st.text_input("Identificação do Infrator", "Em averiguação")
        gravidade = st.select_slider("Gravidade Proposta", options=["Leve", "Grave", "Muito Grave"])

# --- MOTOR DE FORMATAÇÃO WORD PROFISSIONAL ---
def gerar_docx_profissional(texto_ia):
    doc = Document()
    
    # Estilo de Fonte Padrão: Arial
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)

    # Margens Normas Administrativas
    for section in doc.sections:
        section.top_margin = Cm(2.5)
        section.bottom_margin = Cm(2.5)
        section.left_margin = Cm(3.0)
        section.right_margin = Cm(2.5)

    # Limpeza de caracteres da IA (asteriscos e cardinal)
    texto_limpo = texto_ia.replace('*', '').replace('#', '')
    linhas = texto_limpo.split('\n')

    for linha in linhas:
        linha = linha.strip()
        if not linha:
            continue
            
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.space_after = Pt(8)
        
        # Lógica para BOLD em Capítulos e Subcapítulos
        # Deteta: "1. TÍTULO", "RELATÓRIO", "1.1. Subtítulo"
        is_header = re.match(r'^(\d+\.|RELATÓRIO|PROPOSTA|AUTO|CONCLUSÃO|FUNDAMENTAÇÃO|ASSUNTO)', linha.upper())
        is_sub_header = re.match(r'^\d+\.\d+\.', linha)

        if is_header or is_sub_header:
            run = p.add_run(linha)
            run.bold = True
            if is_header:
                run.font.size = Pt(12)
            else:
                run.font.size = Pt(11)
        else:
            run = p.add_run(linha)

    output = BytesIO()
    doc.save(output)
    output.seek(0)
    return output

# --- GERAÇÃO ---
st.markdown("---")
if st.button("🚀 Gerar Documentação e Proposta de Auto"):
    if not api_key:
        st.warning("Por favor, introduza a sua Google API Key na barra lateral.")
    else:
        with st.spinner("A IA está a redigir o parecer jurídico com acentuação correta..."):
            model = genai.GenerativeModel(modelo_nome)
            prompt = f"""
            Age como Fiscal do Território e Jurista Sénior. 
            Escreve um documento formal com acentos e português correto.
            
            ESTRUTURA:
            1. RELATÓRIO DE FISCALIZAÇÃO
            1.1. Introdução e Localização ({local})
            1.2. Descrição da Ocorrência (Área: {area} m2, Ação: {ocupacao})
            1.3. Enquadramento Legal (RAN: {r_ran}, REN: {t_ren}, ZEC/ZPE: {t_zec})
            1.4. Análise Técnica e Danos
            
            2. PROPOSTA DE AUTO DE NOTÍCIA
            2.1. Identificação da Infração e Infrator ({infrator})
            2.2. Moldura Contraordenacional (Gravidade: {gravidade}. Indica valores de coimas para singulares e coletivas)
            2.3. Medidas de Reposição da Legalidade
            
            REGRAS: Texto justificado, sem asteriscos, capítulos bem definidos.
            """
            
            try:
                res = model.generate_content(prompt).text
                docx_file = gerar_docx_profissional(res)
                
                st.success("Documento Word gerado com sucesso!")
                st.download_button(
                    label="📥 Descarregar Relatório de Fiscalização (.docx)",
                    data=docx_file,
                    file_name=f"Relatorio_Fiscalizacao_{local}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
                with st.expander("Ver Pré-visualização do Conteúdo"):
                    st.write(res.replace('*', ''))
            except Exception as e:
                st.error(f"Erro ao gerar conteúdo: {e}")

