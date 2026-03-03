import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
import re

# 1. Configuração de Interface
st.set_page_config(page_title="Sistema Integrado de Fiscalização Território/Ambiente", layout="wide", page_icon="🛡️")

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
if api_key:
    genai.configure(api_key=api_key)

# =========================================================
# BASES DE DADOS TÉCNICAS (TOTALMENTE RECUPERADAS)
# =========================================================

# 1. REN - TIPOLOGIAS INTEGRAIS (DL 239/2012)
ren_litoral = ["Faixa marítima de proteção costeira", "Praias", "Barreiras detríticas (ilhas-barreira, restingas)", "Tômbolos", "Sapais", "Ilhéus e rochedos emersos no mar", "Dunas costeiras e dunas fósseis", "Arribas e respetivas faixas de proteção", "Faixa terrestre de proteção costeira", "Águas de transição e respetivos leitos, margens e faixas de proteção"]
ren_hidro = ["Cursos de água e respetivos leitos e margens", "Lagoas e lagos e respetivos leitos, margens e faixas de proteção", "Albufeiras (conectividade ecológica), leitos, margens e faixas de proteção", "Áreas estratégicas de proteção e recarga de aquíferos"]
ren_riscos = ["Zonas adjacentes", "Zonas ameaçadas pelo mar", "Zonas ameaçadas pelas cheias", "Áreas de elevado risco de erosão hídrica do solo", "Áreas de instabilidade de vertentes"]

# 2. REDE NATURA 2000 - Artigo 9.º n.º 2 (Texto na Íntegra conforme Lei)
condicionantes_natura = [
    "a) A realização de obras de construção civil fora dos perímetros urbanos, com excepção das obras de reconstrução, demolição, conservação de edifícios e ampliação desde que esta não envolva aumento de área de implantação superior a 50% da área inicial e a área total de ampliação seja inferior a 100 m2",
    "b) A alteração do uso actual do solo que abranja áreas contínuas superiores a 5 ha",
    "c) As modificações de coberto vegetal resultantes da alteração entre tipos de uso agrícola e florestal, em áreas contínuas superiores a 5 ha, considerando-se continuidade as ocupações similares que distem entre si menos de 500 m",
    "d) As alterações à morfologia do solo, com excepção das decorrentes das normais actividades agrícolas e florestais",
    "e) A alteração do uso actual dos terrenos das zonas húmidas ou marinhas, bem como as alterações à sua configuração e topografia",
    "f) A deposição de sucatas e de resíduos sólidos e líquidos",
    "g) A abertura de novas vias de comunicação, bem como o alargamento das existentes",
    "h) A instalação de infra-estruturas de electricidade e telefónicas, aéreas ou subterrâneas, de telecomunicações, de transporte de gás natural ou de outros combustíveis, de saneamento básico e de aproveitamento de energias renováveis ou similares fora dos perímetros urbanos",
    "i) A prática de actividades motorizadas organizadas e competições desportivas fora dos perímetros urbanos",
    "j) A prática de alpinismo, de escalada e de montanhismo",
    "l) A reintrodução de espécies indígenas da fauna e da flora selvagens"
]

# 3. RNAP - REDE NACIONAL DE ÁREAS PROTEGIDAS (Listagem Oficial)
rnap_lista = ["P.N. da Peneda-Gerês", "P.N. do Alvão", "P.N. do Douro Internacional", "P.N. da Serra da Estrela", "P.N. das Serras de Aire e Candeeiros", "P.N. de Montesinho", "P.N. do Tejo Internacional", "P.N. da Arrábida", "P.N. do Sudoeste Alentejano e Costa Vicentina", "P.N. do Vale do Guadiana", "P.N. da Ria Formosa", "R.N. do Paul do Boquilobo", "R.N. das Berlengas", "R.N. da Serra da Malcata", "R.N. do Estuário do Tejo", "R.N. do Estuário do Sado", "P.P. da Serra do Açor", "M.N. das Pegadas de Dinossáurios"]

