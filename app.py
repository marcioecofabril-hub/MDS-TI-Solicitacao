import os

import requests
from flask import Flask, jsonify, render_template, request


app = Flask(__name__)

WEB3FORMS_URL = "https://api.web3forms.com/submit"


@app.route("/", methods=["GET"])
def inicio():
    return render_template("index.html")


@app.route("/registrar", methods=["POST"])
@app.route("/api/customers", methods=["POST"])
def registrar():
    try:
        dados = request.get_json(silent=True) or {}

        nome = str(dados.get("nome", "")).strip()
        email = str(dados.get("email", "")).strip().lower()
        celular = str(dados.get("celular", "")).strip()

        if not nome or not email or not celular:
            return jsonify({
                "success": False,
                "message": "Preencha todos os campos corretamente."
            }), 400

        access_key = os.environ.get(
            "WEB3FORMS_ACCESS_KEY",
            ""
        ).strip()

        if not access_key:
            print("ERRO: WEB3FORMS_ACCESS_KEY não configurada.")

            return jsonify({
                "success": False,
                "message": "O serviço de envio não está configurado."
            }), 500

        conteudo_email = f"""
NOVA SOLICITAÇÃO DE TESTE

=====================================
DADOS DO CLIENTE
=====================================

Nome: {nome}
E-mail: {email}
WhatsApp: {celular}

=====================================

Solicitação recebida pela página MDS_TI.
"""

        payload = {
            "access_key": access_key,
            "subject": f"Nova solicitação de teste | {nome}",
            "from_name": "MDS_TI - Solicitação",
            "name": nome,
            "email": email,
            "whatsapp": celular,
            "message": conteudo_email
        }

        resposta = requests.post(
            WEB3FORMS_URL,
            json=payload,
            timeout=15
        )

        try:
            resposta_web3forms = resposta.json()
        except ValueError:
            resposta_web3forms = {}

        print(
            "Web3Forms:",
            resposta.status_code,
            resposta_web3forms
        )

        if not resposta.ok:
            return jsonify({
                "success": False,
                "message": "Não foi possível enviar a solicitação."
            }), 502

        if not resposta_web3forms.get("success"):
            return jsonify({
                "success": False,
                "message": resposta_web3forms.get(
                    "message",
                    "O Web3Forms recusou a solicitação."
                )
            }), 502

        return jsonify({
            "success": True,
            "message": "Teste liberado com sucesso.",
            "template": (
                "Seu teste MDS_TI foi liberado! "
                "Acesse os dados enviados no seu e-mail e WhatsApp."
            )
        }), 200

    except requests.Timeout:
        print("ERRO: timeout ao conectar ao Web3Forms.")

        return jsonify({
            "success": False,
            "message": "O serviço de envio demorou para responder."
        }), 504

    except requests.RequestException as erro:
        print("ERRO WEB3FORMS:", repr(erro))

        return jsonify({
            "success": False,
            "message": "Não foi possível conectar ao serviço de envio."
        }), 502

    except Exception as erro:
        print("ERRO INTERNO:", repr(erro))

        return jsonify({
            "success": False,
            "message": "Erro interno ao processar a solicitação."
        }), 500


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
