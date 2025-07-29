import pymupdf
import re
import os
import asyncio

# --- Processadores de Dados Específicos ---
def processar_nascimento_idade(valor_bruto_linha, linhas=None, indice_linha_chave=None):
    if valor_bruto_linha and isinstance(valor_bruto_linha, str) and valor_bruto_linha != "Não encontrado":
        match_completo = re.search(r"(\d{2}/\d{2}/\d{4})\s*\((\d+)\s*anos\)", valor_bruto_linha)
        if match_completo:
            return {"NASCIMENTO": match_completo.group(1).strip(), "IDADE": match_completo.group(2).strip()}
        match_so_data = re.search(r"(\d{2}/\d{2}/\d{4})", valor_bruto_linha)
        if match_so_data:
            data_nasc = match_so_data.group(1).strip()
            idade_encontrada = "Não encontrado"
            idade_match_parenteses_anos = re.search(r"\((\d+)\s*anos\)", valor_bruto_linha)
            if idade_match_parenteses_anos:
                idade_encontrada = idade_match_parenteses_anos.group(1).strip()
            else:
                idade_match_parenteses_so_num = re.search(r"\((\d+)\)", valor_bruto_linha)
                if idade_match_parenteses_so_num:
                    idade_encontrada = idade_match_parenteses_so_num.group(1).strip()
            return {"NASCIMENTO": data_nasc, "IDADE": idade_encontrada}
    return {"NASCIMENTO": "Não encontrado", "IDADE": "Não encontrado"}

def limpar_valor_simples(valor_bruto, linhas=None, indice_linha_chave=None):
    if isinstance(valor_bruto, str):
        return " ".join(valor_bruto.split()).strip()
    return valor_bruto

