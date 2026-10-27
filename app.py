import os

import requests
from flask import Flask, jsonify, render_template, request


app = Flask(__name__)


# ============================================================
# CONFIGURAÇÕES
# ============================================================

WEB3FORMS_URL = "https://api.web3forms.com/submit"


# ============================================================
# PÁGINA PRINCIPAL
# ============================================================

@app.route("/", methods=["GET"])
def inicio():
    return render_template("index.html")


# ============================================================
# REGISTRAR SOLICITAÇÃO
# ============================================================

@app.route("/registrar", methods=["POST"])
@app.route("/api/customers", methods=["POST"])
def registrar():

    try:

        # ----------------------------------------------------
        # RECEBE OS DADOS DO FRONT-END
        # ----------------------------------------------------

        dados = request.get_json(silent=True)

        if not dados:
            return jsonify({
                "success": False,
                "message": "Nenhum dado foi recebido pelo servidor."
            }), 400


        nome = str(
            dados.get("nome", "")
        ).strip()


        email = str(
            dados.get("email", "")
        ).strip().lower()


        celular = str(
            dados.get("celular", "")
        ).strip()


        # ----------------------------------------------------
        # VALIDAÇÃO
        # ----------------------------------------------------

        if not nome:
            return jsonify({
                "success": False,
                "message": "Informe o nome completo."
            }), 400


        if not email or "@" not in email:
            return jsonify({
                "success": False,
                "message": "Informe um e-mail válido."
            }), 400


        celular_numeros = "".join(
            numero for numero in celular if numero.isdigit()
        )


        if len(celular_numeros) < 10:

            return jsonify({
                "success": False,
                "message": "Informe um WhatsApp válido com DDD."
            }), 400


        # ----------------------------------------------------
        # PEGA A CHAVE DO WEB3FORMS NO RENDER
        # ----------------------------------------------------

        web3forms_access_key = os.environ.get(
            "WEB3FORMS_ACCESS_KEY",
            ""
        ).strip()


        if not web3forms_access_key:

            print(
                "ERRO: variável WEB3FORMS_ACCESS_KEY não configurada."
            )

            return jsonify({
                "success": False,
                "message": (
                    "O serviço de envio de e-mail "
                    "não está configurado no servidor."
                )
            }), 500


        # ----------------------------------------------------
        # MONTA O E-MAIL
        # ----------------------------------------------------

        mensagem_email = f"""
NOVA SOLICITAÇÃO DE TESTE MDS_TI

=====================================
DADOS DO CLIENTE
=====================================

Nome: {nome}

E-mail: {email}

WhatsApp: {celular_numeros}

=====================================

Solicitação recebida através da página MDS_TI.
"""


        payload = {

            "access_key": web3forms_access_key,

            "subject": (
                f"Nova solicitação de teste | {nome}"
            ),

            "from_name": "MDS_TI - Solicitação",

            "name": nome,

            "email": email,

            "whatsapp": celular_numeros,

            "message": mensagem_email
        }


        # ----------------------------------------------------
        # ENVIA PARA O WEB3FORMS
        # ----------------------------------------------------

        try:

            resposta_web3forms = requests.post(
                WEB3FORMS_URL,
                json=payload,
                timeout=20
            )


        except requests.Timeout:

            print(
                "ERRO: timeout ao conectar com Web3Forms."
            )

            return jsonify({
                "success": False,
                "message": (
                    "O serviço de e-mail demorou "
                    "demais para responder."
                )
            }), 504


        except requests.RequestException as erro:

            print(
                "ERRO DE CONEXÃO COM WEB3FORMS:",
                repr(erro)
            )

            return jsonify({
                "success": False,
                "message": (
                    "Não foi possível conectar "
                    "ao serviço de envio de e-mail."
                )
            }), 502


        # ----------------------------------------------------
        # TENTA INTERPRETAR RESPOSTA
        # ----------------------------------------------------

        try:

            resultado_web3forms = resposta_web3forms.json()

        except ValueError:

            print(
                "RESPOSTA INVÁLIDA DO WEB3FORMS:",
                resposta_web3forms.text
            )

            return jsonify({
                "success": False,
                "message": (
                    "O serviço de envio retornou "
                    "uma resposta inválida."
                )
            }), 502


        print(
            "WEB3FORMS STATUS:",
            resposta_web3forms.status_code
        )

        print(
            "WEB3FORMS RESPOSTA:",
            resultado_web3forms
        )


        # ----------------------------------------------------
        # VERIFICA HTTP
        # ----------------------------------------------------

        if not resposta_web3forms.ok:

            mensagem_erro = resultado_web3forms.get(
                "message",
                "O serviço de e-mail recusou a solicitação."
            )

            return jsonify({
                "success": False,
                "message": mensagem_erro
            }), 502


        # ----------------------------------------------------
        # VERIFICA RESPOSTA DO WEB3FORMS
        # ----------------------------------------------------

        if not resultado_web3forms.get(
            "success",
            False
        ):

            mensagem_erro = resultado_web3forms.get(
                "message",
                "O e-mail não pôde ser enviado."
            )

            return jsonify({
                "success": False,
                "message": mensagem_erro
            }), 502


        # ----------------------------------------------------
        # SUCESSO
        # ----------------------------------------------------

        print(
            f"SOLICITAÇÃO REGISTRADA: "
            f"{nome} | {email} | {celular_numeros}"
        )


        return jsonify({

            "success": True,

            "message": (
                "Solicitação registrada com sucesso!"
            ),

            "template": (
                "Seu teste MDS_TI foi liberado!\n\n"
                "Os dados da solicitação foram enviados "
                "com sucesso."
            )

        }), 200


    except Exception as erro:

        print(
            "ERRO INTERNO EM /registrar:",
            repr(erro)
        )

        return jsonify({
            "success": False,
            "message": (
                "Ocorreu um erro interno ao processar "
                "a solicitação."
            )
        }), 500


# ============================================================
# EXECUÇÃO LOCAL
# ============================================================

if __name__ == "__main__":

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
