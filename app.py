import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
from datetime import date
import re
from pypdf import PdfReader

# 1. Configuração de Interface
st.set_page_config(page_title="Fiscalização Pro: Zonamento e Território", layout="wide", page_icon="🛡️")

# Estilo CSS Profissional
st.markdown("""
    <style>
    .main { background-color: #f4f7f6; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { background-color: #e8f5e9; border-radius: 4px; padding: 10px 20px; font-weight: bold; }
    .stTabs [aria-selected="true"] { background-color: #1b5e20 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR CONFIG (CHAVE DINÂMICA) ---
st.sidebar.header("⚙️ Painel de Controlo")
api_key = st.sidebar.text_input("Google API Key", type="password")

modelo_selecionado = "gemini-1.5-pro"
if api_key:
    genai.configure(api_key=api_key)
    try:
        modelos_disponiveis = [m.name.replace('models/', '') for m in genai.list_models() 
                               if 'generateContent' in m.supported_generation_methods]
        modelo_selecionado = st.sidebar.selectbox("Motor de IA Ativo", modelos_disponiveis, index=0)
    except:
        st.sidebar.error("Erro ao listar modelos.")

# --- DICIONÁRIOS DE TIPOLOGIAS E ZONAMENTOS ---
tipologias_ren_completa = [
    "Áreas de Proteção de Encostas", "Áreas de Infiltração Máxima", "Zonas Adjacentes",
    "Cursos de Água e respetivas faixas de proteção", "Cabeceiras de linhas de água",
    "Albufeiras e respetivas faixas de proteção", "Zonas Ameaçadas pelas Cheias",
    "Zonas Ameaçadas pelo Mar", "Arribas e respetivas faixas de proteção"
]

zec_zpe_centro_expandida = [
    "ZEC Serra de Aire e Candeeiros", "ZEC Serra da Estrela", "ZEC Sicó/Alvaiázere", 
    "ZEC Paul de Arzila", "ZEC Serra da Lousã", "ZEC Malcata", "ZEC Rio Zêzere",
    "ZEC Albufeira de Castelo do Bode", "ZPE Paul do Boquilobo", "ZPE Estuário do Mondego", 
    "ZPE Ria de Aveiro", "ZPE Douro Internacional"
]

áreas_protegidas_expandida = [
    "Parque Natural do Douro Internacional (PNDI)",
    "Parque Natural da Serra da Estrela (PNSE)",
    "Parque Natural das Serras de Aire e Candeeiros (PNSAC)",
    "Parque Natural do Tejo Internacional (PNTI)",
    "Reserva Natural do Paul de Arzila",
    "Reserva Natural da Serra da Malcata",
    "Reserva Natural do Paul do Boquilobo"
]

# Zonamentos típicos dos Planos de Ordenamento (POAP)
zonamentos_rnap = [
    "Reserva Integral",
    "Reserva Parcial",
    "Zona de Proteção Parcial de Tipo I",
    "Zona de Proteção Parcial de Tipo II",
    "Zona de Proteção Complementar de Tipo I",
    "Zona de Proteção Complementar de Tipo II",
    "Áreas de Intervenção Específica",
    "Áreas de Recreio e Lazer"
]

# --- INTERFACE ---
st.title("🛡️ Sistema de Apoio à Fiscalização: Zonamento RNAP")
st.markdown("Análise multidisciplinar: **Zonamentos POAP, REN, RAN e Rede Natura 2000**.")

tab1, tab2, tab3 = st.tabs(["📍 Ocorrência", "⚖️ Enquadramento Legal", "📑 Análise Documental"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        local = st.text_input("Concelho / Localidade", "Tomar / Alenquer / Manteigas")
        area = st.number_input("Área Afetada (m²)", value=15591.67, format="%.2f")
    with col2:
        ocupacao = st.text_area("Descrição da Ação Detetada", "Execução de aterro, remoção de vegetação e alteração da morfologia do solo.")

with tab2:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🌾 Regimes Territoriais")
        r_ran = st.checkbox("RAN (DL 73/2009)")
        r_ren = st.checkbox("REN (DL 166/2008)")
        t_ren = st.multiselect("Tipologias REN:", tipologias_ren_completa) if r_ren else []
    
    with c2:
        st.subheader("🌿 Conservação da Natureza")
        r_ap = st.checkbox("Áreas Protegidas (RNAP - DL 142/2008)")
        t_ap = st.multiselect("Parques e Reservas Selecionados:", áreas_protegidas_expandida) if r_ap else []
        
        # Checkbox dinâmica para Zonamentos
        t_zonas = st.multiselect("Zonamentos do Plano de Ordenamento (POAP):", zonamentos_rnap) if r_ap else []
        
        r_rn2000 = st.checkbox("Rede Natura 2000 (ZEC/ZPE)")
        t_rn2000 = st.multiselect("Sítios ZEC/ZPE:", zec_zpe_centro_expandida) if r_rn2000 else []
        
        st.divider()
        gravidade = st.select_slider("Gravidade Proposta", options=["Leve", "Grave", "Muito Grave"])

conteudo_poap = ""
with tab3:
    st.write("Carregue o Regulamento específico (PDF) para citações automáticas de artigos.")
    arquivo_poap = st.file_uploader("Upload PDF (POAP/PDM)", type=['pdf'])
    if arquivo_poap:
        reader = PdfReader(arquivo_poap)
        conteudo_poap = "\n".join([page.extract_text() for page in reader.pages[:15]])
        st.success("Documento carregado e pronto para análise.")

# --- MOTOR DOCX ---
def gerar_docx_final(texto_ia):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)

    for section in doc.sections:
        section.top_margin, section.bottom_margin = Cm(2.5), Cm(2.5)
        section.left_margin, section.right_margin = Cm(3.0), Cm(2.5)

    texto_formatado = texto_ia.replace('*', '').replace('#', '')
    for linha in texto_formatado.split('\n'):
        linha = linha.strip()
        if not linha: continue
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        
        if re.match(r'^(\d+\.|RELATÓRIO|PROPOSTA|AUTO|FUNDAMENTAÇÃO|CONCLUSÃO)', linha.upper()):
            run = p.add_run(linha)
            run.bold = True
            run.font.size = Pt(12)
        elif re.match(r'^\d+\.\d+\.', linha):
            run = p.add_run(linha)
            run.bold = True
        else:
            p.add_run(linha)

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- GERAÇÃO ---
st.divider()
if st.button("🚀 Gerar Relatório e Auto com Zonamento"):
    if not api_key:
        st.error("Introduza a Google API Key na barra lateral.")
    else:
        with st.spinner(f"A analisar o zonamento e regimes legais com {modelo_selecionado}..."):
            model = genai.GenerativeModel(modelo_selecionado)
            
            prompt = f"""
            Age como Fiscal do Território e Jurista Sénior. 
            Redigi um RELATÓRIO DE FISCALIZAÇÃO e uma PROPOSTA DE AUTO DE NOTÍCIA profissionais.
            
            DADOS DA OCORRÊNCIA:
            - Local: {local}. Área: {area} m2. Ocupação: {ocupacao}.
            - Enquadramento: RAN={r_ran}, REN={t_ren}, ZEC/ZPE={t_rn2000}, Área Protegida={t_ap}.
            - ZONAMENTO ESPECÍFICO (POAP): {t_zonas}.
            - Conteúdo do Regulamento Carregado: {conteudo_poap[:2500]}
            
            DIRETRIZES TÉCNICAS:
            - No RELATÓRIO, foca na incompatibilidade da ação com o zonamento {t_zonas}.
            - Explica que em Zonas de Proteção Parcial ou Reservas, a alteração da morfologia do solo é interdita pelo regime do DL 142/2008 e pelos POAP.
            - No AUTO, define as coimas baseadas na gravidade {gravidade} e na Lei 50/2006.
            - Usa PORTUGUÊS FORMAL COM ACENTOS. Texto JUSTIFICADO. Capítulos a BOLD.
            """
            
            try:
                res = model.generate_content(prompt).text
                docx_file = gerar_docx_final(res)
                st.success("Análise de zonamento concluída!")
                st.download_button("📥 Descarregar Word (.docx)", docx_file, 
                                   file_name=f"Fiscalizacao_{local.replace(' ', '_')}.docx")
                with st.expander("Ver rascunho"):
                    st.write(res.replace('*', ''))
            except Exception as e:
                st.error(f"Erro: {e}")