# --- Lógica Principal de Extração ---
def extrair_valor_para_chave(linhas_pdf, indice_linha_chave_encontrada, config_campo, todas_chaves_principais_texto):
    chave_texto_busca = config_campo['label']
    valor_final_extraido = "Não encontrado"

    if config_campo.get('pegar_resto_linha_chave', False):
        linha_da_chave = linhas_pdf[indice_linha_chave_encontrada]
        pos_chave = linha_da_chave.lower().find(chave_texto_busca.lower())
        if pos_chave != -1:
            texto_apos_chave = linha_da_chave[pos_chave + len(chave_texto_busca):].strip()
            if texto_apos_chave.startswith(':'):
                texto_apos_chave = texto_apos_chave[1:].strip()
            if texto_apos_chave:
                valor_candidato = texto_apos_chave
                value_pattern_regex = config_campo.get('value_pattern', None)
                processador_aplicavel = config_campo.get('processador_valor_regex') or config_campo.get('processador_linha_unica') or config_campo.get('processador_valor_bruto')
                if value_pattern_regex:
                    match = re.search(value_pattern_regex, valor_candidato, re.IGNORECASE)
                    if match:
                        valor_final_extraido = match.group(1) if match.groups() and len(match.groups()) >=1 else match.group(0)
                        if processador_aplicavel:
                            valor_final_extraido = processador_aplicavel(valor_final_extraido, linhas_pdf, indice_linha_chave_encontrada)
                        if chave_texto_busca.lower() in ["nome médico solicitante", "crm:", "data solicitação:"]:
                             print(f"DEBUG [{chave_texto_busca.upper()} PEGAR_RESTO_LINHA_CHAVE_PATTERN]: Valor: '{valor_final_extraido}'")
                        return valor_final_extraido
                elif not value_pattern_regex and valor_candidato :
                    valor_final_extraido = valor_candidato
                    if processador_aplicavel:
                        valor_final_extraido = processador_aplicavel(valor_final_extraido, linhas_pdf, indice_linha_chave_encontrada)
                    if chave_texto_busca.lower() in ["nome médico solicitante", "crm:", "data solicitação:"]:
                        print(f"DEBUG [{chave_texto_busca.upper()} PEGAR_RESTO_LINHA_CHAVE_NO_PATTERN]: Valor: '{valor_final_extraido}'")
                    return valor_final_extraido
    if config_campo.get('pegar_resto_linha_chave', False) and valor_final_extraido != "Não encontrado":
        return valor_final_extraido

    linhas_a_pular_apos_chave = config_campo.get('pular_linhas_inicio', 0)
    max_linhas_para_buscar_valor = config_campo.get('max_linhas_valor', 5)
    value_pattern_regex = config_campo.get('value_pattern', None)
    indice_inicio_busca_nas_linhas = indice_linha_chave_encontrada + 1 + linhas_a_pular_apos_chave

    for i in range(max_linhas_para_buscar_valor):
        idx_linha_candidata_valor = indice_inicio_busca_nas_linhas + i
        if idx_linha_candidata_valor < len(linhas_pdf):
            linha_candidata_texto = linhas_pdf[idx_linha_candidata_valor].strip()
            if chave_texto_busca.lower() in ["nome médico solicitante", "crm:", "data solicitação:"]:
                print(f"\n--- DEBUG CAMPO: {chave_texto_busca.upper()} ---")
                print(f"Processando config: {config_campo}")
                print(f"Linha da label '{chave_texto_busca}' encontrada no índice: {indice_linha_chave_encontrada}")
                print(f"Índice de início da busca por valor: {indice_inicio_busca_nas_linhas}")
                print(f"Tentando linha candidata nª {i+1}/{max_linhas_para_buscar_valor} (índice real: {idx_linha_candidata_valor})")
                print(f"Conteúdo da linha candidata: '{linha_candidata_texto}'")

            linha_candidata_lower = linha_candidata_texto.lower()
            if not linha_candidata_texto:
                if chave_texto_busca.lower() in ["nome médico solicitante", "crm:", "data solicitação:"]:
                    print(f"DEBUG [{chave_texto_busca.upper()}]: Linha candidata vazia, pulando.")
                continue

            e_rotulo_intermediario = False
            rotulos_intermediarios_a_ignorar = config_campo.get('ignorar_rotulos', [])
            if rotulos_intermediarios_a_ignorar:
                for rotulo_ignorar_txt in rotulos_intermediarios_a_ignorar:
                    rotulo_ignorar_lower = rotulo_ignorar_txt.lower()
                    # Modificado para ser mais cuidadoso: só ignora se a linha INTEIRA for o rótulo a ignorar,
                    # ou se a linha COMEÇAR com o rótulo E o rótulo terminar com ":" (para evitar ignorar "01879...")
                    if (rotulo_ignorar_lower.endswith(":") and linha_candidata_lower.startswith(rotulo_ignorar_lower)) or \
                       linha_candidata_lower == rotulo_ignorar_lower:
                        e_rotulo_intermediario = True
                        break
            if e_rotulo_intermediario:
                if chave_texto_busca.lower() in ["nome médico solicitante", "crm:", "data solicitação:"]:
                    print(f"DEBUG [{chave_texto_busca.upper()}]: IGNORADO como rótulo intermediário: '{linha_candidata_texto}'")
                continue

            e_outra_chave_geral = False
            if config_campo.get('parar_em_chave_principal', True):
                for outra_chave_texto_principal in todas_chaves_principais_texto:
                    if outra_chave_texto_principal.lower() == chave_texto_busca.lower():
                        continue
                    outra_chave_lower = outra_chave_texto_principal.lower()
                    if (linha_candidata_lower.startswith(outra_chave_lower) or
                        (outra_chave_lower.endswith(":") and outra_chave_lower in linha_candidata_lower) or
                        (len(outra_chave_lower) > 5 and outra_chave_lower in linha_candidata_lower and linha_candidata_texto.endswith(':')) or
                         linha_candidata_lower == outra_chave_lower ):
                        e_outra_chave_geral = True
                        break
            if e_outra_chave_geral:
                if chave_texto_busca.lower() in ["nome médico solicitante", "crm:", "data solicitação:"]:
                    print(f"DEBUG [{chave_texto_busca.upper()}]: PAROU devido à outra chave principal: '{linha_candidata_texto}'")
                return "Não encontrado"

            if value_pattern_regex:
                if chave_texto_busca.lower() in ["nome médico solicitante", "crm:", "data solicitação:"]:
                    print(f"DEBUG [{chave_texto_busca.upper()}]: Aplicando value_pattern: '{value_pattern_regex}'")
                match = re.search(value_pattern_regex, linha_candidata_texto, re.IGNORECASE)
                if match:
                    if chave_texto_busca.lower() in ["nome médico solicitante", "crm:", "data solicitação:"]:
                        # Tenta pegar o último grupo de captura se houver múltiplos, senão o primeiro, senão o match todo.
                        valor_capturado_debug = match.group(len(match.groups())) if match.groups() else match.group(0)
                        print(f"DEBUG [{chave_texto_busca.upper()}]: PATTERN MATCHED! Valor capturado: '{valor_capturado_debug}'")

                    valor_casado = ""
                    if config_campo.get('retornar_linha_inteira_se_pattern_match', False):
                        valor_casado = linha_candidata_texto
                    else:
                        # Prioriza o último grupo de captura se houver, pois pode ser o mais específico
                        valor_casado = match.group(len(match.groups())) if match.groups() else match.group(0)

                    processador_de_valor_regex = config_campo.get('processador_valor_regex')
                    if processador_de_valor_regex:
                        return processador_de_valor_regex(valor_casado, linhas_pdf, idx_linha_candidata_valor)
                    return valor_casado
                elif i < max_linhas_para_buscar_valor - 1:
                    if chave_texto_busca.lower() in ["nome médico solicitante", "crm:", "data solicitação:"]:
                        print(f"DEBUG [{chave_texto_busca.upper()}]: Pattern não casou, continuando para próxima linha da config.")
                    continue
                else:
                    if chave_texto_busca.lower() in ["nome médico solicitante", "crm:", "data solicitação:"]:
                        print(f"DEBUG [{chave_texto_busca.upper()}]: Fim das max_linhas, pattern não casou na última tentativa para esta config.")
                    return "Não encontrado"
            else: 
                if chave_texto_busca.lower() in ["nome médico solicitante", "crm:", "data solicitação:"]:
                    print(f"DEBUG [{chave_texto_busca.upper()}]: Sem value_pattern, pegando linha bruta: '{linha_candidata_texto}'")
                processador_de_linha_bruta = config_campo.get('processador_valor_bruto') or config_campo.get('processador_linha_unica')
                if processador_de_linha_bruta:
                    return processador_de_linha_bruta(linha_candidata_texto, linhas_pdf, idx_linha_candidata_valor)
                return linha_candidata_texto
        else:
            break
    return "Não encontrado"

