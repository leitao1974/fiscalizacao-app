import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
import re
from pypdf import PdfReader

# 1. Configuração de Interface
st.set_page_config(page_title="Fiscalização Pro: Matriz de Infrações", layout="wide", page_icon="🛡️")

# Estilo CSS para melhor legibilidade das checkboxes
st.markdown("""
    <style>
    .stCheckbox { margin-bottom: -10px; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #f0f2f6; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR CONFIG (CHAVE DINÂMICA) ---
st.sidebar.header("⚙️ Painel de Controlo")
api_key = st.sidebar.text_input("Google API Key", type="password")
modelo_selecionado = "gemini-1.5-pro"

if api_key:
    genai.configure(api_key=api_key)
    try:
        modelos = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        modelo_selecionado = st.sidebar.selectbox("Motor de IA", modelos, index=0)
    except:
        st.sidebar.error("Erro na API Key.")

# --- DICIONÁRIO EXAUSTIVO DE INFRAÇÕES ---
inf_ran = ["Alteração do relevo técnico/morfologia do solo", "Utilização de solo RAN para fins não agrícolas", "Instalação de estaleiros/depósitos sem título", "Impermeabilização definitiva de solos RAN", "Remoção de terras de classe A/B"]
inf_ren = ["Aterros e escavações em áreas de proteção", "Destruição de coberto vegetal/desmatagem", "Interrupção de linhas de água/drenagem natural", "Impermeabilização em zonas de infiltração máxima", "Instalação de vias de comunicação sem parecer vinculativo"]
inf_conservacao = ["Destruição de habitats protegidos (Rede Natura 2000)", "Corte de Sobreiros/Azinheiras em povoamento", "Perturbação de fauna em período de nidificação", "Introdução de espécies exóticas invasoras", "Realização de ações interditas em Reserva Integral/Parcial"]
inf_residuos = ["Abandono/Deposição de RCD (Entulho)", "Mistura de resíduos perigosos com não perigosos", "Queima incontrolada de resíduos", "Falta de guias de acompanhamento (e-GAR)", "Operação de gestão de resíduos sem licenciamento"]
inf_agua = ["Ocupação do domínio hídrico (leito/margem)", "Captação de água sem título (furo/poço)", "Rejeição de águas residuais sem tratamento", "Obstrução ao livre curso das águas", "Extração ilícita de inertes (areias)"]
inf_patrimonio = ["Obras em Zona Geral de Proteção (50m) sem parecer", "Alteração de fachadas/volumetria em imóvel classificado", "Escavações em Sítio Arqueológico inventariado", "Danos estruturais em património de interesse público"]

# --- INTERFACE ---
st.title("🛡️ Sistema de Fiscalização: Matriz de Contraordenações")

tab1, tab2, tab3 = st.tabs(["📍 Ocorrência", "⚖️ Tipificação de Infrações", "📑 Fundamentação"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📍 Identificação do Local")
        local = st.text_input("Localização / Freguesia", "Alenquer")
        area = st.number_input("Área Afetada (m²)", value=1000.0)
        desc_livre = st.text_area("Notas de Campo", "Deteção visual de intervenção pesada com maquinaria.")
    with c2:
        st.subheader("👤 Identificação do Infrator")
        inf_nome = st.text_input("Nome/Entidade", "Desconhecido")
        inf_nif = st.text_input("NIF/NIPC", "000000000")
        inf_morada = st.text_input("Morada de Notificação", "N/A")

with tab2:
    st.subheader("⚠️ Seleção de Infrações por Regime Jurídico")
    col_a, col_b, col_c = st.columns(3)
    
    with col_a:
        st.info("**🌾 RAN & REN**")
        sel_ran = [i for i in inf_ran if st.checkbox(i, key=f"ran_{i}")]
        sel_ren = [i for i in inf_ren if st.checkbox(i, key=f"ren_{i}")]
        
    with col_b:
        st.success("**🌿 Conservação & Natureza**")
        sel_cons = [i for i in inf_conservacao if st.checkbox(i, key=f"cons_{i}")]
        st.warning("**🏛️ Património Cultural**")
        sel_pat = [i for i in inf_patrimonio if st.checkbox(i, key=f"pat_{i}")]

    with col_c:
        st.error("**🗑️ Resíduos & Água**")
        sel_res = [i for i in inf_residuos if st.checkbox(i, key=f"res_{i}")]
        sel_agua = [i for i in inf_agua if st.checkbox(i, key=f"agua_{i}")]

    st.divider()
    gravidade = st.select_slider("Gravidade Consolidada", options=["Leve", "Grave", "Muito Grave"])

with tab3:
    st.write("Análise documental e geração de documentos.")
    arquivo_pdf = st.file_uploader("Upload de Regulamento/POAP", type=['pdf'])
    pdf_text = ""
    if arquivo_pdf:
        reader = PdfReader(arquivo_pdf)
        pdf_text = "\n".join([p.extract_text() for p in reader.pages[:10]])
        st.success("Análise documental ativa.")

# --- GERAÇÃO DOCX ---
def export_docx(res_text):
    doc = Document()
    for s in doc.sections:
        s.top_margin, s.bottom_margin = Cm(2.5), Cm(2.5)
    
    res_text = res_text.replace('*', '').replace('#', '')
    for linha in res_text.split('\n'):
        if not linha.strip(): continue
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        if re.match(r'^(\d+\.|RELATÓRIO|AUTO|INFRAÇÃO|DADOS|FUNDAMENTAÇÃO)', linha.upper()):
            run = p.add_run(linha)
            run.bold = True
        else:
            p.add_run(linha)
    
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- BOTÃO DE AÇÃO ---
st.divider()
if st.button("🚀 Gerar Relatório e Auto Baseado na Matriz"):
    if not api_key:
        st.error("Insira a API Key na barra lateral.")
    else:
        with st.spinner("A cruzar matriz de infrações com legislação vigente..."):
            model = genai.GenerativeModel(modelo_selecionado)
            prompt = f"""
            Age como Fiscal Sénior e Jurista. Redigi Relatório e Proposta de Auto de Notícia.
            Língua: Português Formal (PT-PT). Texto Justificado.
            
            DADOS:
            Local: {local}. Área: {area}m2. Infrator: {inf_nome}, NIF: {inf_nif}, Morada: {inf_morada}.
            Notas: {desc_livre}
            
            INFRAÇÕES SELECIONADAS:
            - RAN: {sel_ran}
            - REN: {sel_ren}
            - Conservação/ZECs: {sel_cons}
            - Património: {sel_pat}
            - Resíduos: {sel_res}
            - Domínio Hídrico: {sel_agua}
            
            INSTRUÇÕES:
            1. No RELATÓRIO: Identifica o nexo de causalidade e cita os diplomas (DL 73/2009, DL 166/2008, DL 142/2008, Lei 107/2001, Lei 58/2005, DL 102-D/2020).
            2. No AUTO: Tipifica as contraordenações. Define coimas mín/máx para gravidade {gravidade} baseadas na Lei 50/2006 (Ambiental) e RGCO.
            3. Medidas Cautelares: Propõe embargo e reposição.
            """
            try:
                res = model.generate_content(prompt).text
                docx_file = export_docx(res)
                st.success("Documentação gerada com sucesso.")
                st.download_button("📥 Descarregar Word (.docx)", docx_file, file_name=f"Fiscalizacao_{local}.docx")
                with st.expander("Pré-visualização"):
                    st.write(res)
            except Exception as e:
                st.error(f"Erro: {e}")

