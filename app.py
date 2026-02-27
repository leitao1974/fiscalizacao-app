import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
import re
from pypdf import PdfReader

# 1. Configuração de Interface
st.set_page_config(page_title="Fiscalização Pro: Matriz Jurídica Total", layout="wide", page_icon="🛡️")

st.markdown("""
    <style>
    .stCheckbox { margin-bottom: -15px; font-size: 13px; }
    .stTabs [data-baseweb="tab"] { font-weight: bold; }
    .stTextArea textarea { background-color: #f9f9f9; }
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

# --- BASE DE DATA TÉCNICA ---
tipologias_ren = ["Áreas de Proteção de Encostas", "Áreas de Infiltração Máxima", "Zonas Adjacentes", "Cursos de Água", "Cabeceiras de linhas de água", "Albufeiras", "Zonas Ameaçadas pelas Cheias", "Arribas", "Dunas", "Praias", "Estuários"]

# Infrações REN (DL 166/2008)
inf_ren = [
    "🚫 (Int.) Loteamentos e obras de urbanização",
    "🚫 (Int.) Obras de edificação (construção nova)",
    "🚫 (Int.) Impermeabilização de solos e revestimentos asfálticos",
    "🚫 (Int.) Escavações e aterros (alteração do perfil natural)",
    "🚫 (Int.) Destruição do coberto vegetal e abate de árvores",
    "🚫 (Int.) Alteração da rede de drenagem natural",
    "⚠️ (Cond.) Obras de reconstrução/ampliação sem parecer CCDR",
    "⚠️ (Cond.) Vias de comunicação/infraestruturas sem Título de Interesse Público"
]

# Infrações RAN (DL 73/2009)
inf_ran = [
    "🚫 (Int.) Utilização de terras para fins não agrícolas",
    "🚫 (Int.) Ações que destruam ou degradem o potencial agrícola",
    "🚫 (Int.) Impermeabilização definitiva de solos de classe A ou B",
    "⚠️ (Cond.) Construção de habitação própria de agricultor sem parecer DRAP",
    "⚠️ (Cond.) Instalação de unidades agroindustriais sem parecer vinculado"
]

# Património Cultural (Lei 107/2001)
inf_patrimonio = [
    "🚫 (Int.) Destruição ou alteração de imóvel classificado",
    "🚫 (Int.) Execução de obras sem acompanhamento arqueológico obrigatório",
    "⚠️ (Cond.) Obras em Zona Geral de Proteção (50m) sem parecer da tutela",
    "⚠️ (Cond.) Intervenções em imóveis em vias de classificação sem autorização"
]

art9_natura = [
    "a) Obras construção civil (limites área/ampliação)",
    "b) Alteração uso solo > 5 ha",
    "c) Modificações coberto vegetal > 5 ha",
    "d) Alterações morfologia solo (extra agrícolas)",
    "e) Alteração zonas húmidas/marinhas",
    "f) Deposição sucatas/resíduos",
    "g) Novas vias/alargamento",
    "h) Infraestruturas (energia/telecom)",
    "i) Atividades motorizadas/competições",
    "l) Reintrodução espécies fauna/flora"
]

# --- INTERFACE ---
st.title("🛡️ Sistema Integral de Fiscalização: Matriz de Contraordenações")

tab1, tab2, tab3, tab4 = st.tabs(["📍 Local & Infrator", "🌿 Conservação & Natura", "🌾 REN, RAN & Património", "📑 Documentação"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        local = st.text_input("Localização/Concelho", "Região Centro")
        area_m2 = st.number_input("Área Afetada (m²)", value=1000.0)
        desc_visual = st.text_area("Descrição visual das ações", "Deteção de intervenção ilícita...")
    with c2:
        infrator = st.text_input("Nome do Infrator", "Em averiguação")
        tipo_entidade = st.radio("Entidade", ["Pessoa Singular", "Pessoa Coletiva"])
        nif = st.text_input("NIF/NIPC", "000000000")

with tab2:
    st.info("**Rede Natura 2000 & Biodiversidade**")
    col_n1, col_n2 = st.columns(2)
    with col_n1:
        st.write("**Condicionantes Art. 9.º (DL 140/99):**")
        sel_art9 = [i for i in art9_natura if st.checkbox(i)]
    with col_n2:
        st.write("**Áreas Protegidas & Zonamento (DL 142/2008):**")
        sel_zonamento = st.multiselect("Zonamento POAP:", ["Reserva Integral", "Reserva Parcial", "Proteção Parcial I", "Proteção Parcial II", "Proteção Complementar"])
        st.write("---")
        upload_poap = st.file_uploader("📂 Carregar Plano de Ordenamento (POAP) - PDF", type=['pdf'], key="poap_upload")

with tab3:
    st.info("**Regimes Territoriais e Patrimoniais**")
    col_r1, col_r2, col_r3 = st.columns(3)
    
    with col_r1:
        st.subheader("💧 REN (DL 166/2008)")
        sel_ren_tipos = st.multiselect("Tipologias afetadas:", tipologias_ren)
        sel_ren_inf = [i for i in inf_ren if st.checkbox(i)]
        
    with col_r2:
        st.subheader("🌾 RAN (DL 73/2009)")
        sel_ran_inf = [i for i in inf_ran if st.checkbox(i)]

    with col_r3:
        st.subheader("🏛️ Património (Lei 107/2001)")
        sel_pat_inf = [i for i in inf_patrimonio if st.checkbox(i)]

    st.divider()
    outros_txt = st.text_area("📝 Outras infrações ou detalhes (Ex: PDM, RGEU, Águas):")
    gravidade = st.select_slider("Gravidade Proposta:", options=["Leve", "Grave", "Muito Grave"])

# --- PROCESSAMENTO DOCX ---
def gerar_docx(texto_final):
    doc = Document()
    for s in doc.sections:
        s.top_margin, s.bottom_margin = Cm(2.5), Cm(2.5)
        s.left_margin, s.right_margin = Cm(3.0), Cm(2.5)
    
    for linha in texto_final.replace('*', '').replace('#', '').split('\n'):
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

with tab4:
    if st.button("🚀 Gerar Relatório e Auto de Notícia"):
        if not api_key:
            st.error("Insira a API Key.")
        else:
            with st.spinner("A fundir matrizes de interdição com enquadramento legal..."):
                poap_text = ""
                if upload_poap:
                    reader = PdfReader(upload_poap)
                    poap_text = "\n".join([p.extract_text() for p in reader.pages[:5]])
                
                model = genai.GenerativeModel(modelo_selecionado)
                prompt = f"""
                Age como Fiscal Sénior e Jurista. Redigi Relatório e Auto de Notícia.
                DADOS: Local {local}, Área {area_m2}m2, Infrator {infrator} ({tipo_entidade}, NIF {nif}).
                
                INFRAÇÕES SELECIONADAS:
                - Natura 2000 (Art. 9º DL 140/99): {sel_art9}
                - Áreas Protegidas (Zonamento): {sel_zonamento}
                - REN (Tipologias e Infrações): {sel_ren_tipos} | {sel_ren_inf}
                - RAN: {sel_ran_inf}
                - Património: {sel_pat_inf}
                - Outros/Detalhes: {outros_txt}
                - Texto Extraído do POAP: {poap_text[:1000]}

                FUNDAMENTAÇÃO:
                1. No RELATÓRIO: Cruza as infrações. Explica porque é que a ação viola as interdições/condicionantes selecionadas.
                2. No AUTO: Tipifica contraordenações e define coimas para gravidade {gravidade} e entidade {tipo_entidade} (Lei 50/2006).
                3. Estilo: Formal, Português de Portugal, capítulos a BOLD.
                """
                try:
                    resultado = model.generate_content(prompt).text
                    ficheiro = gerar_docx(resultado)
                    st.success("Documentação gerada com sucesso!")
                    st.download_button("📥 Descarregar Word (.docx)", ficheiro, file_name=f"Auto_{local}.docx")
                    st.write(resultado)
                except Exception as e:
                    st.error(f"Erro: {e}")



