import html
import json
import os
import re
import threading
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request


app = Flask(__name__)


# ============================================================
# CONFIGURAÇÃO
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

ARQUIVO_CLIENTES = BASE_DIR / "clientes.json"
ARQUIVO_DADOS_API = BASE_DIR / "dados_api.json"

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


def formatar_celular(celular):
    numeros = normalizar_celular(celular)

    if len(numeros) == 11:
        return (
            f"({numeros[0:2]}) "
            f"{numeros[2:7]}-"
            f"{numeros[7:11]}"
        )

    if len(numeros) == 10:
        return (
            f"({numeros[0:2]}) "
            f"{numeros[2:6]}-"
            f"{numeros[6:10]}"
        )

    return numeros


def obter_ip_cliente():
    encaminhado = request.headers.get(
        "X-Forwarded-For",
        ""
    )

    if encaminhado:
        return encaminhado.split(",")[0].strip()

    return request.remote_addr or ""


# ============================================================
# CLIENTES.JSON
# ============================================================

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

        dados = json.loads(conteudo)

        if isinstance(dados, list):
            return dados

        return []

    except json.JSONDecodeError as erro:
        print(
            "[ERRO clientes.json] "
            f"{erro}"
        )

        return []

    except OSError as erro:
        print(
            "[ERRO clientes.json] "
            f"{erro}"
        )

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
# DADOS_API.JSON
# ============================================================

def carregar_dados_api():
    if not ARQUIVO_DADOS_API.exists():
        raise RuntimeError(
            "O arquivo dados_api.json não foi encontrado."
        )

    try:
        conteudo = ARQUIVO_DADOS_API.read_text(
            encoding="utf-8"
        ).strip()

        if not conteudo:
            raise RuntimeError(
                "O arquivo dados_api.json está vazio."
            )

        dados_api = json.loads(
            conteudo
        )

    except json.JSONDecodeError as erro:
        raise RuntimeError(
            "O arquivo dados_api.json possui "
            f"um JSON inválido: {erro}"
        ) from erro

    except OSError as erro:
        raise RuntimeError(
            "Não foi possível abrir dados_api.json."
        ) from erro

    if not isinstance(dados_api, list):
        raise RuntimeError(
            "dados_api.json precisa conter uma lista."
        )

    return dados_api


def obter_template_portugues():
    dados_api = carregar_dados_api()

    for item in dados_api:
        if not isinstance(item, dict):
            continue

        idioma = str(
            item.get("key") or ""
        ).strip().lower()

        if idioma != "pt":
            continue

        template = item.get(
            "template"
        )

        if template is None:
            raise RuntimeError(
                "O template PT não foi encontrado."
            )

        template_texto = html.unescape(
            str(template)
        ).strip()

        if not template_texto:
            raise RuntimeError(
                "O template PT está vazio."
            )

        return template_texto

    raise RuntimeError(
        "Não existe key='pt' em dados_api.json."
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
# TESTE DO DADOS_API.JSON
# ============================================================

@app.route("/api/status", methods=["GET"])
def api_status():
    try:
        template_pt = obter_template_portugues()

        return jsonify({
            "success": True,
            "arquivo": "dados_api.json",
            "template_pt": True,
            "quantidade_caracteres": len(
                template_pt
            )
        }), 200

    except Exception as erro:
        print(
            "[ERRO dados_api.json] "
            f"{erro}"
        )

        return jsonify({
            "success": False,
            "message": str(erro)
        }), 500


# ============================================================
# REGISTRAR SOLICITAÇÃO
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

    # --------------------------------------------------------
    # VALIDAÇÕES
    # --------------------------------------------------------

    if not nome:
        return jsonify({
            "success": False,
            "message": "Informe seu nome."
        }), 400

    if len(nome) < 2:
        return jsonify({
            "success": False,
            "message": "Informe um nome válido."
        }), 400

    if not email_cliente:
        return jsonify({
            "success": False,
            "message": "Informe seu e-mail."
        }), 400

    if not email_valido(email_cliente):
        return jsonify({
            "success": False,
            "message": "Informe um e-mail válido."
        }), 400

    if not celular:
        return jsonify({
            "success": False,
            "message": "Informe seu WhatsApp."
        }), 400

    if not celular_valido(celular):
        return jsonify({
            "success": False,
            "message": (
                "Informe um WhatsApp válido com DDD."
            )
        }), 400

    # --------------------------------------------------------
    # CARREGA O TESTE
    # --------------------------------------------------------

    try:
        template_pt = obter_template_portugues()

    except Exception as erro:
        print(
            "[ERRO AO CARREGAR TESTE] "
            f"{erro}"
        )

        return jsonify({
            "success": False,
            "message": (
                "Não foi possível carregar o teste."
            )
        }), 500

    data_solicitacao = datetime.now().strftime(
        "%d/%m/%Y às %H:%M:%S"
    )

    ip_cliente = obter_ip_cliente()

    celular_formatado = formatar_celular(
        celular
    )

    # --------------------------------------------------------
    # VERIFICA DUPLICIDADE
    # --------------------------------------------------------

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
                        "Este e-mail já utilizou o teste."
                    )
                }), 409

            if celular_registrado == celular:
                return jsonify({
                    "success": False,
                    "message": (
                        "Este WhatsApp já utilizou o teste."
                    )
                }), 409

        # ----------------------------------------------------
        # REGISTRA O CLIENTE
        # ----------------------------------------------------

        novo_cliente = {
            "nome": nome,
            "email": email_cliente,
            "celular": celular,
            "celular_formatado": celular_formatado,
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

    # --------------------------------------------------------
    # RETORNO PARA A TELA
    # --------------------------------------------------------

    return jsonify({
        "success": True,

        "message": (
            "Teste liberado com sucesso."
        ),

        "cliente": {
            "nome": nome,
            "email": email_cliente,
            "celular": celular_formatado,
            "data_solicitacao": data_solicitacao
        },

        "template": template_pt

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
