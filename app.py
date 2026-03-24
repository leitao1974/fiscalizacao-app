import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
import re
from pypdf import PdfReader

# --------------------------------------------------
# CONFIGURAÇÃO DA INTERFACE
# --------------------------------------------------

st.set_page_config(
    page_title="Fiscalização Pro: Matriz Legal Total",
    layout="wide",
    page_icon="🛡️"
)

if 'desc_detalhada' not in st.session_state:
    st.session_state['desc_detalhada'] = ""

st.markdown("""
<style>
.stCheckbox { margin-bottom: -15px; font-size: 13px; }
.stTabs [data-baseweb="tab"] { font-weight: bold; }
.stTextArea textarea { background-color: #f8f9fa; }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

st.sidebar.header("⚙️ Configuração")

api_key = st.sidebar.text_input("Google API Key", type="password")
modelo_selecionado = "gemini-1.5-pro"

if api_key:
    genai.configure(api_key=api_key)
    try:
        modelos = [
            m.name.replace('models/', '')
            for m in genai.list_models()
            if 'generateContent' in m.supported_generation_methods
        ]
        modelo_selecionado = st.sidebar.selectbox("Motor de IA Ativo", modelos)
    except:
        st.sidebar.error("Erro na API Key.")

# --------------------------------------------------
# MATRIZ LEGAL (RESUMIDA)
# --------------------------------------------------

QUADRO_LEGAL_REF = {
    "REN": [
        "DL 166/2008",
        "DL 124/2019",
        "DL 123/2024",
        "Portaria 419/2012"
    ],
    "RAN": [
        "DL 73/2009",
        "DL 199/2015",
        "Portaria 162/2011"
    ],
    "NATURA 2000": [
        "DL 140/99",
        "DL 49/2005"
    ],
    "ORDENAMENTO": [
        "DL 80/2015 (RJIGT)",
        "DL 555/99 (RJUE)"
    ],
    "CONTRAORDENAÇÕES": [
        "Lei 50/2006",
        "DL 87/2024"
    ]
}

# --------------------------------------------------
# MEDIDAS AMBIENTAIS
# --------------------------------------------------

medidas_minimizacao = [
    "Reposição da topografia original",
    "Replantação de espécies autóctones",
    "Remoção de entulhos",
    "Redução da impermeabilização",
    "Integração paisagística"
]

# --------------------------------------------------
# FUNÇÃO EXPORTAÇÃO WORD
# --------------------------------------------------

def export_docx(res_text):

    doc = Document()

    for s in doc.sections:
        s.top_margin = Cm(2.5)
        s.bottom_margin = Cm(2.5)
        s.left_margin = Cm(3)
        s.right_margin = Cm(2.5)

    for linha in res_text.replace('*','').replace('#','').split("\n"):

        linha = linha.strip()

        if not linha:
            continue

        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

        if re.match(r'^(\d+\.|OBJETIVO|ANÁLISE|FUNDAMENTAÇÃO|CONCLUSÃO)', linha.upper()):
            p.add_run(linha).bold = True
        else:
            p.add_run(linha)

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    return buffer

# --------------------------------------------------
# INTERFACE PRINCIPAL
# --------------------------------------------------

st.title("🛡️ Sistema de Fiscalização: Master Território e Ambiente")

tabs = st.tabs([
"📍 Identificação",
"💧 REN",
"🌿 Natura",
"🌾 RAN",
"🏛️ Património",
"🌊 Recursos Hídricos",
"🗺️ PDM"
])

# --------------------------------------------------
# TAB IDENTIFICAÇÃO
# --------------------------------------------------

with tabs[0]:

    col1,col2 = st.columns(2)

    with col1:

        local = st.text_input("Localização")

        lat = st.text_input("Latitude")
        lon = st.text_input("Longitude")

        area_m2 = st.number_input("Área Afetada (m2)", value=1000)

        fotos = st.file_uploader("Fotos", accept_multiple_files=True)

    with col2:

        inf_nome = st.text_input("Nome / Entidade")

        tipo_ent = st.radio("Tipo",["Pessoa Singular","Pessoa Coletiva"])

        upload_auto = st.file_uploader("Auto de Notícia PDF",type=['pdf'])

        st.session_state.desc_detalhada = st.text_area(
            "Observações",
            value=st.session_state.get('desc_detalhada',""),
            key="desc_input"
        )

# --------------------------------------------------
# TAB REN
# --------------------------------------------------

with tabs[1]:

    incide_ren = st.toggle("Área REN")

    sel_ren=[]
    sel_inter_ren=[]

# --------------------------------------------------
# TAB NATURA
# --------------------------------------------------

with tabs[2]:

    incide_natura = st.toggle("Rede Natura")

    sel_zec=[]
    sel_rnap=[]
    sel_art9=[]

# --------------------------------------------------
# TAB RAN
# --------------------------------------------------

with tabs[3]:

    incide_ran = st.toggle("Área RAN")

    sel_inter_ran=[]
    sel_util_ran=[]

# --------------------------------------------------
# TAB PATRIMÓNIO
# --------------------------------------------------

with tabs[4]:

    incide_patrimonio = st.toggle("Património")

# --------------------------------------------------
# TAB RECURSOS HÍDRICOS
# --------------------------------------------------

with tabs[5]:

    incide_rh = st.toggle("Recursos Hídricos")

# --------------------------------------------------
# TAB PDM
# --------------------------------------------------

with tabs[6]:

    incide_pdm = st.toggle("Violação PDM")

    sel_pdm = st.multiselect(
        "Categoria de solo",
        ["Solo Urbano","Solo Rústico","Espaço Natural"]
    )

    artigo_pdm = st.text_input("Artigo PDM")

    upload_pdm = st.file_uploader("Regulamento PDM", type=['pdf'])

    desc_pdm = st.text_area("Análise técnica")

# --------------------------------------------------
# FINALIZAÇÃO (FORA DOS TABS)
# --------------------------------------------------

st.divider()
st.subheader("🏁 Finalização e Auditoria Transversal")

st.subheader("🛠️ Medidas de Minimização")

sel_medidas=[i for i in medidas_minimizacao if st.checkbox(i)]

texto_adicional_medidas=st.text_area("Prescrições técnicas")

gravidade = st.select_slider(
"Gravidade",
options=["Leve","Grave","Muito Grave"]
)

r_crime = st.checkbox("Possível crime ambiental")

beneficio_economico = st.checkbox("Benefício económico")

reincidencia = st.checkbox("Reincidência")

col_reg1,col_reg2 = st.columns(2)

with col_reg1:

    if incide_ren:
        st.warning("Regime REN ativo")

    if incide_ran:
        st.warning("Regime RAN ativo")

with col_reg2:

    st.info("Graduação automática pela IA")

st.divider()

# --------------------------------------------------
# BOTÃO PRINCIPAL
# --------------------------------------------------

if st.button("🚀 Gerar Informação Técnica Fundamentada"):

    if not api_key:

        st.error("Falta API Key")

    else:

        with st.spinner("IA a realizar auditoria pericial e a prescrever medidas (2024-2026)..."):

            model = genai.GenerativeModel(modelo_selecionado)

            # Segurança

            v_ren = {
            'sel_ren': locals().get('sel_ren', []),
            'sel_inter_ren': locals().get('sel_inter_ren', [])
            }

            v_ran = {
            'sel_inter_ran': locals().get('sel_inter_ran', []),
            'sel_util_ran': locals().get('sel_util_ran', [])
            }

            v_natura = {
            'sel_zec': locals().get('sel_zec', []),
            'sel_rnap': locals().get('sel_rnap', []),
            'sel_art9': locals().get('sel_art9', [])
            }

            v_pdm = {
            'sel_pdm': locals().get('sel_pdm', []),
            'artigo_pdm': locals().get('artigo_pdm', ''),
            'desc_pdm': locals().get('desc_pdm', '')
            }

            # Leitura Auto

            texto_auto=""

            if upload_auto:

                try:

                    reader=PdfReader(upload_auto)

                    texto_auto="\n".join(
                    [p.extract_text() for p in reader.pages]
                    )

                except:

                    texto_auto="Erro leitura auto"

            # Leitura PDM

            texto_pdm_reg=""

            if upload_pdm:

                try:

                    reader=PdfReader(upload_pdm)

                    texto_pdm_reg="\n".join(
                    [p.extract_text() for p in reader.pages[:15]]
                    )

                except:

                    texto_pdm_reg="Erro leitura PDM"

            # Instruções

            instrucoes_periciais="""
            Determinar gravidade da infração.
            Prescrever medidas ambientais.
            Cruzar Auto com regulamentos.
            """

            legis_ref_text="\n".join(
            [f"- {c}: {', '.join(l)}"
            for c,l in QUADRO_LEGAL_REF.items()]
            )

            prompt=f"""

Age como Perito Técnico Sénior.

AUTO:
{texto_auto}

PDM:
{texto_pdm_reg}

DESCRIÇÃO:
{st.session_state.get('desc_input','')}

REN: {v_ren}
RAN: {v_ran}
PDM: {v_pdm}

QUADRO LEGAL
{legis_ref_text}

Estrutura:

1 OBJETIVO  
2 ANÁLISE TÉCNICA  
3 FUNDAMENTAÇÃO JURÍDICA  
4 MEDIDAS DE REPOSIÇÃO  
5 CONCLUSÃO
"""

            try:

                res=model.generate_content(prompt).text

                st.success("Relatório gerado")

                st.download_button(
                "Descarregar Word",
                export_docx(res),
                file_name=f"InfoTecnica_{local}.docx"
                )

                st.write(res)

            except Exception as e:

                st.error(e)
