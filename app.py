import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
from datetime import date
import re
from pypdf import PdfReader

# 1. Configuração de Interface
st.set_page_config(page_title="Fiscalização Pro: Regimes e Infrações", layout="wide", page_icon="🛡️")

# Estilo CSS
st.markdown("""
    <style>
    .main { background-color: #f4f7f6; }
    .stTabs [data-baseweb="tab"] { font-weight: bold; }
    .stTabs [aria-selected="true"] { border-bottom: 2px solid #2e7d32; color: #2e7d32; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR CONFIG ---
st.sidebar.header("⚙️ Painel de Controlo")
api_key = st.sidebar.text_input("Google API Key", type="password")
modelo_selecionado = "gemini-1.5-pro"

if api_key:
    genai.configure(api_key=api_key)
    try:
        modelos = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        modelo_selecionado = st.sidebar.selectbox("Motor de IA", modelos, index=0)
    except:
        st.sidebar.error("Verifica a API Key.")

# --- LISTAS DE INFRAÇÕES POR REGIME ---
inf_territorio = [
    "Alteração da morfologia do solo (Aterro/Escavação)",
    "Destruição do coberto vegetal",
    "Instalação de estruturas temporárias sem licença",
    "Impermeabilização de solos protegidos",
    "Corte de espécies arbóreas protegidas (Sobreiro/Azinheira)",
    "Utilização de solo RAN para fins não agrícolas"
]

inf_residuos_agua = [
    "Abandono de Resíduos de Construção e Demolição (RCD)",
    "Deposição incontrolada de resíduos perigosos",
    "Queima de resíduos a céu aberto",
    "Captação de água sem título (furo ilícito)",
    "Rejeição de efluentes no solo ou em linha de água",
    "Ocupação de Domínio Hídrico (leito ou margem)"
]

inf_patrimonio_natureza = [
    "Intervenção em ZGP/ZEP sem parecer da tutela",
    "Danos em património classificado",
    "Destruição de habitats protegidos (Rede Natura 2000)",
    "Circulação de veículos fora de trilhos em Área Protegida",
    "Realização de eventos/atividades interditas pelo POAP"
]

# --- INTERFACE ---
st.title("🛡️ Sistema de Fiscalização Territorial Integrada")

tab1, tab2, tab3 = st.tabs(["📍 Ocorrência e Infrator", "⚖️ Infrações e Regimes", "📑 Documentação"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Dados do Local")
        local = st.text_input("Localização / Concelho", "Alenquer")
        area = st.number_input("Área Afetada (m²)", value=15591.67)
        ocupacao = st.text_area("Descrição Sumária", "Deteção de infrações multidisciplinares no local.")
    with col2:
        st.subheader("Dados do Infrator")
        infrator_n = st.text_input("Nome / Empresa", "Em averiguação")
        nif = st.text_input("NIF / NIPC", "000000000")
        morada = st.text_input("Morada", "Desconhecida")

with tab2:
    st.subheader("⚠️ Tipificação de Infrações Detetadas")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.write("**Território e Solo (RAN/REN)**")
        sel_territorio = [inf for inf in inf_territorio if st.checkbox(inf)]
    with c2:
        st.write("**Resíduos e Água**")
        sel_residuos = [inf for inf in inf_residuos_agua if st.checkbox(inf)]
    with c3:
        st.write("**Conservação e Património**")
        sel_patrimonio = [inf for inf in inf_patrimonio_natureza if st.checkbox(inf)]

    st.divider()
    gravidade = st.select_slider("Gravidade da Ocorrência", options=["Leve", "Grave", "Muito Grave"])

with tab3:
    st.write("Carregue o regulamento (PDF) para análise de artigos específicos.")
    arq = st.file_uploader("Upload PDF", type=['pdf'])
    conteudo_extra = ""
    if arq:
        reader = PdfReader(arq)
        conteudo_extra = "\n".join([p.extract_text() for p in reader.pages[:10]])
        st.success("Plano carregado.")

# --- MOTOR DOCX ---
def gerar_docx(texto):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)
    
    for section in doc.sections:
        section.top_margin, section.bottom_margin = Cm(2.5), Cm(2.5)
        section.left_margin, section.right_margin = Cm(3.0), Cm(2.5)

    for linha in texto.replace('*', '').replace('#', '').split('\n'):
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
    
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# --- GERAÇÃO ---
if st.button("🚀 Gerar Relatório e Auto Baseado em Infrações"):
    if not api_key:
        st.error("Insere a Google API Key.")
    else:
        with st.spinner("A cruzar as infrações selecionadas com os regimes legais..."):
            model = genai.GenerativeModel(modelo_selecionado)
            prompt = f"""
            Age como Fiscal e Jurista Sénior. Elabora um Relatório de Fiscalização e Proposta de Auto de Notícia.
            Texto Justificado, Português Formal com acentos, sem asteriscos.
            
            DADOS:
            - Local: {local}. Área: {area} m2.
            - INFRATOR: {infrator_n}, NIF: {nif}, Morada: {morada}.
            - INFRAÇÕES DETETADAS:
              Território: {sel_territorio}
              Resíduos/Água: {sel_residuos}
              Património/Natureza: {sel_patrimonio}
            
            ESTRUTURA:
            1. RELATÓRIO DE FISCALIZAÇÃO: Fundamenta juridicamente cada infração selecionada (DL 73/2009, DL 166/2008, DL 142/2008, Lei 58/2005, Lei 107/2001, DL 102-D/2020).
            2. PROPOSTA DE AUTO DE NOTÍCIA: Tipifica as contraordenações. Indica coimas mín/máx para gravidade {gravidade} conforme a Lei 50/2006.
            """
            try:
                res = model.generate_content(prompt).text
                docx = gerar_docx(res)
                st.success("Documentação gerada!")
                st.download_button("📥 Descarregar Word (.docx)", docx, file_name=f"Auto_{local}.docx")
                st.text_area("Pré-visualização", res.replace('*', ''), height=300)
            except Exception as e:
                st.error(f"Erro: {e}")
