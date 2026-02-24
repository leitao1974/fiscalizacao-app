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
st.set_page_config(page_title="Fiscalização Pro: Conservação e Território", layout="wide", page_icon="🛡️")

# CSS para layout profissional
st.markdown("""
    <style>
    .main { background-color: #f4f7f6; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { background-color: #e8f5e9; border-radius: 4px; padding: 10px 20px; font-weight: bold; }
    .stTabs [aria-selected="true"] { background-color: #2e7d32 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR CONFIG (CHAVE DINÂMICA) ---
st.sidebar.header("⚙️ Painel de Controlo")
api_key = st.sidebar.text_input("Google API Key", type="password")

modelo_selecionado = "gemini-1.5-pro" # Valor padrão

if api_key:
    genai.configure(api_key=api_key)
    try:
        # Recupera dinamicamente os modelos disponíveis para a chave inserida
        modelos_disponiveis = [m.name.replace('models/', '') for m in genai.list_models() 
                               if 'generateContent' in m.supported_generation_methods]
        modelo_selecionado = st.sidebar.selectbox("Motor de IA Ativo", modelos_disponiveis, index=0)
        st.sidebar.success(f"Ligado ao motor: {modelo_selecionado}")
    except Exception as e:
        st.sidebar.error("Erro ao listar modelos. Verifica a tua API Key.")

# --- LISTAS DE APOIO (REGIÃO CENTRO & CONSERVAÇÃO) ---
zec_zpe_centro = [
    "ZEC Serra de Aire e Candeeiros", "ZEC Serra da Estrela", "ZEC Sicó/Alvaiázere", 
    "ZEC Paul de Arzila", "ZEC Serra da Lousã", "ZEC Malcata", "ZEC Rio Paiva",
    "ZPE Estuário do Mondego", "ZPE Ria de Aveiro", "ZPE Paul de Taipal"
]

rnap_nacional = [
    "Parque Natural da Serra da Estrela", "Parque Natural das Serras de Aire e Candeeiros",
    "Parque Natural do Tejo Internacional", "Reserva Natural do Paul de Arzila",
    "Reserva Natural da Serra da Malcata", "Reserva Natural das Berlengas"
]

rnap_local = [
    "Paisagem Protegida Local do Monte de S. Bartolomeu",
    "Reserva Natural Local do Paul da Tornada",
    "Paisagem Protegida Local das Serras do Socorro e Archeira"
]

# --- INTERFACE ---
st.title("🛡️ Sistema de Apoio à Fiscalização e Auto de Notícia")
st.markdown("Análise integrada: **RAN, REN, Rede Natura 2000 e Conservação da Natureza (DL 142/2008)**.")

tab1, tab2, tab3 = st.tabs(["📍 Ocorrência", "⚖️ Enquadramento Legal", "📑 Planos de Ordenamento"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        local = st.text_input("Localização / Concelho", "Alenquer")
        area = st.number_input("Área Afetada (m²)", value=15591.67, format="%.2f")
    with col2:
        ocupacao = st.text_area("Descrição da Ação Detetada", "Execução de aterro com deposição de materiais inertes e alteração da morfologia do solo.")

with tab2:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Regimes Agrícolas e Ecológicos")
        r_ran = st.checkbox("RAN (Decreto-Lei n.º 73/2009)")
        r_ren = st.checkbox("REN (Decreto-Lei n.º 166/2008)")
        t_ren = st.multiselect("Tipologias REN:", ["Encostas", "Infiltração Máxima", "Cursos de Água"]) if r_ren else []
    
    with c2:
        st.subheader("Conservação da Natureza")
        r_rn2000 = st.checkbox("Rede Natura 2000 (ZEC/ZPE)")
        t_rn2000 = st.multiselect("Zonas Selecionadas:", zec_zpe_centro) if r_rn2000 else []
        
        r_ap = st.checkbox("Áreas Protegidas (RNAP - DL 142/2008)")
        t_ap_nac = st.multiselect("Âmbito Nacional:", rnap_nacional) if r_ap else []
        t_ap_loc = st.multiselect("Âmbito Local/Regional:", rnap_local) if r_ap else []
        
        st.divider()
        gravidade = st.select_slider("Gravidade da Infração", options=["Leve", "Grave", "Muito Grave"])

conteudo_poap = ""
with tab3:
    st.write("Carregue o Plano de Ordenamento (POAP) ou Plano de Gestão para fundamentação automática.")
    arquivo_poap = st.file_uploader("Upload Regulamento (PDF)", type=['pdf'])
    if arquivo_poap:
        reader = PdfReader(arquivo_poap)
        conteudo_poap = "\n".join([page.extract_text() for page in reader.pages[:15]])
        st.success(f"Plano lido com sucesso ({len(reader.pages)} páginas).")

# --- MOTOR DOCX PROFISSIONAL ---
def gerar_docx_final(texto_ia):
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = 'Arial'
    style.font.size = Pt(11)

    for section in doc.sections:
        section.top_margin, section.bottom_margin = Cm(2.5), Cm(2.5)
        section.left_margin, section.right_margin = Cm(3.0), Cm(2.5)

    # Limpeza de formatação Markdown da IA
    texto_formatado = texto_ia.replace('*', '').replace('#', '')
    
    for linha in texto_formatado.split('\n'):
        linha = linha.strip()
        if not linha: continue
        
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        
        # Detecção de Capítulos e Subcapítulos para BOLD
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

# --- GERAÇÃO DOS DOCUMENTOS ---
st.divider()
if st.button("🚀 Gerar Relatório de Fiscalização e Proposta de Auto"):
    if not api_key:
        st.error("Introduza a Google API Key na barra lateral.")
    else:
        with st.spinner(f"A utilizar o motor {modelo_selecionado} para análise jurídica..."):
            model = genai.GenerativeModel(modelo_selecionado)
            
            prompt = f"""
            Age como Fiscal do Território e Jurista Especialista em Conservação da Natureza.
            Redigi dois documentos separados: 1. RELATÓRIO DE FISCALIZAÇÃO e 2. PROPOSTA DE AUTO DE NOTÍCIA.
            
            Usa Português Formal, acentos e texto justificado. NÃO uses asteriscos.
            
            CONTEXTO LEGAL:
            - Local: {local}. Área: {area} m2. Ocupação: {ocupacao}.
            - Regimes: RAN={r_ran}, REN={t_ren}, ZEC/ZPE={t_rn2000}, Áreas Protegidas={t_ap_nac + t_ap_loc}.
            - Diploma Base: Regime Jurídico da Conservação da Natureza (DL 142/2008).
            
            CONTEÚDO DO PLANO DE ORDENAMENTO (POAP):
            {conteudo_poap[:2500]}
            
            INSTRUÇÕES ESPECÍFICAS:
            - Analisa se a infração ocorre em solo da Rede Nacional de Áreas Protegidas e as implicações do DL 142/2008.
            - No AUTO, tipifica a gravidade ({gravidade}) e indica as coimas (singulares e coletivas) baseadas na Lei n.º 50/2006 (Lei da Contraordenação Ambiental).
            - Propõe embargo imediato e reposição do terreno.
            """
            
            try:
                res = model.generate_content(prompt).text
                docx_file = gerar_docx_final(res)
                st.success("Análise concluída com sucesso!")
                st.download_button("📥 Descarregar Documentos Word", docx_file, 
                                   file_name=f"Fiscalizacao_{local}.docx",
                                   mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
                with st.expander("Pré-visualização do Parecer"):
                    st.write(res.replace('*', ''))
            except Exception as e:
                st.error(f"Erro na geração com o modelo {modelo_selecionado}: {e}")
