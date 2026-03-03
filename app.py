import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
import re

# 1. Configuração de Interface
st.set_page_config(page_title="Sistema de Fiscalização Pro: Matriz Legal Total", layout="wide", page_icon="🛡️")

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
modelo_selecionado = "gemini-1.5-pro"

if api_key:
    genai.configure(api_key=api_key)
    try:
        modelos = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        modelo_selecionado = st.sidebar.selectbox("Motor de IA Ativo", modelos, index=0)
    except:
        st.sidebar.error("Erro na API Key.")

# --- BASE DE DADOS CONSOLIDADAS ---

# REN - Tipologias Oficiais (DL 239/2012)
ren_litoral = ["Faixa marítima de proteção", "Praias", "Barreiras detríticas", "Tômbolos", "Sapais", "Ilhéus", "Dunas", "Arribas", "Faixa terrestre", "Águas de transição"]
ren_hidro = ["Cursos de água", "Lagoas e lagos", "Albufeiras", "Áreas de recarga de aquíferos"]
ren_riscos = ["Zonas adjacentes", "Zonas ameaçadas pelo mar", "Zonas ameaçadas pelas cheias", "Elevado risco de erosão", "Instabilidade de vertentes"]

# DL 140/99 Artigo 9.º n.º 2 (Texto Integral)
condicionantes_art9 = [
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

# ÁREAS PROTEGIDAS (RNAP)
rnap_lista = ["P.N. da Peneda-Gerês", "P.N. do Alvão", "P.N. do Douro Internacional", "P.N. da Serra da Estrela", "P.N. das Serras de Aire e Candeeiros", "P.N. de Montesinho", "P.N. do Tejo Internacional", "R.N. do Paul do Boquilobo", "R.N. das Berlengas", "R.N. da Serra da Malcata", "R.N. do Estuário do Tejo", "R.N. do Estuário do Sado", "P.P. da Serra do Açor"]

# SÍTIO NATURA 2000
zec_zpe_lista = ["ZEC Serra de Aire e Candeeiros", "ZEC Serra da Estrela", "ZEC Rio Zêzere", "ZEC Albufeira de Castelo do Bode", "ZEC Sicó/Alvaiázere", "ZPE Paul do Boquilobo", "ZPE Estuário do Mondego"]

# RAN (DL 73/2009 + DL 199/2015)
ran_tipologias = ["Utilização não agrícola sem parecer (Art. 22.º)", "Ações que destruam o potencial agrícola do solo", "Intervenção em Aproveitamento Hidroagrícola (Regadio)", "Impermeabilização de solos de Classe A ou B"]

# --- INTERFACE ---
st.title("🛡️ Sistema de Fiscalização: Master Território e Ambiente")

tabs = st.tabs(["📍 Identificação", "💧 REN", "🌿 Natura & AP", "🌾 RAN", "🏛️ Património", "📑 Documentação"])

with tabs[0]:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📍 Localização e GPS")
        local = st.text_input("Localização/Concelho", "Região Centro")
        col_gps1, col_gps2 = st.columns(2)
        lat = col_gps1.text_input("Latitude", placeholder="39.xxxx")
        lon = col_gps2.text_input("Longitude", placeholder="-8.xxxx")
        area_m2 = st.number_input("Área Afetada (m²)", value=1000.0)
        fotos = st.file_uploader("📸 Fotos", accept_multiple_files=True, type=['jpg', 'jpeg', 'png'])
    with c2:
        st.subheader("👤 Dados do Infrator")
        inf_nome = st.text_input("Nome/Entidade")
        inf_morada = st.text_input("Morada/Sede")
        inf_nif = st.text_input("NIF/NIPC")
        inf_tel = st.text_input("Telefone")
        tipo_ent = st.radio("Tipo", ["Pessoa Singular", "Pessoa Coletiva"], horizontal=True)
        desc_visual = st.text_area("Notas de Campo")

with tabs[1]:
    st.info("**Tipologias REN (DL 166/2008 + DL 239/2012)**")
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Áreas Afetadas**")
        sel_ren = [i for i in (ren_litoral + ren_hidro + ren_riscos) if st.checkbox(i, key=f"ren_{i}")]
    with col2:
        st.write("**Interdições e Títulos**")
        c_previa = st.checkbox("Falta de Comunicação Prévia")
        p_apa = st.checkbox("Falta de Parecer APA")
        lim_area_ren = st.checkbox("Excede limites de área/impermeabilização REN")

with tabs[2]:
    st.success("**Conservação da Natureza (DL 140/99 + DL 142/2008)**")
    col1, col2 = st.columns(2)
    with col1:
        sel_zec = st.multiselect("Sítios ZEC/ZPE:", zec_zpe_lista)
        sel_rnap = st.multiselect("RNAP (Parques/Reservas):", rnap_lista)
        st.write("**Condicionantes Art. 9.º n.º 2:**")
        sel_art9 = [i for i in condicionantes_art9 if st.checkbox(i, key=f"art9_{i}")]
    with col2:
        sel_zon = st.multiselect("Zonamento (POAP):", ["Reserva Integral", "Reserva Parcial", "Proteção Parcial I", "Proteção Parcial II"])
        upload_poap = st.file_uploader("📂 Regulamento POAP (PDF)", type=['pdf'])

with tabs[3]:
    st.info("**Reserva Agrícola Nacional (DL 199/2015 + Portaria 162/2011)**")
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Infrações Core**")
        sel_ran = [i for i in ran_tipologias if st.checkbox(i, key=f"ran_{i}")]
    with col2:
        st.write("**Limites Técnicos (Portaria 162/2011)**")
        lim_apoio = st.checkbox("Apoio Agrícola > 750m² ou >1% área exploração")
        lim_hab = st.checkbox("Habitação Agricultor > 300m²")
        lim_vias = st.checkbox("Vias > 5m de largura ou pavimento impermeável")
        falta_alt = st.checkbox("Falta de prova de inexistência de alternativa fora da RAN")

with tabs[4]:
    st.warning("**Património Cultural (Lei 107/2001)**")
    r_pat = st.checkbox("Intervenção em Zona Geral de Proteção (50m) sem parecer")
    t_pat = st.text_area("Descreva a infração ao Património")

with tabs[5]:
    gravidade = st.select_slider("Gravidade Proposta", options=["Leve", "Grave", "Muito Grave"])
    r_crime = st.checkbox("⚠️ Suspeita de Crime (Art. 278.º Código Penal)")
    if st.button("🚀 Gerar Documentação Final"):
        if not api_key: st.error("Insira a API Key.")
        else:
            with st.spinner("A fundir todos os regimes jurídicos..."):
                model = genai.GenerativeModel(modelo_selecionado)
                prompt = f"""
                Age como Fiscal Sénior e Jurista. Redigi Relatório e Auto de Notícia.
                DADOS: Local {local}, GPS: {lat}, {lon}. Área {area_m2}m2.
                INFRATOR: {inf_nome}, NIF: {inf_nif}, Tel: {inf_tel} ({tipo_ent}).
                
                ENQUADRAMENTO:
                - REN: {sel_ren}. Interdições: {c_previa}/{p_apa}.
                - Natura 2000 (Art 9º nº 2 DL 140/99): {sel_art9}.
                - RAN (DL 199/2015): {sel_ran}. Limites Portaria 162/2011: Apoio={lim_apoio}, Hab={lim_hab}, Vias={lim_vias}, Alternativa={falta_alt}.
                - Crime Art 278 CP: {r_crime}.
                
                INSTRUÇÕES:
                1. No RELATÓRIO: Cita o n.º 2 do Artigo 9.º do DL 140/99 na íntegra para as condicionantes selecionadas.
                2. Fundamenta a violação da RAN citando o DL 199/2015 e a Portaria 162/2011 (limites de área).
                3. No AUTO: Tipifica e calcula coimas para gravidade {gravidade} e entidade {tipo_ent} (Lei 50/2006).
                4. Estilo: Formal, PT-PT, capítulos a BOLD.
                """
                try:
                    res = model.generate_content(prompt).text
                    # (Inserir função export_docx aqui...)
                    st.success("Gerado!")
                    st.write(res)
                except Exception as e: st.error(f"Erro: {e}")

