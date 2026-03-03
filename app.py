import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
import re
from pypdf import PdfReader

# 1. Configuração de Interface
st.set_page_config(page_title="Sistema Omni-Fiscalização Territorial", layout="wide", page_icon="🛡️")

st.markdown("""
    <style>
    .stCheckbox { margin-bottom: -15px; font-size: 13px; }
    .stTabs [data-baseweb="tab"] { font-weight: bold; }
    .stTextArea textarea { background-color: #fcfcfc; }
    .stNumberInput { margin-bottom: -10px; }
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
        st.sidebar.error("Erro na API Key.")

# --- BASE DE DADOS INTEGRADA ---
ren_litoral = ["Faixa marítima", "Praias", "Barreiras detríticas", "Tômbolos", "Sapais", "Ilhéus", "Dunas", "Arribas e faixas proteção", "Faixa terrestre proteção", "Águas de transição"]
ren_hidro = ["Cursos de água", "Lagoas e lagos", "Albufeiras", "Áreas recarga aquíferos"]
ren_riscos = ["Zonas adjacentes", "Zonas ameaçadas pelo mar", "Zonas ameaçadas pelas cheias", "Elevado risco erosão hídrica", "Instabilidade de vertentes"]

medidas_minimizacao = ["Recuperação da topografia original", "Reposição do coberto vegetal autóctone", "Controlo de espécies invasoras", "Gestão de águas pluviais", "Limitação de períodos de intervenção (fauna)", "Monitorização arqueológica", "Limpeza e remoção de sobrantes"]

zec_zpe_centro = ["ZEC Serra de Aire e Candeeiros", "ZEC Serra da Estrela", "ZEC Rio Zêzere", "ZEC Albufeira de Castelo do Bode", "ZEC Sicó/Alvaiázere", "ZPE Paul do Boquilobo", "ZPE Estuário do Mondego", "ZPE Douro Internacional"]

art9_natura = [
    "a) Obras construção civil (limites área/ampliação)", "b) Alteração uso solo > 5 ha", "c) Coberto vegetal > 5 ha",
    "d) Alterações morfologia solo (extra agrícolas)", "e) Alteração zonas húmidas/marinhas", "f) Deposição sucatas/resíduos",
    "g) Novas vias/alargamento", "h) Infraestruturas (energia/telecom)", "i) Atividades motorizadas/competições", "l) Reintrodução espécies"
]

areas_protegidas = ["P.N. Douro Internacional", "P.N. Serra da Estrela", "P.N. Serras de Aire e Candeeiros", "R.N. Paul do Boquilobo", "R.N. Serra da Malcata"]

# --- INTERFACE ---
st.title("🛡️ Sistema de Fiscalização: Master Território e Ambiente")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📍 Ocorrência & GPS", "💧 Matriz REN", "🌿 Natura & AP", "🌾 Solo & Património", "📑 Documentação"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📍 Localização e Evidências")
        local = st.text_input("Local/Concelho", "Região Centro / Médio Tejo")
        col_gps1, col_gps2 = st.columns(2)
        lat = col_gps1.text_input("Latitude (WGS84)", placeholder="Ex: 39.1234")
        lon = col_gps2.text_input("Longitude (WGS84)", placeholder="Ex: -8.5678")
        area_m2 = st.number_input("Área Afetada (m²)", value=1000.0)
        fotos = st.file_uploader("📸 Registos Fotográficos (JPG/PNG)", accept_multiple_files=True)
    with c2:
        st.subheader("👤 Identificação do Infrator")
        infrator = st.text_input("Nome/Entidade", "Em averiguação")
        tipo_ent = st.radio("Tipo", ["Pessoa Singular", "Pessoa Coletiva"], horizontal=True)
        nif = st.text_input("NIF/NIPC", "000000000")
        desc_visual = st.text_area("Descrição visual das ações detetadas", "Intervenção com maquinaria pesada...")

with tab2:
    st.info("**Tipologias e Interdições REN (DL 166/2008 atualizado)**")
    col_r1, col_r2, col_r3 = st.columns(3)
    with col_r1:
        st.write("**Áreas Litorais/Hidro**")
        sel_ren_tipos = [i for i in (ren_litoral + ren_hido) if st.checkbox(i)]
    with col_r2:
        st.write("**Áreas de Risco**")
        sel_riscos = [i for i in ren_riscos if st.checkbox(i)]
    with col_r3:
        st.write("**Interdições (Art. 20.º)**")
        sel_int_ren = [i for i in ["Loteamento", "Construção/Ampliação", "Vias de comunicação", "Escavações/Aterros", "Destruição revestimento vegetal"] if st.checkbox(i)]
    
    st.subheader("🛠️ Medidas de Minimização (Incumpridas)")
    sel_medidas = [i for i in medidas_minimizacao if st.checkbox(i)]

with tab3:
    col_n1, col_n2 = st.columns(2)
    with col_n1:
        st.success("**Rede Natura 2000 (DL 140/99)**")
        sel_zec = st.multiselect("Sítios ZEC/ZPE:", zec_zpe_centro)
        st.write("**Condicionantes Artigo 9.º**")
        sel_art9 = [i for i in art9_natura if st.checkbox(i)]
    with col_n2:
        st.success("**Áreas Protegidas (RNAP)**")
        sel_ap = st.multiselect("Parques e Reservas:", areas_protegidas)
        sel_zon = st.multiselect("Zonamento (POAP):", ["Reserva Integral", "Reserva Parcial", "Proteção Parcial I", "Proteção Parcial II"])
        upload_poap = st.file_uploader("📂 Upload Regulamento POAP (PDF)", type=['pdf'])

with tab4:
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.info("**🌾 RAN (DL 73/2009)**")
        r_ran = st.checkbox("Violação de solos agrícolas")
        t_ran = st.text_area("Notas RAN:")
    with col_s2:
        st.warning("**🏛️ Património Cultural (Lei 107/2001)**")
        r_pat = st.checkbox("Violação de ZGP/ZEP")
        t_pat = st.text_area("Notas Património:")
    
    st.divider()
    r_crime = st.checkbox("⚠️ Suspeita de crime contra o Ordenamento (Art. 278.º Código Penal)")
    gravidade = st.select_slider("Gravidade Contraordenacional", options=["Leve", "Grave", "Muito Grave"])

with tab5:
    if st.button("🚀 Gerar Documentação Final"):
        if not api_key: st.error("Falta a API Key.")
        else:
            with st.spinner("A fundir regimes jurídicos, coordenadas e evidências..."):
                model = genai.GenerativeModel(modelo_selecionado)
                prompt = f"""
                Age como Fiscal Sénior e Jurista. Redigi Relatório e Auto de Notícia profissionais.
                DADOS: Local {local}, GPS: {lat}, {lon}. Área {area_m2}m2. Infrator {infrator} ({tipo_ent}).
                
                QUADRO REN: Tipologias {sel_ren_tipos}, Riscos {sel_riscos}, Interdições {sel_int_ren}.
                MEDIDAS INCUMPRIDAS: {sel_medidas}.
                QUADRO NATURA: Sítios {sel_zec}, Art 9º {sel_art9}, Zonamento {sel_zon}.
                OUTROS: Crime Art 278 CP: {r_crime}. Património: {t_pat}. RAN: {t_ran}.
                
                INSTRUÇÕES:
                1. RELATÓRIO: Fundamenta a violação do DL 166/2008 e DL 140/99 (Art 9º). 
                2. Menciona a localização exata por coordenadas GPS {lat}, {lon} e o registo fotográfico efetuado.
                3. AUTO: Tipifica contraordenações muito graves para interdições REN. 
                4. Aplica coimas para gravidade {gravidade} e entidade {tipo_ent} (Lei 50/2006).
                5. Propõe Embargo e Intimação para reposição do terreno.
                Texto em PT-PT, Justificado, capítulos a BOLD.
                """
                try:
                    res = model.generate_content(prompt).text
                    st.success("Documentação preparada!")
                    st.download_button("📥 Descarregar Word", BytesIO(), file_name=f"Fiscalizacao_{local}.docx")
                    st.write(res)
                except Exception as e: st.error(f"Erro: {e}")


