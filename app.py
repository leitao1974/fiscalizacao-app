import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
from datetime import date
import re

# 1. Configuração da Página
st.set_page_config(page_title="Fiscalização Pro - Região Centro", layout="wide", page_icon="🛡️")

# Estilo CSS para interface limpa
st.markdown("""
    <style>
    .main { background-color: #fcfcfc; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #f0f2f6; border-radius: 5px; padding: 8px 16px; }
    .stTabs [aria-selected="true"] { background-color: #2e7d32 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- CONFIGURAÇÃO IA ---
st.sidebar.header("⚙️ Configuração")
api_key = st.sidebar.text_input("Google API Key", type="password")

modelo_nome = "gemini-1.5-flash"
if api_key:
    genai.configure(api_key=api_key)
    try:
        models = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        modelo_nome = st.sidebar.selectbox("Modelo", models)
    except:
        st.sidebar.error("Chave API inválida.")

# --- LISTAS DE REDE NATURA 2000 - REGIÃO CENTRO (COMPLETA) ---
# Divididas por ZEC (Habitats) e ZPE (Aves)
áreas_rn2000 = [
    "ZEC - Serra de Aire e Candeeiros",
    "ZEC - Serra da Estrela",
    "ZEC - Sicó/Alvaiázere",
    "ZEC - Paul de Arzila",
    "ZEC - Dunas de Mira, Gândara e Gafanhas",
    "ZEC - Serra da Lousã",
    "ZEC - Arquipélago das Berlengas",
    "ZEC - Peniche/Santa Cruz",
    "ZEC - Sintra/Cascais (Extensão Norte)",
    "ZEC - Rio Vouga",
    "ZEC - Rio Paiva",
    "ZEC - Serra do Açor",
    "ZEC - Serra de Alvelos",
    "ZEC - Gardunha",
    "ZEC - Malcata",
    "ZEC - São Mamede (Norte)",
    "ZPE - Estuário do Mondego",
    "ZPE - Paul de Taipal",
    "ZPE - Paul de Arzila",
    "ZPE - Ria de Aveiro",
    "ZPE - Serra da Estrela",
    "ZPE - Serra de Aire e Candeeiros",
    "ZPE - Ilhas Berlengas"
]

tipos_ren = ["Estrutura de Proteção de Encostas", "Áreas de Infiltração Máxima", "Zonas Adjacentes", "Cabeceiras de Linhas de Água", "Zonas Ameaçadas pelas Cheias"]

# --- INTERFACE ---
st.title("🛡️ Apoio à Fiscalização Territorial")
st.info("Emissão de Relatório e Auto de Notícia para a Região Centro")

tab1, tab2 = st.tabs(["📍 Localização e Factos", "⚖️ Enquadramento Legal"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        local = st.text_input("Concelho / Localidade", "Alenquer")
        area = st.number_input("Área Afetada (m²)", value=15591.67)
    with col2:
        ocupacao = st.text_area("Ocupação / Ação Detetada", "Aterro de materiais inertes com alteração da morfologia do solo.")

with tab2:
    col3, col4 = st.columns(2)
    with col3:
        st.write("**Servidões e Restrições:**")
        r_ran = st.checkbox("RAN (DL 73/2009)")
        r_ren = st.checkbox("REN (DL 166/2008)")
        r_rn2000 = st.checkbox("Rede Natura 2000 (ZEC/ZPE)")
        
        t_ren = st.multiselect("Tipologias REN:", tipos_ren) if r_ren else []
    with col4:
        t_rn2000 = st.multiselect("Áreas Rede Natura 2000 (Centro):", áreas_rn2000) if r_rn2000 else []
        st.write("**Gravidade e Infrator:**")
        infrator = st.text_input("Identificação do Infrator", "Em averiguação")
        gravidade = st.select_slider("Gravidade Proposta", options=["Leve", "Grave", "Muito Grave"])

# --- MOTOR DE FORMATAÇÃO DOCX ---
def gerar_docx_oficial(texto_ia):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)

    for section in doc.sections:
        section.top_margin, section.bottom_margin = Cm(2.5), Cm(2.5)
        section.left_margin, section.right_margin = Cm(3.0), Cm(2.5)

    linhas = texto_ia.replace('*', '').replace('#', '').split('\n')

    for linha in linhas:
        linha = linha.strip()
        if not linha: continue
            
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        
        # Detetar Capítulos e Subcapítulos para Bold
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
st.markdown("---")
if st.button("🚀 Gerar Documentação Final (.docx)"):
    if not api_key:
        st.error("Insere a Google API Key.")
    else:
        with st.spinner("A IA está a cruzar a legislação da Região Centro..."):
            model = genai.GenerativeModel(modelo_nome)
            prompt = f"""
            Age como Fiscal e Jurista Especialista em Ordenamento do Territorio.
            Escreve um documento formal com acentos e justificacao.
            
            ESTRUTURA:
            1. RELATORIO DE FISCALIZACAO
            1.1. Objeto e Localizacao ({local})
            1.2. Factos Detetados (Area: {area} m2, Acao: {ocupacao})
            1.3. Enquadramento Juridico (RAN: {r_ran}, REN: {t_ren}, Rede Natura 2000: {t_rn2000})
            
            2. PROPOSTA DE AUTO DE NOTICIA
            2.1. Tipificacao da Infracao e Gravidade ({gravidade})
            2.2. Moldura Contraordenacional (Valores de coimas para pessoas singulares e coletivas)
            2.3. Medidas de Reposicao da Legalidade e Embargo
            
            Regras: Sem asteriscos, capitulos a bold, texto justificado, vocabulario tecnico juridico portugues.
            """
            
            try:
                res = model.generate_content(prompt).text
                docx = gerar_docx_oficial(res)
                st.success("Documentos preparados!")
                st.download_button("📥 Descarregar Word", docx, file_name=f"Fiscalizacao_{local}.docx")
                with st.expander("Ver rascunho"):
                    st.write(res.replace('*', ''))
            except Exception as e:
                st.error(f"Erro: {e}")
