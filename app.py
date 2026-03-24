import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
import re
from pypdf import PdfReader

# 1. Configuração de Interface
st.set_page_config(page_title="Fiscalização Pro: Matriz Legal Total", layout="wide", page_icon="🛡️")

# Inicialização segura do Session State
if 'desc_detalhada' not in st.session_state:
    st.session_state['desc_detalhada'] = ""

def update_desc():
    st.session_state.desc_detalhada = st.session_state.desc_input

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
    try:
        modelos = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        modelo_selecionado = st.sidebar.selectbox("Motor de IA Ativo", modelos, index=0)
    except:
        st.sidebar.error("Erro na API Key.")

# --- 📚 MATRIZ LEGISLATIVA CONSOLIDADA (2024-2026) ---
QUADRO_LEGAL_REF = {
    "REN": [
        "Decreto-Lei n.º 166/2008, de 22 de Agosto (Regime Jurídico da REN)",
        "Decreto-Lei n.º 239/2012, de 2 de novembro (1.ª alteração)",
        "Decreto-Lei n.º 124/2019, de 28 de agosto (Alteração e Republicação)",
        "Decreto-Lei n.º 124/2019 com alterações do DL n.º 123/2024, de 31 de Dezembro (Vigente)",
        "Portaria n.º 419/2012, de 20 de dezembro (Condições e Requisitos Técnicos)"
    ],
    "RAN": [
        "Decreto-Lei n.º 73/2009, de 31 de Março (Regime Jurídico da RAN)",
        "Decreto-Lei n.º 199/2015, de 16 de setembro (Alteração)",
        "Portaria n.º 162/2011, de 18 de Abril (Utilizações não agrícolas)"
    ],
    "NATURA 2000": [
        "Decreto-Lei n.º 140/99, de 24 de Abril (Regime Jurídico)",
        "Decreto-Lei n.º 49/2005 de 24 de Fevereiro (Alteração)",
        "Decreto-Lei n.º 169/2001, de 25 de maio (Redação atual)"
    ],
    "ORDENAMENTO": [
        "Decreto-Lei n.º 80/2015 (RJIGT)",
        "Decreto-Lei n.º 555/99 (RJUE)"
    ],
    "CONTRAORDENAÇÕES": [
        "Lei n.º 50/2006, de 29 de agosto (LQCA)",
        "Alterações: Lei 89/2009, 114/2015, DL 42-A/2016, Lei 25/2019 e DL 87/2024 (Vigente)"
    ]
}

# --- BASES DE DADOS DE TIPOLOGIAS ---
ren_litoral_dict = {
    "Faixa marítima de proteção costeira": "Linha do leito até batimétrica dos 30m",
    "Praias": "Acumulação de sedimentos (areia/cascalho)",
    "Barreiras detríticas": "Restingas, barreiras soldadas e ilhas-barreira",
    "Tômbolos": "Sedimentos que ligam ilha ao continente",
    "Sapais": "Zonas intertidais com vegetação halofítica",
    "Arribas e faixas de proteção": "Vertentes abruptas e áreas adjacentes",
    "Dunas costeiras e dunas fósseis": "Acumulações eólicas de areia"
}

ren_hidro_dict = {
    "Cursos de água, leitos e margens": "Terreno coberto pelas águas e faixas confinantes",
    "Lagoas e lagos": "Meios hídricos lênticos e faixas de proteção",
    "Áreas estratégicas de proteção e recarga de aquíferos": "Zonas de infiltração máxima"
}

ren_riscos_dict = {
    "Zonas ameaçadas pelo mar": "Inundações por galgamento oceânico",
    "Zonas ameaçadas pelas cheias": "Suscetíveis a transbordo de cursos de água",
    "Áreas de elevado risco de erosão hídrica": "Declive e solo propícios a perda de terra",
    "Áreas de instabilidade de vertentes": "Movimentos de massa/deslizamentos"
}

ren_interdicoes_gerais = [
    "🏗️ Operações de loteamento",
    "🧱 Obras de urbanização, construção e ampliação",
    "🛣️ Vias de comunicação e acessos",
    "🚜 Escavações e aterros (alteração da morfologia do solo)",
    "🪓 Destruição do revestimento vegetal",
    "🌊 Alteração da rede de drenagem natural"
]

ran_interdicoes_dict = {
    "a) Operações de loteamento e obras de urbanização/construção": "Art. 21.º DL 73/2009",
    "b) Lançamento ou depósito de resíduos/produtos contaminantes": "Art. 21.º DL 73/2009",
    "d) Intervenções que provoquem degradação do solo/erosão": "Art. 21.º DL 73/2009",
    "f) Deposição de entulhos ou sucatas": "Art. 21.º DL 73/2009"
}

