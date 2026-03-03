import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
import re

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

ren_litoral = ["Faixa marítima de proteção", "Praias", "Barreiras detríticas", "Tômbolos", "Sapais", "Ilhéus", "Dunas", "Arribas", "Faixa terrestre", "Águas de transição"]
ren_hidro = ["Cursos de água", "Lagoas e lagos", "Albufeiras", "Áreas de recarga de aquíferos"]
ren_riscos = ["Zonas adjacentes", "Zonas ameaçadas pelo mar", "Zonas ameaçadas pelas cheias", "Elevado risco de erosão", "Instabilidade de vertentes"]

zec_zpe_lista = ["ZEC Serra de Aire e Candeeiros", "ZEC Serra da Estrela", "ZEC Rio Zêzere", "ZEC Albufeira de Castelo do Bode", "ZEC Sicó/Alvaiázere", "ZEC Serra da Lousã", "ZEC Rio Vouga", "ZEC Rio Paiva", "ZEC Arrábida/Espichel", "ZEC Estuário do Tejo", "ZEC Monfurado", "ZEC Costa Vicentina", "ZEC Sintra-Cascais", "ZPE Paul do Boquilobo", "ZPE Estuário do Mondego", "ZPE Lagoa de Albufeira", "ZPE Douro Internacional", "ZPE Castro Verde", "ZPE Ria de Aveiro", "ZPE Beira Interior"]

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

rnap_lista = ["Parque Natural das Serras de Aire e Candeeiros", "Parque Natural da Serra da Estrela", "Parque Natural do Tejo Internacional", "Parque Natural do Douro Internacional", "Reserva Natural do Paul do Boquilobo", "Reserva Natural da Serra da Malcata", "Reserva Natural das Berlengas", "Reserva Natural do Paul de Arzila", "Reserva Natural das Dunas de São Jacinto", "Paisagem Protegida da Serra do Açor", "Monumento Natural do Cabo Mondego", "Monumento Natural das Pegadas de Dinossáurios de Ourém/Torres Novas"]

zonamento_tipologias = ["Reserva Integral", "Reserva Parcial I", "Reserva Parcial II", "Proteção Parcial I", "Proteção Parcial II", "Proteção Complementar I", "Proteção Complementar II", "Área de Intervenção Específica", "Zona de Proteção Estrita", "Zona de Proteção de Albufeira"]

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

medidas_minimizacao = [
    "🌱 Reposição da topografia original e do coberto vegetal autóctone",
    "🧱 Utilização de pavimentos permeáveis ou semipermeáveis",
    "🌳 Criação de cortinas arbóreas para integração paisagística",
    "💧 Implementação de sistemas de retenção e infiltração de águas pluviais",
    "🏗️ Redução da área de impermeabilização ou da cércea da edificação",
    "🚧 Remoção imediata de entulhos e resíduos de construção",
    "🛡️ Instalação de barreiras acústicas ou de contenção de poeiras"
]

matriz_sancionatoria = {
    "REN": "DL 166/2008, Art. 43.º",
    "RAN": "DL 73/2009, Art. 43.º",
    "NATURA 2000": "DL 140/99, Art. 30.º / Lei 50/2006",
    "AGUA": "Lei 58/2005, Art. 95.º e 96.º / Lei 50/2006"
}

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
        lim_apoio = st.checkbox("Apoio Agrícola > 750m² ou >1% da área")
        lim_hab = st.checkbox("Habitação Agricultor > 300m²")
        lim_vias = st.checkbox("Vias de acesso > 5m ou pavimento impermeável")
        falta_alt = st.checkbox("Falta de prova de inexistência de alternativa fora da RAN")

with tabs[4]:
    st.warning("**Património Cultural (Lei 107/2001)**")
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Interdições e Condicionantes**")
        sel_pat_int = [i for i in patrimonio_interdicoes if st.checkbox(i)]
        sel_pat_cond = [i for i in patrimonio_condicionantes if st.checkbox(i)]
    with col2:
        st.write("**Deveres do Proprietário e Arqueologia**")
        sel_pat_dev = [i for i in patrimonio_deveres if st.checkbox(i)]
        obs_pat = st.text_area("Notas Técnicas (Estado de conservação, tipologia, etc.):")
    st.divider()
    st.info("ℹ️ Nota Jurídica: Licenças que infrinjam estas normas são nulas (Art. 4.º e 5.º Lei 107/2001).")

with tabs[5]:
    st.info("**Recursos Hídricos (Lei da Água - Lei n.º 58/2005)**")
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Interdições e Utilizações**")
        sel_rh_int = [i for i in rh_interdicoes if st.checkbox(i)]
    with col2:
        st.write("**Zonas de Proteção**")
        sel_rh_cond = [i for i in rh_condicionantes if st.checkbox(i)]
        obs_rh = st.text_area("Notas sobre o Meio Hídrico:")
    st.divider()
    st.warning("ℹ️ Verifique a titularidade e a servidão de margem (Art. 21.º Lei da Água).")

with tabs[6]:
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
            with st.spinner("A gerar relatório jurídico..."):
                model = genai.GenerativeModel(modelo_selecionado)
                prompt = f"""
                Age como Fiscal Sénior e Jurista. Redigi Relatório e Auto de Notícia.
                DADOS: Local {local}, GPS: {lat}, {lon}. Área {area_m2}m2.
                INFRATOR: {inf_nome}, NIF: {inf_nif}, Tel: {inf_tel} ({tipo_ent}).
                
                ENQUADRAMENTO:
                - REN: {sel_ren}. Interdições: {c_previa}/{p_apa}.
                - Natura 2000: {sel_zec}. Zonamento: {sel_zon}. Art 9º nº 2: {sel_art9}.
                - RAN: Interdições={sel_ran_int}, Condicionantes={sel_ran_cond}. Limites={lim_apoio}/{lim_hab}/{lim_vias}.
                - PATRIMÓNIO: {sel_pat_int}/{sel_pat_cond}. Deveres={sel_pat_dev}. Notas={obs_pat}.
                - RECURSOS HÍDRICOS: {sel_rh_int}/{sel_rh_cond}. Notas={obs_rh}.
                - MINIMIZAÇÃO: {sel_medidas}. Notas={texto_adicional_medidas}.
                - CRIME Art 278 CP: {r_crime}. Reincidência: {reincidencia}. Benefício: {beneficio_economico}.
                
                INSTRUÇÕES SANCIONATÓRIAS:
                1. REN: Aplica Art. 43º DL 166/2008.
                2. RAN: Aplica Art. 43º DL 73/2009 (Singulares: 250€-3740€; Coletivas: até 44890€).
                3. NATURA: Lei 50/2006 (Art. 30º DL 140/99).
                4. ÁGUA: Lei 50/2006 (Art. 96º Lei 58/2005).
                5. GRADUAÇÃO: Gravidade {gravidade}, Infrator {tipo_ent}. Benefício Económico elevado ao terço superior.
                6. SANÇÕES ACESSÓRIAS: Suspensão e reposição (Art. 30º Lei 50/2006).
                7. ESTILO: Formal, PT-PT, BOLD nos capítulos.
                """
                try:
                    res = model.generate_content(prompt).text
                    st.success("Pronto!")
                    st.download_button("📥 Descarregar Word", export_docx(res), file_name=f"Fiscalizacao_{local}.docx")
                    st.write(res)
                except Exception as e:
                    st.error(f"Erro: {e}")

