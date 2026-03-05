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

# 🌿 REDE NATURA 2000 - REGIÃO CENTRO (SIC/ZEC e ZPE - Listagem Consolidada ICNF)
zec_zpe_lista = [
    "ZEC Serra de Aire e Candeeiros", "ZEC Serra da Estrela", "ZEC Rio Zêzere", 
    "ZEC Albufeira de Castelo do Bode", "ZEC Sicó/Alvaiázere", "ZEC Serra da Lousã", 
    "ZEC Rio Vouga", "ZEC Rio Paiva", "ZEC Arrábida/Espichel", "ZEC Estuário do Tejo", 
    "ZEC Monfurado", "ZEC Costa Vicentina", "ZEC Sintra-Cascais", "ZEC Montejunto",
    "ZEC Peniche", "ZEC Berlengas", "ZEC Dunas de Mira, Gândara e Gafanhas", 
    "ZEC Serras de Socorro e Archeira", "ZEC Arquipélago das Berlengas (Marinha)",
    "ZEC São Pedro de Moel", "ZEC Complexo do Alviela", "ZEC Ribeira de Alge",
    "ZPE Paul do Boquilobo", "ZPE Estuário do Mondego", "ZPE Lagoa de Albufeira", 
    "ZPE Douro Internacional", "ZPE Castro Verde", "ZPE Ria de Aveiro", 
    "ZPE Beira Interior (Tejo Internacional e Erges)", "ZPE Serra da Gardunha",
    "ZPE Serra da Lousã", "ZPE Paul de Arzila", "ZPE Paul do Taipal",
    "ZPE Serra da Estrela (Cumes e Planalto Superior)", "ZPE Arquipélago das Berlengas"
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

# 🌾 RAN - MATRIZ TÉCNICA REFINADA (DL 199/2015 + Portaria 162/2011)
ran_interdicoes_gerais = [
    "🏗️ Operações de loteamento e urbanização",
    "🧱 Obras de construção ou ampliação (sem enquadramento)",
    "🛣️ Instalação de vias de comunicação e acessos",
    "🚜 Escavações e aterros que alterem o perfil do solo",
    "🪓 Destruição do revestimento vegetal (não agrícola/florestal)"
]

ran_limites_dict = {
    "Habitação Própria": "ATI Máxima: 500 m²",
    "Turismo em Espaço Rural (TER)": "Máximo 20% da área (limite 5.000 m²)",
    "Unidades Agro-industriais": "Máximo 10% da área (limite 2.000 m²)",
    "Apoios Agrícolas": "Área de implantação ≤ 40 m²",
    "Cabinas de Rega": "Área inferior a 4 m²",
    "Muros de Suporte": "Limite à cota do terreno ou +0,20m"
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

# 💰 MATRIZ JURÍDICA DE SANÇÕES
matriz_sancionatoria = {
    "REN": "DL 166/2008, Art. 43.º (Contraordenações Graves ou Muito Graves)",
    "RAN": "DL 73/2009, Art. 43.º (Coimas de 250€ a 3.740€ para pessoas singulares e até 44.890€ para coletivas)",
    "NATURA 2000": "DL 140/99, Art. 30.º (Remete para a Lei 50/2006)",
    "AGUA": "Lei 58/2005, Art. 95.º e 96.º (Remete para o regime da Lei 50/2006)"
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
        desc_visual = st.text_area("Notas de Campo")

with tabs[1]:
    st.info("**Regime Jurídico da REN (DL 166/2008 atualizado pelo DL 239/2012)**")
    
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.subheader("1. Tipologias da REN")
        
        with st.expander("🌊 1. Áreas de Proteção do Litoral"):
            sel_litoral = st.multiselect("Selecione as subtipologias:", list(ren_litoral_dict.keys()))
            
        with st.expander("💧 2. Ciclo Hidrológico Terrestre"):
            sel_hidro = st.multiselect("Selecione as subtipologias:", list(ren_hidro_dict.keys()))
            
        with st.expander("⚠️ 3. Prevenção de Riscos Naturais"):
            sel_riscos = st.multiselect("Selecione as subtipologias:", list(ren_riscos_dict.keys()))
            
        # Unificar as seleções para o prompt
        sel_ren = sel_litoral + sel_hidro + sel_riscos
        
        st.write("---")
        st.write("**Interdições Gerais Observadas:**")
        sel_inter_ren = [i for i in ren_interdicoes_gerais if st.checkbox(i)]
        
    with col_t2:
        st.subheader("2. Regime de Controlo")
        sel_regime_ren = st.radio("Enquadramento da Ação:", ren_regimes_controlo)
        st.write("---")
        st.write("**Verificação de Conformidade:**")
        c_previa = st.checkbox("Falta de Comunicação Prévia (Obrigatória pós-2012)")
        p_apa = st.checkbox("Falta de Parecer/Autorização (APA/CCDR)")
        lim_area_ren = st.checkbox("Violação de índices (Portaria 419/2012)")
        interesse_publico = st.checkbox("Ação de Relevante Interesse Público s/ Despacho")

    st.divider()
    st.caption("Nota: O DL 239/2012 privilegia a Comunicação Prévia para simplificação administrativa.")

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
    st.info("**Reserva Agrícola Nacional (DL 73/2009 atualizado pelo DL 199/2015)**")
    
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        st.subheader("1. Interdições e Uso do Solo")
        st.write("**Interdições Gerais Observadas:**")
        sel_inter_ran = [i for i in ran_interdicoes_gerais if st.checkbox(i)]
        
        st.divider()
        st.write("**Regime de Controlo Administrativo:**")
        regime_ran = st.radio("Procedimento:", 
            ["Isenção (Reduzido impacto)", "Comunicação Prévia (Prazo 22 dias)", "Relevante Interesse Público (Despacho)"], 
            key="reg_ran")

    with col_t2: # Coluna Direita
        st.subheader("2. Verificação de Limites (Portaria 162/2011)")
        st.write("A pretensão excede os limites máximos?")
        
        # Checkboxes baseadas nos limites da Portaria
        lim_hab = st.checkbox("Habitação: Excede ATI de 500 m²")
        lim_turismo = st.checkbox("Turismo: Excede 20% da área ou 5.000 m²")
        lim_agroind = st.checkbox("Agro-indústria: Excede 10% ou 2.000 m²")
        lim_apoio = st.checkbox("Apoio Agrícola: Área > 40 m²")
        
        st.divider()
        st.write("**Critérios de Rejeição:**")
        falta_alternativa = st.checkbox("Existe alternativa viável fora da RAN")
        impacto_biofisico = st.checkbox("Afeta o equilíbrio do sistema biofísico")
        parecer_apa_neg = st.checkbox("Parecer desfavorável da APA (se aplicável)")

    st.divider()
    st.caption("Nota: A CCDR Centro tem 22 dias para rejeitar a Comunicação Prévia; a ausência de resposta nesse prazo viabiliza a pretensão.")

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
    sel_medidas = [i for i in medidas_minimizacao if st.checkbox(i)]
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
        if sel_ran_int or sel_ran_cond: st.warning(f"🔹 **RAN:** {matriz_sancionatoria['RAN']}")
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
            with st.spinner("A analisar conformidade legal (Anexo II REN, RAN e Água)..."):
                model = genai.GenerativeModel(modelo_selecionado)
                prompt = f"""
                Age como Perito Técnico Sénior e Jurista especializado em Ordenamento do Território. 
                O teu objetivo é redigir uma INFORMAÇÃO TÉCNICA FUNDAMENTADA detalhada.

                DADOS DO LOCAL E INTERESSADO:
                - Localidade: {local}, Coordenadas: {lat}/{lon}. Área afetada: {area_m2}m2.
                - Interessado: {inf_nome}, NIF: {inf_nif}.

                ELEMENTOS DE ANÁLISE SELECIONADOS:
                # No prompt, dentro de ENQUADRAMENTO REN:
                - ÁREAS AFETADAS (SUBTIPOLOGIAS): {sel_ren}.
                - INTERDIÇÕES VIOLADAS (Art. 20º): {sel_inter_ren}.
                - REGIME DE CONTROLO: {sel_regime_ren}.

                # Nas instruções:
                - PARA A REN: Utiliza as definições técnicas das áreas selecionadas (ex: se selecionar 'Arribas', menciona a necessidade de garantir estabilidade e segurança). 
                - Cruza as interdições {sel_inter_ren} com o regime de {sel_regime_ren} para determinar a gravidade da infração.

                # Nas INSTRUÇÕES DE FUNDAMENTAÇÃO:
                - PARA A REN: Analisa se a ação constitui uma violação de Interdição Geral (Art. 20.º) ou apenas falta de título (Comunicação Prévia). 
                - Cita o DL 239/2012 para explicar a simplificação do regime e a obrigatoriamente de controlo sucessivo.
                - Se houver 'Destruição de coberto vegetal', verifica a exceção para explorações agrícolas/florestais correntes.
                - Classifica a gravidade: LEVE (falta de comunicação), GRAVE (falta de autorização), ou MUITO GRAVE (usos interditos ou violação de embargo).
				- REN: {sel_ren}. Ações Anexo II: {sel_comp if 'sel_comp' in locals() else 'Não selecionado'}.
                - NATURA 2000 & AP: {sel_zec} / {sel_rnap}. Condicionantes Art. 9º nº 2: {sel_art9}.
                # No ENQUADRAMENTO RAN do Prompt:
                - INTERDIÇÕES RAN: {sel_inter_ran}.
                - REGIME ESCOLHIDO: {regime_ran}.
                - VIOLAÇÃO DE LIMITES (Portaria 162/2011): Habitação={lim_hab}, Turismo={lim_turismo}, Agroindústria={lim_agroind}, Apoio={lim_apoio}.
                - FATORES DE REJEIÇÃO: Falta Alternativa={falta_alternativa}, Impacto Biofísico={impacto_biofisico}, Parecer APA={parecer_apa_neg}.

                # Nas INSTRUÇÕES DE FUNDAMENTAÇÃO:
                - PARA A RAN: Se houver violação de limites ({lim_hab}, {lim_turismo}, etc.), fundamenta com base na Portaria n.º 162/2011.
                - Menciona a obrigação de preservação da aptidão produtiva do solo conforme o DL 199/2015.
                - Analisa a questão da 'Inexistência de alternativa viável' como critério cumulativo para qualquer uso não agrícola.
                - Refere o prazo de 22 dias de oposição sucessiva da CCDR Centro no regime de Comunicação Prévia.
                - PDM (Ordenamento): Classe={sel_pdm}. Conformidade={confo_pdm}. Artigo={artigo_pdm}.
                - ANÁLISE TÉCNICA PDM: {desc_pdm}
                - RECURSOS HÍDRICOS: {sel_rh_int}/{sel_rh_cond}.
                - MEDIDAS DE REPOSIÇÃO: {sel_medidas}. Notas: {texto_adicional_medidas}.

                ESTRUTURA OBRIGATÓRIA:
                1. OBJETIVO: Análise da conformidade legal face aos regimes de utilidade pública e planos territoriais.
                2. DESCRIÇÃO DOS FACTOS: Relatar tecnicamente as ações observadas.
                3. FUNDAMENTAÇÃO JURÍDICA:
                   - PARA A REN: Citar Declaração de Retificação n.º 63-B/2008 (Anexo II) e Art. 20.º do DL 166/2008.
                   - PARA O PDM: Integrar a análise ({desc_pdm}) e citar o Artigo {artigo_pdm} do Regulamento Municipal.
                   - PARA REDE NATURA 2000: Transcrever alíneas do Art. 9.º n.º 2 do DL 140/99.
                   - PARA A RAN: Fundamentar com o Art. 22.º do DL 73/2009.
                4. CONCLUSÃO E PARECER TÉCNICO: Juízo sobre legalidade e possibilidade de reposição.
                5. PRESCRIÇÕES TÉCNICAS: Listar as medidas {sel_medidas}.

                ESTILO: Altamente formal, PT-PT, capítulos a BOLD. SEM proposta de coimas.
                """
                try:
                    res = model.generate_content(prompt).text
                    st.success("Documentação preparada!")
                    st.download_button("📥 Descarregar Word", export_docx(res), file_name=f"Fiscalizacao_{local}.docx")
                    st.write(res)
                except Exception as e:
                    st.error(f"Erro: {e}")