# --- INTERFACE ---
st.title("🛡️ Sistema de Fiscalização: Master Território e Ambiente")

tabs = st.tabs(["📍 Identificação", "💧 REN", "🌿 Natura", "🌾 RAN", "🏛️ Património", "🌊 Recursos Hídricos", "🗺️ PDM"])

with tabs[0]:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📍 Localização e GPS")
        local = st.text_input("Localização/Concelho", "Região Centro")
        col_gps1, col_gps2 = st.columns(2)
        lat = col_gps1.text_input("Latitude", placeholder="39.xxxx")
        lon = col_gps2.text_input("Longitude", placeholder="-8.xxxx")
        area_m2 = st.number_input("Área Afetada (m²)", value=1000.0)
    with c2:
        st.subheader("👤 Dados do Infrator e Documentação")
        inf_nome = st.text_input("Nome/Entidade")
        tipo_ent = st.radio("Tipo", ["Pessoa Singular", "Pessoa Coletiva"], horizontal=True)
        upload_auto = st.file_uploader("📄 Carregar Auto de Notícia (PDF)", type=['pdf'], key="auto_noticia_pdf")
        
        st.session_state.desc_detalhada = st.text_area(
            "📝 Observações Adicionais", 
            value=st.session_state.get('desc_detalhada', ""),
            placeholder="Factos complementares não constantes no Auto...",
            key="desc_input"
        )

with tabs[1]:
    incide_ren = st.toggle("🚨 A infração localiza-se em área de REN?", key="switch_ren")
    if incide_ren:
        st.info("**Regime Jurídico da REN:** DL 166/2008, redação atualizada pelo **DL 123/2024**.")
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("1. Tipologias da REN")
            with st.expander("🌊 Litoral"):
                sel_litoral = st.multiselect("Subtipologias:", list(ren_litoral_dict.keys()), key="ren_litoral")
            with st.expander("💧 Hidrologia"):
                sel_hidro = st.multiselect("Subtipologias:", list(ren_hidro_dict.keys()), key="ren_hidro")
            with st.expander("⚠️ Riscos"):
                sel_riscos = st.multiselect("Subtipologias:", list(ren_riscos_dict.keys()), key="ren_riscos")
            sel_ren = sel_litoral + sel_hidro + sel_riscos
        with c2:
            st.subheader("2. Interdições Observadas (Art. 20.º)")
            sel_inter_ren = [i for i in ren_interdicoes_gerais if st.checkbox(i, key=f"int_ren_{i}")]
            st.caption("ℹ️ Auditoria técnica (Portaria 419/2012) realizada automaticamente pela IA.")

with tabs[2]:
    incide_natura = st.toggle("🌿 A infração localiza-se em Rede Natura 2000 / AP?", key="switch_natura")
    if incide_natura:
        col1, col2 = st.columns(2)
        with col1:
            sel_zec = st.multiselect("Sítios ZEC/ZPE:", zec_zpe_lista)
            sel_rnap = st.multiselect("Áreas Protegidas (RNAP):", rnap_lista)
        with col2:
            sel_art9 = [i for i in condicionantes_art9 if st.checkbox(i, key=f"art9_{i}")]

with tabs[3]:
    incide_ran = st.toggle("🌾 A infração localiza-se em área de RAN?", key="switch_ran")
    if incide_ran:
        st.info("**Regime RAN:** DL 73/2009 e republicação pelo DL 199/2015.")
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("1. Ações Interditas (Art. 21.º)")
            sel_inter_ran = [k for k in ran_interdicoes_dict.keys() if st.checkbox(k, key=f'ran_int_{k[:5]}')]
        with c2:
            st.subheader("2. Pretensão (Art. 22.º)")
            sel_util_ran = st.multiselect("Enquadramento:", list(ran_utilizacoes_permitidas.keys()), key="util_ran_sel")
            st.caption("ℹ️ Verificação de limites (Portaria 162/2011) realizada automaticamente pela IA.")

with tabs[6]:
    incide_pdm = st.toggle("🗺️ A infração viola o PDM / Urbanismo?", key="switch_pdm")
    if incide_pdm:
        col1, col2 = st.columns(2)
        with col1:
            sel_pdm = st.multiselect("Categoria de solo:", pdm_classes_solo)
            artigo_pdm = st.text_input("Artigo(s) do Regulamento:")
        with col2:
            upload_pdm = st.file_uploader("📂 Regulamento PDM (PDF)", type=['pdf'], key="pdm_reg_upload")
        desc_pdm = st.text_area("📝 Análise Técnica PDM", height=100)

