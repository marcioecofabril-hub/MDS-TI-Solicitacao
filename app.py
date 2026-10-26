import json
import os
import re
import threading
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request


app = Flask(__name__)


# ============================================================
# CONFIGURAÇÃO DO ARQUIVO DE REGISTROS
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
    return re.sub(r"\D", "", str(celular or ""))


def email_valido(email):
    padrao = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    return re.match(padrao, email) is not None


def celular_valido(celular):
    return 10 <= len(celular) <= 13


def criar_arquivo_se_necessario():
    if not ARQUIVO_CLIENTES.exists():
        ARQUIVO_CLIENTES.write_text(
            "[]",
            encoding="utf-8"
        )


def carregar_clientes():
    criar_arquivo_se_necessario()

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

    except (json.JSONDecodeError, OSError):
        return []


def salvar_clientes(clientes):
    arquivo_temporario = ARQUIVO_CLIENTES.with_suffix(
        ".tmp"
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


def obter_ip_cliente():
    ip_encaminhado = request.headers.get(
        "X-Forwarded-For",
        ""
    )

    if ip_encaminhado:
        return ip_encaminhado.split(",")[0].strip()

    return request.remote_addr or ""


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
# REGISTRO DO TESTE
# ============================================================

@app.route("/registrar", methods=["POST"])
def registrar():

    dados = request.get_json(
        silent=True
    ) or {}

    nome = str(
        dados.get("nome") or ""
    ).strip()

    email = normalizar_email(
        dados.get("email")
    )

    celular = normalizar_celular(
        dados.get("celular")
    )

    if not nome or not email or not celular:
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

    if not email_valido(email):
        return jsonify({
            "success": False,
            "message": "Informe um e-mail válido."
        }), 400

    if not celular_valido(celular):
        return jsonify({
            "success": False,
            "message": "Informe um celular válido com DDD."
        }), 400

    with bloqueio_arquivo:

        clientes = carregar_clientes()

        for cliente in clientes:

            email_registrado = normalizar_email(
                cliente.get("email")
            )

            celular_registrado = normalizar_celular(
                cliente.get("celular")
            )

            if email_registrado == email:
                return jsonify({
                    "success": False,
                    "already_used": True,
                    "message": (
                        "Este e-mail já utilizou o teste."
                    )
                }), 409

            if celular_registrado == celular:
                return jsonify({
                    "success": False,
                    "already_used": True,
                    "message": (
                        "Este celular já utilizou o teste."
                    )
                }), 409

        novo_cliente = {
            "nome": nome,
            "email": email,
            "celular": celular,
            "data_solicitacao": datetime.now().isoformat(
                timespec="seconds"
            ),
            "ip": obter_ip_cliente()
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
                "[ERRO] Não foi possível salvar "
                f"clientes.json: {erro}"
            )

            return jsonify({
                "success": False,
                "message": (
                    "Não foi possível registrar a "
                    "solicitação."
                )
            }), 500

    print(
        "[REGISTRO] Nova solicitação: "
        f"{email} | {celular}"
    )

    return jsonify({
        "success": True,
        "message": "Solicitação registrada."
    }), 201


# ============================================================
# EXECUÇÃO LOCAL
# ============================================================

if __name__ == "__main__":

    criar_arquivo_se_necessario()

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
