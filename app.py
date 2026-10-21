import os
import smtplib
import ssl

from email.message import EmailMessage
from flask import Flask, render_template, request


app = Flask(__name__)


@app.route("/")
def inicio():
    return render_template("index.html")


@app.route("/solicitar", methods=["POST"])
def solicitar():

    # =========================
    # DADOS DO FORMULÁRIO
    # =========================

    nome = request.form.get("nome", "").strip()
    email = request.form.get("email", "").strip()
    whatsapp = request.form.get("whatsapp", "").strip()

    # Validação básica
    if not nome or not email or not whatsapp:
        return render_template(
            "index.html",
            erro="Preencha nome, e-mail e WhatsApp."
        )


    # =========================
    # CONFIGURAÇÃO DO E-MAIL
    # =========================

    remetente = os.environ.get("EMAIL_USER")
    senha_app = os.environ.get("EMAIL_PASSWORD")
    destinatario = os.environ.get("EMAIL_DESTINO")


    # Verifica se as variáveis existem
    if not remetente or not senha_app or not destinatario:

        print(
            "ERRO: Variáveis de e-mail não configuradas no Render."
        )

        return render_template(
            "index.html",
            erro="Não foi possível enviar a solicitação. Tente novamente."
        )


    # =========================
    # CRIAÇÃO DA MENSAGEM
    # =========================

    mensagem = EmailMessage()

    mensagem["From"] = remetente
    mensagem["To"] = destinatario

    mensagem["Subject"] = (
        "Nova Solicitação de Teste | MDS_TI"
    )

    mensagem.set_content(
        f"""
NOVA SOLICITAÇÃO DE TESTE - MDS_TI


Nome:
{nome}

E-mail:
{email}

WhatsApp:
{whatsapp}


Entrar em contato com o solicitante pelo WhatsApp
para entender a necessidade e concluir os detalhes
da solicitação do teste.


----------------------------------------
MDS_TI
Tecnologia e Soluções
        """
    )


    # =========================
    # ENVIO PELO GMAIL
    # =========================

    try:

        contexto_ssl = ssl.create_default_context()

        with smtplib.SMTP_SSL(
            "smtp.gmail.com",
            465,
            context=contexto_ssl,
            timeout=20
        ) as servidor:

            servidor.login(
                remetente,
                senha_app
            )

            servidor.send_message(
                mensagem
            )


        print(
            f"SOLICITACAO ENVIADA COM SUCESSO: "
            f"{nome} | {email} | {whatsapp}"
        )


        # =========================
        # CONFIRMAÇÃO NA TELA
        # =========================

        return render_template(
            "index.html",
            sucesso=True,
            nome=nome
        )


    except Exception as erro:

        print(
            "ERRO AO ENVIAR EMAIL:",
            repr(erro)
        )

        return render_template(
            "index.html",
            erro=(
                "Não foi possível enviar sua solicitação. "
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
