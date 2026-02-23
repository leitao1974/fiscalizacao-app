import streamlit as st
import geopandas as gpd
import os
from docx import Document

# ... (restante do código anterior)

def realizar_analise_completa(user_gdf, path_cos, path_ren, path_ran, path_natura):
    resultados = []
    
    # 1. Cruzamento com a COS (Alteração de Uso do Solo)
    analise_uso = "Não analisado"
    if os.path.exists(path_cos):
        cos_gdf = gpd.read_file(path_cos).to_crs(user_gdf.crs)
        inter_cos = gpd.overlay(user_gdf, cos_gdf, how='intersection')
        
        if not inter_cos.empty:
            # Pegamos o valor dominante ou o primeiro encontrado
            uso_oficial = inter_cos['COS23_n4_L'].iloc[0]
            uso_fiscalizacao = inter_cos['tipo_obra'].iloc[0]
            
            if uso_oficial != uso_fiscalizacao:
                analise_uso = f"⚠️ INCOERÊNCIA: Oficial (COS) é '{uso_oficial}' mas detetado '{uso_fiscalizacao}'."
                st.error(analise_uso)
            else:
                analise_uso = f"✅ Coerente: O uso '{uso_fiscalizacao}' coincide com a COS."
                st.success(analise_uso)
    
    # 2. Interseção com Regimes (REN, RAN, Natura)
    # [Lógica de interseção espacial que já definimos anteriormente]
    # ... 

    return analise_uso, resultados

# --- Na parte de gerar o WORD ---
def atualizar_relatorio_word(analise_uso, resultados_regimes, area_total):
    doc = Document()
    doc.add_heading('Relatório de Fiscalização e Conformidade', 0)
    
    # Secção COS
    doc.add_heading('1. Análise de Uso do Solo (COS 2023)', level=1)
    doc.add_paragraph(analise_uso)
    
    # Secção Regimes Jurídicos
    doc.add_heading('2. Servidões e Restrições (REN/RAN/Natura)', level=1)
    # ... (tabela de áreas que fizemos antes)
    
    doc.save("Relatorio_Final.docx")
