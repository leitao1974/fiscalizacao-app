import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
import re
from pypdf import PdfReader

# 1. Configuração de Interface
st.set_page_config(page_title="Fiscalização Pro: Matriz Flexível", layout="wide", page_icon="🛡️")

# Estilo para interface profissional
st.markdown("""
    <style>
    .stCheckbox { margin-bottom: -15px; }
    .stTabs [data-baseweb="tab"] { font-weight: bold; }
    .stTextArea textarea { background-color: #ffffff; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR: CONFIGURAÇÃO ---
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

# --- MATRIZES DE INFRAÇÕES ---
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

# --- INTERFACE ---
st.title("🛡️ Sistema de Fiscalização: Relatório e Auto Integrado")

tab1, tab2, tab3 = st.tabs(["📍 Ocorrência", "⚖️ Tipificação Jurídica", "📑 Geração de Documentos"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📍 Localização")
        local = st.text_input("Local/Concelho", "Região Centro")
        area = st.number_input("Área Afetada (m²)", value=1000.0)
        desc = st.text_area("Descrição visual sumária", "Deteção de infrações no local...")
    with c2:
        st.subheader("👤 Identificação")
        infrator = st.text_input("Infrator (Nome/NIF)", "Em averiguação")
        tipo_infrator = st.radio("Tipo de Entidade", ["Pessoa Singular", "Pessoa Coletiva"])

with tab2:
    st.info("Assinale as infrações detetadas e adicione outras se necessário.")
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.success("**🌿 Rede Natura 2000 (Art. 9.º - DL 140/99)**")
        sel_natura = [i for i in inf_natura_art9 if st.checkbox(i)]
        outros_natura = st.text_area("Outras infrações Natura 2000 não listadas:", placeholder="Ex: Incumprimento de medidas de minimização...")
        
        st.warning("**🏛️ Património Cultural (Lei 107/2001)**")
        r_pat = st.checkbox("Violação de Património Cultural")
        t_pat = st.text_area("Descreva a infração ao Património:", placeholder="Ex: Alteração de fachada em imóvel de interesse público...") if r_pat else ""

    with col_b:
        st.info("**🌾 Solo e Ordenamento (RAN / REN)**")
        r_ran_ren = st.checkbox("Infrações RAN / REN")
        t_ran_ren = st.text_area("Descreva as infrações RAN/REN:", placeholder="Ex: Impermeabilização de solo de classe A...") if r_ran_ren else ""
        
        st.error("**🗑️ Águas e Resíduos**")
        r_agua_res = st.checkbox("Infrações Águas / Resíduos")
        t_agua_res = st.text_area("Descreva as infrações de Águas/Resíduos:", placeholder="Ex: Descarga de efluentes não tratados...") if r_agua_res else ""

    st.subheader("📝 Outras Infrações Não Tipificadas")
    outros_geral = st.text_area("Indique quaisquer outras normas ou regulamentos violados:", 
                                placeholder="Ex: Violação do Art. X do Regulamento do PDM; Falta de alvará de construção...")

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
    
    res_text = res_text.replace('*', '').replace('#', '')
    for linha in res_text.split('\n'):
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
        with st.spinner("A fundir as infrações tipificadas e os dados livres..."):
            model = genai.GenerativeModel(modelo_selecionado)
            prompt = f"""
            Age como Fiscal Sénior e Jurista Especialista em Ambiente e Território. 
            Redigi um Relatório de Fiscalização e uma Proposta de Auto de Notícia em Português Formal (PT-PT).
            
            DADOS DA OCORRÊNCIA:
            - Local: {local}. Área: {area} m2.
            - Infrator: {infrator} ({tipo_infrator}).
            - Descrição Visual: {desc}
            
            INFRAÇÕES SELECIONADAS E DESCRITAS:
            - Natura 2000 (Art. 9.º DL 140/99): {sel_natura}. Extras: {outros_natura}
            - Património Cultural: {t_pat}
            - RAN / REN: {t_ran_ren}
            - Águas e Resíduos: {t_agua_res}
            - Outros não tipificados: {outros_geral}
            
            INSTRUÇÕES JURÍDICAS:
            1. No RELATÓRIO: Fundamenta juridicamente as infrações de acordo com os diplomas aplicáveis (DL 140/99, DL 166/2008, DL 73/2009, Lei 107/2001, Lei 58/2005, DL 102-D/2020).
            2. Se houver dados em 'Outros não tipificados', incorpora-os na análise jurídica (ex: PDM ou RGEU).
            3. No AUTO: Tipifica as contraordenações e calcula coimas para gravidade {gravidade} e entidade {tipo_infrator} (Lei 50/2006).
            4. Estilo: Profissional, justificado, sem asteriscos.
            """
            try:
                res = model.generate_content(prompt).text
                docx = export_docx(res)
                st.success("Documentação preparada!")
                st.download_button("📥 Descarregar Word (.docx)", docx, file_name=f"Fiscalizacao_{local}.docx")
                st.write(res)
            except Exception as e:
                st.error(f"Erro: {e}")


