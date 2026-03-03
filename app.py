import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
import re

# 1. Configuração de Interface
st.set_page_config(page_title="Sistema Omni-Fiscalização Territorial", layout="wide", page_icon="🛡️")

st.markdown("""
    <style>
    .stCheckbox { margin-bottom: -15px; font-size: 13px; }
    .stTabs [data-baseweb="tab"] { font-weight: bold; }
    .stTextArea textarea { background-color: #f8f9fa; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR: CONFIGURAÇÃO ---
st.sidebar.header("⚙️ Configuração")
api_key = st.sidebar.text_input("Google API Key", type="password")
if api_key:
    genai.configure(api_key=api_key)

# =========================================================
# BASES DE DADOS RECUPERADAS (NÃO APAGAR)
# =========================================================

# 1. REN (DL 166/2008, DL 239/2012 e Portaria 419/2012)
ren_litoral = ["Faixa marítima de proteção costeira", "Praias", "Barreiras detríticas", "Tômbolos", "Sapais", "Ilhéus e rochedos emersos no mar", "Dunas costeiras e dunas fósseis", "Arribas e respetivas faixas de proteção", "Faixa terrestre de proteção costeira", "Águas de transição e respetivos leitos, margens e faixas de proteção"]
ren_hidro = ["Cursos de água e respetivos leitos e margens", "Lagoas e lagos e respetivos leitos, margens e faixas de proteção", "Albufeiras (conectividade ecológica), leitos, margens e faixas de proteção", "Áreas estratégicas de proteção e recarga de aquíferos"]
ren_riscos = ["Zonas adjacentes", "Zonas ameaçadas pelo mar", "Zonas ameaçadas pelas cheias", "Áreas de elevado risco de erosão hídrica do solo", "Áreas de instabilidade de vertentes"]

# 2. REDE NATURA 2000 (Sítios e Condicionantes integrais)
natura_sitios = ["ZEC Serra de Aire e Candeeiros", "ZEC Serra da Estrela", "ZEC Rio Zêzere", "ZEC Sicó/Alvaiázere", "ZEC Monfurado", "ZEC Estuário do Tejo", "ZEC Serra da Lousã", "ZPE Paul do Boquilobo", "ZPE Estuário do Mondego", "ZPE Douro Internacional", "ZPE Castro Verde"]

art9_integral = [
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

# 3. RNAP (Rede Nacional de Áreas Protegidas - Âmbito Nacional)
rnap_lista = ["P.N. da Peneda-Gerês", "P.N. do Alvão", "P.N. do Douro Internacional", "P.N. da Serra da Estrela", "P.N. das Serras de Aire e Candeeiros", "P.N. de Montesinho", "P.N. do Tejo Internacional", "P.N. da Arrábida", "P.N. do Sudoeste Alentejano e Costa Vicentina", "P.N. do Vale do Guadiana", "P.N. da Ria Formosa", "R.N. do Paul do Boquilobo", "R.N. das Berlengas", "R.N. da Serra da Malcata", "R.N. do Estuário do Tejo", "R.N. do Estuário do Sado", "P.P. da Serra do Açor", "M.N. das Pegadas de Dinossáurios"]

# 4. RAN (DL 73/2009, DL 199/2015 e Portaria 162/2011)
ran_tipos = ["Utilização não agrícola sem parecer vinculado (Art. 22.º)", "Destruição/Degradação do potencial agrícola do solo", "Intervenção em Aproveitamento Hidroagrócola (Regadio Público)", "Impermeabilização de solos de Classe A ou B"]

# =========================================================
# INTERFACEstreamlite
# =========================================================

st.title("🛡️ Fiscalização Integrada: Master Território e Ambiente")

tabs = st.tabs(["📍 Identificação", "💧 REN", "🌿 Natura & RNAP", "🌾 RAN", "🏛️ Património", "📑 Gerar Documentação"])

with tabs[0]:
    c1, c2 = st.columns(2)
    with c1:
        local = st.text_input("Localização/Concelho")
        col_gps1, col_gps2 = st.columns(2)
        lat = col_gps1.text_input("Latitude", placeholder="39.xxxx")
        lon = col_gps2.text_input("Longitude", placeholder="-8.xxxx")
        fotos = st.file_uploader("📸 Fotos", accept_multiple_files=True)
    with c2:
        inf_nome = st.text_input("Nome/Entidade")
        inf_morada = st.text_input("Morada")
        inf_nif = st.text_input("NIF")
        inf_tel = st.text_input("Telefone")
        tipo_ent = st.radio("Tipo", ["Pessoa Singular", "Pessoa Coletiva"], horizontal=True)

with tabs[1]:
    st.info("**Matriz REN (DL 166/2008)**")
    c1, c2 = st.columns(2)
    with c1:
        st.write("**Tipologias Afetadas**")
        sel_ren = [i for i in (ren_litoral + ren_hidro + ren_riscos) if st.checkbox(i, key=f"ren_{i}")]
    with c2:
        st.write("**Interdições e Checklist Portaria 419/2012**")
        sel_int_ren = [i for i in ["Loteamento", "Construção/Ampliação", "Escavações/Aterros", "Destruição vegetal"] if st.checkbox(i)]
        c_previa_ren = st.checkbox("Falta de Comunicação Prévia à CCDR")
        p_apa_ren = st.checkbox("Falta de Parecer APA (Zonas de Risco/Aquíferos)")

with tabs[2]:
    st.success("**Natureza: Rede Natura 2000 e RNAP**")
    c1, c2 = st.columns(2)
    with c1:
        sel_rnap = st.multiselect("Área Protegida (RNAP):", rnap_lista)
        sel_nat = st.multiselect("Sítio Natura 2000 (ZEC/ZPE):", natura_sitios)
        sel_zon = st.multiselect("Zonamento (POAP):", ["Reserva Integral", "Reserva Parcial", "Proteção I", "Proteção II"])
    with c2:
        st.write("**Condicionantes Art. 9.º n.º 2 (Texto Integral):**")
        sel_art9 = [i for i in art9_integral if st.checkbox(i, key=f"art9_{i}")]

with tabs[3]:
    st.info("**Reserva Agrícola Nacional (DL 199/2015)**")
    c1, c2 = st.columns(2)
    with c1:
        st.write("**Infrações RAN**")
        sel_ran = [i for i in ran_tipos if st.checkbox(i, key=f"ran_{i}")]
    with col2 := c2:
        st.write("**Limites Portaria 162/2011**")
        l_apoio = st.checkbox("Apoio Agrícola > 750m² ou >1% área")
        l_hab = st.checkbox("Habitação Agricultor > 300m²")
        l_vias = st.checkbox("Vias > 5m de largura")
        f_alt = st.checkbox("Falta de prova de inexistência de alternativa")

with tabs[4]:
    st.warning("**Património Cultural (Lei 107/2001)**")
    r_pat = st.checkbox("Intervenção em Zona Geral de Proteção (50m) sem parecer")
    t_pat = st.text_area("Notas sobre Património/Arqueologia")

with tabs[5]:
    gravidade = st.select_slider("Gravidade Proposta", options=["Leve", "Grave", "Muito Grave"])
    r_crime = st.checkbox("⚠️ Crime contra Ordenamento (Art. 278.º CP)")
    if st.button("🚀 Gerar Relatório e Auto"):
        # Lógica de processamento final aqui...
        st.write("A processar com todos os regimes consolidados...")

