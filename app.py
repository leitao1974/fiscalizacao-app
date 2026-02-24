import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
from datetime import date
import re

st.set_page_config(page_title="Gestão de Fiscalização Territorial", layout="wide")

# --- CONFIGURAÇÃO IA ---
st.sidebar.title("🔑 Configuração")
api_key = st.sidebar.text_input("Google API Key", type="password")

if api_key:
    genai.configure(api_key=api_key)
    try:
        models = [m.name.replace('models/', '') for m in genai.list_models() 
                  if 'generateContent' in m.supported_generation_methods]
        modelo = st.sidebar.selectbox("Motor de IA Gemini", models, index=0)
    except:
        st.sidebar.error("Erro na API Key.")

# --- LISTAS DE TIPOLOGIAS ---
tipologias_ren = ["Estrutura de Proteção de Encostas", "Áreas de Infiltração Máxima", "Zonas Adjacentes", "Cabeceiras de Linhas de Água", "Zonas Ameaçadas pelas Cheias"]
tipologias_zec = ["ZEC - Serra de Aire e Candeeiros", "ZEC - Paul de Arzila", "ZEC - Serra da Estrela", "ZEC - Sicó/Alvaiázere", "ZPE - Paul de Taipal / Arzila"]

# --- INTERFACE ---
st.title("🛡️ Relatório de Fiscalização e Auto de Notícia")
st.markdown("Ferramenta de análise jurídica baseada nos regimes **REN, RAN e Rede Natura 2000 (ZEC/ZPE)**.")

col1, col2 = st.columns(2)

with col1:
    st.subheader("📍 Caracterização")
    local = st.text_input("Localização", "Alenquer")
    area = st.number_input("Área Afetada (m²)", value=15591.67)
    ocupacao = st.text_area("Descrição da Ocupação", "Execução de aterro com deposição de materiais, alterando a morfologia do solo.")
    
    st.subheader("📜 Regimes de Proteção")
    r_ran = st.checkbox("RAN (DL 73/2009)")
    r_ren = st.checkbox("REN (DL 166/2008)")
    r_zec = st.checkbox("ZEC/ZPE (Rede Natura 2000)")

with col2:
    st.subheader("🔍 Especificidades")
    t_ren = st.multiselect("Tipologias REN:", tipologias_ren) if r_ren else []
    t_zec = st.multiselect("Zonas Especiais (ZEC/ZPE):", tipologias_zec) if r_zec else []
    
    st.subheader("⚖️ Procedimento")
    infrator = st.text_input("Infrator", "Em averiguação")
    gravidade = st.select_slider("Gravidade", options=["Leve", "Grave", "Muito Grave"])

# --- FUNÇÃO DE CRIAÇÃO DE WORD FORMATADO ---
def criar_word_profissional(texto_bruto):
    doc = Document()
    
    # Limpar os asteriscos que a IA usa para negrito e substituir por formatação Word
    # Dividir o texto em seções baseadas nos títulos que a IA gera
    linhas = texto_bruto.split('\n')
    
    for linha in linhas:
        # Remover asteriscos de marcação
        linha_limpa = linha.replace('*', '').strip()
        if not linha_limpa: continue
        
        para = doc.add_paragraph()
        para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY # Justificar texto
        
        # Se a linha parecer um título (letras maiúsculas ou início de seção)
        if re.match(r'^[0-9].|RELATÓRIO|AUTO|FUNDAMENTAÇÃO|CONCLUSÃO', linha_limpa.upper()):
            run = para.add_run(linha_limpa)
            run.bold = True
            run.font.size = Pt(12)
        else:
            run = para.add_run(linha_limpa)
            run.font.size = Pt(11)
            
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

if st.button("🤖 Gerar Documentação Oficial"):
    if api_key:
        with st.spinner("A redigir com rigor jurídico..."):
            model = genai.GenerativeModel(modelo)
            prompt = f"""
            Age como Fiscal e Jurista Sénior. Elabora um Relatório de Fiscalização e uma Proposta de Auto de Notícia.
            USA ACENTUAÇÃO CORRETA E PORTUGUÊS FORMAL (Ex: ação, infração, jurisdição).
            NÃO USES ASTERISCOS (*) NO TEXTO.
            
            DADOS:
            - Local: {local}. Área: {area} m2.
            - Ação: {ocupacao}.
            - Regimes: RAN ({r_ran}), REN ({t_ren}), ZEC/ZPE ({t_zec}).
            - Gravidade: {gravidade}. Infrator: {infrator}.
            
            ESTRUTURA:
            1. RELATÓRIO DE FISCALIZAÇÃO: Descreve os factos, fundamenta com o DL 73/2009 e DL 166/2008.
            2. PROPOSTA DE AUTO DE NOTÍCIA: Tipifica a infração, indica as coimas (mín/máx) para pessoas singulares e coletivas e propõe o embargo.
            """
            
            resposta = model.generate_content(prompt).text
            # Limpeza final de asteriscos residuais antes de ir para o docx
            resposta_limpa = resposta.replace('*', '')
            
            doc_word = criar_word_profissional(resposta_limpa)
            
            st.success("Documentos gerados com sucesso!")
            st.download_button("📥 Baixar Relatório e Auto (.docx)", doc_word, 
                               file_name=f"Fiscalizacao_{local}.docx",
                               mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            st.text_area("Pré-visualização (Texto Justificado no Word):", resposta_limpa, height=300)
    else:
        st.error("Insere a API Key.")