# 4. RAN - TIPOLOGIAS E INFRAÇÕES (DL 199/2015)
ran_tipologias = [
    "Utilização de terras para fins não agrícolas (Art. 20.º)",
    "Ações que destruam ou degradem o potencial agrícola (Art. 21.º)",
    "Intervenção em áreas beneficiadas por Aproveitamentos Hidroagrócolas (Regadio Público)",
    "Impermeabilização definitiva de solos de alta qualidade (Classe A/B)",
    "Obras sem parecer vinculativo da Entidade Regional da RAN (Art. 22.º)"
]

# --- INTERFACE ---
st.title("🛡️ Sistema de Fiscalização Integral: Matriz Consolidada")

tabs = st.tabs(["📍 Identificação", "💧 REN", "🌿 Natura & RNAP", "🌾 RAN", "🏛️ Património", "📑 Gerar Documentação"])

with tabs[0]:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Localização GPS")
        local = st.text_input("Localização / Concelho")
        col_gps1, col_gps2 = st.columns(2)
        lat = col_gps1.text_input("Latitude (WGS84)")
        lon = col_gps2.text_input("Longitude (WGS84)")
        area_m2 = st.number_input("Área Afetada (m²)", value=1000.0)
        fotos = st.file_uploader("📸 Fotos", accept_multiple_files=True)
    with c2:
        st.subheader("Dados do Infrator")
        inf_nome = st.text_input("Nome/Entidade")
        inf_nif = st.text_input("NIF/NIPC")
        inf_tel = st.text_input("Contacto Telefónico")
        tipo_ent = st.radio("Entidade", ["Pessoa Singular", "Pessoa Coletiva"], horizontal=True)

with tabs[1]:
    st.info("**Reserva Ecológica Nacional (DL 166/2008)**")
    c1, col_check = st.columns(2)
    with c1:
        st.write("**Tipologias Afetadas**")
        sel_ren = [i for i in (ren_litoral + ren_hidro + ren_riscos) if st.checkbox(i, key=f"ren_{i}")]
    with col_check:
        st.write("**Verificação (Portaria 419/2012)**")
        c_previa = st.checkbox("Falta de Comunicação Prévia")
        p_apa = st.checkbox("Falta de Parecer APA")
        l_area_ren = st.checkbox("Excede limites de área/impermeabilização")

with tabs[2]:
    st.success("**Conservação da Natureza**")
    c1, c2 = st.columns(2)
    with c1:
        sel_rnap = st.multiselect("Área Protegida (RNAP):", rnap_lista)
        sel_zec = st.multiselect("Sítio Natura 2000 (ZEC/ZPE):", ["ZEC Serra de Aire/Candeeiros", "ZEC Rio Zêzere", "ZPE Paul do Boquilobo"])
    with c2:
        st.write("**Condicionantes Art. 9.º n.º 2 (DL 140/99)**")
        sel_art9 = [i for i in condicionantes_natura if st.checkbox(i, key=f"nat_{i}")]

with tabs[3]:
    st.info("**Reserva Agrícola Nacional (DL 199/2015)**")
    c1, c2 = st.columns(2)
    with c1:
        st.write("**Infrações RAN**")
        sel_ran = [i for i in ran_tipologias if st.checkbox(i, key=f"ran_{i}")]
    with c2:
        st.write("**Limites Técnicos (Portaria 162/2011)**")
        l_apoio = st.checkbox("Apoio Agrícola > 750m² ou >1% da exploração")
        l_hab = st.checkbox("Habitação Agricultor > 300m²")
        l_vias = st.checkbox("Vias > 5m de largura ou impermeáveis")
        f_alt_ran = st.checkbox("Sem prova de inexistência de alternativa fora da RAN")

with tabs[4]:
    st.warning("**Património Cultural (Lei 107/2001)**")
    sel_pat = st.checkbox("Violação de Zona Geral de Proteção (50m) sem parecer")
    t_pat = st.text_area("Notas sobre Património/Arqueologia")

with tabs[5]:
    st.subheader("Gerar Documentação")
    gravidade = st.select_slider("Gravidade Proposta", options=["Leve", "Grave", "Muito Grave"])
    r_crime = st.checkbox("⚠️ Suspeita de Crime (Art. 278.º Código Penal)")
    
    if st.button("🚀 Gerar Documentação Final"):
        # Lógica de integração total IA
        st.write("A processar relatório com tipologias exaustivas...")


