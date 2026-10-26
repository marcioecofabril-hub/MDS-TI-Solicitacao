import os
from flask import Flask, jsonify, render_template

app = Flask(__name__)

# Os dados da sua API salvos no servidor de teste
DADOS_API_TESTE = [
    {
        "key": "de",
        "template": "O administrador do painel não configurou um template para este servidor no seu idioma. Peça ao administrador do painel para editar o servidor."
    },
    {
        "key": "en",
        "template": "O administrador do painel não configurou um template para este servidor no seu idioma. Peça ao administrador do painel para editar o servidor."
    },
    {
        "key": "es",
        "template": "O administrador do painel não configurou um template para este servidor no seu idioma. Peça ao administrador do painel para editar o servidor."
    },
    {
        "key": "fr",
        "template": "O administrador do painel não configurou um template para este servidor no seu idioma. Peça ao administrador do painel para editar o servidor."
    },
    {
        "key": "pt",
        "template": "Royal Platinum ⭕ ( *Servidor Premium*)\n🔺top¹\n_________________________________________\n🔐 DADOS DE ACESSO\n\n✅ *Usuário:* 8612723\n✅ *Senha:* 7665256\n\n🟠 URL(dedicada): http://royal3.fun\n\n🟠 URL2: http://srph.fun\n_________________________________________\n\n🌏 Link(dedicada+M3U): http://royal3.fun\n\n🌏 Link2 (M3U): http://srph.fun\n_________________________________________\n📲 APLICATIVOS PARCEIROS E CÓDIGOS\n\n🔶 Kayros player | Kayros pro \n*Obs: Samsung ano 2023 para cima 🔝*\n🔍 (Roku • Samsung • Android)\n\n✅Usuário: 8612723\n✅ Senha: 7665256\n*🔢 Server Code: 3898 ➕ RECOMENDADO* \n\n🔄 Server Code alternativo: 4937 — 2ª opção"
    }
]

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

# Endpoint que seu frontend vai chamar para pegar o template em tempo real
@app.route("/api/teste", methods=["GET"])
def obter_dados_teste():
    return jsonify(DADOS_API_TESTE)

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
