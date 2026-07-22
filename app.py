def extrair_dados_pdf(texto_bruto):
    dados = []
    periodo_doc = "Período Indefinido"
    match_per = re.search(r'PER[ÍI]ODO DE (\d{2}/\d{2}/\d{4}) [AÀ] (\d{2}/\d{2}/\d{4})', texto_bruto, re.IGNORECASE)
    if match_per: periodo_doc = f"{match_per.group(1)} a {match_per.group(2)}"

    blocos = re.split(r'(?=\b\d{2}/\d{2}/\d{4}\s+\d+)', texto_bruto)
    
    for bloco in blocos:
        if len(bloco.strip()) < 20: continue 
        
        # 1. CÓDIGO DO PACIENTE 
        match_header = re.search(r'(\d{2}/\d{2}/\d{4})\s+(\d+)', bloco)
        if not match_header: continue
        data_pac = match_header.group(1)
        cod_pac = match_header.group(2)

        # 2. SEXO INFERIDO PELO NOME (IA Simbólica Expandida)
        sexo_pac = "Não Informado"
        match_nome = re.search(r'Nome:\s*([^\n]+)', bloco, re.IGNORECASE)
        if match_nome:
            nome = match_nome.group(1).strip().upper()
            primeiro_nome = nome.split()[0].replace(' ', '')
            
            # Verificação Agressiva Feminina
            if primeiro_nome.endswith('A') or primeiro_nome.endswith('I') or primeiro_nome in ['LOURDES', 'STHEFANIE', 'ALINE', 'VIVIANE', 'CARMEM', 'ESTER', 'RUTH', 'STHEF', 'SUELI', 'ROSELI', 'CLEIDE', 'IVONE', 'MIRIAN', 'RAQUEL', 'ELISABETE', 'BEATRIZ', 'IRIS', 'MARGARETE', 'ELIZABETH', 'IRENE', 'DIRCE', 'NEUZA', 'NEUSA', 'TEREZA', 'EUNICE', 'INES', 'INÊS']:
                sexo_pac = "Feminino"
            # Verificação Agressiva Masculina
            elif primeiro_nome.endswith('O') or primeiro_nome in ['LUIS', 'GABRIEL', 'DANIEL', 'IGOR', 'VITOR', 'ARTHUR', 'DAVI', 'RAFAEL', 'MIGUEL', 'LUCAS', 'GIOVANI', 'KAUE', 'THIAGO', 'WILLIAN', 'JEFFERSON', 'JOSE', 'JOSÉ', 'JOAO', 'JOÃO', 'MANUEL', 'MANOEL', 'CARLOS', 'EDSON', 'WAGNER', 'ALEX', 'DOUGLAS', 'VANDERLEI']:
                sexo_pac = "Masculino"
                
            # Trava de Segurança para nomes duplos muito comuns
            if "MARIA " in nome or "ANA " in nome: sexo_pac = "Feminino"
            if "JOSE " in nome or "JOSÉ " in nome or "JOAO " in nome or "JOÃO " in nome: sexo_pac = "Masculino"

        # 3. IDADE 
        idade_pac = "Não Informada"
        match_idade = re.search(r'(?:Idade|I\s*d\s*a\s*d\s*e)[\s:=]*(\d+)', bloco, re.IGNORECASE)
        if match_idade: idade_pac = match_idade.group(1)

        # 4. UNIDADE (Com Fallback e Tolerância a Erros)
        unidade_pac = "Sede / Sem Unidade"
        match_unidade = re.search(r'Unidade:\s*([^\n]+)', bloco, re.IGNORECASE)
        if match_unidade:
            u_str = match_unidade.group(1).upper()
            if "MONTE ALEGRE" in u_str: unidade_pac = "5 - Monte Alegre"
            elif "SERRA NEGRA" in u_str: unidade_pac = "1 - Serra Negra"
            elif "AME" in u_str: unidade_pac = "3 - AME"
            elif "AMPARO" in u_str and "4" in u_str: unidade_pac = "4 - Amparo Unidade 4"
            elif "LIND" in u_str and "AGUAS" not in u_str and "ÁGUAS" not in u_str: unidade_pac = "6 - Lindóia"
            elif "CENAM" in u_str: unidade_pac = "9 - Cenam"
            elif "BPA" in u_str: unidade_pac = "10 - Amparo Unidade BPA"
            elif "AGUAS" in u_str or "ÁGUAS" in u_str: unidade_pac = "12 - Águas de Lindóia"
            else: # Fallback - Caso o nome venha cortado, mas tenha o número da unidade
                if "5" in u_str: unidade_pac = "5 - Monte Alegre"
                elif "1" in u_str and "0" not in u_str and "2" not in u_str: unidade_pac = "1 - Serra Negra"
                elif "3" in u_str: unidade_pac = "3 - AME"
                elif "4" in u_str: unidade_pac = "4 - Amparo Unidade 4"
                elif "6" in u_str: unidade_pac = "6 - Lindóia"
                elif "9" in u_str: unidade_pac = "9 - Cenam"
                elif "10" in u_str: unidade_pac = "10 - Amparo Unidade BPA"
                elif "12" in u_str: unidade_pac = "12 - Águas de Lindóia"

        if unidade_pac == "Excluir": continue 

        linha = {
            "data_exame": data_pac, "codigo_paciente": cod_pac, 
            "idade": idade_pac, "sexo": sexo_pac, "material_exame": "Não Informado", 
            "resultado": "Negativo", "bacteria": "N/A", 
            "indicados_s": "", "resistentes_r": "", 
            "unidade": unidade_pac, "periodo_arquivo": periodo_doc
        }
        
        bloco_limpo = re.sub(r'\s+', ' ', bloco) 
        
        # 5. MATERIAL DO EXAME
        if "URO1" in bloco_limpo or "URINA" in bloco_limpo.upper(): linha["material_exame"] = "Urina"
        elif "HEMOCULTURA" in bloco_limpo.upper() or "SANGUE" in bloco_limpo.upper(): linha["material_exame"] = "Sangue"
        elif "SECRE" in bloco_limpo.upper(): linha["material_exame"] = "Secreção"
        elif "FEZES" in bloco_limpo.upper() or "COPRO" in bloco_limpo.upper(): linha["material_exame"] = "Fezes"
        else:
            match_mat = re.search(r'(?:MAT(?:ERIAL)?|AMOSTRA)[\s:=]+([A-Za-zÀ-ÿ\s]+?)(?:(?=RES|M[EÉ]TODO|DATA|IDADE|UNIDADE|\n|1:|\.1:|$))', bloco, re.IGNORECASE)
            if match_mat: linha["material_exame"] = padronizar_material(match_mat.group(1))
        
        # 7. ANTIBIOGRAMA (Processado ANTES do resultado para servir de Regra de Ouro)
        sensiveis, resistentes = [], []
        matches_atb = re.findall(r'([A-Z]{2,5})\d*[\s:=]+([SR])\b', bloco_limpo)
        for atb, status in matches_atb:
            if status == 'S': sensiveis.append(atb)
            elif status == 'R': resistentes.append(atb)
            
        tem_antibiograma = len(sensiveis) > 0 or len(resistentes) > 0
        linha["indicados_s"] = ", ".join(sorted(list(set(sensiveis))))
        linha["resistentes_r"] = ", ".join(sorted(list(set(resistentes))))
        
        # 6. RESULTADO (Regra de Ouro Invertida)
        # Se tem antibiótico, É POSITIVO independente do texto.
        if tem_antibiograma:
            linha["resultado"] = "Positivo"
        elif re.search(r'N[ãa]o\s+houve\s+desenvolvimento', bloco_limpo, re.IGNORECASE):
            linha["resultado"] = "Negativo"
        else:
            # Se não disse que não houve, e também não tem antibiograma... 
            # Verifica se acha o nome de alguma bactéria no texto. Se sim, Positivo. Se não, Negativo.
            linha["resultado"] = "Negativo" 
            lista_bacterias = ["escherichia coli", "klebsiella", "proteus", "pseudomonas", "staphylococcus", "streptococcus", "enterococcus", "enterobacter", "acinetobacter", "citrobacter", "morganella", "salmonella"]
            for bac in lista_bacterias:
                if bac in bloco_limpo.lower():
                    linha["resultado"] = "Positivo"
                    break

        # 8. BACTÉRIA (Só procura se o resultado for Positivo)
        if linha["resultado"] == "Positivo":
            regex_bac = r'(?i:identificado|MIC|isolado\s*\d*|\b1|\.1|aer[oó]bia[^:]*|anaer[oó]bia[^:]*)\s*:\s*([A-Z][a-z]{2,}(?:\s+[a-z]{2,})?(?:\s+sp\.?)?)'
            match_bac = re.search(regex_bac, bloco_limpo)
            
            if match_bac:
                bac_str = match_bac.group(1).replace(":", "").strip()
                if "Não houve" not in bac_str and "Aplic" not in bac_str: 
                    linha["bacteria"] = padronizar_bacteria(bac_str)
            
            # PLANO B: Caçador de Bactérias 
            if linha["bacteria"] == "N/A" or linha["bacteria"] == "":
                lista_bacterias = ["escherichia coli", "klebsiella", "proteus", "pseudomonas", "staphylococcus", "streptococcus", "enterococcus", "enterobacter", "acinetobacter", "citrobacter", "morganella", "salmonella"]
                for bac in lista_bacterias:
                    if bac in bloco_limpo.lower():
                        linha["bacteria"] = padronizar_bacteria(bac)
                        break
        
        dados.append(linha)
            
    return pd.DataFrame(dados)
