#!/usr/bin/env python3
"""
Script de automação para criar a esteira do Projeto de Extensão (PEX) no Trello.
Usa apenas bibliotecas nativas do Python (zero dependências externas / sem necessidade de venv).
"""

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# ==============================================================================
# CONFIGURAÇÃO DE CREDENCIAIS
# 1. Acesse https://trello.com/power-ups/admin
# 2. Crie uma integração (New) para pegar sua API Key.
# 3. Na mesma tela, clique no link "Token" (ao lado da API Key) para autorizar e gerar o Token.
# ==============================================================================
API_KEY = "COLE_SUA_API_KEY_AQUI"
TOKEN = "COLE_SEU_TOKEN_AQUI"

BASE_URL = "https://api.trello.com/1"


def trello_request(method: str, endpoint: str, params: dict) -> dict:
    """Executa requisições HTTP na API do Trello com tratamento de erros e rate-limit."""
    params["key"] = API_KEY
    params["token"] = TOKEN

    query_string = urllib.parse.urlencode(params)
    url = f"{BASE_URL}/{endpoint.lstrip('/')}?{query_string}"

    req = urllib.request.Request(url, method=method)
    req.add_header("Accept", "application/json")

    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        print(f"\n[ERRO HTTP {e.code}] Falha no endpoint /{endpoint}: {error_body}")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"\n[ERRO DE REDE] Não foi possível conectar ao Trello: {e.reason}")
        sys.exit(1)


def create_board(name: str, desc: str) -> dict:
    print(f"-> Criando quadro: {name}...")
    return trello_request(
        "POST",
        "/boards/",
        {
            "name": name,
            "desc": desc,
            "defaultLabels": "false",  # Evita etiquetas padrão vazias
            "defaultLists": "false",   # Evita as listas padrão "A fazer / Fazendo / Feito"
            "prefs_background": "blue",
        },
    )


def create_label(board_id: str, name: str, color: str) -> str:
    print(f"-> Criando etiqueta: {name} ({color})...")
    res = trello_request(
        "POST",
        "/labels",
        {
            "idBoard": board_id,
            "name": name,
            "color": color,
        },
    )
    return res["id"]


def create_list(board_id: str, name: str, pos: int) -> str:
    print(f"-> Criando coluna: {name}...")
    res = trello_request(
        "POST",
        "/lists",
        {
            "idBoard": board_id,
            "name": name,
            "pos": str(pos),
        },
    )
    return res["id"]


def create_card(
    list_id: str,
    name: str,
    desc: str = "",
    label_ids: list = None,
    checklist_items: list = None,
) -> str:
    print(f"   + Criando cartão: {name}")
    params = {
        "idList": list_id,
        "name": name,
        "desc": desc,
        "pos": "bottom",
    }
    if label_ids:
        params["idLabels"] = ",".join(label_ids)

    card = trello_request("POST", "/cards", params)
    card_id = card["id"]

    if checklist_items:
        checklist = trello_request(
            "POST",
            "/checklists",
            {
                "idCard": card_id,
                "name": "Passos Práticos",
                "pos": "bottom",
            },
        )
        checklist_id = checklist["id"]
        for item in checklist_items:
            trello_request(
                "POST",
                f"/checklists/{checklist_id}/checkItems",
                {
                    "name": item,
                    "pos": "bottom",
                    "checked": "false",
                },
            )
            time.sleep(0.1)  # Pausa curta para respeitar o rate limit da API

    return card_id


