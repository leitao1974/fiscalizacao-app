import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
import re

# 1. Configuração de Interface
st.set_page_config(page_title="Sistema Integrado de Fiscalização Território/Ambiente", layout="wide", page_icon="🛡️")

st.markdown("""
    <style>
    .stCheckbox { margin-bottom: -15px; font-size: 13px; }
    .stTabs [data-baseweb="tab"] { font-weight: bold; }
    .stTextArea textarea { background-color: #fcfcfc; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR: CONFIGURAÇÃO ---
st.sidebar.header("⚙️ Configuração")
api_key = st.sidebar.text_input("Google API Key", type="password")
modelo_selecionado = "gemini-1.5-pro"

if api_key:
    genai.configure(api_key=api_key)

# --- BASES DE DADOS CONSOLIDADAS ---

# REN - Tipologias (DL 166/2008 e DL 239/2012)
ren_litoral = ["Faixa marítima de proteção", "Praias", "Barreiras detríticas", "Tômbolos", "Sapais", "Ilhéus", "Dunas", "Arribas e respetivas faixas de proteção", "Faixa terrestre de proteção", "Águas de transição"]
ren_hidro = ["Cursos de água", "Lagoas e lagos", "Albufeiras", "Áreas estratégicas de proteção e recarga de aquíferos"]
ren_riscos = ["Zonas adjacentes", "Zonas ameaçadas pelo mar", "Zonas ameaçadas pelas cheias", "Áreas de elevado risco de erosão hídrica do solo", "Áreas de instabilidade de vertentes"]

# REDE NATURA 2000 - Artigo 9.º n.º 2 (Texto Íntegra)
condicionantes_natura = [
    "a) A realização de obras de construção civil fora dos perímetros urbanos, com excepção das obras de reconstrução, demolição, conservação de edifícios e ampliação desde que esta não envolva aumento de área de implantação superior a 50% da área inicial e a área total de ampliação seja inferior a 100 m2",
    "b) A alteração do uso actual do solo que abranja áreas contínuas superiores a 5 ha",
    "c) As modificações de coberto vegetal resultantes da alteração entre tipos de uso agrícola e florestal, em áreas contínuas superiores a 5 ha, considerando-se continuidade as ocupações similares que distem entre si menos de 500 m",
    "d) As alterações à morfologia do solo, com excepção das decorrentes das normais actividades agrícolas e florestais",
    "e) A alteração do uso actual dos terrenos das zonas húmidas ou marinhas, bem como as alterações à sua configuração e topografia",
    "f) A deposição de sucatas e de resíduos sólidos e líquidos",
    "g) A abertura de novas vias de comunicação, bem como o alargamento das existentes",
    "h) A instalação de infra-estruturas de electricidade e telefónicas, aéreas ou subterrâneas, de telecomunicações, de transporte de gás natural ou de outros combustíveis, de saneamento básico e de aproveitamento de energias renováveis ou similares fora dos perímetros urbanos",
    "i) A prática de actividades motorizadas organizadas e competições desportivas fora dos perímetros urbanos",
    "j) A prática de alpinismo, de escalada e de montanhismo",
    "l) A reintrodução de espécies indígenas da fauna e da flora selvagens"
]

zec_zpe_centro = ["ZEC Serra de Aire e Candeeiros", "ZEC Serra da Estrela", "ZEC Rio Zêzere", "ZEC Albufeira de Castelo do Bode", "ZEC Sicó/Alvaiázere", "ZPE Paul do Boquilobo", "ZPE Estuário do Mondego"]

# --- INTERFACE ---
st.title("🛡️ Sistema de Fiscalização: Master Território e Ambiente")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📍 Ocorrência & Infrator", "💧 Matriz REN", "🌿 Natura & AP", "🌾 RAN & Património", "📑 Documentação"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📍 Localização e Evidências")
        local = st.text_input("Localização/Concelho", "Região Centro")
        col_gps1, col_gps2 = st.columns(2)
        lat = col_gps1.text_input("Latitude", placeholder="39.xxxx")
        lon = col_gps2.text_input("Longitude", placeholder="-8.xxxx")
        area_m2 = st.number_input("Área Afetada (m²)", value=1000.0)
        fotos = st.file_uploader("📸 Registos Fotográficos", accept_multiple_files=True, type=['jpg', 'jpeg', 'png'])
            
    with c2:
        st.subheader("👤 Dados do Infrator")
        inf_nome = st.text_input("Nome / Designação Social")
        inf_morada = st.text_input("Morada / Sede Social")
        inf_nif = st.text_input("NIF / NIPC")
        inf_tel = st.text_input("Contacto Telefónico")
        tipo_ent = st.radio("Entidade", ["Pessoa Singular", "Pessoa Coletiva"], horizontal=True)

with tab2:
    st.info("**Tipologias REN e Checklist Técnica (Portaria 419/2012)**")
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        st.write("**Áreas Afetadas (Tipologias)**")
        sel_ren = [i for i in (ren_litoral + ren_hidro + ren_riscos) if st.checkbox(i)]
        st.write("**Interdições (Art. 20.º)**")
        sel_int_ren = [i for i in ["Loteamento", "Construção/Ampliação", "Escavações/Aterros", "Destruição do revestimento vegetal"] if st.checkbox(i)]
    with col_r2:
        st.write("**Checklist Portaria 419/2012**")
        c_previa_ren = st.checkbox("Ausência de Comunicação Prévia à CCDR")
        p_apa = st.checkbox("Ausência de Parecer Vinculativo da APA")
        lim_area_ren = st.checkbox("Excede limites de área/impermeabilização REN")

with tab3:
    st.success("**Rede Natura 2000 (DL 140/99) e Áreas Protegidas**")
    col_n1, col_n2 = st.columns(2)
    with col_n1:
        sel_zec = st.multiselect("Sítios ZEC/ZPE Afetados:", zec_zpe_centro)
        st.write("**Condicionantes Artigo 9.º n.º 2 (Seleção):**")
        sel_art9 = [i for i in condicionantes_natura if st.checkbox(i)]
    with col_n2:
        sel_zon = st.multiselect("Zonamento POAP/PNA:", ["Reserva Integral", "Reserva Parcial", "Proteção Parcial I", "Proteção Parcial II"])
        desc_natura = st.text_area("Notas Adicionais Fauna/Flora")

with tab4:
    st.info("**🌾 Reserva Agrícola Nacional (DL 199/2015 e Portaria 162/2011)**")
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.write("**Infrações RAN**")
        sel_ran = [i for i in ["Utilização não agrícola sem parecer", "Destruição de solo agrícola", "Intervenção em regadio público (Hidroagrícola)"] if st.checkbox(i)]
        r_pat = st.checkbox("🏛️ Violação de Património Cultural (Lei 107/2001)")
    with col_s2:
        st.write("**Limites Técnicos Portaria 162/2011**")
        lim_apoio = st.checkbox("Apoio Agrícola > 750m² ou >1% da exploração")
        lim_hab = st.checkbox("Habitação Agricultor > 300m²")
        lim_vias_ran = st.checkbox("Vias > 5m de largura ou pavimento impermeável")
        falta_alt_ran = st.checkbox("Falta de prova de inexistência de alternativa fora da RAN")

    st.divider()
    r_crime = st.checkbox("⚠️ Suspeita de crime contra o Ordenamento (Art. 278.º CP)")
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
        if re.match(r'^(\d+\.|RELATÓRIO|PROPOSTA|AUTO|INFRAÇÃO|DADOS|FUNDAMENTAÇÃO|CONCLUSÃO)', linha.upper()):
            p.add_run(linha).bold = True
        else:
            p.add_run(linha)
    
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

with tab5:
    if st.button("🚀 Gerar Auto de Notícia e Relatório"):
        if not api_key: st.error("Falta a API Key.")
        else:
            with st.spinner("A fundir toda a legislação (REN, Natura, RAN)..."):
                model = genai.GenerativeModel(modelo_selecionado)
                prompt = f"""
                Age como Fiscal Sénior e Jurista. Redigi Relatório e Auto de Notícia.
                DADOS: Local {local}, GPS: {lat}, {lon}. Área {area_m2}m2.
                INFRATOR: {inf_nome}, Morada: {inf_morada}, NIF: {inf_nif}, Tel: {inf_tel} ({tipo_ent}).
                
                QUADRO JURÍDICO CONSOLIDADO:
                1. REN: {sel_ren}. Interdições: {sel_int_ren}. Checklist Portaria 419/2012: {c_previa_ren}, {p_apa}, {lim_area_ren}.
                2. REDE NATURA 2000: Artigo 9º nº 2 (Texto Integral): {sel_art9}. Sítios: {sel_zec}.
                3. RAN: {sel_ran}. Limites Portaria 162/2011: Apoio={lim_apoio}, Habitação={lim_hab}, Vias={lim_vias_ran}, Alternativa={falta_alt_ran}.
                4. OUTROS: Património={r_pat}, Crime CP 278={r_crime}. Gravidade: {gravidade}.
                
                INSTRUÇÕES:
                - Transcreve as alíneas selecionadas do Artigo 9º nº 2 do DL 140/99 na íntegra.
                - Aplica o regime contraordenacional da Lei 50/2006.
                - Menciona que utilizações em RAN sem parecer ou fora dos limites da Portaria 162/2011 são ilegais.
                - Texto em PT-PT, formal, justificado.
                """
                try:
                    res = model.generate_content(prompt).text
                    st.success("Documentação preparada!")
                    st.download_button("📥 Descarregar Word", export_docx(res), file_name=f"Auto_Fiscalizacao_{local}.docx")
                    st.write(res)
                except Exception as e: st.error(f"Erro: {e}")

