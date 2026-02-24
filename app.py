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
st.set_page_config(page_title="Fiscalização Territorial Integrada", layout="wide", page_icon="🛡️")

# CSS para layout profissional e "chave dinâmica"
st.markdown("""
    <style>
    .main { background-color: #f4f7f6; }
    .stTabs [data-baseweb="tab"] { font-weight: bold; }
    .stTabs [aria-selected="true"] { border-bottom: 2px solid #1b5e20; color: #1b5e20; }
    </style>
    """, unsafe_allow_html=True)

# --- RECUPERAÇÃO DA CHAVE DINÂMICA (MODELOS) ---
st.sidebar.header("⚙️ Painel de Controlo")
api_key = st.sidebar.text_input("Google API Key", type="password")

modelo_selecionado = "gemini-1.5-pro" # Default para análise complexa

if api_key:
    genai.configure(api_key=api_key)
    try:
        # Lista dinamicamente os modelos disponíveis na tua conta
        modelos_disponiveis = [m.name.replace('models/', '') for m in genai.list_models() 
                               if 'generateContent' in m.supported_generation_methods]
        modelo_selecionado = st.sidebar.selectbox("Motor de IA Ativo (Chave Dinâmica)", modelos_disponiveis, index=0)
        st.sidebar.success(f"Ligado ao motor: {modelo_selecionado}")
    except Exception as e:
        st.sidebar.error("Erro ao listar modelos. Verifica a tua API Key.")

# --- LISTAS DE APOIO ---
zec_zpe_centro = ["ZEC Serra de Aire e Candeeiros", "ZEC Serra da Estrela", "ZEC Sicó/Alvaiázere", "ZEC Paul de Arzila", "ZEC Serra da Lousã", "ZEC Malcata", "ZPE Estuário do Mondego", "ZPE Ria de Aveiro"]
rnap_centro = ["P.N. Serra da Estrela", "P.N. Serras de Aire e Candeeiros", "R.N. Paul de Arzila", "R.N. Serra da Malcata", "R.N. Berlengas"]
tipos_residuos = ["RCD (Resíduos de Construção e Demolição)", "Terras e Rochas", "Misturas de Resíduos Perigosos", "Pneus/Óleos"]

# --- INTERFACE ---
st.title("🛡️ Sistema de Fiscalização e Contraordenações")
st.markdown("Análise jurídica multidisciplinar: **Solo, Água, Resíduos e Conservação**.")

tab1, tab2, tab3 = st.tabs(["📍 Localização e Factos", "⚖️ Tipologias Jurídicas", "📑 Análise de Planos (POAP)"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        local = st.text_input("Concelho / Localidade", "Alenquer")
        area = st.number_input("Área Afetada (m²)", value=15591.67, format="%.2f")
    with col2:
        ocupacao = st.text_area("Descrição da Ação", "Deposição de materiais e alteração da morfologia do solo em zona sensível.")

with tab2:
    c1, c2, c3 = st.columns(3)
    with c1:
        st.subheader("🌾 Ordenamento")
        r_ran = st.checkbox("RAN (DL 73/2009)")
        r_ren = st.checkbox("REN (DL 166/2008)")
        r_rjaia = st.checkbox("RJAIA (Impacte Ambiental)")
    with c2:
        st.subheader("🌿 Conservação (DL 142/2008)")
        r_rn2000 = st.checkbox("Rede Natura 2000 (ZEC/ZPE)")
        t_rn2000 = st.multiselect("Sítios:", zec_zpe_centro) if r_rn2000 else []
        r_ap = st.checkbox("Áreas Protegidas (RNAP)")
        t_ap = st.multiselect("Parques/Reservas:", rnap_centro) if r_ap else []
    with c3:
        st.subheader("💧 Água e 🗑️ Resíduos")
        r_agua = st.checkbox("Lei da Água (Domínio Hídrico)")
        r_residuos = st.checkbox("Resíduos (RGGR)")
        t_residuos = st.multiselect("Tipos:", tipos_residuos) if r_residuos else []

    st.divider()
    infrator = st.text_input("Infrator", "Em averiguação")
    gravidade = st.select_slider("Gravidade Proposta", options=["Leve", "Grave", "Muito Grave"])

conteudo_poap = ""
with tab3:
    st.write("Carregue o regulamento (PDF) para que a IA cite os artigos específicos.")
    arq = st.file_uploader("Upload PDF (POAP/PDM/RJCNB)", type=['pdf'])
    if arq:
        reader = PdfReader(arq)
        conteudo_poap = "\n".join([p.extract_text() for p in reader.pages[:10]])
        st.success("Plano carregado com sucesso.")

# --- MOTOR DOCX ---
def gerar_docx_profissional(texto_ia):
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
        elif re.match(r'^\d+\.\d+\.', linha):
            run = p.add_run(linha)
            run.bold = True
        else:
            p.add_run(linha)
    
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# --- GERAÇÃO ---
if st.button("🚀 Gerar Documentação de Fiscalização (Word)"):
    if not api_key:
        st.error("Insere a Google API Key.")
    else:
        with st.spinner(f"A utilizar o motor {modelo_selecionado} para análise jurídica..."):
            model = genai.GenerativeModel(modelo_selecionado)
            prompt = f"""
            Age como Fiscal e Jurista Especialista em Ambiente e Ordenamento.
            Elabora um Relatório de Fiscalização e uma Proposta de Auto de Notícia.
            PORTUGUÊS FORMAL COM ACENTOS. TEXTO JUSTIFICADO. SEM ASTERISCOS.
            
            DADOS:
            - Local: {local}. Área: {area} m2. Ação: {ocupacao}.
            - Regimes: RAN={r_ran}, REN={r_ren}, RJAIA={r_rjaia}, RN2000={t_rn2000}, Áreas Protegidas={t_ap}, Água={r_agua}, Resíduos={t_residuos}.
            - Conteúdo do Plano: {conteudo_poap[:2000]}
            
            ESTRUTURA:
            1. RELATÓRIO DE FISCALIZAÇÃO: Analisa a violação face a todos os regimes selecionados e ao Plano de Ordenamento.
            2. PROPOSTA DE AUTO DE NOTÍCIA: Tipifica as infrações. Indica coimas mín/máx de acordo com a Lei 50/2006 (Quadro Ambiental) e regimes específicos. Propõe embargo e reposição.
            """
            
            try:
                res = model.generate_content(prompt).text
                docx = gerar_docx_profissional(res)
                st.success("Documentação gerada com sucesso!")
                st.download_button("📥 Descarregar Word (.docx)", docx, file_name=f"Fiscalizacao_{local}.docx")
            except Exception as e:
                st.error(f"Erro na IA: {e}")