def extrair_dados_pdf_com_config(linhas_do_pdf, mapa_configuracao_extracao):
    # ... (resto da função extrair_dados_pdf_com_config permanece igual à versão anterior) ...
    dados_extraidos_finais = {}
    todas_labels_chaves_principais = [
        config['label']
        for configs_por_campo in mapa_configuracao_extracao.values()
        for config in configs_por_campo
    ]
    todas_labels_chaves_principais = list(set(todas_labels_chaves_principais))
    for nome_campo_destino in mapa_configuracao_extracao.keys():
        if nome_campo_destino.endswith("_COMBINADO"):
            continue
        dados_extraidos_finais[nome_campo_destino] = "Não encontrado"
    for nome_campo_destino, lista_configs_para_campo in mapa_configuracao_extracao.items():
        valor_final_para_campo = "Não encontrado"
        for config_especifica in lista_configs_para_campo:
            label_chave_atual_para_buscar = config_especifica['label']
            ocorrencia_desejada_da_chave = config_especifica.get('ocorrencia', 1)
            processador_principal_do_campo = config_especifica.get('processador', None)
            contagem_atual_ocorrencias = 0
            idx_label_encontrada_para_processador = -1
            for idx_linha, linha_atual_do_pdf in enumerate(linhas_do_pdf):
                if label_chave_atual_para_buscar.lower() in linha_atual_do_pdf.lower():
                    contagem_atual_ocorrencias += 1
                    if contagem_atual_ocorrencias == ocorrencia_desejada_da_chave:
                        idx_label_encontrada_para_processador = idx_linha
                        valor_extraido_bruto = extrair_valor_para_chave(
                            linhas_do_pdf,
                            idx_linha,
                            config_especifica,
                            todas_labels_chaves_principais
                        )
                        if valor_extraido_bruto != "Não encontrado":
                            if processador_principal_do_campo:
                                resultado_processado = processador_principal_do_campo(valor_extraido_bruto, linhas_do_pdf, idx_label_encontrada_para_processador)
                                if isinstance(resultado_processado, dict):
                                    for k, v in resultado_processado.items():
                                        dados_extraidos_finais[k] = v
                                    if nome_campo_destino.endswith("_COMBINADO"):
                                        valor_final_para_campo = "PROCESSADO_EM_DICT"
                                    elif nome_campo_destino in resultado_processado:
                                         valor_final_para_campo = resultado_processado[nome_campo_destino]
                                    else:
                                        valor_final_para_campo = valor_extraido_bruto
                                else:
                                    valor_final_para_campo = resultado_processado
                            else:
                                valor_final_para_campo = valor_extraido_bruto
                            if not nome_campo_destino.endswith("_COMBINADO") and \
                               valor_final_para_campo != "Não encontrado" and \
                               valor_final_para_campo != "PROCESSADO_EM_DICT":
                                dados_extraidos_finais[nome_campo_destino] = valor_final_para_campo
                            break 
            if valor_final_para_campo != "Não encontrado" and valor_final_para_campo != "PROCESSADO_EM_DICT":
                if not nome_campo_destino.endswith("_COMBINADO"):
                     dados_extraidos_finais[nome_campo_destino] = valor_final_para_campo
                break 
        if not nome_campo_destino.endswith("_COMBINADO"):
            if dados_extraidos_finais.get(nome_campo_destino) == "Não encontrado" and \
               valor_final_para_campo != "PROCESSADO_EM_DICT" and \
               valor_final_para_campo != "Não encontrado":
                dados_extraidos_finais[nome_campo_destino] = valor_final_para_campo
    chaves_finais_obrigatorias = [
        "PACIENTE", "NASCIMENTO", "IDADE", "MAE", "TELEFONE", "CRM", "MEDICO",
        "DIAGNOSTICO", "PROCEDIMENTO", "NACIONALIDADE", "CEP", "RISCO",
        "DIAGNOSTICO_INICIAL", "CENTRAL", "UNIDADE", "DATA_SOLICITACAO",
        "SITUACAO_ATUAL", "HOSPITAL", "CODIGO_SOLICITACAO"
    ]
    for chave_obrigatoria in chaves_finais_obrigatorias:
        if chave_obrigatoria not in dados_extraidos_finais:
            dados_extraidos_finais[chave_obrigatoria] = "Não encontrado"
        elif dados_extraidos_finais[chave_obrigatoria] is None :
             dados_extraidos_finais[chave_obrigatoria] = "Não encontrado"
    return dados_extraidos_finais

