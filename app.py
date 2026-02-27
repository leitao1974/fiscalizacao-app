import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
import re
from pypdf import PdfReader

# 1. Configuração de Interface
st.set_page_config(page_title="Sistema Integrado de Fiscalização Território/Ambiente", layout="wide", page_icon="🛡️")

# Estilo para interface profissional e compacta
st.markdown("""
    <style>
    .stCheckbox { margin-bottom: -15px; }
    .stTabs [data-baseweb="tab"] { font-weight: bold; }
    .stTabs [aria-selected="true"] { border-bottom: 2px solid #2e7d32; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR: CHAVE DINÂMICA ---
st.sidebar.header("⚙️ Configuração")
api_key = st.sidebar.text_input("Google API Key", type="password")
modelo_selecionado = "gemini-1.5-pro"

if api_key:
    genai.configure(api_key=api_key)
    try:
        modelos = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        modelo_selecionado = st.sidebar.selectbox("Motor de IA", modelos, index=0)
    except:
        st.sidebar.error("Verifica a API Key.")

# --- MATRIZES DE INFRAÇÕES (INTEGRAÇÃO TOTAL) ---

# A. Rede Natura 2000 (DL 140/99 - Artigo 9.º Completo)
inf_natura_art9 = [
    "a) Obras de construção civil (fora perímetros urbanos / limites ampliação)",
    "b) Alteração do uso atual do solo > 5 ha",
    "c) Modificações de coberto vegetal (agrícola/florestal) > 5 ha",
    "d) Alterações à morfologia do solo (extra agrícolas/florestais)",
    "e) Alteração de zonas húmidas ou marinhas (configuração/topografia)",
    "f) Deposição de sucatas e de resíduos sólidos e líquidos",
    "g) Abertura de novas vias de comunicação ou alargamento",
    "h) Instalação de infraestruturas (energia, telecom, saneamento)",
    "i) Atividades motorizadas organizadas / competições",
    "j) Prática de alpinismo, escalada e montanhismo",
    "l) Reintrodução de espécies indígenas fauna/flora"
]

# B. REN (DL 166/2008)
inf_ren = [
    "Interdição: Obras de urbanização / Edificação",
    "Interdição: Impermeabilização de solos",
    "Interdição: Destruição do coberto vegetal",
    "Interdição: Alteração da rede de drenagem natural",
    "Condicionada: Reconstrução/Ampliação sem parecer CCDR"
]

# C. RAN (DL 73/2009)
inf_ran = [
    "Interdição: Utilização de solo para fins não agrícolas",
    "Interdição: Ações que destruam o potencial agrícola",
    "Condicionada: Obras de utilidade pública sem despacho reconhecimento"
]

# D. Património Cultural (Lei 107/2001)
inf_patrimonio = [
    "Obras em Zona Geral de Proteção (50m) sem parecer DGPC/Cultura",
    "Danos ou alteração em imóvel classificado / vias de classificação",
    "Remoção de terras em Sítio Arqueológico inventariado"
]

# E. Recursos Hídricos e Resíduos (Lei 58/2005 e DL 102-D/2020)
inf_agua_residuos = [
    "Ocupação de Domínio Hídrico (Leito ou Margem) sem título",
    "Abandono / Deposição incontrolada de RCD (Resíduos Construção)",
    "Captação de águas (furo/poço) sem título de utilização",
    "Rejeição de efluentes sem tratamento"
]

# --- INTERFACE ---
st.title("🛡️ Sistema de Fiscalização: Relatório e Auto Integrado")

tab1, tab2, tab3 = st.tabs(["📍 Ocorrência", "⚖️ Tipificação Jurídica", "📑 Geração de Documentos"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📍 Localização")
        local = st.text_input("Local/Concelho", "Médio Tejo / Região Centro")
        area = st.number_input("Área Afetada (m²)", value=15591.67)
        desc = st.text_area("Descrição visual da ação", "Deteção de aterro e remoção de vegetação...")
    with c2:
        st.subheader("👤 Identificação")
        infrator = st.text_input("Infrator (Nome/NIF)", "Em averiguação")
        tipo_infrator = st.radio("Tipo de Entidade", ["Pessoa Singular", "Pessoa Coletiva"])

with tab2:
    st.info("Assinale as infrações detetadas nos vários regimes:")
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.success("**🌿 Rede Natura 2000 (Art. 9.º - DL 140/99)**")
        sel_natura = [i for i in inf_natura_art9 if st.checkbox(i)]
        
        st.warning("**🏛️ Património Cultural (Lei 107/2001)**")
        sel_patrimonio = [i for i in inf_patrimonio if st.checkbox(i)]

    with col_b:
        st.info("**🌾 Solo e Ordenamento (RAN / REN)**")
        sel_ren = [i for i in inf_ren if st.checkbox(i)]
        sel_ran = [i for i in inf_ran if st.checkbox(i)]
        
        st.error("**🗑️ Águas e Resíduos**")
        sel_agua = [i for i in inf_agua_residuos if st.checkbox(i)]

    st.divider()
    gravidade = st.select_slider("Gravidade Proposta", options=["Leve", "Grave", "Muito Grave"])

with tab3:
    arquivo_pdf = st.file_uploader("Upload de Regulamento/POAP", type=['pdf'])
    pdf_text = ""
    if arquivo_pdf:
        reader = PdfReader(arquivo_pdf)
        pdf_text = "\n".join([p.extract_text() for p in reader.pages[:10]])
        st.success("Análise documental pronta.")

# --- MOTOR DOCX ---
def export_docx(res_text):
    doc = Document()
    for s in doc.sections:
        s.top_margin, s.bottom_margin = Cm(2.5), Cm(2.5)
        s.left_margin, s.right_margin = Cm(3.0), Cm(2.5)
    
    for linha in res_text.replace('*', '').replace('#', '').split('\n'):
        linha = linha.strip()
        if not linha: continue
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        if re.match(r'^(\d+\.|RELATÓRIO|PROPOSTA|AUTO|INFRAÇÃO|DADOS|FUNDAMENTAÇÃO|CONCLUSÃO)', linha.upper()):
            p.add_run(linha).bold = True
        else:
            p.add_run(linha)
    
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# --- GERAÇÃO ---
st.divider()
if st.button("🚀 Gerar Documentação de Fiscalização Integral"):
    if not api_key:
        st.error("Insira a API Key.")
    else:
        with st.spinner("A cruzar todos os regimes jurídicos selecionados..."):
            model = genai.GenerativeModel(modelo_selecionado)
            prompt = f"""
            Age como Fiscal Sénior e Jurista. Redigi Relatório e Proposta de Auto de Notícia em Português Formal (PT-PT).
            
            DADOS: Local {local}, Área {area}m2, Infrator {infrator} ({tipo_infrator}).
            
            INFRAÇÕES SELECIONADAS:
            - Natura 2000 (Art. 9.º DL 140/99): {sel_natura}
            - REN: {sel_ren}
            - RAN: {sel_ran}
            - Património: {sel_patrimonio}
            - Águas/Resíduos: {sel_agua}
            
            INSTRUÇÕES JURÍDICAS:
            1. No RELATÓRIO: Fundamenta a violação de cada regime selecionado. Para a Rede Natura, cita obrigatoriamente o Artigo 9.º do DL 140/99 e analisa a falta de parecer/AIncA do ICNF.
            2. No AUTO: Tipifica as contraordenações. Calcula coimas mín/máx para gravidade {gravidade} e entidade {tipo_infrator} de acordo com a Lei 50/2006 (Ambiental) e regimes específicos.
            3. Estilo: Texto justificado, capítulos a BOLD, sem asteriscos.
            """
            try:
                res = model.generate_content(prompt).text
                docx = export_docx(res)
                st.success("Documentação preparada!")
                st.download_button("📥 Descarregar Word (.docx)", docx, file_name=f"Fiscalizacao_{local}.docx")
                st.write(res)
            except Exception as e:
                st.error(f"Erro: {e}")