def main():
    if API_KEY == "COLE_SUA_API_KEY_AQUI" or TOKEN == "COLE_SEU_TOKEN_AQUI":
        print("[ERRO] Preencha as variáveis API_KEY e TOKEN no topo do script antes de executar.")
        sys.exit(1)

    # 1. Criar Quadro
    board = create_board(
        name="PEX - Mapeamento e Triagem (Descalvado)",
        desc="Quadro estruturado com foco em previsibilidade e controle de WIP (Work In Progress).",
    )
    board_id = board["id"]
    board_url = board["url"]

    # 2. Criar Etiquetas por Energia e Contexto
    labels = {
        "RUA": create_label(board_id, "[RUA / SOCIAL]", "blue"),
        "ANALISE": create_label(board_id, "[ANÁLISE / PAPEL]", "purple"),
        "CODIGO": create_label(board_id, "[CÓDIGO / TÉCNICO]", "green"),
        "TRAVADO": create_label(board_id, "[TRAVADO / AGUARDANDO]", "red"),
    }

    # 3. Criar Colunas na Ordem Exata (Esquerda -> Direita)
    columns = [
        ("REF", "📌 Referência Fixa (Regras do Jogo)"),
        ("HIPERFOCO", "🛑 Estacionamento de Hiperfoco (Não tocar agora)"),
        ("FILA", "📋 Fila da Fase 1 (Imersão e Requisitos)"),
        ("FAZENDO", "⚡ Fazendo Agora (MÁX: 2 CARTÕES)"),
        ("AGUARDANDO", "⏳ Aguardando Terceiros"),
        ("CONCLUIDO", "✅ Concluído (Dopamina)"),
    ]

    list_ids = {}
    for idx, (key, col_name) in enumerate(columns, start=1):
        list_ids[key] = create_list(board_id, col_name, pos=idx * 1000)

    # 4. Popular Coluna 1: Referência Fixa
    create_card(
        list_id=list_ids["REF"],
        name="Premissas Inegociáveis do Projeto",
        desc=(
            "### Regras Permanentes de Arquitetura e UX\n\n"
            "1. **Foco no Acolhimento (UX):** O atendente nunca deve olhar mais para a tela do que para a vítima.\n"
            "2. **Sem 'Efeito Faxineira':** O sistema se adapta à rotina atual dos setores, e não o contrário.\n"
            "3. **Risco Zero (LGPD):** Desenvolvimento 100% com banco de dados fictício; nenhum dado real passa pelo ambiente de desenvolvimento.\n"
            "4. **Controle de Foco:** Máximo de 2 cartões na coluna 'Fazendo Agora'."
        ),
    )

    # 5. Popular Coluna 6: Concluído
    completed_cards = [
        "Mapear demanda inicial na Audiência Pública (22/08/2026)",
        "Apresentar escopo e alinhar premissas com a Vereadora Vanise na Câmara",
        "Coletar assinaturas e carimbos na Carta de Apresentação e Termo de Autorização",
        "Estruturar e enviar o Relatório Inicial do PEX na plataforma da Descomplica",
    ]
    for title in completed_cards:
        create_card(list_id=list_ids["CONCLUIDO"], name=title)

    # 6. Popular Coluna 4: Fazendo Agora
    create_card(
        list_id=list_ids["FAZENDO"],
        name="Cartão 1: Agendar a 1ª visita em campo com a Vanise",
        desc=(
            "Definir o primeiro setor de atendimento para iniciar o mapeamento prático.\n\n"
            "**Critério de Pronto:** Data e hora da visita anotadas na agenda."
        ),
        label_ids=[labels["RUA"]],
        checklist_items=[
            "Enviar mensagem de WhatsApp para a Vanise agradecendo as assinaturas e pedindo indicação do 1º setor (priorizar CRAS ou Assistência Social).",
            "Assim que enviado, mover este cartão para a coluna 'Aguardando Terceiros' com a etiqueta [TRAVADO / AGUARDANDO].",
            "Confirmar dia, horário e nome do profissional que vai me receber.",
        ],
    )

    create_card(
        list_id=list_ids["FAZENDO"],
        name="Cartão 2: Criar Repositório Base no GitHub",
        desc=(
            "Preparar o controle de versão para documentar as descobertas de campo antes de escrever código.\n\n"
            "**Critério de Pronto:** Primeiro commit feito com o README.md no ar (tempo estimado: 15 minutos)."
        ),
        label_ids=[labels["CODIGO"]],
        checklist_items=[
            "Criar repositório no GitHub (ex: pex-mapeamento-triagem).",
            "Criar pasta /docs para guardar os resumos das entrevistas.",
            "Colar no README.md o texto da visão geral do relatório do PEX.",
        ],
    )

    # 7. Popular Coluna 3: Fila da Fase 1
    create_card(
        list_id=list_ids["FILA"],
        name="Cartão 3: Preparar folha de entrevista (1 página)",
        desc="**Critério de Pronto:** Roteiro salvo/impresso pronto para levar na mochila.",
        label_ids=[labels["ANALISE"]],
        checklist_items=[
            "Passar a limpo (no papel ou tablet) as 7 perguntas do roteiro (Processo Atual, Cadastro vs. Mapeamento Anônimo e UX na ponta).",
        ],
    )

    create_card(
        list_id=list_ids["FILA"],
        name="Cartão 4: Realizar Visita Setor 1 (CRAS / Assistência Social)",
        desc=(
            "Observar como o acolhimento funciona hoje sem tentar vender ideias de telas.\n\n"
            "**Critério de Pronto:** Sair da visita com as 7 perguntas respondidas em tópicos."
        ),
        label_ids=[labels["RUA"]],
        checklist_items=[
            "Descobrir se já usam sistema obrigatório do governo/SUS.",
            "Verificar se anotam no papel primeiro ou direto no computador/celular.",
            "Tirar foto (em branco!) de qualquer ficha de papel padrão que utilizem hoje.",
        ],
    )

    create_card(
        list_id=list_ids["FILA"],
        name="Cartão 5: Realizar Visita Setor 2 (Saúde ou Delegacia)",
        desc=(
            "Entender a diferença de coleta de dados em relação ao primeiro setor.\n\n"
            "**Critério de Pronto:** Anotações da segunda visita concluídas."
        ),
        label_ids=[labels["RUA"]],
        checklist_items=[
            "Aplicar as mesmas 7 perguntas do roteiro.",
            "Identificar como a informação sai deste setor e chega até a Secretaria da Mulher.",
        ],
    )

    create_card(
        list_id=list_ids["FILA"],
        name="Cartão 6: Definir o 'Denominador Comum' e Escopo Final",
        desc=(
            "Cruzar as anotações dos setores para cravar o que o sistema realmente vai fazer.\n\n"
            "**Critério de Pronto:** Lista fechada dos campos que vão existir no banco de dados."
        ),
        label_ids=[labels["ANALISE"]],
        checklist_items=[
            "Decisão 1: Será apenas Mapeamento Estatístico Anônimo (bairros/ocorrências) OU Cadastro Individual de Vítimas?",
            "Decisão 2: Quais são os 5 a 8 campos obrigatórios que todos os setores têm em comum?",
            "Atualizar o README.md no GitHub com essa lista de campos.",
        ],
    )

    # 8. Popular Coluna 2: Estacionamento de Hiperfoco
    parking_cards = [
        ("[Fase 2] Criar massa de Dados Fictícios (JSON/Mock) seguindo a LGPD", labels["CODIGO"]),
        ("[Fase 2] Testar Prova de Conceito (salvar dado com e sem internet)", labels["CODIGO"]),
        ("[Fase 3] Desenhar rascunho da tela de Triagem Rápida (foco em cliques mínimos)", labels["ANALISE"]),
        ("[Fase 3] Programar protótipo funcional (MVP) com dados fictícios", labels["CODIGO"]),
        ("[Fase 4] Apresentar MVP para Vanise e discutir hospedagem/domínio oficial da Câmara", labels["RUA"]),
        ("[Fase 4] Definir criptografia de produção e controle de acesso por setor", labels["CODIGO"]),
    ]
    for title, label in parking_cards:
        create_card(
            list_id=list_ids["HIPERFOCO"],
            name=title,
            desc="Proibido iniciar antes de concluir o Cartão 6 da Fase 1.",
            label_ids=[label],
        )

    print("\n============================================================")
    print("Quadro criado com sucesso!")
    print(f"Acesse em: {board_url}")
    print("============================================================")


if __name__ == "__main__":
    main()