# --- Mapa de Configuração da Extração CORRIGIDO COM BASE NOS LOGS ---
MAPA_CONFIG_EXTRACAO_REVISAO12 = {
    "PACIENTE": [
        {
            'label': "Nome do Paciente", 'pular_linhas_inicio': 0, 'max_linhas_valor': 5,
            'ignorar_rotulos': ["Nome Social/Apelido:", "Data de Nascimento:", "Sexo:", "CNS:"],
            'value_pattern': r"^([A-ZÀ-Ú\s]{5,})(?:\s*---\s*|\s*\d{2}/\d{2}/\d{4}|FEMININO|MASCULINO|AMARELA|BRASILEIRA|PARDA|$)",
            'processador_valor_regex': limpar_valor_simples
        },
        {'label': "Nome do Paciente", 'pegar_resto_linha_chave': True,
         'value_pattern': r"^([A-ZÀ-Ú\s]{5,})(?:\s*---\s*|\s*\d{2}/\d{2}/\d{4}|FEMININO|MASCULINO|AMARELA|BRASILEIRA|PARDA|$)",
         'processador_valor_regex': limpar_valor_simples},
    ],
    "NASCIMENTO_IDADE_COMBINADO": [
        {'label': "Data de Nascimento:", 'max_linhas_valor': 8,
         'ignorar_rotulos': ["Sexo:", "Nome da Mãe", "Raça:", "Tipo Sanguíneo:", "Nome do Paciente", "CNS:", "Nome Social/Apelido:", "Nacionalidade:", "Município de Nascimento:", "Endereço:", "Telefone:"],
         'value_pattern': r"\d{2}/\d{2}/\d{4}.*\((\d+)\s*anos\)", 'retornar_linha_inteira_se_pattern_match': True, 'processador': processar_nascimento_idade},
        {'label': "Data de Nascimento:", 'max_linhas_valor': 8,
         'ignorar_rotulos': ["Sexo:", "Nome da Mãe", "Raça:", "Tipo Sanguíneo:", "Nome do Paciente", "CNS:", "Nome Social/Apelido:", "Nacionalidade:", "Município de Nascimento:", "Endereço:", "Telefone:"],
         'value_pattern': r"\d{2}/\d{2}/\d{4}", 'retornar_linha_inteira_se_pattern_match': True, 'processador': processar_nascimento_idade}
    ],
    "MAE": [
        {'label': "Nome da Mãe", 'pegar_resto_linha_chave': True,
         'value_pattern': r"^([A-ZÀ-Ú\s]+?)(?:\s{2,}|\s*---\s*|\s*PARDA|BRASILEIRA|AMARELA|$)", 'processador_valor_regex': limpar_valor_simples},
        {'label': "Nome da Mãe", 'max_linhas_valor': 3, 'ignorar_rotulos': ["Raça:", "Tipo Sanguíneo:"],
         'value_pattern': r"^([A-ZÀ-Ú\s]+?)(?:\s{2,}|\s*---\s*|\s*PARDA|BRASILEIRA|AMARELA|$)", 'processador_valor_regex': limpar_valor_simples}
    ],
    "TELEFONE": [
        {'label': "Telefone(s):", 'pegar_resto_linha_chave': True, 'value_pattern': r"(\(\d{2}\)\s*\d{4,5}-\d{4})"},
        {'label': "Telefone(s):", 'max_linhas_valor': 1, 'value_pattern': r"(\(\d{2}\)\s*\d{4,5}-\d{4})"}
    ],
    "CRM": [
        {
            'label': "CRM:", # No PDF de exemplo, a label "CRM:" está numa linha com outras labels (índice 24 dos logs)
            'pular_linhas_inicio': 1,    # O valor "---" está na linha seguinte (índice 25 dos logs)
            'max_linhas_valor': 1,       # Processa apenas essa linha de valor
            'ignorar_rotulos': [],       # Não ignorar nada da linha de valor, pois precisamos extrair dela
            # Pattern para encontrar '---' ou dígitos, permitindo outros textos ao redor. Captura o CRM.
            # Procura por um CPF antes (11 dígitos), depois espaços, e então o CRM.
            'value_pattern': r"(?:\b\d{11}\b\s+)?(---\b|\b\d{3,}\b)",
            'processador_valor_regex': limpar_valor_simples
        }
    ],
    "MEDICO": [
        {
            'label': "Nome Médico Solicitante", # No PDF, label "Nome Médico Solicitante" na linha de labels (índice 24)
            'pular_linhas_inicio': 0,        # O valor (nome) está na linha seguinte (índice 25)
            'max_linhas_valor': 1,           # Processa apenas essa linha de valor
            'ignorar_rotulos': [],           # Não ignorar partes da linha de valor
            # Pattern para encontrar um nome após '---' (CRM) e espaços.
            # O lookahead negativo é para o grupo capturado do nome.
            # Captura o nome do médico (grupo 1 do regex).
            'value_pattern': r"(?:---|\b\d{3,}\b)\s+((?i)(?!NEOPLASIA|DIAGNÓSTICO|DIAGNOSTICO|CID:|SUSPEITA|INVESTIGAÇÃO|PACIENTE COM|\s*-\s*$|PREZADOS|PREZADO)(?:(?:Dr|Dra)\.?\s*)?[A-ZÀ-Ú][a-zA-ZÀ-Ú'\.\s-]{2,}(?:\s+[A-ZÀ-Ú][a-zA-ZÀ-Ú'\.\s-]+){1,4})",
            'processador_valor_regex': limpar_valor_simples
        }
    ],
    "DIAGNOSTICO_INICIAL": [
        {
            'label': "Diagnóstico Inicial:", 'pular_linhas_inicio': 0, 'max_linhas_valor': 3,
            'ignorar_rotulos': ["CID:", "Risco:"],
            'value_pattern': r"^((?![A-Z]\d{2}(?:\.\d+)?\s*$)(?!VERMELHO|AMARELO|VERDE|AZUL|RISCO HABITUAL\s*$)[A-ZÀ-ÚÇÃ-Õ][A-ZÀ-ÚÇÃ-Õ\s\.\-\/\(\),0-9]{10,})$",
            'processador_valor_regex': lambda val, lns, idx: re.sub(r'\s+[A-Z]\d{2}(?:\.\d+)?.*', '', str(val), flags=re.IGNORECASE).strip() if val else val
        }
    ],
    "PROCEDIMENTO": [
        {'label': "Procedimentos Solicitados:", 'max_linhas_valor': 3, 'ignorar_rotulos':["Cód. Unificado:", "Cód. Interno:"],
         'value_pattern': r"^([A-ZÀ-ÚÇÃ-Õ0-9\s\.\-\(\)]+?)(?:\s{2,}\d+.*|$)", 'processador_valor_regex': limpar_valor_simples}
    ],
    "NACIONALIDADE": [ {'label': "Nacionalidade:", 'max_linhas_valor': 2, 'value_pattern': r"(BRASILEIRA)"} ],
    "CEP": [ {'label': "CEP:", 'max_linhas_valor': 6,
         'ignorar_rotulos': ["Número:", "Bairro:", "País de Residência:", "Município de Residência:", "Logradouro:", "Complemento:", "Tipo Logradouro:", "País:", "UF:", "Município de Nascimento:", "Município:", "Telefone(s):"],
         'value_pattern': r"(\d{5}-\d{3})"} ],
    "RISCO": [
        {'label': "Risco:", 'max_linhas_valor': 4, 'ignorar_rotulos': ["CID:", "Central Reguladora:"],
         'value_pattern': r"(VERMELHO(?: - Emergência)?|AMARELO(?: - Urgente)?|VERDE(?: - Pouco Urgente| - Rotina)?|AZUL(?: - Não Urgente)?|RISCO HABITUAL)"},
        {'label': "Risco:", 'max_linhas_valor': 4, 'ignorar_rotulos': ["CID:", "Central Reguladora:"], 'value_pattern': r"^(VERMELHO|AMARELO|VERDE|AZUL)$"}
    ],
    "CENTRAL": [ {'label': "Central Reguladora:", 'pular_linhas_inicio': 0, 'max_linhas_valor': 1, 'processador_valor_bruto': limpar_valor_simples} ],
    "UNIDADE": [ {'label': "Unidade Solicitante:", 'max_linhas_valor': 3, 'ignorar_rotulos': ["Cód. CNES:", "Op. Solicitante:", "Op. Videofonista:"],
         'value_pattern': r"^([A-ZÀ-Ú\d\s\.\-\/\_]+?)(?:\s{2,}\d+|\s*Reserva Técnica|$)", 'processador_valor_regex': limpar_valor_simples}, ],
    "DATA_SOLICITACAO": [
        # Esta configuração precisa ser validada com a saída de log completa das linhas_do_texto
        # para saber a posição relativa da label e do valor.
        # Por agora, mantendo uma config que busca próximo à label.
        {'label': "Data Solicitação:", 'pular_linhas_inicio': 0, 'max_linhas_valor': 3, # Aumentar a janela de busca
         'ignorar_rotulos': ["---", "Unidade Desejada:", "Data Desejada:"],
         'value_pattern': r"(\d{2}/\d{2}/\d{4})"}
    ],
    "SITUACAO_ATUAL": [ {'label': "Situação Atual:", 'max_linhas_valor': 2,
         'value_pattern': r"^(?:\d+\s+)?((?:AGENDAMENTO|SOLICITAÇÃO|PENDENTE|DEVOLVIDA|REGULADOR|CANCELADA|EXECUTANTE)[\w\s\/\-]+)"} ],
    "CODIGO_SOLICITACAO": [ {'label': "Código da Solicitação:",'max_linhas_valor':1, 'value_pattern': r"(\d+)"} ],
    "HOSPITAL": [ {'label': "Unidade Desejada:", 'max_linhas_valor': 3, 'value_pattern': r"^(---|[A-ZÀ-Ú\d\s\.\-\(\)]+)$"} ]
}
if "DIAGNOSTICO" not in MAPA_CONFIG_EXTRACAO_REVISAO12:
    MAPA_CONFIG_EXTRACAO_REVISAO12["DIAGNOSTICO"] = MAPA_CONFIG_EXTRACAO_REVISAO12["DIAGNOSTICO_INICIAL"]


