import os
from flask import Flask, render_template, request

app = Flask(__name__)


@app.route("/")
def inicio():
    return render_template("index.html")


@app.route("/solicitar", methods=["POST"])
def solicitar():
    nome = request.form.get("nome", "")
    empresa = request.form.get("empresa", "")
    email = request.form.get("email", "")
    whatsapp = request.form.get("whatsapp", "")
    tipo_teste = request.form.get("tipo_teste", "")
    equipamento = request.form.get("equipamento", "")
    data = request.form.get("data", "")
    descricao = request.form.get("descricao", "")

    solicitacao = {
        "nome": nome,
        "empresa": empresa,
        "email": email,
        "whatsapp": whatsapp,
        "tipo_teste": tipo_teste,
        "equipamento": equipamento,
        "data": data,
        "descricao": descricao,
    }

    # Na próxima etapa conectaremos esta solicitação
    # ao serviço responsável pelo envio da notificação.
    print("Nova solicitação:", solicitacao)

    return render_template(
        "index.html",
        sucesso=True,
        nome=nome
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
