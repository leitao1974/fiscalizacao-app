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

# No topo do script, após as importações
if 'desc_detalhada' not in st.session_state:
    desc_detalhada = ""

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

# 💧 REN - TIPOLOGIAS DETALHADAS (DL 239/2012)
ren_litoral_dict = {
    "Faixa marítima de proteção costeira": "Linha do leito até batimétrica dos 30m",
    "Praias": "Acumulação de sedimentos (areia/cascalho)",
    "Barreiras detríticas": "Restingas, barreiras soldadas e ilhas-barreira",
    "Tômbolos": "Sedimentos que ligam ilha ao continente",
    "Sapais": "Zonas intertidais com vegetação halofítica",
    "Ilhéus e rochedos emersos no mar": "Formações rochosas destacadas",
    "Dunas costeiras e dunas fósseis": "Acumulações eólicas de areia",
    "Arribas e faixas de proteção": "Vertentes abruptas e áreas adjacentes",
    "Faixa terrestre de proteção costeira": "Proteção na ausência de dunas/arribas",
    "Águas de transição": "Secções terminais sob influência salina"
}

ren_hidro_dict = {
    "Cursos de água, leitos e margens": "Terreno coberto pelas águas e faixas confinantes",
    "Lagoas e lagos": "Meios hídricos lênticos e faixas de proteção",
    "Albufeiras": "Volumes retidos por barragens para conectividade ecológica",
    "Áreas estratégicas de proteção e recarga de aquíferos": "Zonas de infiltração máxima"
}

ren_riscos_dict = {
    "Zonas adjacentes": "Risco de cheia ou ameaça do mar (ato regulamentar)",
    "Zonas ameaçadas pelo mar": "Inundações por galgamento oceânico",
    "Zonas ameaçadas pelas cheias": "Suscetíveis a transbordo de cursos de água",
    "Áreas de elevado risco de erosão hídrica": "Declive e solo propícios a perda de terra",
    "Áreas de instabilidade de vertentes": "Movimentos de massa/deslizamentos"
}
# 🚫 INTERDIÇÕES GERAIS (Artigo 20.º do DL 166/2008)
ren_interdicoes_gerais = [
    "🏗️ Operações de loteamento",
    "🧱 Obras de urbanização, construção e ampliação",
    "🛣️ Vias de comunicação e acessos",
    "🚜 Escavações e aterros (alteração da morfologia do solo)",
    "🪓 Destruição do revestimento vegetal (não agrícola/florestal)",
    "🌊 Alteração da rede de drenagem natural"
]

# 📝 REGIMES DE CONTROLO (De acordo com o DL 239/2012)
ren_regimes_controlo = [
    "🟢 Isento de procedimento (Uso compatível livre)",
    "🟡 Comunicação Prévia à CCDR (Regime regra pós-2012)",
    "🔴 Sujeito a Autorização (Casos específicos/excecionais)",
    "⭐ Relevante Interesse Público (Despacho Governamental - Art. 21.º)"
]

