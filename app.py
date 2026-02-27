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
st.set_page_config(page_title="Fiscalização Pro: Gestão de Ocorrências", layout="wide", page_icon="🛡️")

# Estilo CSS para interface limpa e profissional
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

# --- LISTAS DE APOIO ---
tipologias_patrimonio = ["Monumento Nacional (ZGP/ZEP)", "Imóvel de Interesse Público", "Sítio Arqueológico", "Conjunto Classificado", "Zona Geral de Proteção (50m)"]
tipologias_ren = ["Áreas de Proteção de Encostas", "Áreas de Infiltração Máxima", "Zonas Adjacentes", "Cursos de Água", "Cabeceiras de linhas de água", "Zonas Ameaçadas pelas Cheias", "Arribas"]
zec_zpe_centro = ["ZEC Serra de Aire e Candeeiros", "ZEC Serra da Estrela", "ZEC Sicó/Alvaiázere", "ZEC Paul de Arzila", "ZEC Serra da Lousã", "ZEC Rio Zêzere", "ZEC Albufeira de Castelo do Bode", "ZPE Paul do Boquilobo", "ZPE Estuário do Mondego"]
areas_protegidas_centro = ["P.N. Douro Internacional", "P.N. Serra da Estrela", "P.N. Serras de Aire e Candeeiros", "R.N. Paul do Boquilobo", "R.N. Paul de Arzila", "R.N. Serra da Malcata"]
zonamentos_poap = ["Reserva Integral", "Reserva Parcial", "Proteção Parcial Tipo I", "Proteção Parcial Tipo II", "Proteção Complementar", "Intervenção Específica"]

# --- INTERFACE PRINCIPAL ---
st.title("🛡️ Sistema de Apoio à Fiscalização e Auto de Notícia")

tab1, tab2, tab3 = st.tabs(["📍 Ocorrência e Infrator", "⚖️ Enquadramento Legal", "📑 Documentação Base"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Dados do Local")
        local = st.text_input("Localização / Concelho", "Alenquer / Tomar / Manteigas")
        area = st.number_input("Área Afetada (m²)", value=15591.67, format="%.2f")
        ocupacao = st.text_area("Descrição da Ação Detetada", "Execução de aterro com alteração da morfologia do solo e potencial impacto ambiental.")
    
    with col2:
        st.subheader("Dados do Infrator")
        infrator_nome = st.text_input("Nome / Designação Social", "Em averiguação")
        infrator_morada = st.text_input("Morada / Sede", "Desconhecida")
        nif_nipc = st.text_input("NIF / NIPC", "000000000")
        testemunhas = st.text_area("Testemunhas / Auxiliares (se aplicável)", "N/A")

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
        t_rn2000 = st.multiselect("ZEC/ZPE:", zec_zpe_centro) if r_rn2000 else []

    with c3:
        st.subheader("🏛️ Património / Outros")
        r_patrimonio = st.checkbox("Património Cultural")
        t_patrimonio = st.multiselect("Tipologia:", tipologias_patrimonio) if r_patrimonio else []
        r_agua = st.checkbox("Domínio Hídrico")
        st.divider()
        gravidade = st.select_slider("Gravidade Proposta", options=["Leve", "Grave", "Muito Grave"])

conteudo_poap = ""
with tab3:
    st.write("Carregue o regulamento (PDF) para fundamentação automática.")
    arquivo = st.file_uploader("Upload Regulamento/Plano", type=['pdf'])
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
        
        if re.match(r'^(\d+\.|RELATÓRIO|PROPOSTA|AUTO|FUNDAMENTAÇÃO|CONCLUSÃO|DADOS DO INFRATOR)', linha.upper()):
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
if st.button("🚀 Gerar Documentação Completa (Word)"):
    if not api_key:
        st.error("Introduza a Google API Key.")
    else:
        with st.spinner(f"A redigir relatório e auto com motor {modelo_selecionado}..."):
            model = genai.GenerativeModel(modelo_selecionado)
            prompt = f"""
            Age como Fiscal do Território e Jurista Sénior. Elabora um Relatório de Fiscalização e Proposta de Auto de Notícia.
            PORTUGUÊS FORMAL COM ACENTOS. TEXTO JUSTIFICADO. SEM ASTERISCOS.
            
            DADOS DA OCORRÊNCIA:
            - Local: {local}. Área: {area} m2. Ação: {ocupacao}.
            - INFRATOR: {infrator_nome}, Morada: {infrator_morada}, NIF: {nif_nipc}. Testemunhas: {testemunhas}.
            - Regimes: RAN={r_ran}, REN={t_ren}, RN2000={t_rn2000}, Áreas Protegidas={t_ap} (Zonamento: {t_zonas}), Património={t_patrimonio}.
            - Conteúdo do Regulamento/PDF: {conteudo_poap[:2000]}
            
            ESTRUTURA:
            1. RELATÓRIO DE FISCALIZAÇÃO: Descreve os factos, o local e a fundamentação técnica das violações.
            2. PROPOSTA DE AUTO DE NOTÍCIA: Inclui os dados do infrator. Tipifica a contraordenação conforme a Lei 50/2006. 
            Indica as coimas mín/máx para gravidade {gravidade} (Singulares e Coletivas).
            Propõe embargo e reposição da legalidade.
            """
            try:
                res = model.generate_content(prompt).text
                docx = gerar_docx_final(res)
                st.success("Documentação pronta para descarga!")
                st.download_button("📥 Descarregar Word (.docx)", docx, file_name=f"Fiscalizacao_{local}.docx")
                with st.expander("Pré-visualização do Parecer"):
                    st.write(res.replace('*', ''))
            except Exception as e:
                st.error(f"Erro na IA: {e}")
