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
            erro="Preencha nome, e-mail e WhatsApp corretamente."
        )

    email_user = os.environ.get("EMAIL_USER", "").strip()
    email_password = os.environ.get("EMAIL_PASSWORD", "").replace(" ", "")
    email_destino = os.environ.get("EMAIL_DESTINO", "").strip()

    if not email_user or not email_password or not email_destino:

        print(
            "ERRO DE CONFIGURAÇÃO: "
            "EMAIL_USER, EMAIL_PASSWORD ou EMAIL_DESTINO não configurado."
        )

        return render_template(
            "index.html",
            sucesso=False,
            erro=(
                "Não foi possível processar a solicitação. "
                "A configuração de e-mail não está completa."
            )
        )

    mensagem = EmailMessage()

    mensagem["From"] = email_user
    mensagem["To"] = email_destino
    mensagem["Reply-To"] = email
    mensagem["Subject"] = f"Nova Solicitação de Teste | {nome}"

    mensagem.set_content(
        f"""
NOVA SOLICITAÇÃO DE TESTE - MDS_TI

Nome: {nome}
E-mail: {email}
WhatsApp: {whatsapp}

Entre em contato com o solicitante pelo WhatsApp
para entender a necessidade e concluir os detalhes
da solicitação do teste.

----------------------------------------
MDS_TI
Tecnologia e Soluções
"""
    )

    try:

        contexto_ssl = ssl.create_default_context()

        with smtplib.SMTP_SSL(
            host="smtp.gmail.com",
            port=465,
            context=contexto_ssl,
            timeout=30
        ) as servidor:

            servidor.login(
                email_user,
                email_password
            )

            servidor.send_message(
                mensagem
            )

        print(
            "EMAIL ENVIADO COM SUCESSO: "
            f"{nome} | {email} | {whatsapp}"
        )

        return render_template(
            "index.html",
            sucesso=True,
            nome=nome,
            erro=None
        )

    except smtplib.SMTPAuthenticationError as erro:

        print(
            "ERRO DE AUTENTICAÇÃO DO GMAIL:",
            repr(erro)
        )

        return render_template(
            "index.html",
            sucesso=False,
            erro=(
                "Não foi possível autenticar no Gmail. "
                "Verifique a senha de aplicativo configurada no Render."
            )
        )

    except smtplib.SMTPException as erro:

        print(
            "ERRO SMTP:",
            repr(erro)
        )

        return render_template(
            "index.html",
            sucesso=False,
            erro=(
                "O Gmail não conseguiu enviar a solicitação. "
                "Por favor, tente novamente."
            )
        )

    except Exception as erro:

        print(
            "ERRO INESPERADO AO ENVIAR E-MAIL:",
            repr(erro)
        )

        return render_template(
            "index.html",
            sucesso=False,
            erro=(
                "Não foi possível enviar a solicitação. "
                "Por favor, tente novamente."
            )
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
