import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
import re
from pypdf import PdfReader

# 1. Configuração de Interface
st.set_page_config(page_title="Fiscalização Pro: Sistema Integral", layout="wide", page_icon="🛡️")

st.markdown("""
    <style>
    .stCheckbox { margin-bottom: -15px; }
    .stTabs [data-baseweb="tab"] { font-weight: bold; }
    .stTextArea textarea { background-color: #ffffff; }
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
        st.sidebar.error("Erro na API Key.")

# --- BASE DE DADOS DE FISCALIZAÇÃO ---

tipologias_ren = ["Áreas de Proteção de Encostas", "Áreas de Infiltração Máxima", "Zonas Adjacentes", "Cursos de Água", "Cabeceiras de linhas de água", "Albufeiras", "Zonas Ameaçadas pelas Cheias", "Zonas Ameaçadas pelo Mar", "Arribas", "Dunas Litorais", "Praias", "Estuários e Áreas Húmidas"]

zec_zpe_centro = ["ZEC Serra de Aire e Candeeiros", "ZEC Serra da Estrela", "ZEC Sicó/Alvaiázere", "ZEC Paul de Arzila", "ZEC Serra da Lousã", "ZEC Malcata", "ZEC Rio Zêzere", "ZEC Albufeira de Castelo do Bode", "ZEC Rio Paiva", "ZEC Douro Internacional", "ZPE Paul do Boquilobo", "ZPE Estuário do Mondego", "ZPE Douro Internacional", "ZPE Ria de Aveiro", "ZPE Beira Interior"]

areas_protegidas = ["P.N. Douro Internacional (PNDI)", "P.N. Serra da Estrela (PNSE)", "P.N. Serras de Aire e Candeeiros (PNSAC)", "P.N. Tejo Internacional", "R.N. Paul do Boquilobo", "R.N. Paul de Arzila", "R.N. Serra da Malcata", "R.N. Berlengas", "M.N. Pegadas de Dinossáurios"]

zonamentos_poap = ["Reserva Integral", "Reserva Parcial", "Proteção Parcial Tipo I", "Proteção Parcial Tipo II", "Proteção Complementar I", "Proteção Complementar II", "Área de Intervenção Específica"]

art9_natura = ["a) Obras construção civil (limites área/ampliação)", "b) Alteração uso solo > 5 ha", "c) Modificações coberto vegetal > 5 ha", "d) Alterações morfologia solo (extra agrícolas)", "e) Alteração zonas húmidas/marinhas", "f) Deposição sucatas/resíduos", "g) Novas vias/alargamento", "h) Infraestruturas (energia/telecom)", "i) Atividades motorizadas/competições", "j) Alpinismo/Escalada", "l) Reintrodução espécies fauna/flora"]

# --- INTERFACE ---
st.title("🛡️ Sistema Integral de Fiscalização Territorial e Ambiental")

tab1, tab2, tab3, tab4 = st.tabs(["📍 Ocorrência", "🌿 Natureza e Conservação", "🌾 Solo e Património", "📑 Gerar Documentação"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📍 Localização")
        local = st.text_input("Local/Concelho", "Médio Tejo / Região Centro")
        area_m2 = st.number_input("Área Afetada (m²)", value=15591.67)
        desc_visual = st.text_area("Descrição visual das ações detetadas", "Deteção de aterro e movimentação de terras...")
    with c2:
        st.subheader("👤 Infrator")
        infrator = st.text_input("Nome/Entidade", "Em averiguação")
        tipo_entidade = st.radio("Tipo", ["Pessoa Singular", "Pessoa Coletiva"])
        nif_infrator = st.text_input("NIF/NIPC", "000000000")

with tab2:
    st.info("Regime Jurídico da Conservação da Natureza e Rede Natura 2000")
    col_nat1, col_nat2 = st.columns(2)
    with col_nat1:
        st.success("**Rede Natura 2000 (ZEC/ZPE)**")
        sel_zec = st.multiselect("Sítios Selecionados:", zec_zpe_centro)
        st.write("**Condicionantes Artigo 9.º (DL 140/99):**")
        sel_art9 = [i for i in art9_natura if st.checkbox(i)]
        outros_natura = st.text_area("Outras Interdições/Condicionantes Natura 2000:")
    with col_nat2:
        st.success("**Áreas Protegidas (RNAP)**")
        sel_ap = st.multiselect("Parques e Reservas:", areas_protegidas)
        sel_zonamento = st.multiselect("Zonamento (POAP):", zonamentos_poap)
        outros_ap = st.text_area("Outras Interdições Áreas Protegidas (DL 142/2008):")

with tab3:
    col_solo1, col_solo2 = st.columns(2)
    with col_solo1:
        st.info("**🌾 RAN & REN**")
        sel_ren_tipo = st.multiselect("Tipologias REN:", tipologias_ren)
        int_ren_ran = st.text_area("Interdições/Condicionantes detetadas (RAN/REN):", placeholder="Ex: Construção em zona de cheia; Impermeabilização de solo RAN...")
    with col_solo2:
        st.warning("**🏛️ Património, Águas e Resíduos**")
        r_pat = st.checkbox("Património Cultural (Lei 107/2001)")
        t_pat = st.text_area("Descrição infração Património:") if r_pat else ""
        r_agua = st.checkbox("Domínio Hídrico / Resíduos")
        t_agua = st.text_area("Descrição infração Água/Resíduos:") if r_agua else ""
    
    st.subheader("📝 Outras Infrações não Tipificadas")
    outros_geral = st.text_area("Indique quaisquer outras normas violadas (Ex: PDM):")
    st.divider()
    gravidade = st.select_slider("Gravidade Proposta", options=["Leve", "Grave", "Muito Grave"])

with tab4:
    arquivo_pdf = st.file_uploader("Upload de Regulamento/POAP", type=['pdf'])
    pdf_text = ""
    if arquivo_pdf:
        reader = PdfReader(arquivo_pdf)
        pdf_text = "\n".join([p.extract_text() for p in reader.pages[:10]])
    
    if st.button("🚀 Gerar Documentação Final"):
        if not api_key: st.error("Insira a API Key.")
        else:
            with st.spinner("A fundir toda a base de dados jurídica..."):
                model = genai.GenerativeModel(modelo_selecionado)
                prompt = f"""
                Age como Fiscal Sénior e Jurista. Redigi Relatório e Auto de Notícia.
                DADOS: Local {local}, Área {area_m2}m2, Infrator {infrator} ({tipo_entidade}, NIF: {nif_infrator}).
                
                ENQUADRAMENTO:
                - Rede Natura: {sel_zec}. Artigo 9º DL 140/99: {sel_art9}. Outros: {outros_natura}
                - Áreas Protegidas: {sel_ap}. Zonamento: {sel_zonamento}. Outros: {outros_ap}
                - REN: {sel_ren_tipo}. RAN/REN Detalhes: {int_ren_ran}
                - Património: {t_pat}. Águas/Resíduos: {t_agua}
                - Outros: {outros_geral}
                - Regulamento PDF: {pdf_text[:1500]}

                INSTRUÇÕES:
                1. No RELATÓRIO: Cita DL 140/99, DL 142/2008, DL 166/2008, DL 73/2009 e Lei 107/2001.
                2. No AUTO: Tipifica infrações e define coimas para gravidade {gravidade} e entidade {tipo_entidade} (Lei 50/2006).
                3. Texto JUSTIFICADO, BOLD nos capítulos, sem asteriscos.
                """
                try:
                    res = model.generate_content(prompt).text
                    # Função de exportação docx aqui...
                    st.success("Gerado!")
                    st.download_button("📥 Descarregar Word", BytesIO(), file_name="Fiscalizacao.docx") # Simplificado para exemplo
                    st.write(res)
                except Exception as e: st.error(f"Erro: {e}")