async def extrair_campos(pdf_path):
    # ... (resto da função extrair_campos permanece igual à versão anterior, com os prints de DEBUG ATIVOS) ...
    try:
        with pymupdf.open(pdf_path) as doc:
            texto_completo_pdf = ""
            for pagina in doc:
                texto_completo_pdf += pagina.get_text("text", sort=True)
    except Exception as e:
        print(f"Erro ao abrir ou ler o PDF '{os.path.basename(pdf_path)}': {e}")
        mapa_config_ref = MAPA_CONFIG_EXTRACAO_REVISAO12 
        dados_vazios = {campo: "Não encontrado" for campo in mapa_config_ref if not campo.endswith("_COMBINADO")}
        if "NASCIMENTO_IDADE_COMBINADO" in mapa_config_ref: 
            dados_vazios["NASCIMENTO"] = "Não encontrado"
            dados_vazios["IDADE"] = "Não encontrado"
        chaves_obrigatorias_ref = [ 
            "PACIENTE", "NASCIMENTO", "IDADE", "MAE", "TELEFONE", "CRM", "MEDICO",
            "DIAGNOSTICO", "PROCEDIMENTO", "NACIONALIDADE", "CEP", "RISCO",
            "DIAGNOSTICO_INICIAL", "CENTRAL", "UNIDADE", "DATA_SOLICITACAO",
            "SITUACAO_ATUAL", "HOSPITAL", "CODIGO_SOLICITACAO"
        ]
        for chave_obrigatoria in chaves_obrigatorias_ref:
            if chave_obrigatoria not in dados_vazios:
                dados_vazios[chave_obrigatoria] = "Não encontrado"
        return dados_vazios

    linhas_do_texto = texto_completo_pdf.splitlines()
    
    print("\n--- DEBUG: Início Linhas LIMPAS (primeiras 80 linhas originais, depois de strip/remoção de vazias) ---")
    temp_linhas_limpas_debug = []
    for i_debug, l_debug in enumerate(linhas_do_texto[:80]): # Mostra as primeiras 80 linhas ANTES do strip completo da lista
        l_debug_strip = l_debug.strip()
        if l_debug_strip: 
            temp_linhas_limpas_debug.append(l_debug_strip) # Constrói uma lista temporária para mostrar índices contínuos das linhas não-vazias
    
    for i_print_debug, l_print_debug in enumerate(temp_linhas_limpas_debug):
         print(f"Linha Limpa (índice na lista final {i_print_debug}): '{l_print_debug}'")
    print("--- DEBUG: Fim Linhas LIMPAS ---\n")
    
    linhas_do_texto = [linha.strip() for linha in linhas_do_texto if linha.strip()]

    if not linhas_do_texto:
        print(f"Nenhum texto útil extraído do PDF: {os.path.basename(pdf_path)}")
        mapa_config_ref = MAPA_CONFIG_EXTRACAO_REVISAO12
        dados_vazios = {campo: "Não encontrado" for campo in mapa_config_ref if not campo.endswith("_COMBINADO")}
        if "NASCIMENTO_IDADE_COMBINADO" in mapa_config_ref:
            dados_vazios["NASCIMENTO"] = "Não encontrado"
            dados_vazios["IDADE"] = "Não encontrado"
        chaves_obrigatorias_ref = [
            "PACIENTE", "NASCIMENTO", "IDADE", "MAE", "TELEFONE", "CRM", "MEDICO",
            "DIAGNOSTICO", "PROCEDIMENTO", "NACIONALIDADE", "CEP", "RISCO",
            "DIAGNOSTICO_INICIAL", "CENTRAL", "UNIDADE", "DATA_SOLICITACAO",
            "SITUACAO_ATUAL", "HOSPITAL", "CODIGO_SOLICITACAO"
        ]
        for chave_obrigatoria in chaves_obrigatorias_ref:
            if chave_obrigatoria not in dados_vazios:
                dados_vazios[chave_obrigatoria] = "Não encontrado"
        return dados_vazios

    dados_finais_extraidos = extrair_dados_pdf_com_config(linhas_do_texto, MAPA_CONFIG_EXTRACAO_REVISAO12)

    if dados_finais_extraidos.get("DIAGNOSTICO") == "Não encontrado" and \
       dados_finais_extraidos.get("DIAGNOSTICO_INICIAL") not in ["Não encontrado", None]:
        dados_finais_extraidos["DIAGNOSTICO"] = dados_finais_extraidos["DIAGNOSTICO_INICIAL"]

    medico_valor = dados_finais_extraidos.get("MEDICO")
    diagnostico_inicial_valor = dados_finais_extraidos.get("DIAGNOSTICO_INICIAL")
    diagnostico_valor = dados_finais_extraidos.get("DIAGNOSTICO")
    medico_lower = str(medico_valor).lower()
    termos_diagnostico_suspeitos = ["neoplasia", "diagnostico", "cid", "suspeita", "investigação", "paciente com", "prezados"]
    resetar_medico = False
    if medico_valor not in ["Não encontrado", None] and medico_valor != "": 
        if diagnostico_inicial_valor not in ["Não encontrado", None] and medico_lower == str(diagnostico_inicial_valor).lower():
            resetar_medico = True
        elif diagnostico_valor not in ["Não encontrado", None] and medico_lower == str(diagnostico_valor).lower():
            resetar_medico = True
        else:
            for termo_suspeito in termos_diagnostico_suspeitos:
                if termo_suspeito in medico_lower:
                    if len(medico_lower) < len(termo_suspeito) + 10: 
                        resetar_medico = True
                        break
    if resetar_medico:
        print(f"DEBUG MÉDICO PÓS-PROC: MEDICO ('{medico_valor}') suspeito ou igual ao DIAGNOSTICO. Resetando MEDICO para 'Não encontrado'.")
        dados_finais_extraidos["MEDICO"] = "Não encontrado"
    print(f"Campos extraídos (COM DEBUG ATIVO E CORREÇÕES LOGS) do PDF: {os.path.basename(pdf_path)}", dados_finais_extraidos)
    return dados_finais_extraidos

