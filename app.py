import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
import re
from pypdf import PdfReader

# 1. Configuração de Interface
st.set_page_config(page_title="Fiscalização Pro: DL 140/99 Art. 9.º", layout="wide", page_icon="🛡️")

# Estilo para leitura técnica
st.markdown("<style>.stCheckbox { margin-bottom: -15px; }</style>", unsafe_allow_html=True)

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

# --- MATRIZ DE CONDICIONANTES DL 140/99 (ARTIGO 9.º) ---
condicionantes_140_99 = [
    "a) Obras de construção civil fora de perímetros urbanos (excedendo limites de ampliação/área)",
    "b) Alteração do uso atual do solo > 5 ha",
    "c) Modificações de coberto vegetal (agrícola/florestal) > 5 ha (ou continuidade < 500m)",
    "d) Alterações à morfologia do solo (extra atividades normais agrícolas/florestais)",
    "e) Alteração do uso, configuração ou topografia de zonas húmidas ou marinhas",
    "f) Deposição de sucatas e de resíduos sólidos e líquidos",
    "g) Abertura de novas vias de comunicação ou alargamento das existentes",
    "h) Instalação de infraestruturas (energia, telecomunicações, saneamento, gás) fora de perímetros urbanos",
    "i) Atividades motorizadas organizadas e competições desportivas fora de perímetros urbanos",
    "j) Prática de alpinismo, escalada e montanhismo",
    "l) Reintrodução de espécies indígenas da fauna e da flora selvagens"
]

# --- INTERFACE ---
st.title("🛡️ Fiscalização: Incidências do Artigo 9.º - DL 140/99")

tab1, tab2, tab3 = st.tabs(["📍 Ocorrência", "⚖️ Condicionantes Art. 9.º", "📑 Gerar Auto"])

with tab1:
    col_a, col_b = st.columns(2)
    with col_a:
        local = st.text_input("Localização (ZEC/ZPE)", "Médio Tejo / Região Centro")
        area_afetada = st.number_input("Área da Ocorrência (m²)", value=15591.67)
    with col_b:
        infrator = st.text_input("Identificação do Infrator", "Nome/NIF")
        notas = st.text_area("Notas de Campo", "Deteção de intervenção sem sinalética de licenciamento...")

with tab2:
    st.subheader("⚠️ Ações Condicionadas (Sujeitas a Parecer do ICNF)")
    st.info("Selecione as ações realizadas sem o prévio título de autorização ou parecer favorável:")
    
    # Dividir em duas colunas para melhor leitura
    m1, m2 = st.columns(2)
    meio = len(condicionantes_140_99) // 2 + 1
    
    with m1:
        sel_a_f = [i for i in condicionantes_140_99[:6] if st.checkbox(i)]
    with m2:
        sel_g_l = [i for i in condicionantes_140_99[6:] if st.checkbox(i)]
    
    selecao_final = sel_a_f + sel_g_l

    st.divider()
    gravidade = st.select_slider("Gravidade Proposta (Lei 50/2006)", options=["Leve", "Grave", "Muito Grave"])

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

# --- GERAÇÃO ---
if st.button("🚀 Gerar Auto de Notícia (Rede Natura 2000)"):
    if not api_key:
        st.error("Insira a API Key.")
    else:
        with st.spinner("A fundamentar a violação do Artigo 9.º do DL 140/99..."):
            model = genai.GenerativeModel(modelo_selecionado)
            prompt = f"""
            Age como Fiscal Sénior e Jurista Especialista em Conservação da Natureza.
            Redigi um Relatório de Fiscalização e uma Proposta de Auto de Notícia.
            
            DADOS:
            Local: {local}. Área: {area_afetada} m2. Infrator: {infrator}.
            Ações Detetadas (DL 140/99, Art. 9.º): {selecao_final}
            
            FUNDAMENTAÇÃO JURÍDICA:
            1. No RELATÓRIO: Explica que as ações selecionadas carecem obrigatoriamente de parecer favorável ou autorização do ICNF, I. P., conforme o Artigo 9.º do Decreto-Lei n.º 140/99 na sua redação atual.
            2. Analisa o impacto da ação '{selecao_final}' na integridade da Zona Especial de Conservação ou Zona de Proteção Especial.
            3. No AUTO: Tipifica a contraordenação ambiental. Indica coimas para gravidade {gravidade} (Lei 50/2006).
            
            ESTILO: Português Formal, Justificado, Capítulos a BOLD, sem asteriscos.
            """
            try:
                res = model.generate_content(prompt).text
                docx = export_docx(res)
                st.success("Documentação pronta!")
                st.download_button("📥 Descarregar Word", docx, file_name=f"Auto_Natura2000_{local}.docx")
                st.write(res)
            except Exception as e:
                st.error(f"Erro: {e}")
