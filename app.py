import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
import re
from pypdf import PdfReader

# 1. Configuração de Interface
st.set_page_config(page_title="Fiscalização Pro: Interdições e Condicionamentos", layout="wide", page_icon="🛡️")

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

# --- DICIONÁRIO DE INFRAÇÕES (INTERDIÇÕES VS CONDICIONADAS) ---

# RAN e REN
inf_territorio = [
    "[INTERDIÇÃO] Alteração definitiva de solo RAN para fins não agrícolas",
    "[INTERDIÇÃO] Construção em zonas de risco (cheias/arribas)",
    "[CONDICIONADA] Obras de construção/ampliação sem parecer prévio da CCDR (REN)",
    "[CONDICIONADA] Infraestruturas coletivas sem título de reconhecimento de interesse público (RAN)",
    "[CONDICIONADA] Abertura de caminhos ou acessos sem autorização (REN)"
]

# Rede Natura 2000 (DL 140/99) e Conservação
inf_natureza = [
    "[INTERDIÇÃO] Destruição de habitats de interesse comunitário (Anexo B-I)",
    "[INTERDIÇÃO] Abate de exemplares de espécies da flora protegida",
    "[CONDICIONADA] Realização de ações/projetos sem Avaliação de Incidências Ambientais (AIncA)",
    "[CONDICIONADA] Atividades turísticas ou eventos sem autorização do ICNF",
    "[CONDICIONADA] Alteração do uso do solo sem parecer Natura 2000"
]

# Água e Património
inf_outros = [
    "[INTERDIÇÃO] Descarga direta de efluentes no domínio hídrico",
    "[INTERDIÇÃO] Destruição ou alteração de património classificado",
    "[CONDICIONADA] Captação de águas ou furos sem Título de Utilização (APA)",
    "[CONDICIONADA] Obras em Zona de Proteção (50m) sem parecer da DGPC/Cultura",
    "[CONDICIONADA] Ocupação temporária de domínio hídrico sem licença"
]

# --- INTERFACE ---
st.title("🛡️ Matriz de Fiscalização: Interdições e Ações Condicionadas")

tab1, tab2, tab3 = st.tabs(["📍 Ocorrência", "⚖️ Tipificação Jurídica", "📑 Documentação"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        local = st.text_input("Localização", "Região Centro / Médio Tejo")
        area = st.number_input("Área (m²)", value=1000.0)
    with c2:
        infrator = st.text_input("Infrator", "Em averiguação")
        nif = st.text_input("NIF", "000000000")

with tab2:
    st.subheader("⚠️ Seleção de Infrações (Tipificadas por Regime)")
    st.caption("Nota: As ações condicionadas referem-se a atos realizados sem o prévio título obrigatório.")
    
    col_a, col_b, col_c = st.columns(3)
    
    with col_a:
        st.info("**🌾 Solo (RAN/REN)**")
        sel_territorio = [i for i in inf_territorio if st.checkbox(i)]
        
    with col_b:
        st.success("**🌿 Natureza (DL 140/99)**")
        sel_natureza = [i for i in inf_natureza if st.checkbox(i)]

    with col_c:
        st.warning("**🏛️ Outros Regimes**")
        sel_outros = [i for i in inf_outros if st.checkbox(i)]

    st.divider()
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
        if re.match(r'^(\d+\.|RELATÓRIO|AUTO|INFRAÇÃO|DADOS|FUNDAMENTAÇÃO)', linha.upper()):
            p.add_run(linha).bold = True
        else:
            p.add_run(linha)
    
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# --- GERAÇÃO ---
if st.button("🚀 Gerar Auto de Notícia Integrado"):
    if not api_key:
        st.error("Insira a API Key.")
    else:
        with st.spinner("A analisar interdições e falta de títulos..."):
            model = genai.GenerativeModel(modelo_selecionado)
            prompt = f"""
            Age como Fiscal Sénior e Jurista. Redigi Relatório e Auto de Notícia.
            Dados: Local {local}, Área {area}m2, Infrator {infrator} (NIF {nif}).
            
            Infrações selecionadas:
            - Solo: {sel_territorio}
            - Natureza (DL 140/99): {sel_natureza}
            - Outros: {sel_outros}
            
            Instruções:
            1. No Relatório, distingue claramente o que é Interdição (proibido) do que é Ação Condicionada realizada sem título (falta de autorização).
            2. Cita o DL 140/99 na redação atual para a Rede Natura 2000.
            3. No Auto, tipifica a contraordenação e indica as coimas para gravidade {gravidade} (Lei 50/2006).
            """
            try:
                res = model.generate_content(prompt).text
                docx = export_docx(res)
                st.success("Documentação gerada!")
                st.download_button("📥 Descarregar Word", docx, file_name=f"Fiscalizacao_{local}.docx")
                st.write(res)
            except Exception as e:
                st.error(f"Erro: {e}")

