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
st.set_page_config(page_title="Fiscalização Integrada: Património e Território", layout="wide", page_icon="🛡️")

# Estilo CSS para interface profissional
st.markdown("""
    <style>
    .main { background-color: #f4f7f6; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { background-color: #e8f5e9; border-radius: 4px; padding: 10px 20px; font-weight: bold; }
    .stTabs [aria-selected="true"] { background-color: #2e7d32 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR CONFIG (CHAVE DINÂMICA) ---
st.sidebar.header("⚙️ Painel de Controlo")
api_key = st.sidebar.text_input("Google API Key", type="password")

modelo_selecionado = "gemini-1.5-pro"
if api_key:
    genai.configure(api_key=api_key)
    try:
        modelos_disponiveis = [m.name.replace('models/', '') for m in genai.list_models() 
                               if 'generateContent' in m.supported_generation_methods]
        modelo_selecionado = st.sidebar.selectbox("Motor de IA Ativo", modelos_disponiveis, index=0)
    except:
        st.sidebar.error("Erro na API Key.")

# --- LISTAS DE APOIO (PATRIMÓNIO, RN2000, REN, AP) ---
tipologias_patrimonio = [
    "Monumento Nacional (ZGP/ZEP - 50m)",
    "Imóvel de Interesse Público (ZGP/ZEP)",
    "Imóvel de Interesse Municipal",
    "Sítio Arqueológico (Proteção de Subsolo)",
    "Conjunto ou Sítio Classificado",
    "Zona Especial de Proteção (ZEP) específica"
]

tipologias_ren = [
    "Áreas de Proteção de Encostas", "Áreas de Infiltração Máxima", "Zonas Adjacentes",
    "Cursos de Água", "Cabeceiras de linhas de água", "Zonas Ameaçadas pelas Cheias",
    "Arribas e respetivas faixas de proteção", "Estuários e Áreas Húmidas"
]

zec_zpe_centro_completa = [
    "ZEC Serra de Aire e Candeeiros", "ZEC Serra da Estrela", "ZEC Sicó/Alvaiázere", 
    "ZEC Paul de Arzila", "ZEC Serra da Lousã", "ZEC Malcata", "ZEC Rio Zêzere",
    "ZEC Albufeira de Castelo do Bode", "ZEC Rio Paiva", "ZEC Douro Internacional",
    "ZPE Paul do Boquilobo", "ZPE Estuário do Mondego", "ZPE Douro Internacional"
]

areas_protegidas_centro = [
    "Parque Natural do Douro Internacional (PNDI)",
    "Parque Natural da Serra da Estrela (PNSE)",
    "Parque Natural das Serras de Aire e Candeeiros (PNSAC)",
    "Parque Natural do Tejo Internacional",
    "Reserva Natural do Paul do Boquilobo",
    "Reserva Natural do Paul de Arzila",
    "Reserva Natural da Serra da Malcata"
]

zonamentos_poap = [
    "Reserva Integral", "Reserva Parcial", 
    "Zona de Proteção Parcial de Tipo I", "Zona de Proteção Parcial de Tipo II",
    "Zona de Proteção Complementar", "Área de Intervenção Específica"
]

# --- INTERFACE ---
st.title("🛡️ Sistema de Apoio à Fiscalização e Auto de Notícia")
st.markdown("Análise Jurídica: **RAN, REN, ZEC/ZPE, Património Cultural e Conservação da Natureza**.")

tab1, tab2, tab3 = st.tabs(["📍 Ocorrência", "⚖️ Enquadramento Legal", "📑 Documentação Base"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        local = st.text_input("Localização / Concelho", "Alenquer / Tomar / Figueira de Castelo Rodrigo")
        area = st.number_input("Área Afetada (m²)", value=15591.67, format="%.2f")
    with col2:
        ocupacao = st.text_area("Descrição da Ação Detetada", "Execução de aterro com alteração da morfologia do solo e potencial impacto em património/natureza.")

with tab2:
    c1, c2, c3 = st.columns(3)
    with c1:
        st.subheader("🌾 Uso do Solo")
        r_ran = st.checkbox("RAN (DL 73/2009)")
        r_ren = st.checkbox("REN (DL 166/2008)")
        t_ren = st.multiselect("Tipologias REN:", tipologias_ren) if r_ren else []
        
    with c2:
        st.subheader("🌿 Conservação")
        r_ap = st.checkbox("Área Protegida (RNAP)")
        t_ap = st.multiselect("Parques/Reservas:", areas_protegidas_centro) if r_ap else []
        t_zonas = st.multiselect("Zonamento POAP:", zonamentos_poap) if r_ap else []
        
        r_rn2000 = st.checkbox("Rede Natura 2000")
        t_rn2000 = st.multiselect("ZEC/ZPE:", zec_zpe_centro_completa) if r_rn2000 else []

    with c3:
        st.subheader("🏛️ Património e Água")
        r_patrimonio = st.checkbox("Património Cultural")
        t_patrimonio = st.multiselect("Tipologia:", tipologias_patrimonio) if r_patrimonio else []
        
        r_agua = st.checkbox("Domínio Hídrico (Lei Água)")
        st.divider()
        gravidade = st.select_slider("Gravidade Proposta", options=["Leve", "Grave", "Muito Grave"])

conteudo_poap = ""
with tab3:
    st.write("Carregue o regulamento (PDF) para fundamentação automática.")
    arquivo = st.file_uploader("Upload PDF (Regulamento/Plano)", type=['pdf'])
    if arquivo:
        reader = PdfReader(arquivo)
        conteudo_poap = "\n".join([page.extract_text() for page in reader.pages[:15]])
        st.success("Plano carregado.")

# --- MOTOR DOCX ---
def gerar_docx_final(texto_ia):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)
    
    for section in doc.sections:
        section.top_margin, section.bottom_margin = Cm(2.5), Cm(2.5)
        section.left_margin, section.right_margin = Cm(3.0), Cm(2.5)

    texto_limpo = texto_ia.replace('*', '').replace('#', '')
    for linha in texto_limpo.split('\n'):
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
st.divider()
if st.button("🚀 Gerar Relatório e Auto de Notícia Profissional"):
    if not api_key:
        st.error("Introduza a Google API Key.")
    else:
        with st.spinner(f"A utilizar o motor {modelo_selecionado} para análise jurídica..."):
            model = genai.GenerativeModel(modelo_selecionado)
            prompt = f"""
            Age como Fiscal do Território e Jurista Sénior. Elabora um Relatório de Fiscalização e Proposta de Auto de Notícia.
            PORTUGUÊS FORMAL COM ACENTOS. TEXTO JUSTIFICADO. SEM ASTERISCOS.
            
            DADOS:
            - Local: {local}. Área: {area} m2. Ação: {ocupacao}.
            - Enquadramento: RAN={r_ran}, REN={t_ren}, RN2000={t_rn2000}, Áreas Protegidas={t_ap} (Zonamento: {t_zonas}).
            - Património Cultural ({r_patrimonio}): {t_patrimonio}.
            - Conteúdo do Regulamento: {conteudo_poap[:2000]}
            
            FUNDAMENTAÇÃO OBRIGATÓRIA:
            1. PATRIMÓNIO: Cita Lei n.º 107/2001 e DL 309/2009 se houver impacto em zonas de proteção.
            2. NATUREZA: Cita DL 142/2008 (RNAP) e DL 140/99 (RN2000).
            3. TERRITÓRIO: Cita DL 73/2009 (RAN) e DL 166/2008 (REN).
            4. AUTO: Define coimas mín/máx para gravidade {gravidade} baseadas na Lei 50/2006.
            """
            
            try:
                res = model.generate_content(prompt).text
                docx = gerar_docx_final(res)
                st.success("Documentação preparada com sucesso!")
                st.download_button("📥 Descarregar Word (.docx)", docx, file_name=f"Fiscalizacao_{local}.docx")
            except Exception as e:
                st.error(f"Erro: {e}")
