import html
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
    return re.sub(r"\D", "", str(celular or ""))


def email_valido(email):
    padrao = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    return re.match(padrao, email) is not None


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


def enviar_email_teste(
    nome,
    email_cliente,
    celular,
    data_solicitacao,
    ip_cliente
):
    resend_api_key = os.environ.get(
        "RESEND_API_KEY",
        ""
    ).strip()

    email_destino = os.environ.get(
        "EMAIL_DESTINO",
        ""
    ).strip()

    remetente_email = os.environ.get(
        "RESEND_FROM_EMAIL",
        "MDS_TI <onboarding@resend.dev>"
    ).strip()

    dados_teste = os.environ.get(
        "DADOS_COMPLETOS_TESTE",
        ""
    ).strip()

    if not resend_api_key:
        raise RuntimeError(
            "A variável RESEND_API_KEY não foi configurada."
        )

    if not email_destino:
        raise RuntimeError(
            "A variável EMAIL_DESTINO não foi configurada."
        )

    if not dados_teste:
        raise RuntimeError(
            "A variável DADOS_COMPLETOS_TESTE não foi configurada."
        )

    nome_seguro = html.escape(nome)
    email_seguro = html.escape(email_cliente)
    celular_seguro = html.escape(celular)
    data_segura = html.escape(data_solicitacao)
    ip_seguro = html.escape(ip_cliente)
    teste_seguro = html.escape(dados_teste)

    teste_formatado = teste_seguro.replace(
        "\n",
        "<br>"
    )

    corpo_email = f"""
    <div style="
        font-family: Arial, Helvetica, sans-serif;
        max-width: 700px;
        margin: auto;
        color: #172033;
    ">
        <div style="
            background: #0b67b2;
            color: white;
            padding: 22px;
            border-radius: 12px 12px 0 0;
        ">
            <h1 style="margin: 0; font-size: 24px;">
                Nova solicitação de teste
            </h1>
        </div>

        <div style="
            padding: 24px;
            border: 1px solid #d7e0ea;
            border-top: 0;
        ">
            <h2 style="color: #10233f;">
                Dados do cliente
            </h2>

            <p>
                <strong>Nome:</strong>
                {nome_seguro}
            </p>

            <p>
                <strong>E-mail:</strong>
                {email_seguro}
            </p>

            <p>
                <strong>WhatsApp:</strong>
                {celular_seguro}
            </p>

            <p>
                <strong>Data da solicitação:</strong>
                {data_segura}
            </p>

            <p>
                <strong>IP:</strong>
                {ip_seguro}
            </p>

            <hr style="
                border: 0;
                border-top: 1px solid #d7e0ea;
                margin: 25px 0;
            ">

            <h2 style="color: #10233f;">
                Informações completas do teste
            </h2>

            <div style="
                padding: 18px;
                border-radius: 10px;
                background: #f3f6fa;
                line-height: 1.7;
                white-space: normal;
            ">
                {teste_formatado}
            </div>
        </div>
    </div>
    """

    resposta = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {resend_api_key}",
            "Content-Type": "application/json"
        },
        json={
            "from": remetente_email,
            "to": [email_destino],
            "subject": (
                f"Nova solicitação de teste | {nome}"
            ),
            "html": corpo_email,
            "reply_to": email_cliente
        },
        timeout=20
    )

    if resposta.status_code not in (200, 201):
        raise RuntimeError(
            "Falha no envio do e-mail. "
            f"Status: {resposta.status_code}. "
            f"Resposta: {resposta.text}"
        )

    return resposta.json()


# ============================================================
# PÁGINA PRINCIPAL
# ============================================================

@app.route("/", methods=["GET"])
def inicio():
    return render_template(
        "index.html"
    )


# ============================================================
# REGISTRO E ENVIO
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

        try:
            resultado_email = enviar_email_teste(
                nome=nome,
                email_cliente=email_cliente,
                celular=celular,
                data_solicitacao=data_solicitacao,
                ip_cliente=ip_cliente
            )

            print(
                "[EMAIL ENVIADO] "
                f"Resultado: {resultado_email}"
            )

        except Exception as erro:
            print(
                "[ERRO DE ENVIO] "
                f"{erro}"
            )

            return jsonify({
                "success": False,
                "message": (
                    "Não foi possível enviar a solicitação. "
                    "Tente novamente."
                )
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
                    "O e-mail foi enviado, mas não foi "
                    "possível registrar a solicitação."
                )
            }), 500

    return jsonify({
        "success": True,
        "message": (
            "Solicitação enviada com sucesso. "
            "Aguarde o contato."
        )
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
