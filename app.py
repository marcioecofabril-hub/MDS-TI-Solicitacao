import json
import os
import re
import threading
from datetime import datetime
from pathlib import Path

import requests
from flask import Flask, jsonify, render_template, request


app = Flask(__name__)


# ============================================================
# CONFIGURAÇÃO
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
ARQUIVO_CLIENTES = BASE_DIR / "clientes.json"

bloqueio_arquivo = threading.Lock()


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def normalizar_email(email):
    return str(email or "").strip().lower()


def normalizar_celular(celular):
    return re.sub(
        r"\D",
        "",
        str(celular or "")
    )


def email_valido(email):
    padrao = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

    return re.match(
        padrao,
        email
    ) is not None


def celular_valido(celular):
    return 10 <= len(celular) <= 13


def obter_ip_cliente():
    encaminhado = request.headers.get(
        "X-Forwarded-For",
        ""
    )

    if encaminhado:
        return encaminhado.split(",")[0].strip()

    return request.remote_addr or ""


def criar_arquivo_clientes():
    if not ARQUIVO_CLIENTES.exists():
        ARQUIVO_CLIENTES.write_text(
            "[]",
            encoding="utf-8"
        )


def carregar_clientes():
    criar_arquivo_clientes()

    try:
        conteudo = ARQUIVO_CLIENTES.read_text(
            encoding="utf-8"
        ).strip()

        if not conteudo:
            return []

        dados = json.loads(
            conteudo
        )

        if isinstance(dados, list):
            return dados

        return []

    except (
        json.JSONDecodeError,
        OSError
    ):
        return []


def salvar_clientes(clientes):
    arquivo_temporario = (
        ARQUIVO_CLIENTES.with_suffix(".tmp")
    )

    arquivo_temporario.write_text(
        json.dumps(
            clientes,
            ensure_ascii=False,
            indent=4
        ),
        encoding="utf-8"
    )

    arquivo_temporario.replace(
        ARQUIVO_CLIENTES
    )


# ============================================================
# CONSULTA À API
# ============================================================

def consultar_api():
    api_url = os.environ.get(
        "API_URL",
        ""
    ).strip()

    api_token = os.environ.get(
        "API_TOKEN",
        ""
    ).strip()

    if not api_url:
        raise RuntimeError(
            "A variável API_URL não foi configurada."
        )

    cabecalhos = {
        "Accept": "application/json",
        "User-Agent": "MDS-TI-Solicitacao/1.0"
    }

    if api_token:
        cabecalhos["Authorization"] = (
            f"Bearer {api_token}"
        )

    resposta = requests.get(
        api_url,
        headers=cabecalhos,
        timeout=20
    )

    resposta.raise_for_status()

    try:
        dados_api = resposta.json()

    except ValueError as erro:
        raise RuntimeError(
            "A API não devolveu um JSON válido."
        ) from erro

    return dados_api


def localizar_template_portugues(dados_api):
    """
    Procura o objeto com key igual a 'pt'.

    Exemplo esperado:

    [
        {
            "key": "pt",
            "template": "Informações do teste"
        }
    ]
    """

    if isinstance(dados_api, list):

        for item in dados_api:

            if not isinstance(item, dict):
                continue

            chave = str(
                item.get("key") or ""
            ).strip().lower()

            if chave == "pt":
                template = item.get(
                    "template"
                )

                if template:
                    return str(template)

    if isinstance(dados_api, dict):

        chave = str(
            dados_api.get("key") or ""
        ).strip().lower()

        if chave == "pt":
            template = dados_api.get(
                "template"
            )

            if template:
                return str(template)

        if dados_api.get("template"):
            return str(
                dados_api["template"]
            )

    return json.dumps(
        dados_api,
        ensure_ascii=False,
        indent=2
    )


# ============================================================
# PÁGINA PRINCIPAL
# ============================================================

@app.route("/", methods=["GET"])
def inicio():
    web3forms_access_key = os.environ.get(
        "WEB3FORMS_ACCESS_KEY",
        ""
    ).strip()

    return render_template(
        "index.html",
        web3forms_access_key=web3forms_access_key
    )


