import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
import re
from pypdf import PdfReader

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
modelo_selecionado = "gemini-1.5-pro"

if api_key:
    genai.configure(api_key=api_key)
    try:
        modelos = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        modelo_selecionado = st.sidebar.selectbox("Motor de IA", modelos, index=0)
    except:
        st.sidebar.error("Erro na API Key.")

# --- BASE DE DADOS INTEGRADA (REVISÃO PORTARIA 419/2012) ---

# REN - Tipologias Oficiais
ren_litoral = ["Faixa marítima", "Praias", "Barreiras detríticas", "Tômbolos", "Sapais", "Ilhéus", "Dunas", "Arribas", "Faixa terrestre proteção", "Águas de transição"]
ren_hidro = ["Cursos de água", "Lagoas e lagos", "Albufeiras", "Áreas estratégicas de recarga de aquíferos"]
ren_riscos = ["Zonas adjacentes", "Zonas ameaçadas pelo mar", "Zonas ameaçadas pelas cheias", "Elevado risco de erosão hídrica", "Instabilidade de vertentes"]

# Natura 2000 - ZEC/ZPE Médio Tejo e Centro
zec_zpe_centro = ["ZEC Serra de Aire e Candeeiros", "ZEC Serra da Estrela", "ZEC Rio Zêzere", "ZEC Albufeira de Castelo do Bode", "ZEC Sicó/Alvaiázere", "ZPE Paul do Boquilobo", "ZPE Estuário do Mondego"]

# Artigo 9.º DL 140/99
art9_natura = ["a) Obras construção civil", "b) Uso solo > 5ha", "c) Coberto vegetal > 5ha", "d) Morfologia solo", "f) Deposição resíduos", "g) Vias comunicação", "h) Infraestruturas"]

# --- INTERFACE ---
st.title("🛡️ Sistema de Fiscalização: Master Território e Ambiente")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📍 Ocorrência & GPS", "💧 Matriz REN", "🌿 Natura & AP", "🌾 Solo & Património", "📑 Gerar Auto"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📍 Localização e GPS")
        local = st.text_input("Localização", "Médio Tejo / Região Centro")
        col_gps1, col_gps2 = st.columns(2)
        lat = col_gps1.text_input("Latitude", placeholder="39.xxxx")
        lon = col_gps2.text_input("Longitude", placeholder="-8.xxxx")
        area_m2 = st.number_input("Área Afetada (m²)", value=1000.0)
    with c2:
        st.subheader("👤 Identificação do Infrator")
        infrator = st.text_input("Nome/Entidade")
        tipo_ent = st.radio("Tipo", ["Pessoa Singular", "Pessoa Coletiva"], horizontal=True)
        nif = st.text_input("NIF/NIPC")
        desc_visual = st.text_area("Descrição visual das ações", "Deteção de intervenção...")

with tab2:
    st.info("**Tipologias REN e Checklist Técnica (Portaria 419/2012)**")
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        st.write("**Tipologias Afetadas**")
        sel_ren = [i for i in (ren_litoral + ren_hidro + ren_riscos) if st.checkbox(i)]
        st.write("**Interdições (Art. 20.º)**")
        sel_int = [i for i in ["Loteamento", "Construção/Ampliação", "Escavações/Aterros", "Destruição vegetal"] if st.checkbox(i)]
    
    with col_r2:
        st.write("**Verificação de Compatibilidade / Títulos**")
        c_previva = st.checkbox("Falta de Comunicação Prévia à CCDR")
        parecer_apa = st.checkbox("Falta de Parecer Vinculativo da APA")
        limite_area = st.checkbox("Excede limite de área (Ex: >1000m² apoio agrícola / >250m² habitação)")
        limite_imp = st.checkbox("Excede impermeabilização (Ex: >2% da área do prédio)")
        rec_interesse = st.checkbox("Falta de Despacho de Relevante Interesse Público")

with tab3:
    col_n1, col_n2 = st.columns(2)
    with col_n1:
        st.success("**Rede Natura 2000 (DL 140/99)**")
        sel_zec = st.multiselect("Sítios ZEC/ZPE:", zec_zpe_centro)
        st.write("**Condicionantes Art. 9.º**")
        sel_art9 = [i for i in art9_natura if st.checkbox(i)]
    with col_n2:
        st.success("**Zonamento Áreas Protegidas**")
        sel_zon = st.multiselect("Zonamento (POAP):", ["Reserva Integral", "Reserva Parcial", "Proteção Parcial I", "Proteção Parcial II"])
        upload_poap = st.file_uploader("📂 Upload Regulamento POAP/Carta REN", type=['pdf'])

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
            with st.spinner("A fundir regimes jurídicos e limites da Portaria 419/2012..."):
                model = genai.GenerativeModel(modelo_selecionado)
                prompt = f"""
                Age como Fiscal Sénior e Jurista. Redigi Relatório e Auto de Notícia.
                DADOS: Local {local}, GPS: {lat}, {lon}. Área {area_m2}m2. Infrator {infrator} ({tipo_ent}).
                
                ENQUADRAMENTO REN:
                - Tipologias: {sel_ren}. Interdições: {sel_int}.
                - Checklist Técnica: Comunicação Prévia={c_previva}, Parecer APA={parecer_apa}, Excesso Área={limite_area}, Excesso Impermeabilização={limite_imp}.
                - Relevante Interesse Público: {rec_interesse}.
                
                ENQUADRAMENTO EXTRA:
                - Natura 2000 (Art 9º DL 140/99): {sel_art9} | Sítios: {sel_zec}.
                - Património/RAN: {t_pat} {t_ran}. Crime Art 278 CP: {r_crime}.
                
                FUNDAMENTAÇÃO:
                1. RELATÓRIO: Cita o DL 166/2008, DL 239/2012 e os requisitos da Portaria 419/2012. 
                2. Se houver excesso de área ou impermeabilização, fundamenta como infração MUITO GRAVE por violação de interdição (não é uso compatível).
                3. Menciona a nulidade de atos administrativos que violem a REN.
                4. AUTO: Tipifica contraordenações e define coimas para gravidade {gravidade} e entidade {tipo_ent} (Lei 50/2006).
                5. Texto em PT-PT, Justificado, capítulos a BOLD.
                """
                try:
                    res = model.generate_content(prompt).text
                    docx = export_docx(res)
                    st.success("Documentação preparada!")
                    st.download_button("📥 Descarregar Word", docx, file_name=f"Fiscalizacao_{local}.docx")
                    st.write(res)
                except Exception as e: st.error(f"Erro: {e}")



