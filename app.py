import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
import re
from pypdf import PdfReader

# 1. Configuração de Interface
st.set_page_config(page_title="Sistema Integrado de Fiscalização Pro", layout="wide", page_icon="🛡️")

st.markdown("""
    <style>
    .stCheckbox { margin-bottom: -15px; font-size: 13px; }
    .stTabs [data-baseweb="tab"] { font-weight: bold; }
    .stTextArea textarea { background-color: #fcfcfc; }
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
        modelo_selecionado = st.sidebar.selectbox("Motor de IA Ativo", modelos, index=0)
    except:
        st.sidebar.error("Verifica a API Key.")

# --- MATRIZ DE DADOS RAN (ATUALIZADA DL 199/2015) ---
inf_ran_interdicoes = [
    "🚫 (Int.) Utilização de terras para fins não agrícolas (sem enquadramento)",
    "🚫 (Int.) Ações que destruam ou degradem o potencial agrícola do solo",
    "🚫 (Int.) Impermeabilização definitiva de solos de alta qualidade (Classe A/B)",
    "🚫 (Int.) Deposição de estéreis, resíduos ou materiais de construção",
    "🚫 (Int.) Intervenção em área beneficiada por Aproveitamento Hidroagrícola"
]

inf_ran_condicionantes = [
    "⚠️ (Cond.) Apoios agrícolas sem parecer da Entidade Regional da RAN",
    "⚠️ (Cond.) Habitação de agricultor sem título de parecer vinculado",
    "⚠️ (Cond.) Obras de utilidade pública sem despacho de reconhecimento (Art. 25.º)",
    "⚠️ (Cond.) Infraestruturas (energia/vias) sem verificação de inexistência de alternativa"
]

# --- BASES DE DADOS CONSOLIDADAS (SEM ALTERAÇÃO) ---
ren_tipologias = ["Faixa marítima", "Praias", "Dunas", "Arribas", "Cursos de água", "Albufeiras", "Recarga de aquíferos", "Zonas de cheia", "Riscos vertentes"]
art9_natura = [
    "a) Obras construção civil (limites área/ampliação)", "b) Alteração uso solo > 5 ha", "c) Coberto vegetal > 5 ha",
    "d) Alterações morfologia solo", "e) Alteração zonas húmidas/marinhas", "f) Deposição sucatas/resíduos",
    "g) Novas vias/alargamento", "h) Infraestruturas", "i) Atividades motorizadas", "l) Reintrodução espécies"
]
zec_zpe_centro = ["ZEC Serra de Aire e Candeeiros", "ZEC Serra da Estrela", "ZEC Rio Zêzere", "ZEC Albufeira de Castelo do Bode", "ZPE Paul do Boquilobo"]

# --- INTERFACE ---
st.title("🛡️ Sistema de Fiscalização: Master Território e Ambiente")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📍 Ocorrência & Infrator", "💧 Matriz REN", "🌿 Natura & AP", "🌾 RAN & Património", "📑 Gerar Documentação"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📍 Localização e Evidências")
        local = st.text_input("Localização/Concelho", "Região Centro")
        col_gps1, col_gps2 = st.columns(2)
        lat = col_gps1.text_input("Latitude", placeholder="39.xxxx")
        lon = col_gps2.text_input("Longitude", placeholder="-8.xxxx")
        area_m2 = st.number_input("Área Afetada (m²)", value=1000.0)
        fotos = st.file_uploader("📸 Registos Fotográficos", accept_multiple_files=True, type=['jpg', 'jpeg', 'png'])
            
    with c2:
        st.subheader("👤 Dados do Infrator")
        inf_nome = st.text_input("Nome / Designação Social")
        inf_morada = st.text_input("Morada / Sede Social")
        inf_nif = st.text_input("NIF / NIPC")
        inf_tel = st.text_input("Contacto Telefónico")
        tipo_ent = st.radio("Entidade", ["Pessoa Singular", "Pessoa Coletiva"], horizontal=True)

with tab2:
    st.info("**Tipologias REN e Checklist de Compatibilidade (Portaria 419/2012)**")
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        st.write("**Áreas Afetadas**")
        sel_ren = [i for i in ren_tipologias if st.checkbox(i)]
        st.write("**Interdições (Art. 20.º)**")
        sel_int = [i for i in ["Loteamento", "Construção/Ampliação", "Escavações/Aterros", "Destruição vegetal"] if st.checkbox(i)]
    with col_r2:
        st.write("**Limites Técnicos e Títulos**")
        c_previa_ren = st.checkbox("Falta de Comunicação Prévia à CCDR")
        lim_area_ren = st.checkbox("Excede limites de área REN")

with tab3:
    col_n1, col_n2 = st.columns(2)
    with col_n1:
        st.success("**Rede Natura 2000 (DL 140/99)**")
        sel_zec = st.multiselect("Sítios ZEC/ZPE:", zec_zpe_centro)
        st.write("**Condicionantes Art. 9.º n.º 2:**")
        sel_art9 = [i for i in art9_natura if st.checkbox(i)]
    with col_n2:
        st.success("**Áreas Protegidas**")
        sel_zon = st.multiselect("Zonamento (POAP):", ["Reserva Integral", "Reserva Parcial", "Proteção Parcial I", "Proteção Parcial II"])
        upload_poap = st.file_uploader("📂 Upload Regulamento POAP (PDF)", type=['pdf'])

with tab4:
    st.info("**🌾 Reserva Agrícola Nacional (DL 199/2015 e Portaria 162/2011)**")
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.write("**Infrações RAN Detetadas**")
        sel_ran_int = [i for i in inf_ran_interdicoes if st.checkbox(i)]
        sel_ran_cond = [i for i in inf_ran_condicionantes if st.checkbox(i)]
    with col_s2:
        st.write("**Checklist Técnica RAN (Portaria 162/2011)**")
        lim_apoio = st.checkbox("Excede Área Implantação (Apoio Agrícola > 750m² ou >1% da exploração)")
        lim_hab = st.checkbox("Excede Área Habitação (Agricultor > 300m²)")
        lim_vias = st.checkbox("Vias de acesso > 5m de largura ou pavimento impermeável")
        falta_alt = st.checkbox("Falta de comprovação de inexistência de alternativa fora da RAN")

    st.warning("**🏛️ Património Cultural (Lei 107/2001)**")
    r_pat = st.checkbox("Violação de ZGP/ZEP de património classificado")
    
    st.divider()
    r_crime = st.checkbox("⚠️ Suspeita de crime contra o Ordenamento (Art. 278.º CP)")
    gravidade = st.select_slider("Gravidade Proposta", options=["Leve", "Grave", "Muito Grave"])

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

with tab5:
    if st.button("🚀 Gerar Documentação Final"):
        if not api_key: st.error("Falta a API Key.")
        else:
            with st.spinner("A fundir regimes jurídicos e dados técnicos RAN..."):
                model = genai.GenerativeModel(modelo_selecionado)
                prompt = f"""
                Age como Fiscal Sénior e Jurista. Redigi Relatório e Auto de Notícia.
                DADOS: Local {local}, GPS: {lat}, {lon}. Área {area_m2}m2.
                INFRATOR: {inf_nome}, NIF: {inf_nif}, Tel: {inf_tel} ({tipo_ent}).
                
                ENQUADRAMENTO RAN (DL 73/2009 e 199/2015):
                - Interdições: {sel_ran_int}. Condicionantes sem Título: {sel_ran_cond}.
                - Limites Portaria 162/2011: Apoios={lim_apoio}, Habitação={lim_hab}, Vias={lim_vias}, Alternativa={falta_alt}.
                
                ENQUADRAMENTO CONSOLIDADO:
                - REN: {sel_ren}. Interdições REN: {sel_int}.
                - Natura 2000 (Art 9º nº 2 DL 140/99): {sel_art9}.
                - Património/Crime: {r_pat}, {r_crime}.
                
                INSTRUÇÕES JURÍDICAS:
                1. No RELATÓRIO: Cita o DL 199/2015 e os limites da Portaria 162/2011 para a RAN. 
                2. Fundamenta que utilizações fora dos limites de área ou sem parecer da Entidade Regional da RAN são nulas.
                3. No AUTO: Tipifica infrações e define coimas para gravidade {gravidade} e entidade {tipo_ent}.
                4. Estilo: Profissional, PT-PT, Justificado, BOLD nos capítulos.
                """
                try:
                    res = model.generate_content(prompt).text
                    st.success("Documentação preparada!")
                    st.download_button("📥 Descarregar Word", export_docx(res), file_name=f"Fiscalizacao_{local}.docx")
                    st.write(res)
                except Exception as e: st.error(f"Erro: {e}")


