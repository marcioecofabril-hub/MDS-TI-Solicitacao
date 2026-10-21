import os
import smtplib
import ssl

from email.message import EmailMessage
from flask import Flask, render_template, request


app = Flask(__name__)


@app.route("/", methods=["GET"])
def inicio():
    return render_template(
        "index.html",
        sucesso=False,
        erro=None
    )


@app.route("/solicitar", methods=["POST"])
def solicitar():

    nome = request.form.get("nome", "").strip()
    email = request.form.get("email", "").strip()
    whatsapp = request.form.get("whatsapp", "").strip()

    if not nome or not email or not whatsapp:
        return render_template(
            "index.html",
            sucesso=False,
            erro="Preencha nome, e-mail e WhatsApp."
        )

    email_user = os.environ.get("EMAIL_USER")
    email_password = os.environ.get("EMAIL_PASSWORD")
    email_destino = os.environ.get("EMAIL_DESTINO")

    if not email_user or not email_password or not email_destino:
        print("ERRO: Variáveis de e-mail não configuradas.")

        return render_template(
            "index.html",
            sucesso=False,
            erro="Não foi possível enviar a solicitação."
        )

    mensagem = EmailMessage()

    mensagem["From"] = email_user
    mensagem["To"] = email_destino
    mensagem["Reply-To"] = email

    mensagem["Subject"] = (
        f"Nova Solicitação de Teste | {nome}"
    )

    mensagem.set_content(
        f"""
NOVA SOLICITAÇÃO DE TESTE - MDS_TI

Nome: {nome}
E-mail: {email}
WhatsApp: {whatsapp}

Entre em contato com o solicitante pelo WhatsApp
para concluir os detalhes do teste.

----------------------------------------
MDS_TI
Tecnologia e Soluções
"""
    )

    try:

        contexto_ssl = ssl.create_default_context()

        with smtplib.SMTP_SSL(
            "smtp.gmail.com",
            465,
            context=contexto_ssl,
            timeout=20
        ) as servidor:

            servidor.login(
                email_user,
                email_password
            )

            servidor.send_message(
                mensagem
            )

        print(
            f"EMAIL ENVIADO COM SUCESSO: {nome}"
        )

        return render_template(
            "index.html",
            sucesso=True,
            nome=nome,
            erro=None
        )

    except Exception as erro:

        print(
            "ERRO AO ENVIAR EMAIL:",
            repr(erro)
        )

        return render_template(
            "index.html",
            sucesso=False,
            erro="Não foi possível enviar a solicitação. Tente novamente."
        )


if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
