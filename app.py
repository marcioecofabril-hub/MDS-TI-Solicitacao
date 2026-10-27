import os
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)


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


# Rota simplificada apenas para dar sinal verde para o formulário enviar o e-mail
@app.route("/registrar", methods=["POST"])
@app.route("/api/customers", methods=["POST"])
def registrar():
    return jsonify({
        "success": True,
        "message": "Processando...",
        "template": "Seu teste MDS_TI foi liberado! Acesse os dados enviados no seu e-mail."
    })


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