# --- FINALIZAÇÃO E GERAÇÃO ---
st.divider()
st.subheader("🏁 Auditoria e Geração Final")

if st.button("🚀 Gerar Informação Técnica Fundamentada"):
    if not api_key:
        st.error("Falta a API Key.")
    else:
        with st.spinner("IA a realizar auditoria pericial transversal (2024-2026)..."):
            model = genai.GenerativeModel(modelo_selecionado)
            
            # Inicialização segura de variáveis
            v_ren = {'sel_ren': locals().get('sel_ren', []), 'sel_inter_ren': locals().get('sel_inter_ren', [])}
            v_ran = {'sel_inter_ran': locals().get('sel_inter_ran', []), 'sel_util_ran': locals().get('sel_util_ran', [])}
            v_natura = {'sel_zec': locals().get('sel_zec', []), 'sel_rnap': locals().get('sel_rnap', []), 'sel_art9': locals().get('sel_art9', [])}
            v_pdm = {'sel_pdm': locals().get('sel_pdm', []), 'artigo_pdm': locals().get('artigo_pdm', ''), 'desc_pdm': locals().get('desc_pdm', '')}

            # Extração de PDFs
            t_auto = ""
            if 'auto_noticia_pdf' in st.session_state and st.session_state.auto_noticia_pdf:
                try: t_auto = "\n".join([p.extract_text() for p in PdfReader(st.session_state.auto_noticia_pdf).pages])
                except: t_auto = "Erro na leitura do Auto."

            t_pdm = ""
            if 'pdm_reg_upload' in st.session_state and st.session_state.pdm_reg_upload:
                try: t_pdm = "\n".join([p.extract_text() for p in PdfReader(st.session_state.pdm_reg_upload).pages[:15]])
                except: t_pdm = "Erro na leitura do PDM."

            legis_ref = "\n".join([f"- {c}: {', '.join(l)}" for c, l in QUADRO_LEGAL_REF.items()])

            prompt = f"""
            Age como Perito Técnico Sénior e Jurista especializado em Ordenamento e Ambiente.
            O teu objetivo é redigir uma INFORMAÇÃO TÉCNICA FUNDAMENTADA integral.

            INSTRUÇÕES PERICIAIS:
            1. AUDITORIA: Cruza o Auto de Notícia ({t_auto}) e o Regulamento PDM ({t_pdm}) com a legislação vigente.
            2. REN: Determina o regime de controlo e verifica a conformidade com a Portaria 419/2012 (permeabilidade/solo) de forma autónoma.
            3. RAN: Analisa áreas métricas e verifica limites da Portaria 162/2011 (habitação 300m2, etc) autonomamente.
            4. SANCIONATÓRIO: Determina a GRAVIDADE (Leve/Grave/M.Grave) e prescreve MEDIDAS DE MINIMIZAÇÃO/REPOSIÇÃO específicas (Lei 50/2006 atualizada pelo DL 87/2024).

            MATRIZ DO CASO:
            - Local: {local} | Área: {area_m2}m2
            - Descrição Manual: {st.session_state.get('desc_input', '')}
            - Servidões: REN({v_ren['sel_ren']}), RAN({v_ran['sel_inter_ran']}), PDM({v_pdm['sel_pdm']})
            
            QUADRO LEGAL: {legis_ref}

            ESTRUTURA: **OBJETIVO**, **AUDITORIA TÉCNICA TRANSVERSAL**, **FUNDAMENTAÇÃO JURÍDICA E GRADUAÇÃO DA INFRAÇÃO**, **PRESCRIÇÃO DE MEDIDAS E CONCLUSÃO**.
            Linguagem: Formal, PT-PT.
            """
            
            try:
                def export_docx(text):
                    doc = Document()
                    for line in text.replace('#', '').split('\n'):
                        if not line.strip(): continue
                        p = doc.add_paragraph()
                        if re.match(r'^(\d+\.|OBJETIVO|AUDITORIA|FUNDAMENTAÇÃO|PRESCRIÇÃO|CONCLUSÃO)', line.upper()):
                            p.add_run(line).bold = True
                        else: p.add_run(line)
                    b = BytesIO(); doc.save(b); b.seek(0); return b

                res = model.generate_content(prompt).text
                st.success("Relatório Pericial gerado com auditoria total!")
                st.download_button("📥 Baixar Word", export_docx(res), file_name=f"Relatorio_{local}.docx")
                st.markdown(res)
            except Exception as e:
                st.error(f"Erro na geração: {e}")
