import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
import re
from pypdf import PdfReader

# 1. Configuração de Interface
st.set_page_config(page_title="Fiscalização Pro: Regime Jurídico Completo", layout="wide", page_icon="🛡️")

# Estilo para melhor leitura das listas longas
st.markdown("<style>.stCheckbox { margin-bottom: -12px; font-size: 14px; }</style>", unsafe_allow_html=True)

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

# --- MATRIZ EXAUSTIVA DE INFRAÇÕES ---

# 1. REN (Decreto-Lei n.º 166/2008)
inf_ren = {
    "Interdições": [
        "Loteamentos e obras de urbanização",
        "Obras de edificação de qualquer natureza (exceto exceções previstas)",
        "Impermeabilização de solos e revestimentos asfálticos",
        "Escavações e aterros que alterem o perfil natural do terreno",
        "Destruição do coberto vegetal e abate de árvores",
        "Alteração da rede de drenagem natural",
        "Deposição de resíduos, entulhos ou materiais de construção"
    ],
    "Ações Condicionadas (Sem Título)": [
        "Instalações de lazer e recreio sem parecer da CCDR",
        "Obras de reconstrução ou ampliação sem título de exceção",
        "Vias de comunicação e infraestruturas sem reconhecimento de interesse público",
        "Limpeza de cursos de água com recurso a maquinaria pesada sem autorização"
    ]
}

# 2. Rede Natura 2000 (Decreto-Lei n.º 140/99)
inf_natura = {
    "Interdições": [
        "Alteração do uso atual do solo (pastagens para florestação/agrícola)",
        "Deterioração de habitats naturais (Anexo B-I)",
        "Perturbação significativa de espécies (Anexo B-II/B-IV)",
        "Drenagem de zonas húmidas e alteração de linhas de água",
        "Introdução de espécies não indígenas (invasoras)",
        "Extração de inertes (areia/cascalho) fora das zonas previstas"
    ],
    "Ações Condicionadas (Sem Título)": [
        "Realização de projetos/ações sem Avaliação de Incidências Ambientais (AIncA)",
        "Turismo de natureza ou eventos desportivos sem parecer do ICNF",
        "Alteração da morfologia do solo ou do coberto vegetal sem título",
        "Construções de apoio agrícola/florestal sem parecer Natura 2000"
    ]
}

# 3. RAN (Decreto-Lei n.º 73/2009)
inf_ran = {
    "Interdições": [
        "Utilização de terras para fins não agrícolas",
        "Ações que destruam o potencial agrícola do solo",
        "Impermeabilização definitiva de solos de classe A ou B",
        "Deposição de estéreis ou resíduos no solo"
    ],
    "Ações Condicionadas (Sem Título)": [
        "Obras de habitação própria de agricultores sem parecer da DRAP",
        "Instalação de unidades agroindustriais sem parecer vinculado",
        "Obras de utilidade pública sem despacho de reconhecimento"
    ]
}

# --- INTERFACE ---
st.title("🛡️ Sistema de Fiscalização: Regime Jurídico Integral")

tab1, tab2, tab3 = st.tabs(["📍 Dados e Infrator", "⚖️ Matriz de Infrações", "📑 Geração de Relatório"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        local = st.text_input("Localização (Freguesia/Concelho)", "Abrantes / Tomar")
        area = st.number_input("Área (m²)", value=15591.67)
    with c2:
        infrator = st.text_input("Infrator (Nome/NIF)", "Em averiguação")
        desc_campo = st.text_area("Notas de Campo", "Deteção de movimentação de terras em zona protegida.")

with tab2:
    st.info("Selecione as infrações detetadas de acordo com o regime jurídico aplicável.")
    
    col_ren, col_nat, col_ran = st.columns(3)
    
    with col_ren:
        st.subheader("💧 REN (DL 166/2008)")
        sel_ren_int = [i for i in inf_ren["Interdições"] if st.checkbox(f"🚫 {i}", key=f"int_ren_{i}")]
        sel_ren_con = [i for i in inf_ren["Ações Condicionadas (Sem Título)"] if st.checkbox(f"⚠️ {i}", key=f"con_ren_{i}")]
        
    with col_nat:
        st.subheader("🌿 Natura 2000 (DL 140/99)")
        sel_nat_int = [i for i in inf_natura["Interdições"] if st.checkbox(f"🚫 {i}", key=f"int_nat_{i}")]
        sel_nat_con = [i for i in inf_natura["Ações Condicionadas (Sem Título)"] if st.checkbox(f"⚠️ {i}", key=f"con_nat_{i}")]

    with col_ran:
        st.subheader("🌾 RAN (DL 73/2009)")
        sel_ran_int = [i for i in inf_ran["Interdições"] if st.checkbox(f"🚫 {i}", key=f"int_ran_{i}")]
        sel_ran_con = [i for i in inf_ran["Ações Condicionadas (Sem Título)"] if st.checkbox(f"⚠️ {i}", key=f"con_ran_{i}")]

    st.divider()
    gravidade = st.select_slider("Gravidade Consolidada", options=["Leve", "Grave", "Muito Grave"])

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
        if re.match(r'^(\d+\.|RELATÓRIO|AUTO|INFRAÇÃO|DADOS|FUNDAMENTAÇÃO|CONCLUSÃO)', linha.upper()):
            p.add_run(linha).bold = True
        else:
            p.add_run(linha)
    
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# --- GERAÇÃO ---
if st.button("🚀 Gerar Documentação de Fiscalização"):
    if not api_key:
        st.error("Insira a API Key.")
    else:
        with st.spinner("A cruzar os factos com as interdições e condicionantes legais..."):
            model = genai.GenerativeModel(modelo_selecionado)
            prompt = f"""
            Age como Fiscal Sénior e Jurista. Redigi Relatório e Auto de Notícia.
            Local: {local}, Área {area}m2, Infrator {infrator}.
            
            INFRAÇÕES REN (Interdições: {sel_ren_int}, Condicionantes sem Título: {sel_ren_con})
            INFRAÇÕES NATURA 2000 (Interdições: {sel_nat_int}, Condicionantes sem Título: {sel_nat_con})
            INFRAÇÕES RAN (Interdições: {sel_ran_int}, Condicionantes sem Título: {sel_ran_con})
            
            FUNDAMENTAÇÃO OBRIGATÓRIA:
            1. No RELATÓRIO: Analisa cada ponto selecionado. Para a Rede Natura 2000, cita especificamente o DL 140/99 na sua atual redação. 
               Explica que as ações condicionadas realizadas sem título constituem infração por falta de parecer/licenciamento.
            2. No AUTO: Tipifica as contraordenações. Indica as coimas para gravidade {gravidade} de acordo com a Lei 50/2006.
            3. Propõe o embargo e a reposição do solo.
            """
            try:
                res = model.generate_content(prompt).text
                docx = export_docx(res)
                st.success("Relatório gerado!")
                st.download_button("📥 Descarregar Word (.docx)", docx, file_name=f"Fiscalizacao_{local}.docx")
                st.write(res)
            except Exception as e:
                st.error(f"Erro: {e}")
