import os
from flask import Flask, render_template, request

app = Flask(__name__)


@app.route("/")
def inicio():
    return render_template("index.html")


@app.route("/solicitar", methods=["POST"])
def solicitar():
    nome = request.form.get("nome", "").strip()
    email = request.form.get("email", "").strip()
    whatsapp = request.form.get("whatsapp", "").strip()

    # Dados recebidos pelo formulário
    solicitacao = {
        "nome": nome,
        "email": email,
        "whatsapp": whatsapp
    }

    # Temporariamente registra no log do Render.
    # Depois conectaremos aqui o envio da notificação.
    print("NOVA SOLICITACAO DE TESTE:", solicitacao)

    return render_template(
        "index.html",
        sucesso=True,
        nome=nome
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port
    )
