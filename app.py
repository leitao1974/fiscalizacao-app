def gerar_word(resultados, analise_uso, area_total):
    doc = Document()
    
    # Cabeçalho Profissional
    doc.add_heading('Relatório Técnico de Fiscalização Territorial', 0)
    
    # 1. Enquadramento e Metodologia
    doc.add_heading('1. Identificação da Área e Metodologia', level=1)
    p = doc.add_paragraph()
    p.add_run('Data da Análise: ').bold = True
    p.add_run(date.today().strftime('%d/%m/%Y'))
    
    p = doc.add_paragraph()
    p.add_run('Área Total do Polígono: ').bold = True
    p.add_run(f'{area_total:.2f} m²')
    
    doc.add_paragraph(
        "A presente análise foi efetuada através de cruzamento geospacial automático entre o polígono "
        "fornecido e as bases de dados oficiais da DGT (COS 2023) e do SNIG (REN, RAN e Rede Natura 2000)."
    )

    # 2. Verificação de Alteração do Uso do Solo (COS)
    doc.add_heading('2. Análise de Ocupação do Solo (COS 2023)', level=1)
    doc.add_paragraph(analise_uso)
    if "DIVERGÊNCIA" in analise_uso:
        doc.add_paragraph(
            "Fundamentação: A discrepância entre o uso cartografado e o uso detetado constitui um indício de "
            "infração ao regime de uso e ocupação do solo, podendo configurar uma alteração ilícita sem o "
            "devido licenciamento municipal ou setorial."
        )

    # 3. Análise Jurídica das Servidões e Restrições
    doc.add_heading('3. Análise Jurídica de Servidões e Restrições', level=1)
    
    if not resultados:
        doc.add_paragraph("Não foram detetadas sobreposições com regimes de proteção ambiental ou agrícola.")
    else:
        for res in resultados:
            doc.add_heading(f"Regime: {res['Regime']}", level=2)
            
            # Dados técnicos
            p = doc.add_paragraph()
            p.add_run(f"Área intersetada: {res['Área (m2)']} m² ({res['Percentagem']}% da área total).").italic = True
            
            # Corpo Jurídico por Regime
            if res['Regime'] == "REN":
                doc.add_paragraph(
                    "Enquadramento Legal: Regime Jurídico da Reserva Ecológica Nacional (DL n.º 166/2008, de 22 de agosto, na redação atual).\n"
                    "Análise: A REN é uma restrição de utilidade pública que visa a proteção de ecossistemas e a prevenção de riscos naturais. "
                    "Nos termos do Artigo 20.º, são proibidas ações de loteamento, obras de urbanização, construção e alteração do relevo natural. "
                    "Qualquer exceção requer parecer prévio vinculativo da CCDR territorialmente competente (Artigo 21.º)."
                )
            
            elif res['Regime'] == "RAN":
                doc.add_paragraph(
                    "Enquadramento Legal: Regime Jurídico da Reserva Agrícola Nacional (DL n.º 73/2009, de 31 de março).\n"
                    "Análise: Os solos da RAN destinam-se exclusivamente à exploração agrícola. A utilização para fins não agrícolas (como edificações) "
                    "é proibida nos termos do Artigo 22.º, salvo situações excecionais devidamente autorizadas pela Entidade Regional da RAN "
                    "ou pela DGADR, sob pena de nulidade dos atos de licenciamento."
                )
            
            elif res['Regime'] == "Rede Natura":
                doc.add_paragraph(
                    "Enquadramento Legal: Plano de Gestão da Rede Natura 2000 (DL n.º 142/2008, de 24 de julho).\n"
                    "Análise: Sendo uma área integrada na Rede Natura 2000, qualquer ação ou projeto suscetível de afetar a integridade "
                    "dos habitats ou espécies protegidas deve ser submetido a uma Avaliação de Incidências Ambientais (AIA) junto do ICNF, "
                    "conforme as diretrizes das Diretivas Aves e Habitats."
                )

    # 4. Conclusões e Recomendações
    doc.add_heading('4. Conclusões e Medidas de Tutela', level=1)
    doc.add_paragraph(
        "Face ao exposto, recomenda-se:\n"
        "1. A verificação da existência de processos de licenciamento ou autorização prévia nos serviços municipais.\n"
        "2. Caso as obras/ações não possuam título autorizativo, deverá proceder-se ao levantamento do respetivo Auto de Notícia.\n"
        "3. A notificação dos proprietários para a reposição da situação anterior, se aplicável."
    )

    fname = "Relatorio_Fiscalizacao_Final.docx"
    doc.save(fname)
    return fname

