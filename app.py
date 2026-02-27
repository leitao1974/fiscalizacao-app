import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
import re
from pypdf import PdfReader

# 1. Configuração de Interface
st.set_page_config(page_title="Fiscalização Pro: Região Centro e Médio Tejo", layout="wide", page_icon="🛡️")

st.markdown("""
    <style>
    .stCheckbox { margin-bottom: -15px; font-size: 13px; }
    .stTabs [data-baseweb="tab"] { font-weight: bold; }
    .stTextArea textarea { background-color: #f9f9f9; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR: CONFIGURAÇÃO ---
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

# --- BASE DE DADOS GEOGRÁFICA E JURÍDICA ---

# ZEC e ZPE Expandidas (Região Centro e Médio Tejo)
zec_zpe_centro_completa = [
    "ZEC Serra de Aire e Candeeiros", "ZEC Serra da Estrela", "ZEC Sicó/Alvaiázere", 
    "ZEC Paul de Arzila", "ZEC Serra da Lousã", "ZEC Malcata", "ZEC Rio Zêzere (Médio Tejo)",
    "ZEC Albufeira de Castelo do Bode (Médio Tejo)", "ZEC Rio Paiva", "ZEC Douro Internacional",
    "ZEC São Mamede", "ZEC Ribeira de Nisa / Nisa", "ZEC Rio Vouga", "ZEC Dunas de Mira, Gândara e Gafanhas",
    "ZPE Paul do Boquilobo (Médio Tejo)", "ZPE Estuário do Mondego", "ZPE Ria de Aveiro", 
    "ZPE Paul de Taipal", "ZPE Douro Internacional", "ZPE Beira Interior", "ZPE Serra da Estrela",
    "ZPE Serra de Aire e Candeeiros"
]

areas_protegidas = [
    "Parque Natural do Douro Internacional (PNDI)", "Parque Natural da Serra da Estrela (PNSE)",
    "Parque Natural das Serras de Aire e Candeeiros (PNSAC)", "Parque Natural do Tejo Internacional",
    "Reserva Natural do Paul do Boquilobo", "Reserva Natural do Paul de Arzila",
    "Reserva Natural da Serra da Malcata", "Reserva Natural das Berlengas",
    "Monumento Natural das Pegadas de Dinossáurios de Ourém/Torres Novas"
]

tipologias_ren = ["Áreas de Proteção de Encostas", "Áreas de Infiltração Máxima", "Zonas Adjacentes", "Cursos de Água", "Cabeceiras de linhas de água", "Albufeiras", "Zonas Ameaçadas pelas Cheias", "Arribas"]

# Infrações por Regime
inf_ren = ["🚫 (Int.) Obras de edificação / Urbanização", "🚫 (Int.) Impermeabilização de solos", "🚫 (Int.) Destruição do coberto vegetal", "🚫 (Int.) Alteração da rede de drenagem natural", "⚠️ (Cond.) Obras sem parecer CCDR"]
inf_ran = ["🚫 (Int.) Utilização não agrícola", "🚫 (Int.) Ações que destruam potencial agrícola", "⚠️ (Cond.) Construção agricultor sem parecer DRAP"]
inf_patrimonio = ["🚫 (Int.) Danos em imóvel classificado", "⚠️ (Cond.) Obras em ZGP (50m) sem parecer DGPC"]

art9_natura = [
    "a) Obras construção civil (fora perímetros urbanos)", "b) Alteração uso solo > 5 ha", "c) Modificações coberto vegetal > 5 ha",
    "d) Alterações morfologia solo (extra agrícolas)", "e) Alteração zonas húmidas/marinhas", "f) Deposição sucatas/resíduos",
    "g) Novas vias/alargamento", "h) Infraestruturas (energia/telecom)", "i) Atividades motorizadas/competições", "l) Reintrodução espécies"
]

# --- INTERFACE ---
st.title("🛡️ Sistema Integral de Fiscalização Territorial")

tab1, tab2, tab3, tab4 = st.tabs(["📍 Local & Infrator", "🌿 Conservação & Natura", "🌾 Solo & Património", "📑 Documentação"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        local = st.text_input("Localização/Concelho", "Médio Tejo / Região Centro")
        area_m2 = st.number_input("Área Afetada (m²)", value=15591.67)
        desc_visual = st.text_area("Descrição visual das ações", "Deteção de aterro e movimentação de terras...")
    with c2:
        infrator = st.text_input("Nome do Infrator", "Em averiguação")
        tipo_entidade = st.radio("Entidade", ["Pessoa Singular", "Pessoa Coletiva"])
        nif = st.text_input("NIF/NIPC", "000000000")

with tab2:
    st.info("**Rede Natura 2000 & Biodiversidade (DL 140/99 e DL 142/2008)**")
    col_n1, col_n2 = st.columns(2)
    with col_n1:
        st.subheader("Rede Natura 2000")
        sel_zec = st.multiselect("Sítios ZEC/ZPE (Listagem Completa):", zec_zpe_centro_completa)
        st.write("**Condicionantes Art. 9.º (DL 140/99):**")
        sel_art9 = [i for i in art9_natura if st.checkbox(i)]
    with col_n2:
        st.subheader("Áreas Protegidas")
        sel_ap = st.multiselect("Parques e Reservas (RNAP):", areas_protegidas)
        sel_zonamento = st.multiselect("Zonamento POAP:", ["Reserva Integral", "Reserva Parcial", "Proteção Parcial I", "Proteção Parcial II", "Proteção Complementar"])
        st.write("---")
        upload_poap = st.file_uploader("📂 Carregar Regulamento/POAP (PDF)", type=['pdf'])

with tab3:
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
    outros_txt = st.text_area("📝 Outras infrações (Ex: PDM, Águas, Resíduos):")
    gravidade = st.select_slider("Gravidade Proposta:", options=["Leve", "Grave", "Muito Grave"])

# --- MOTOR DOCX ---
def gerar_docx(texto_final):
    doc = Document()
    for s in doc.sections: s.top_margin, s.left_margin = Cm(2.5), Cm(3.0)
    for linha in texto_final.replace('*', '').replace('#', '').split('\n'):
        if not linha.strip(): continue
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        if re.match(r'^(\d+\.|RELATÓRIO|PROPOSTA|AUTO|INFRAÇÃO|DADOS|FUNDAMENTAÇÃO|CONCLUSÃO)', linha.upper()):
            p.add_run(linha).bold = True
        else: p.add_run(linha)
    buf = BytesIO(); doc.save(buf); buf.seek(0)
    return buf

with tab4:
    if st.button("🚀 Gerar Documentação Final"):
        if not api_key: st.error("Insira a API Key.")
        else:
            with st.spinner("A fundir matrizes jurídicas..."):
                poap_txt = ""
                if upload_poap:
                    reader = PdfReader(upload_poap)
                    poap_txt = "\n".join([p.extract_text() for p in reader.pages[:10]])
                
                model = genai.GenerativeModel(modelo_selecionado)
                prompt = f"""
                Age como Fiscal Sénior e Jurista. Redigi Relatório e Auto de Notícia profissionais.
                DADOS: Local {local}, Área {area_m2}m2, Infrator {infrator} ({tipo_entidade}, NIF {nif}).
                INFRAÇÕES: Natura 2000={sel_zec}, Art 9º DL 140/99={sel_art9}, AP={sel_ap}, Zonamento={sel_zonamento}, REN={sel_ren_tipos}|{sel_ren_inf}, RAN={sel_ran_inf}, Património={sel_pat_inf}, Outros={outros_txt}.
                FUNDAMENTAÇÃO: Analisa violações ao DL 140/99, DL 142/2008, DL 166/2008, DL 73/2009 e Lei 107/2001. No Auto, tipifica e indica coimas para gravidade {gravidade} (Lei 50/2006).
                """
                try:
                    res = model.generate_content(prompt).text
                    st.success("Documentação gerada!")
                    st.download_button("📥 Descarregar Word", gerar_docx(res), file_name=f"Auto_{local}.docx")
                    st.write(res)
                except Exception as e: st.error(f"Erro: {e}")