# 🌿 REDE NATURA 2000 - REGIÃO CENTRO (ZEC e ZPE - PSRN2000)
zec_zpe_lista = [
    "ZEC Serra da Malcata", "ZEC Serra da Estrela", "ZEC Serra de Aire e Candeeiros", 
    "ZEC Sicó/Alvaiázere", "ZEC Serra da Lousã", "ZEC Serra do Açor", 
    "ZEC Gardunha", "ZEC Rio Zêzere", "ZEC Rio Paiva", "ZEC Rio Vouga", 
    "ZEC Estuário do Mondego", "ZEC Estuário do Tejo", "ZEC Paul de Arzila", 
    "ZEC Paul do Boquilobo", "ZEC Dunas de Mira, Gândara e Gafanhas", 
    "ZEC São Pedro de Moel", "ZEC Peniche", "ZEC Berlengas", "ZEC Montejunto", 
    "ZEC Sintra-Cascais", "ZEC Arrábida/Espichel", "ZEC Complexo do Alviela", 
    "ZEC Ribeira de Alge", "ZEC Cabeço das Videiras", "ZEC Nisa/Nelas",
    "ZPE Serra da Malcata", "ZPE Serra da Estrela", "ZPE Serra da Gardunha", 
    "ZPE Beira Interior (Tejo Internacional e Erges)", "ZPE Serra da Lousã", 
    "ZPE Paul de Arzila", "ZPE Paul do Taipal", "ZPE Paul do Boquilobo", 
    "ZPE Estuário do Mondego", "ZPE Ria de Aveiro", "ZPE Estuário do Tejo"
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

# 🌾 RAN - MATRIZ LEGAL INTEGRAL (DL 73/2009 republicado pelo DL 199/2015)

# Transcrição Integral: Ações Interditas - Artigo 21.º
ran_interdicoes_dict = {
    "a) Operações de loteamento e obras de urbanização, construção ou ampliação, com excepção das utilizações previstas no artigo seguinte;": "Interdição de novas edificações fora das exceções legais [cite: 238, 1034]",
    "b) Lançamento ou depósito de resíduos radioactivos, resíduos sólidos urbanos, residuos industriais ou outros produtos que contenham substâncias ou microrganismos que possam alterar e deteriorar as características do solo;": "Proibição de deposição de produtos contaminantes [cite: 239, 1035]",
    "c) Aplicação de volumes excessivos de lamas nos termos da legislação aplicável, designadamente resultantes da utilização indiscriminada de processos de tratamento de efluentes;": "Violação dos limites de tratamento de efluentes no solo [cite: 240, 1036]",
    "d) Intervenções ou utilizações que provoquem a degradação do solo, nomeadamente erosão, compactação, desprendimento de terras, encharcamento, inundações, excesso de salinidade, poluição e outros efeitos perniciosos;": "Ações prejudiciais à estrutura física/química do solo [cite: 241, 1037]",
    "e) Utilização indevida de técnicas ou produtos fertilizantes e fitofarmacêuticos;": "Uso de químicos fora das normas técnicas [cite: 244, 1038]",
    "f) Deposição, abandono ou depósito de entulhos, sucatas ou quaisquer outros resíduos.": "Deposição de resíduos de construção ou veículos em fim de vida [cite: 245, 1039]"
}

# Transcrição Integral: Utilizações Permitidas - Artigo 22.º (Cruzado com Portaria 162/2011)
ran_utilizacoes_permitidas = {
    "a) Obras com finalidade agrícola, quando integradas na gestão das explorações ligadas à actividade agrícola, nomeadamente, obras de edificação, obras hidráulicas, vias de acesso, aterros e escavações, e edificações para armazenamento ou comercialização;": "Portaria 162/2011: Implantação ≤ 1% da exploração (máx 750m2). Apoios ≤ 40m2 [cite: 249, 1043, 1449]",
    "b) Construção ou ampliação de habitação para residência própria e permanente de agricultores em exploração agrícola;": "Portaria 162/2011: ATI máxima de 300m2. Requer prova de rendimento agrícola [cite: 250, 1044, 1474]",
    "c) Construção ou ampliação de habitação para residência própria e permanente dos proprietários e respectivos agregados familiares, com os limites de área e tipologia estabelecidos no regime da habitação a custos controlados...": "Portaria 162/2011: ATI máxima de 300m2 [cite: 251, 1045, 1481]",
    "d) Instalações ou equipamentos para produção de energia a partir de fontes de energia renováveis;": "Requer projeto de recuperação dos solos para parecer da DRAP [cite: 252, 1046, 1497]",
    "e) Prospecção geológica e hidrogeológica e exploração de recursos geológicos, e respectivos anexos de apoio à exploração, respeitada a legislação específica...": "Planos de lavra e PARP devem ter parecer da DRAP [cite: 253, 1048, 1516]",
    "f) Estabelecimentos industriais, comerciais ou de serviços complementares à actividade agrícola, tal como identificados no regime de licenciamento aplicável;": "Pelo menos 50% da capacidade para produtos da própria exploração [cite: 254, 1049, 1537]",
    "g) Empreendimentos de turismo no espaço rural e de turismo de habitação, bem como empreendimentos reconhecidos como turismo de natureza, complementares à actividade agrícola;": "Área de implantação total ≤ 600m2 [cite: 255, 1050, 1543]",
    "h) Instalações de recreio e lazer complementares à actividade agrícola e ao espaço rural;": "Estruturas amovíveis e necessidade justificada pela atividade [cite: 256, 1051, 1550]",
    "i) Instalações desportivas especializadas destinadas à prática de golfe, com parecer favorável pelo Turismo de Portugal, I. P., desde que não impliquem alterações irreversíveis na topografia...": "Sem alterações irreversíveis na topografia [cite: 257, 1052, 1559]",
    "j) Obras e intervenções indispensáveis à salvaguarda do património cultural, designadamente de natureza arqueológica, recuperação paisagística ou medidas de minimização...": "Determinadas pelas autoridades competentes [cite: 258, 1053, 1566]",
    "l) Obras de construção, requalificação ou beneficiação de infra-estruturas públicas rodoviárias, ferroviárias, aeroportuárias, de logística, de saneamento, de transporte e distribuição de energia eléctrica...": "Justificação da localização e medidas de minimização de ocupação RAN [cite: 259, 1054, 1572]",
    "m) Obras indispensáveis para a protecção civil;": "Sem alternativa viável fora da RAN e parecer da Proteção Civil [cite: 261, 1055, 1593]",
    "n) Obras de reconstrução e ampliação de construções já existentes, desde que estas já se destinassem e continuem a destinar-se a habitação própria;": "Portaria 162/2011: ATI total de impermeabilização ≤ 300m2 [cite: 262, 1055, 1600]",
    "o) Obras de captação de águas ou de implantação de infra-estruturas hidráulicas;": "Necessidade justificada e medidas de minimização de escavação [cite: 263, 1056, 1607]",
    "p) Obras decorrentes de exigências legais supervenientes relativas à regularização de actividades económicas previamente exercidas.": "Novo enquadramento pelo DL 199/2015 [cite: 705, 1057]"
}

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

# 💰 MATRIZ JURÍDICA DE SANÇÕES ATUALIZADA
matriz_sancionatoria = {
    "REN": {
        "Diploma": "DL 166/2008 (Art. 43.º) e Lei 50/2006",
        "Pessoa Singular": "2.000€ a 37.500€ (Contraordenação Muito Grave)",
        "Pessoa Coletiva": "12.000€ a 2.500.000€ (Conforme dimensão da empresa)"
    },
    "RAN": {
        "Diploma": "DL 73/2009 (Art. 39.º) atualizado pelo DL 199/2015",
        "Interdições/Utilizações": "1.000€ a 3.500€ (Singular) | 1.000€ a 35.000€ (Coletiva)",
        "Deveres Acessórios": "500€ a 1.750€ (Singular) | 500€ a 17.500€ (Coletiva)"
    },
    "NATURA 2000": {
        "Diploma": "DL 140/99 (Art. 30.º) e Lei 50/2006 (Lei de Bases do Ambiente)",
        "Pessoa Singular": "2.000€ a 37.500€ (Contraordenação Muito Grave)",
        "Pessoa Coletiva": "12.000€ a 5.000.000€ (Conforme gravidade e índice de faturação)"
    }
}

# 🏛️ ORDENAMENTO DO TERRITÓRIO (PDM - Regime Jurídico IGT)
pdm_classes_solo = [
    "🏙️ Solo Urbano - Áreas Edificadas (Consolidadas/A expandir)",
    "🏙️ Solo Urbano - Áreas de Atividades Económicas",
    "🏙️ Solo Urbano - Espaços Verdes/Utilização Pública",
    "🌳 Solo Rústico - Espaços Agrícolas (Fora da RAN)",
    "🌲 Solo Rústico - Espaços Florestais (Produção/Conservação)",
    "🏔️ Solo Rústico - Espaços Naturais e de Proteção",
    "🏭 Solo Rústico - Áreas de Exploração de Recursos Geológicos",
    "🏚️ Solo Rústico - Aglomerados Rurais"
]
# --- INTERFACE ---
st.title("🛡️ Sistema de Fiscalização: Master Território e Ambiente")

tabs = st.tabs(["📍 Identificação", "💧 REN", "🌿 Natura & AP", "🌾 RAN", "🏛️ Património", "🌊 Recursos Hídricos", "🗺️ PDM", "📑 Informação Técnica"])

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
        # CORREÇÃO: Variável renomeada para desc_detalhada para evitar o NameError
        desc_detalhada = st.text_area("📝 Descrição Detalhada dos Factos", placeholder="Descreva o que observou no terreno...")

with tabs[1]:
    # Interruptor mestre para REN
    incide_ren = st.toggle("🚨 A infração localiza-se em área de REN?", key="switch_ren")
    
    if incide_ren:
        st.info("**Regime Jurídico da REN (DL 166/2008 atualizado pelo DL 239/2012)**")
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.subheader("1. Tipologias da REN")
            with st.expander("🌊 Áreas de Proteção do Litoral"):
                sel_litoral = st.multiselect("Subtipologias:", list(ren_litoral_dict.keys()), key="ren_litoral")
            with st.expander("💧 Ciclo Hidrológico Terrestre"):
                sel_hidro = st.multiselect("Subtipologias:", list(ren_hidro_dict.keys()), key="ren_hidro")
            with st.expander("⚠️ Prevenção de Riscos Naturais"):
                sel_riscos = st.multiselect("Subtipologias:", list(ren_riscos_dict.keys()), key="ren_riscos")
            
            sel_ren = sel_litoral + sel_hidro + sel_riscos
            st.write("**Interdições Gerais Observadas:**")
            sel_inter_ren = [i for i in ren_interdicoes_gerais if st.checkbox(i, key=f"int_ren_{i}")]
        with col_t2:
            st.subheader("2. Regime de Controlo")
            sel_regime_ren = st.radio("Enquadramento da Ação:", ren_regimes_controlo)
            c_previa_ren = st.checkbox("Falta de Comunicação Prévia", key="cp_ren")
            p_apa_ren = st.checkbox("Falta de Parecer/Autorização", key="p_ren")
            lim_area_ren = st.checkbox("Violação de índices (Portaria 419/2012)", key="lim_ren")
    else:
        st.warning("Área de REN não selecionada. Esta secção será omitida do relatório.")
        sel_ren, sel_inter_ren, sel_regime_ren = [], [], "N/A"
        c_previa_ren, p_apa_ren, lim_area_ren = False, False, False

with tabs[2]:
    incide_natura = st.toggle("🌿 A infração localiza-se em Rede Natura 2000 / AP?", key="switch_natura")
    
    if incide_natura:
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
    else:
        st.warning("Área Natura 2000 não selecionada.")
        sel_zec, sel_rnap, sel_art9, sel_zon = [], [], [], []

with tabs[3]:
    incide_ran = st.toggle("🌾 A infração localiza-se em área de RAN?", key="switch_ran")
    
    if incide_ran:
        st.info("**Reserva Agrícola Nacional (Decreto-Lei n.º 73/2009 e republicação pelo DL 199/2015)**")
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            st.subheader("1. Ações Interditas (Texto Integral Art. 21.º)")
            sel_inter_ran = [k for k in ran_interdicoes_dict.keys() if st.checkbox(k, key=f'ran_int_{k[:5]}')]
            
            st.subheader("2. Pretensão de Enquadramento (Art. 22.º)")
            sel_util_ran = st.multiselect(
                "Ação enquadrada em qual alínea de utilização permitida?", 
                list(ran_utilizacoes_permitidas.keys()),
                key="util_ran_sel"
            )
        with col_r2:
            st.subheader("3. Verificação de Limites (Portaria 162/2011)")
            viola_ati = st.checkbox("Violação de Área (Excede 300m² para habitação ou 750m² para armazéns) [cite: 1449, 1474, 1600]")
            falta_parecer_ran = st.checkbox("Falta de Parecer Prévio Vinculativo da Entidade Regional [cite: 267, 1063]")
            viola_permeabilidade = st.checkbox("Uso de pavimentos não permeáveis em vias de acesso [cite: 1458]")
            
            st.write("---")
            if sel_util_ran:
                for util in sel_util_ran:
                    st.caption(f"🛡️ **Condicionante Técnica:** {ran_utilizacoes_permitidas[util]}")
    else:
        st.warning("Área de RAN não selecionada.")
        sel_inter_ran, sel_util_ran = [], []
with tabs[4]:
    st.warning("**Património Cultural (Lei 107/2001 - Bases da Política e do Regime de Proteção)**")
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Interdições e Condicionantes**")
        sel_pat_int = [i for i in patrimonio_interdicoes if st.checkbox(i, key=f'pat_int_{i}')]
        sel_pat_cond = [i for i in patrimonio_condicionantes if st.checkbox(i, key=f'pat_cond_{i}')]
    with col2:
        st.write("**Deveres do Proprietário e Arqueologia**")
        sel_pat_dev = [i for i in patrimonio_deveres if st.checkbox(i, key=f'pat_dev_{i}')]
        obs_pat = st.text_area("Notas Técnicas (Estado de conservação, tipologia do bem, etc.):")
    
    st.divider()
    st.info("ℹ️ **Nota Jurídica:** Licenças municipais que infrinjam estas normas são nulas (Art. 4.º e 5.º da Lei 107/2001).")
	
with tabs[5]:
    st.info("**Recursos Hídricos (Lei da Água - Lei n.º 58/2005)**")
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Interdições e Utilizações Principais**")
        sel_rh_int = [i for i in rh_interdicoes if st.checkbox(i, key=f'rh_int_{i}')]
    with col2:
        st.write("**Zonas de Proteção e Condicionantes**")
        sel_rh_cond = [i for i in rh_condicionantes if st.checkbox(i, key=f'rh_cond_{i}')]
        obs_rh = st.text_area("Notas sobre o Meio Hídrico (Caudal, poluição, etc.):")
    st.divider()
    st.warning("ℹ️ Nota: Verifique a servidão de margem (Art. 21.º da Lei da Água).")
with tabs[6]:
    st.info("**Ordenamento do Território (Plano Diretor Municipal - PDM)**")
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Classes e Categorias de Espaço (PDM)**")
        sel_pdm = st.multiselect("Selecione a classificação do solo no local:", pdm_classes_solo)
        confo_pdm = st.radio("Conformidade com o Plano:", ["Em conformidade", "Não conforme (Uso não previsto)", "Uso condicionado (Falta de título)"])
    with col2:
        st.write("**Documentação de Suporte**")
        upload_pdm = st.file_uploader("📂 Carregar Regulamento do PDM (PDF)", type=['pdf'], key="pdm_reg")
        artigo_pdm = st.text_input("Artigo(s) do Regulamento aplicável(eis):", placeholder="Ex: Artigo 45.º")
    
    desc_pdm = st.text_area(
        "📝 Análise Técnica de Enquadramento no PDM", 
        placeholder="Descreva a violação dos índices urbanísticos ou afastamentos...",
        height=100
    )
    st.divider()

with tabs[7]:
    st.subheader("🛠️ Medidas de Minimização Propostas")
    sel_medidas = [i for i in medidas_minimizacao if st.checkbox(i, key=f'med_{i}')]
    texto_adicional_medidas = st.text_area("Prescrições técnicas específicas:")
    
    st.divider()
    st.subheader("🏁 Finalização e Geração")
    gravidade = st.select_slider("Gravidade Proposta", options=["Leve", "Grave", "Muito Grave"])
    r_crime = st.checkbox("⚠️ Suspeita de Crime (Art. 278.º Código Penal)")
    beneficio_economico = st.checkbox("Benefício económico mensurável?")
    reincidencia = st.checkbox("Reincidência por parte do infrator?")

    st.write("---")
    st.subheader("⚖️ Regimes Sancionatórios Ativados")
    col_reg1, col_reg2 = st.columns(2)
    with col_reg1:
        if sel_ren: st.warning(f"🔹 **REN:** {matriz_sancionatoria['REN']}")
        if sel_inter_ran: st.warning(f"🔹 **RAN:** {matriz_sancionatoria['RAN']}")
    with col_reg2:
        if sel_zec or sel_art9: st.warning(f"🔹 **Natura 2000:** {matriz_sancionatoria['NATURA 2000']}")
        if sel_rh_int or sel_rh_cond: st.warning(f"🔹 **Água:** {matriz_sancionatoria['AGUA']}")

    # Função interna para exportação
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

    if st.button("🚀 Gerar Informação Técnica Fundamentada"):
        if not api_key:
            st.error("Falta a API Key.")
        else:
            with st.spinner("A analisar conformidade legal e regimes sancionatórios..."):
                model = genai.GenerativeModel(modelo_selecionado)
                
                # Contexto condicional para Natura 2000
                contexto_natura = ""
                if incide_natura:
                    contexto_natura = f"""
                    REDE NATURA 2000 / ÁREAS PROTEGIDAS:
                    - Sítios ZEC/ZPE: {sel_zec}
                    - Áreas Protegidas (RNAP): {sel_rnap}
                    - Condicionantes Art. 9.º n.º 2 (DL 140/99): {sel_art9}
                    - Zonamento: {sel_zon}
                    """

                # Contexto condicional para RAN com cruzamento Portaria 162/2011
                contexto_ran = ""
                if incide_ran:
                    contexto_ran = f"""
                    RESERVA AGRÍCOLA NACIONAL (RAN) - DL 73/2009 e DL 199/2015:
                    - Ações Interditas Selecionadas (Art. 21.º): {sel_inter_ran}
                    - Pretensão de Uso Selecionada (Art. 22.º): {sel_util_ran}
                    - Incumprimentos Técnicos (Portaria 162/2011): 
                        * Violação de Áreas Máximas (ATI): {viola_ati}
                        * Falta de Parecer Prévio Vinculativo: {falta_parecer_ran}
                        * Inexistência de Prova de Alternativa: {falta_alternativa}
                    """

                prompt = f"""
                Age como Perito Técnico Sénior e Jurista especializado em Direito do Ambiente e Ordenamento do Território.
                O teu objetivo é redigir uma INFORMAÇÃO TÉCNICA FUNDAMENTADA detalhada, estruturada para um processo de fiscalização.

                DADOS DO INFRACTOR E LOCAL:
                - Localidade: {local} (Coordenadas: {lat}/{lon}). Área afetada: {area_m2}m2.
                - Interessado: {inf_nome}, NIF: {inf_nif}, Tipo: {tipo_ent}.

                DESCRIÇÃO DOS FACTOS:
                {desc_detalhada}

                MATRIZ LEGAL DE ANÁLISE:
                - REN: {sel_ren if incide_ren else 'N/A'}.
                {contexto_ran}
                {contexto_natura}
                - PDM: Classe={sel_pdm}. Conformidade={confo_pdm}. Análise Técnica={desc_pdm}.

                VALORES DE COIMAS PARA ENQUADRAMENTO:
                {matriz_sancionatoria}

                ESTRUTURA OBRIGATÓRIA DO DOCUMENTO:
                1. **OBJETIVO**: Análise da conformidade legal das ações e apuramento de responsabilidade contraordenacional.
                2. **DESCRIÇÃO TÉCNICA DOS FACTOS**: Relato pormenorizado das ações observadas.
                3. **FUNDAMENTAÇÃO JURÍDICA E TRANSGRESSÕES**:
                   - **PARA A RAN**: Identificar as violações ao Decreto-Lei n.º 73/2009 (republicado pelo DL 199/2015). 
                     * Transcrever na íntegra a alínea violada do Artigo 21.º.
                     * Se houver pretensão de uso do Artigo 22.º, demonstrar tecnicamente o incumprimento dos requisitos da Portaria n.º 162/2011.
                   - **PARA A REN**: Citar o DL 166/2008 e as interdições violadas.
                   - **PARA REDE NATURA 2000**: Citar o DL 140/99 e a violação das condicionantes do Art. 9.º n.º 2.
                4. **QUADRO SANCIONATÓRIO E NULIDADES**:
                   - Indicar que atos administrativos em violação da RAN são **NULOS** (Art. 38.º do DL 73/2009).
                   - Apresentar os valores das coimas aplicáveis em abstrato com base no tipo de infrator ({tipo_ent}) e na gravidade ({gravidade}).
                   - Referir que, para RAN, a coima para interdições (Art. 39.º) varia entre 1.000€ e 3.500€ (Singular) ou 35.000€ (Coletiva).
                   - Referir a remissão para a Lei 50/2006 (REN/Natura 2000).
                5. **PARECER FINAL E MEDIDAS DE REPOSIÇÃO**: Propor a cessação imediata e as medidas: {sel_medidas}. Mencionar a obrigação de reposição da legalidade (Art. 44.º do RJran).

                ESTILO: Formal, PT-PT, capítulos a BOLD. Texto rigoroso e pronto para assinatura técnica.
                """
                
                try:
                    res = model.generate_content(prompt).text
                    st.success("Informação Técnica Gerada com Sucesso!")
                    st.download_button("📥 Descarregar Documento (Word)", export_docx(res), file_name=f"Relatorio_Fiscalizacao_{local}.docx")
                    st.write(res)
                except Exception as e:
                    st.error(f"Erro na geração do documento: {e}")