async def main_test():
    pdf_paths = ["/content/SISREG_III_-_Servidor_de_Producao.pdf"] # <<-- COLOQUE O CAMINHO CORRETO AQUI
    if not pdf_paths or not (os.path.exists(pdf_paths[0]) if pdf_paths and pdf_paths[0] else False) :
        print("Caminho do PDF de teste não fornecido ou inválido.")
        # ... (bloco de simulação) ...
        return
    for pdf_path in pdf_paths:
        if os.path.exists(pdf_path):
            print(f"\n--- Processando PDF: {os.path.basename(pdf_path)} ---")
            await extrair_campos(pdf_path)
        else:
            print(f"Arquivo PDF de teste não encontrado em: {pdf_path}")

if __name__ == '__main__':
    # --- Teste Síncrono Simplificado ---
    def extrair_campos_sync(pdf_path_sync):
        # ... (função extrair_campos_sync da resposta anterior, adaptada para chamar a extrair_dados_pdf_com_config global)
        try:
            with pymupdf.open(pdf_path_sync) as doc:
                texto_completo_pdf = ""
                for pagina in doc:
                    texto_completo_pdf += pagina.get_text("text", sort=True)
        except Exception as e:
            print(f"Erro ao abrir ou ler o PDF '{os.path.basename(pdf_path_sync)}': {e}")
            return {"ERRO": str(e)} 

        linhas_do_texto_sync_brutas = texto_completo_pdf.splitlines()

        print("\n--- DEBUG (SYNC): Início Linhas LIMPAS (primeiras 80 linhas originais, depois de strip/remoção de vazias) ---")
        temp_linhas_limpas_debug = []
        for i_debug, l_debug in enumerate(linhas_do_texto_sync_brutas[:80]):
            l_debug_strip = l_debug.strip()
            if l_debug_strip:
                temp_linhas_limpas_debug.append(l_debug_strip)
        
        for i_print_debug, l_print_debug in enumerate(temp_linhas_limpas_debug):
             print(f"Linha Limpa (índice na lista final {i_print_debug}): '{l_print_debug}'")
        print("--- DEBUG (SYNC): Fim Linhas LIMPAS ---\n")
        
        linhas_do_texto_sync = [l.strip() for l in linhas_do_texto_sync_brutas if l.strip()]


        if not linhas_do_texto_sync:
            print(f"Nenhum texto útil extraído do PDF: {os.path.basename(pdf_path_sync)}")
            return {"ERRO": "Nenhum texto útil extraído"}

        dados_finais = extrair_dados_pdf_com_config(linhas_do_texto_sync, MAPA_CONFIG_EXTRACAO_REVISAO12)
        
        if dados_finais.get("DIAGNOSTICO") == "Não encontrado" and \
           dados_finais.get("DIAGNOSTICO_INICIAL") not in ["Não encontrado", None]:
            dados_finais["DIAGNOSTICO"] = dados_finais["DIAGNOSTICO_INICIAL"]

        medico_valor_sync = dados_finais.get("MEDICO")
        diagnostico_inicial_valor_sync = dados_finais.get("DIAGNOSTICO_INICIAL")
        diagnostico_valor_sync = dados_finais.get("DIAGNOSTICO")
        medico_lower_sync = str(medico_valor_sync).lower()
        termos_diagnostico_suspeitos_sync = ["neoplasia", "diagnostico", "cid", "suspeita", "investigação", "paciente com", "prezados"]
        resetar_medico_sync = False
        if medico_valor_sync not in ["Não encontrado", None] and medico_valor_sync != "":
            if diagnostico_inicial_valor_sync not in ["Não encontrado", None] and medico_lower_sync == str(diagnostico_inicial_valor_sync).lower(): resetar_medico_sync = True
            elif diagnostico_valor_sync not in ["Não encontrado", None] and medico_lower_sync == str(diagnostico_valor_sync).lower(): resetar_medico_sync = True
            else:
                for termo_suspeito in termos_diagnostico_suspeitos_sync:
                    if termo_suspeito in medico_lower_sync:
                        if len(medico_lower_sync) < len(termo_suspeito) + 10: resetar_medico_sync = True; break
        if resetar_medico_sync: 
            print(f"DEBUG MÉDICO PÓS-PROC (SYNC): MEDICO ('{medico_valor_sync}') suspeito ou igual ao DIAGNOSTICO. Resetando MEDICO para 'Não encontrado'.")
            dados_finais["MEDICO"] = "Não encontrado"
        
        print(f"Campos extraídos (SYNC TEST COM DEBUG ATIVO E CORREÇÕES LOGS) do PDF: {os.path.basename(pdf_path_sync)}", dados_finais)
        return dados_finais

    pdf_path_teste_sync = "/content/SISREG_III_-_Servidor_de_Producao.pdf" # <<-- COLOQUE O CAMINHO CORRETO AQUI
    if os.path.exists(pdf_path_teste_sync):
        extrair_campos_sync(pdf_path_teste_sync)
    else:
        print(f"PDF de teste para SYNC não encontrado: {pdf_path_teste_sync}.")
        # Para executar a simulação se o PDF não for encontrado:
        print("Rodando simulação com dados embutidos...")
        linhas_exemplo = [
            "UNIDADE SOLICITANTE", "UNIDADE SOLICITANTE", "Unidade Solicitante:", "Cód. CNES:", "Op. Solicitante:", "Op. Videofonista:",
            "HOSPITAL REGIONAL DE CEILANDIA", "0010480", "HRCRAFAELAFSOL", "---", "DADOS DO PACIENTE", "DADOS DO PACIENTE",
            "CNS:", "700603970203863", "Nome do Paciente", "Nome Social/Apelido:", "Data de Nascimento:", "Sexo:",
            "IVANIR DE SOUZA PEREIRA", "---", "07/12/1959 (65 anos)", "FEMININO", "Nome da Mãe", "Raça:", "Tipo Sanguíneo:",
            "REGINA DE SOUZA PEREIRA", "AMARELA", "---", "Nacionalidade:", "Município de Nascimento:",
            "BRASILEIRA", "CORONEL FABRICIANO - MG", "Tipo Logradouro:", "Logradouro:", "Complemento:",
            "QUADRA", "QR 513 CONJUNTO 04 LOTE", "CASA 01", "Número:", "Bairro:", "CEP:",
            "27", "SAMAMBAIA SUL (SAMAMBAIA)", "72315-004", "País de Residência:", "Município de Residência:",
            "BRASIL", "BRASILIA - DF", "Telefone(s):", "(61) 99209-2340 ● (61) 99279-6835 (Exibir Lista Detalhada)",
            "DADOS DA SOLICITAÇÃO", "DADOS DA SOLICITAÇÃO", "Código da Solicitação:", "Situação Atual:",
            "589323653", "SOLICITAÇÃO / DEVOLVIDA / REGULADOR", "CPF do Médico Solicitante:", "CRM:", "Nome Médico Solicitante:", "Vaga Solicitada:",
            "01879236478", "---", "METODIO RIBAS RAMALHO", "1ª Vez", "Diagnóstico Inicial:", "CID:", "Risco:",
            "NEOPLASIA MALIGNA DO COLO DO UTERO", "C53", "VERMELHO - Emergência", "Central Reguladora:",
            "BRASILIA", "Unidade Desejada:", "Data Desejada:", "Data Solicitação:",
            "---", "---", "14/03/2025", "Procedimentos Solicitados:", "Cód. Unificado:", "Cód. Interno:",
            "CONSULTA EM ONCOLOGIA CLINICA", "0301010072", "0701363", "HISTÓRICO DE OBSERVAÇÕES"
        ]
        print("\n--- DEBUG (SYNC): Início Linhas LIMPAS (SIMULAÇÃO - primeiras 80) ---")
        temp_linhas_limpas_debug = []
        for i_debug, l_debug in enumerate(linhas_exemplo[:80]):
            l_debug_strip = l_debug.strip()
            if l_debug_strip:
                temp_linhas_limpas_debug.append(l_debug_strip)
        for i_print_debug, l_print_debug in enumerate(temp_linhas_limpas_debug):
             print(f"Linha Limpa (índice na lista final {i_print_debug}): '{l_print_debug}'")
        print("--- DEBUG (SYNC): Fim Linhas LIMPAS (SIMULAÇÃO) ---\n")

        linhas_limpas_exemplo = [linha.strip() for linha in linhas_exemplo if linha.strip()]
        dados_simulados = extrair_dados_pdf_com_config(linhas_limpas_exemplo, MAPA_CONFIG_EXTRACAO_REVISAO12)
        print("Campos extraídos (SIMULAÇÃO COM DADOS EMBUTIDOS E DEBUG ATIVO):", dados_simulados)

    # Para usar a versão async original, comente main_sync_test() e descomente:
    # asyncio.run(main_test())