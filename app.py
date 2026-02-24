import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
from datetime import date
import re
from pypdf import PdfReader

# 1. Configuração da Página
st.set_page_config(page_title="Fiscalização Pro - Região Centro", layout="wide", page_icon="🛡️")

# Estilo CSS
st.markdown("""
    <style>
    .main { background-color: #fcfcfc; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #f0f2f6; border-radius: 5px; padding: 8px 16px; }
    .stTabs [aria-selected="true"] { background-color: #1b5e20 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIGURAÇÃO IA ---
st.sidebar.header("⚙️ Configuração")
api_key = st.sidebar.text_input("Google API Key", type="password")

if api_key:
    genai.configure(api_key=api_key)

# --- LISTAS DE APOIO (REGIÃO CENTRO) ---
áreas_rn2000 = [
    "ZEC Serra de Aire e Candeeiros", "ZEC Serra da Estrela", "ZEC Sicó/Alvaiázere", 
    "ZEC Paul de Arzila", "ZEC Serra da Lousã", "ZEC Malcata", "ZPE Estuário do Mondego", "ZPE Ria de Aveiro"
]

áreas_protegidas_centro = [
    "Parque Natural da Serra da Estrela",
    "Parque Natural das Serras de Aire e Candeeiros",
    "Parque Natural do Tejo Internacional",
    "Reserva Natural do Paul de Arzila",
    "Reserva Natural das Berlengas",
    "Reserva Natural da Serra da Malcata",
    "Reserva Natural das Dunas de S. Jacinto",
    "Paisagem Protegida da Serra do Açor"
]

tipos_ren = ["Estrutura de Proteção de Encostas", "Áreas de Infiltração Máxima", "Zonas Adjacentes", "Cabeceiras de Linhas de Água"]

# --- INTERFACE ---
st.title("🛡️ Apoio à Fiscalização: Região Centro")
st.info("Gere documentação fundamentada com base em Regimes Jurídicos e Planos de Ordenamento.")

tab1, tab2, tab3 = st.tabs(["📍 Factos", "📜 Enquadramento Legal", "📑 Planos de Ordenamento"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        local = st.text_input("Concelho / Localidade", "Alenquer")
        area = st.number_input("Área Afetada (m²)", value=15591.67)
    with col2:
        ocupacao = st.text_area("Ação Detetada", "Aterro de materiais inertes com alteração da morfologia do solo.")

with tab2:
    col3, col4 = st.columns(2)
    with col3:
        r_ran = st.checkbox("RAN (DL 73/2009)")
        r_ren = st.checkbox("REN (DL 166/2008)")
        t_ren = st.multiselect("Tipologias REN:", tipos_ren) if r_ren else []
    with col4:
        r_rn2000 = st.checkbox("Rede Natura 2000 (ZEC/ZPE)")
        t_rn2000 = st.multiselect("Sítios RN2000:", áreas_rn2000) if r_rn2000 else []
        r_ap = st.checkbox("Áreas Protegidas (RNAP)")
        t_ap = st.multiselect("Áreas Protegidas (Centro):", áreas_protegidas_centro) if r_ap else []

conteudo_poap = ""
with tab3:
    st.subheader("📄 Análise de Planos de Ordenamento")
    arquivo_poap = st.file_uploader("Carregar PDF do Plano de Ordenamento (POAP/PGF)", type=['pdf'])
    if arquivo_poap:
        reader = PdfReader(arquivo_poap)
        conteudo_poap = "\n".join([page.extract_text() for page in reader.pages[:10]]) # Analisa as primeiras 10 páginas
        st.success("Plano carregado e pronto para análise da IA.")

# --- MOTOR DOCX ---
def gerar_docx_oficial(texto_ia):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)

    for section in doc.sections:
        section.top_margin, section.bottom_margin = Cm(2.5), Cm(2.5)
        section.left_margin, section.right_margin = Cm(3.0), Cm(2.5)

    linhas = texto_ia.replace('*', '').replace('#', '').split('\n')
    for linha in linhas:
        linha = linha.strip()
        if not linha: continue
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        if re.match(r'^(\d+\.|RELATÓRIO|PROPOSTA|AUTO|FUNDAMENTAÇÃO|CONCLUSÃO)', linha.upper()):
            run = p.add_run(linha)
            run.bold = True
            run.font.size = Pt(12)
        else:
            p.add_run(linha)

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- GERAÇÃO ---
st.markdown("---")
if st.button("🚀 Gerar Relatório e Auto de Notícia"):
    if not api_key:
        st.error("Insere a Google API Key.")
    else:
        with st.spinner("A IA está a cruzar os dados com os Planos de Ordenamento..."):
            model = genai.GenerativeModel("gemini-1.5-pro") # Versão Pro para análise de documentos
            
            prompt = f"""
            Age como Fiscal e Jurista Sénior. Elabora um Relatório de Fiscalização e Proposta de Auto de Notícia.
            
            CONTEXTO:
            - Local: {local}. Área: {area} m2. Ação: {ocupacao}.
            - Regimes: RAN={r_ran}, REN={t_ren}, RN2000={t_rn2000}, Áreas Protegidas={t_ap}.
            
            DADOS EXTRAÍDOS DO PLANO DE ORDENAMENTO CARREGADO:
            {conteudo_poap[:2000]} 
            
            TAREFA:
            1. No RELATÓRIO, cita os artigos do Plano de Ordenamento (se carregado) que proíbem esta ação.
            2. Na PROPOSTA DE AUTO, define coimas e medidas de reposição.
            
            REGRAS: Português formal, capítulos a bold, texto justificado, sem asteriscos.
            """
            
            try:
                res = model.generate_content(prompt).text
                docx = gerar_docx_oficial(res)
                st.success("Documentação gerada com base no Plano de Ordenamento!")
                st.download_button("📥 Descarregar Word (.docx)", docx, file_name=f"Fiscalizacao_{local}.docx")
            except Exception as e:
                st.error(f"Erro: {e}")
