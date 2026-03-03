import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
import re
from pypdf import PdfReader

# 1. Configuração de Interface
st.set_page_config(page_title="Fiscalização Pro: Matriz Legal Total", layout="wide", page_icon="🛡️")

st.markdown("""
    <style>
    .stCheckbox { margin-bottom: -15px; font-size: 13px; }
    .stTabs [data-baseweb="tab"] { font-weight: bold; }
    .stTextArea textarea { background-color: #f8f9fa; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR: CONFIGURAÇÃO ---
st.sidebar.header("⚙️ Configuração")
api_key = st.sidebar.text_input("Google API Key", type="password")
modelo_selecionado = "gemini-1.5-pro"

if api_key:
    genai.configure(api_key=api_key)
    try:
        modelos = [m.name.replace('models/', '') for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        modelo_selecionado = st.sidebar.selectbox("Motor de IA Ativo", modelos, index=0)
    except:
        st.sidebar.error("Erro na API Key.")

# --- BASE DE DADOS CONSOLIDADAS ---

# 💧 REN - Tipologias Oficiais (DL 239/2012)
ren_litoral = ["Faixa marítima de proteção", "Praias", "Barreiras detríticas", "Tômbolos", "Sapais", "Ilhéus", "Dunas", "Arribas", "Faixa terrestre", "Águas de transição"]
ren_hidro = ["Cursos de água", "Lagoas e lagos", "Albufeiras", "Áreas de recarga de aquíferos"]
ren_riscos = ["Zonas adjacentes", "Zonas ameaçadas pelo mar", "Zonas ameaçadas pelas cheias", "Elevado risco de erosão", "Instabilidade de vertentes"]

# 🌿 REDE NATURA 2000 (Sítios ZEC e ZPE - Listagem Expandida)
zec_zpe_lista = [
    "ZEC Serra de Aire e Candeeiros", "ZEC Serra da Estrela", "ZEC Rio Zêzere", "ZEC Albufeira de Castelo do Bode", 
    "ZEC Sicó/Alvaiázere", "ZEC Serra da Lousã", "ZEC Rio Vouga", "ZEC Rio Paiva", "ZEC Arrábida/Espichel", 
    "ZEC Estuário do Tejo", "ZEC Monfurado", "ZEC Costa Vicentina", "ZEC Sintra-Cascais", 
    "ZPE Paul do Boquilobo", "ZPE Estuário do Mondego", "ZPE Lagoa de Albufeira", "ZPE Douro Internacional", 
    "ZPE Castro Verde", "ZPE Ria de Aveiro", "ZPE Beira Interior"
]

# 🌿 CONDICIONANTES ART. 9.º N.º 2 (DL 140/99 - Texto Integral)
condicionantes_art9 = [
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

# 🌿 ÁREAS PROTEGIDAS (RNAP)
rnap_lista = [
    "Parque Natural das Serras de Aire e Candeeiros",
    "Parque Natural da Serra da Estrela",
    "Parque Natural do Tejo Internacional",
    "Parque Natural do Douro Internacional",
    "Reserva Natural do Paul do Boquilobo",
    "Reserva Natural da Serra da Malcata",
    "Reserva Natural das Berlengas",
    "Reserva Natural do Paul de Arzila",
    "Reserva Natural das Dunas de São Jacinto",
    "Paisagem Protegida da Serra do Açor",
    "Monumento Natural do Cabo Mondego",
    "Monumento Natural das Pegadas de Dinossáurios de Ourém/Torres Novas"
]

# 🌿 ZONAMENTO (POAP / PNA / RJUE)
zonamento_tipologias = [
    "Reserva Integral", "Reserva Parcial I", "Reserva Parcial II", 
    "Proteção Parcial I", "Proteção Parcial II", "Proteção Complementar I", 
    "Proteção Complementar II", "Área de Intervenção Específica", 
    "Zona de Proteção Estrita", "Zona de Proteção de Albufeira"
]

# 🌾 RAN (DL 73/2009 + DL 199/2015)
# 🌾 RAN - MATRIZ TÉCNICA (DL 73/2009 + DL 199/2015 + Portaria 162/2011)
inf_ran_interdicoes = [
    "🚫 (Int.) Utilização de terras para fins não agrícolas (sem enquadramento)",
    "🚫 (Int.) Ações que destruam ou degradem o potencial agrícola do solo",
    "🚫 (Int.) Impermeabilização definitiva de solos de alta qualidade (Classe A/B)",
    "🚫 (Int.) Deposição de estéreis, resíduos ou materiais de construção",
    "🚫 (Int.) Intervenção em área beneficiada por Aproveitamento Hidroagrícola (Regadio Público)"
]

inf_ran_condicionantes = [
    "⚠️ (Cond.) Apoios agrícolas sem parecer da Entidade Regional da RAN",
    "⚠️ (Cond.) Habitação de agricultor sem título de parecer vinculado",
    "⚠️ (Cond.) Obras de utilidade pública sem despacho de reconhecimento (Art. 25.º)",
    "⚠️ (Cond.) Infraestruturas (energia/vias) sem verificação de inexistência de alternativa"
]

# 🏛️ PATRIMÓNIO CULTURAL (Lei 107/2001)
patrimonio_interdicoes = [
    "🚫 Obra/Intervenção sem autorização da DGPC/DRC (Interior ou Exterior)",
    "🚫 Mudança de uso que afete o valor do bem classificado",
    "🚫 Destruição, danificação ou deterioração do bem",
    "🚫 Saída de bem móvel classificado do território nacional sem autorização"
]

patrimonio_condicionantes = [
    "⚠️ Intervenção em Zona Especial de Proteção (ZEP)",
    "⚠️ Intervenção em Zona de Proteção Provisória (50 metros)",
    "⚠️ Obra em imóvel em vias de classificação (Suspensão de licença)",
    "⚠️ Trabalhos arqueológicos sem autorização prévia"
]

patrimonio_deveres = [
    "❗ Incumprimento do dever de conservação e manutenção",
    "❗ Desrespeito por ordem de obras de emergência/salvaguarda",
    "❗ Violação do dever de facultar o acesso para inspeção técnica"
]

# 💧 RECURSOS HÍDRICOS (Lei n.º 58/2005 - Lei da Água)
rh_interdicoes = [
    "🚫 Utilização do Domínio Público Hídrico sem Título (Licença/Concessão)",
    "🚫 Alteração do leito ou das margens de cursos de água",
    "🚫 Extração de inertes (areia/cascalho) em locais não autorizados",
    "🚫 Descarga de águas residuais ou resíduos sem autorização (APA/ARH)",
    "🚫 Obstrução do livre fluxo das águas ou do acesso às margens"
]

rh_condicionantes = [
    "⚠️ Obras em Margem (faixa de 10m em águas não navegáveis / 50m em navegáveis)",
    "⚠️ Construções em Zonas Adjacentes (Zonas Inundáveis/Ameaçadas pelas Cheias)",
    "⚠️ Captação de águas superficiais ou subterrâneas sem balizamento/medidor",
    "⚠️ Limpeza de linhas de água com destruição de galeria ripícola autóctone"
]

# 🛠️ MEDIDAS DE MINIMIZAÇÃO E REPOSIÇÃO
medidas_minimizacao = [
    "🌱 Reposição da topografia original e do coberto vegetal autóctone",
    "🧱 Utilização de pavimentos permeáveis ou semipermeáveis",
    "🌳 Criação de cortinas arbóreas para integração paisagística",
    "💧 Implementação de sistemas de retenção e infiltração de águas pluviais",
    "🏗️ Redução da área de impermeabilização ou da cércea da edificação",
    "🚧 Remoção imediata de entulhos e resíduos de construção",
    "🛡️ Instalação de barreiras acústicas ou de contenção de poeiras"
]

# --- INTERFACE ---
st.title("🛡️ Sistema de Fiscalização: Master Território e Ambiente")

tabs = st.tabs(["📍 Identificação", "💧 REN", "🌿 Natura & AP", "🌾 RAN", "🏛️ Património", "🌊 Recursos Hídricos", "📑 Gerar Documentação"])

with tabs[0]:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📍 Localização e GPS")
        local = st.text_input("Localização/Concelho", "Região Centro")
        col_gps1, col_gps2 = st.columns(2)
        lat = col_gps1.text_input("Latitude", placeholder="39.xxxx")
        lon = col_gps2.text_input("Longitude", placeholder="-8.xxxx")
        area_m2 = st.number_input("Área Afetada (m²)", value=1000.0)
        fotos = st.file_uploader("📸 Fotos", accept_multiple_files=True, type=['jpg', 'jpeg', 'png'])
    with c2:
        st.subheader("👤 Dados do Infrator")
        inf_nome = st.text_input("Nome/Entidade")
        inf_morada = st.text_input("Morada/Sede")
        inf_nif = st.text_input("NIF/NIPC")
        inf_tel = st.text_input("Telefone")
        tipo_ent = st.radio("Tipo", ["Pessoa Singular", "Pessoa Coletiva"], horizontal=True)
        desc_visual = st.text_area("Notas de Campo")

with tabs[1]:
    st.info("**Tipologias REN (DL 166/2008 + DL 239/2012)**")
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Áreas Afetadas**")
        sel_ren = [i for i in (ren_litoral + ren_hidro + ren_riscos) if st.checkbox(i, key=f"ren_{i}")]
    with col2:
        st.write("**Interdições e Títulos**")
        c_previa = st.checkbox("Falta de Comunicação Prévia")
        p_apa = st.checkbox("Falta de Parecer APA")
        lim_area_ren = st.checkbox("Excede limites de área/impermeabilização REN")

with tabs[2]:
    st.success("**Conservação da Natureza (DL 140/99 + DL 142/2008)**")
    col1, col2 = st.columns(2)
    with col1:
        sel_zec = st.multiselect("Sítios ZEC/ZPE (Rede Natura 2000):", zec_zpe_lista)
        sel_rnap = st.multiselect("Áreas Protegidas (RNAP):", rnap_lista)
        st.write("**Condicionantes Art. 9.º n.º 2:**")
        sel_art9 = [i for i in condicionantes_art9 if st.checkbox(i, key=f"art9_{i}")]
    with col2:
        st.write("**Zonamento (POAP / PNA):**")
        sel_zon = st.multiselect("Selecione o Zonamento afetado:", zonamento_tipologias)
        upload_poap = st.file_uploader("📂 Upload Regulamento POAP (PDF)", type=['pdf'])

with tabs[3]:
    st.info("**Reserva Agrícola Nacional (DL 199/2015 + Portaria 162/2011)**")
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Interdições e Condicionantes RAN**")
        sel_ran_int = [i for i in inf_ran_interdicoes if st.checkbox(i)]
        sel_ran_cond = [i for i in inf_ran_condicionantes if st.checkbox(i)]
    with col2:
        st.write("**Verificação de Limites Técnicos (Portaria 162/2011)**")
        lim_apoio = st.checkbox("Apoio Agrícola > 750m² ou >1% da área da exploração")
        lim_hab = st.checkbox("Habitação Agricultor > 300m² ou sem ónus de inalienabilidade")
        lim_vias = st.checkbox("Vias de acesso > 5m de largura ou pavimento impermeável")
        falta_alt = st.checkbox("Falta de prova de inexistência de alternativa viável fora da RAN")

with tabs[4]:
    st.warning("**Património Cultural (Lei 107/2001 - Bases da Política e do Regime de Proteção)**")
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Interdições e Condicionantes**")
        sel_pat_int = [i for i in patrimonio_interdicoes if st.checkbox(i)]
        sel_pat_cond = [i for i in patrimonio_condicionantes if st.checkbox(i)]
    with col2:
        st.write("**Deveres do Proprietário e Arqueologia**")
        sel_pat_dev = [i for i in patrimonio_deveres if st.checkbox(i)]
        obs_pat = st.text_area("Notas Técnicas (Estado de conservação, tipologia do bem, etc.):")
    
    st.divider()
    st.info("ℹ️ **Nota Jurídica:** Licenças municipais que infrinjam estas normas são nulas (Art. 4.º e 5.º da Lei 107/2001).")
	
with tabs[5]:
    st.info("**Recursos Hídricos (Lei da Água - Lei n.º 58/2005)**")
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Interdições e Utilizações Principais**")
        sel_rh_int = [i for i in rh_interdicoes if st.checkbox(i)]
    with col2:
        st.write("**Zonas de Proteção e Condicionantes**")
        sel_rh_cond = [i for i in rh_condicionantes if st.checkbox(i)]
        obs_rh = st.text_area("Notas sobre o Meio Hídrico (Caudal, poluição visível, erosão):")
    
    st.divider()
    st.warning("ℹ️ **Nota de Campo:** Verifique a titularidade (Público vs Privado) e a servidão de margem (Art. 21.º da Lei da Água).")

with tabs[6]:
    st.subheader("🛠️ Medidas de Minimização Propostas")
    st.write("Selecione as medidas para mitigação do impacto ambiental/territorial:")
    sel_medidas = [i for i in medidas_minimizacao if st.checkbox(i)]
    
    texto_adicional_medidas = st.text_area("Prescrições técnicas específicas (ex: espécies a plantar, prazos):")
    st.divider()

    st.subheader("🏁 Finalização e Geração")
    gravidade = st.select_slider("Gravidade Proposta", options=["Leve", "Grave", "Muito Grave"])
    r_crime = st.checkbox("⚠️ Suspeita de Crime (Art. 278.º Código Penal)")
    
    # Motor Docx (Função consolidada)
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

    if st.button("🚀 Gerar Documentação Final"):
        if not api_key: 
            st.error("Falta a API Key.")
        else:
            with st.spinner("A cruzar regimes jurídicos e zonamentos..."):
                model = genai.GenerativeModel(modelo_selecionado)
                prompt = f"""
                Age como Fiscal Sénior e Jurista. Redigi Relatório e Auto de Notícia.
                DADOS: Local {local}, GPS: {lat}, {lon}. Área {area_m2}m2.
                INFRATOR: {inf_nome}, NIF: {inf_nif}, Tel: {inf_tel} ({tipo_ent}).
                
                ENQUADRAMENTO:
                - REN: {sel_ren}. Interdições: {c_previa}/{p_apa}.
                - Rede Natura 2000 (ZECs/ZPEs): {sel_zec}.
                - Áreas Protegidas (RNAP): {sel_rnap}.
                - Zonamento (POAP): {sel_zon}.
                - Natura 2000 (Art 9º nº 2 DL 140/99): {sel_art9}.
                - RAN (DL 199/2015): Interdições={sel_ran_int}, Condicionantes={sel_ran_cond}. 
                - Limites Técnicos Portaria 162/2011: Apoios={lim_apoio}, Habitação={lim_hab}, Vias={lim_vias}, Alternativa={falta_alt}.
                - PATRIMÓNIO CULTURAL: Interdições={sel_pat_int}, Condicionantes={sel_pat_cond}, Incumprimento de Deveres={sel_pat_dev}.
                - Notas Adicionais Património: {obs_pat}.
                - Nota: Fundamenta a NULIDADE de eventuais licenças administrativas caso violem a Lei 107/2001.
                - RECURSOS HÍDRICOS: Interdições={sel_rh_int}, Condicionantes={sel_rh_cond}.
                - Notas Adicionais Recursos Hídricos: {obs_rh}.
                - Importante: Fundamenta com base no regime de utilização dos recursos hídricos (DL 226-A/2007) e a necessidade de Título de Utilização (TURH).
                - MEDIDAS DE MINIMIZAÇÃO PROPOSTAS: {sel_medidas}.
                - PRESCRIÇÕES TÉCNICAS ADICIONAIS: {texto_adicional_medidas}.
                - Instrução: No capítulo da 'PROPOSTA', detalha como estas medidas ajudam a cumprir os princípios da prevenção e da precaução ambiental.
                
                INSTRUÇÕES:
                1. No RELATÓRIO: Cita o n.º 2 do Artigo 9.º do DL 140/99 na íntegra para as condicionantes selecionadas.
                2. Menciona as interdições específicas do Zonamento {sel_zon} e do Sítio {sel_zec}.
                3. No AUTO: Tipifica e calcula coimas para gravidade {gravidade} e entidade {tipo_ent} (Lei 50/2006).
                4. Estilo: Formal, PT-PT, capítulos a BOLD.
                """
                try:
                    res = model.generate_content(prompt).text
                    st.success("Documentação preparada!")
                    st.download_button("📥 Descarregar Word", export_docx(res), file_name=f"Fiscalizacao_{local}.docx")
                    st.write(res)
                except Exception as e: 
                    st.error(f"Erro: {e}")


