import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
import re
from pypdf import PdfReader

# 1. Configuração de Interface
st.set_page_config(page_title="Fiscalização Pro: Matriz Legal Integrada", layout="wide", page_icon="🛡️")

# Estilo CSS
st.markdown("""
    <style>
    .stCheckbox { margin-bottom: -8px; }
    .stTabs [data-baseweb="tab"] { font-weight: bold; }
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
        st.sidebar.error("Verifica a API Key.")

# --- DICIONÁRIO EXPANDIDO DE INFRAÇÕES ---
# Território e Solo
inf_ran = ["Alteração do relevo técnico/morfologia do solo (Aterros/Escavações)", "Utilização de solo RAN para fins não agrícolas", "Impermeabilização definitiva de solos protegidos", "Instalação de depósitos de materiais/RCDs"]
inf_ren = ["Intervenções em áreas de proteção de encostas", "Interrupção/alteração da drenagem natural", "Destruição de coberto vegetal em zonas de infiltração máxima", "Ocupação de zonas ameaçadas pelas cheias"]

# Conservação da Natureza e Rede Natura 2000 (DL 140/99 e DL 142/2008)
inf_natureza = [
    "Destruição/Deterioração de habitats naturais (Anexo B-I do DL 140/99)",
    "Perturbação de espécies da fauna (especialmente em época de reprodução)",
    "Colheita/Danos em espécies da flora protegidas",
    "Realização de projetos sem Avaliação de Incidências Ambientais (AIncA)",
    "Intervenções em áreas de Reserva Integral ou Parcial sem autorização",
    "Corte de Sobreiros ou Azinheiras (DL 169/2001)"
]

# Água e Resíduos
inf_agua_residuos = [
    "Ocupação do domínio hídrico (leito ou margem)",
    "Obstrução ao livre curso das águas ou danos em taludes",
    "Abandono/Deposição de Resíduos de Construção e Demolição (RCD)",
    "Rejeição de efluentes/águas residuais sem tratamento",
    "Captação de água (furos/poços) sem título de utilização"
]

# Património Cultural
inf_patrimonio = [
    "Obras/Intervenções em Zona Geral de Proteção (50m) sem parecer",
    "Danos em Monumentos ou Imóveis de Interesse Público",
    "Remoção de terras em Sítios Arqueológicos inventariados"
]

# --- INTERFACE ---
st.title("🛡️ Sistema de Fiscalização: Matriz de Contraordenações")

tab1, tab2, tab3 = st.tabs(["📍 Localização e Infrator", "⚖️ Seleção de Infrações", "📑 Geração de Documentos"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        local = st.text_input("Localização / Concelho", "Médio Tejo / Região Centro")
        area = st.number_input("Área Afetada (m²)", value=1000.0)
        desc_campo = st.text_area("Notas de Campo / Descrição Visual", "Deteção de intervenção pesada com maquinaria...")
    with c2:
        inf_nome = st.text_input("Nome/Entidade Infratora", "Desconhecido")
        inf_nif = st.text_input("NIF/NIPC", "000000000")
        inf_morada = st.text_input("Morada de Notificação", "N/A")

with tab2:
    st.subheader("⚠️ Seleção de Infrações por Regime Jurídico")
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.info("**🌾 Solo e Ordenamento (RAN/REN)**")
        sel_ran = [i for i in inf_ran if st.checkbox(i, key=f"ran_{i}")]
        sel_ren = [i for i in inf_ren if st.checkbox(i, key=f"ren_{i}")]
        
        st.error("**🗑️ Resíduos, Água e Domínio Hídrico**")
        sel_ar = [i for i in inf_agua_residuos if st.checkbox(i, key=f"ar_{i}")]
        
    with col_b:
        st.success("**🌿 Rede Natura 2000 e Natureza (DL 140/99 e 142/2008)**")
        sel_nat = [i for i in inf_natureza if st.checkbox(i, key=f"nat_{i}")]
        
        st.warning("**🏛️ Património Cultural (Lei 107/2001)**")
        sel_pat = [i for i in inf_patrimonio if st.checkbox(i, key=f"pat_{i}")]

    st.divider()
    gravidade = st.select_slider("Gravidade Consolidada", options=["Leve", "Grave", "Muito Grave"])

with tab3:
    arquivo_pdf = st.file_uploader("Upload de Regulamento/POAP (Opcional)", type=['pdf'])
    pdf_text = ""
    if arquivo_pdf:
        reader = PdfReader(arquivo_pdf)
        pdf_text = "\n".join([p.extract_text() for p in reader.pages[:10]])
        st.success("Análise documental ativa.")

# --- MOTOR DOCX ---
def export_docx(res_text):
    doc = Document()
    for s in doc.sections:
        s.top_margin, s.bottom_margin = Cm(2.5), Cm(2.5)
        s.left_margin, s.right_margin = Cm(3.0), Cm(2.5)
    
    res_text = res_text.replace('*', '').replace('#', '')
    for linha in res_text.split('\n'):
        linha = linha.strip()
        if not linha: continue
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        if re.match(r'^(\d+\.|RELATÓRIO|PROPOSTA|AUTO|INFRAÇÃO|DADOS|FUNDAMENTAÇÃO|CONCLUSÃO)', linha.upper()):
            run = p.add_run(linha)
            run.bold = True
            run.font.size = Pt(12)
        else:
            p.add_run(linha)
    
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- GERAÇÃO ---
st.divider()
if st.button("🚀 Gerar Relatório e Auto Baseado na Matriz Legal"):
    if not api_key:
        st.error("Insira a API Key na barra lateral.")
    else:
        with st.spinner("A fundir dados técnicos com o quadro contraordenacional..."):
            model = genai.GenerativeModel(modelo_selecionado)
            prompt = f"""
            Age como Fiscal Sénior e Jurista Especialista em Ambiente. Redigi um Relatório de Fiscalização e uma Proposta de Auto de Notícia profissionais.
            
            DADOS TÉCNICOS:
            - Local: {local}. Área: {area} m2.
            - Infrator: {inf_nome}, NIF: {inf_nif}, Morada: {inf_morada}.
            - Notas: {desc_campo}
            
            INFRAÇÕES SELECIONADAS:
            - RAN/REN: {sel_ran} e {sel_ren}
            - Conservação e Rede Natura 2000 (DL 140/99 e DL 142/2008): {sel_nat}
            - Recursos Hídricos e Resíduos: {sel_ar}
            - Património Cultural: {sel_pat}
            
            FUNDAMENTAÇÃO OBRIGATÓRIA:
            1. No RELATÓRIO: Explica o impacto ambiental. Para Rede Natura, cita especificamente o Decreto-Lei 140/99 na sua atual redação.
            2. No AUTO: Tipifica as infrações. Define coimas mín/máx para gravidade {gravidade} conforme a Lei 50/2006 (Quadro Ambiental) e regimes específicos.
            3. Medidas Cautelares: Propõe embargo e reposição imediata.
            """
            try:
                res = model.generate_content(prompt).text
                docx_file = export_docx(res)
                st.success("Análise concluída!")
                st.download_button("📥 Descarregar Word (.docx)", docx_file, file_name=f"Fiscalizacao_{local}.docx")
                with st.expander("Pré-visualização do Parecer"):
                    st.write(res)
            except Exception as e:
                st.error(f"Erro: {e}")