# ============================================================
# ROTA PARA INSPECIONAR A API
# ============================================================

@app.route("/api/teste", methods=["GET"])
def api_teste():
    try:
        dados_api = consultar_api()

        return jsonify({
            "success": True,
            "dados": dados_api
        }), 200

    except requests.RequestException as erro:
        print(
            "[ERRO API] "
            f"{erro}"
        )

        return jsonify({
            "success": False,
            "message": (
                "Não foi possível consultar a API."
            )
        }), 502

    except Exception as erro:
        print(
            "[ERRO API] "
            f"{erro}"
        )

        return jsonify({
            "success": False,
            "message": str(erro)
        }), 500


# ============================================================
# REGISTRO DO CLIENTE E CONSULTA À API
# ============================================================

@app.route("/registrar", methods=["POST"])
def registrar():
    dados = request.get_json(
        silent=True
    ) or {}

    nome = str(
        dados.get("nome") or ""
    ).strip()

    email_cliente = normalizar_email(
        dados.get("email")
    )

    celular = normalizar_celular(
        dados.get("celular")
    )

    if not nome or not email_cliente or not celular:
        return jsonify({
            "success": False,
            "message": (
                "Preencha nome, e-mail e celular."
            )
        }), 400

    if len(nome) < 2:
        return jsonify({
            "success": False,
            "message": "Informe um nome válido."
        }), 400

    if not email_valido(email_cliente):
        return jsonify({
            "success": False,
            "message": "Informe um e-mail válido."
        }), 400

    if not celular_valido(celular):
        return jsonify({
            "success": False,
            "message": (
                "Informe um celular válido com DDD."
            )
        }), 400

    data_solicitacao = datetime.now().strftime(
        "%d/%m/%Y às %H:%M:%S"
    )

    ip_cliente = obter_ip_cliente()

    with bloqueio_arquivo:
        clientes = carregar_clientes()

        for cliente in clientes:
            email_registrado = normalizar_email(
                cliente.get("email")
            )

            celular_registrado = normalizar_celular(
                cliente.get("celular")
            )

            if email_registrado == email_cliente:
                return jsonify({
                    "success": False,
                    "message": (
                        "Este e-mail já utilizou "
                        "a solicitação de teste."
                    )
                }), 409

            if celular_registrado == celular:
                return jsonify({
                    "success": False,
                    "message": (
                        "Este celular já utilizou "
                        "a solicitação de teste."
                    )
                }), 409

        # Consulta a API antes de registrar o cliente
        try:
            dados_api = consultar_api()

            template_api = localizar_template_portugues(
                dados_api
            )

        except requests.Timeout:
            return jsonify({
                "success": False,
                "message": (
                    "A API demorou muito para responder."
                )
            }), 504

        except requests.RequestException as erro:
            print(
                "[ERRO NA CONSULTA À API] "
                f"{erro}"
            )

            return jsonify({
                "success": False,
                "message": (
                    "Não foi possível obter os dados "
                    "da API."
                )
            }), 502

        except Exception as erro:
            print(
                "[ERRO NA CONSULTA À API] "
                f"{erro}"
            )

            return jsonify({
                "success": False,
                "message": str(erro)
            }), 500

        novo_cliente = {
            "nome": nome,
            "email": email_cliente,
            "celular": celular,
            "data_solicitacao": data_solicitacao,
            "ip": ip_cliente
        }

        clientes.append(
            novo_cliente
        )

        try:
            salvar_clientes(
                clientes
            )

        except OSError as erro:
            print(
                "[ERRO AO SALVAR CLIENTE] "
                f"{erro}"
            )

            return jsonify({
                "success": False,
                "message": (
                    "Não foi possível registrar "
                    "a solicitação."
                )
            }), 500

    return jsonify({
        "success": True,
        "message": (
            "Solicitação enviada com sucesso. "
            "Aguarde o contato."
        ),
        "cliente": {
            "nome": nome,
            "email": email_cliente,
            "celular": celular,
            "data_solicitacao": data_solicitacao
        },
        "dados_api": template_api
    }), 201


# ============================================================
# INICIALIZAÇÃO
# ============================================================

if __name__ == "__main__":
    criar_arquivo_clientes()

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
