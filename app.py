import streamlit as st
import google.generativeai as genai
from docx import Document
from io import BytesIO
from datetime import date

st.set_page_config(page_title="Fiscalização IA - Jurídico & Técnico", layout="wide")

# --- CONFIGURAÇÃO IA ---
st.sidebar.title("🔑 Configuração")
api_key = st.sidebar.text_input("Google API Key", type="password")

if api_key:
    genai.configure(api_key=api_key)
    # Recuperação dinâmica dos modelos Gemini disponíveis
    try:
        models = [m.name.replace('models/', '') for m in genai.list_models() 
                  if 'generateContent' in m.supported_generation_methods]
        modelo = st.sidebar.selectbox("Motor de IA Gemini", models, index=0)
    except:
        st.sidebar.error("Erro ao carregar modelos. Verifica a API Key.")

# --- DICIONÁRIO DE TIPOLOGIAS ---
tipologias_ren = [
    "Estrutura de Proteção de Encostas",
    "Áreas de Infiltração Máxima",
    "Zonas Adjacentes (Cursos de Água)",
    "Cabeceiras de Linhas de Água",
    "Zonas Ameaçadas pelas Cheias/Inundações",
    "Arribas e Faixas de Proteção"
]

tipologias_rn2000_centro = [
    "ZEC - Serra de Aire e Candeeiros",
    "ZEC - Paul de Arzila",
    "ZEC - Serra da Estrela",
    "ZEC - Dunas de Mira, Gândara e Gafanhas",
    "ZEC - Sicó/Alvaiázere",
    "ZEC - Arquipélago das Berlengas",
    "ZPE - Paul de Taipal / Arzila (Aves)",
    "ZPE - Estuário do Mondego"
]

# --- INTERFACE ---
st.title("🛡️ Apoio à Fiscalização: Relatório e Auto de Notícia")
st.subheader("Enquadramento Jurídico: REN, RAN e Rede Natura 2000 (ZEC/ZPE)")

col1, col2 = st.columns(2)

with col1:
    st.subheader("📍 Caracterização da Ocorrência")
    local = st.text_input("Localização (Freguesia/Concelho)", "Alenquer")
    area = st.number_input("Área Afetada (m²)", value=15591.67, format="%.2f")
    ocupacao = st.text_area("Descrição da Ocupação Atual", 
                            "Execução de aterro com deposição de terras e entulhos, com alteração irreversível da morfologia do solo.")
    
    st.subheader("📜 Regimes Jurídicos Aplicáveis")
    regime_ran = st.checkbox("RAN (Decreto-Lei n.º 73/2009)")
    regime_ren = st.checkbox("REN (Decreto-Lei n.º 166/2008)")
    regime_rn2000 = st.checkbox("Rede Natura 2000 (ZEC/ZPE)")

with col2:
    st.subheader("🔍 Tipologias e Gravidade")
    
    tipos_selecionados_ren = []
    if regime_ren:
        tipos_selecionados_ren = st.multiselect("Tipologias REN detetadas:", tipologias_ren)
        
    tipos_selecionados_rn2000 = []
    if regime_rn2000:
        tipos_selecionados_rn2000 = st.multiselect("Zonas Especiais de Conservação (ZEC/ZPE) - Centro:", tipologias_rn2000_centro)

    st.subheader("⚖️ Procedimento Contraordenacional")
    infrator = st.text_input("Identificação do Infrator", "Em averiguação")
    gravidade = st.select_slider("Gravidade da Infração", options=["Leve", "Grave", "Muito Grave"])

# --- FUNÇÃO GERADORA DOCX ---
def gerar_documento_word(texto_ia):
    doc = Document()
    # Título do Ficheiro
    doc.add_heading('DOCUMENTAÇÃO TÉCNICO-JURÍDICA DE FISCALIZAÇÃO', 0)
    
    # Inserção do conteúdo gerado pela IA
    doc.add_paragraph(texto_ia)
    
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

if st.button("🤖 Gerar Relatório e Proposta de Auto"):
    if not api_key:
        st.error("Por favor, insere a Google API Key.")
    else:
        with st.spinner("A IA está a cruzar os regimes jurídicos e a calcular coimas..."):
            model = genai.GenerativeModel(modelo)
            
            prompt = f"""
            Age como Fiscal do Território e Consultor Jurídico Sénior em Portugal. 
            Elabora um Relatório de Fiscalização e uma Proposta de Auto de Notícia baseados nos seguintes dados:

            1. RELATÓRIO DE FISCALIZAÇÃO:
            - Objeto: {ocupacao} no local {local}.
            - Área: {area} m2.
            - Enquadramento Legal: RAN ({regime_ran}), REN ({tipos_selecionados_ren}), Rede Natura 2000 - ZEC/ZPE ({tipos_selecionados_rn2000}).
            - Fundamentação: Analisa a compatibilidade da ação com o DL 73/2009 (RAN), DL 166/2008 (REN) e DL 140/99 (Rede Natura). 
            - Conclusão Técnica: Descreve o dano ambiental/territorial.

            2. PROPOSTA DE AUTO DE NOTÍCIA:
            - Infrator: {infrator}. Gravidade: {gravidade}.
            - QUADRO DE COIMAS: Apresenta os valores mínimos e máximos das coimas para a gravidade '{gravidade}', distinguindo Pessoa Singular de Pessoa Coletiva, conforme o regime jurídico mais gravoso identificado.
            - Medidas Cautelares: Propor embargo imediato e reposição da situação anterior (remoção do aterro).

            IMPORTANTE: NÃO USES ACENTOS OU CEDILHAS para garantir total compatibilidade de encoding no ficheiro gerado.
            """
            
            resposta = model.generate_content(prompt).text
            file_word = gerar_documento_word(resposta)
            
            st.success("Relatório e Auto gerados com sucesso!")
            st.download_button(
                label="📥 Baixar Documentos Word (.docx)",
                data=file_word,
                file_name=f"Fiscalizacao_{local}_{date.today()}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            st.text_area("Pré-visualização da Redação:", resposta, height=400)
