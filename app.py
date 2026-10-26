import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

# Os dados da sua API salvos no servidor de teste
DADOS_API_TESTE = {
    "key": "pt",
    "template": "Royal Platinum ⭕ ( *Servidor Premium*)\n🔺top¹\n_________________________________________\n🔐 DADOS DE ACESSO\n\n✅ *Usuário:* 8612723\n✅ *Senha:* 7665256\n\n🟠 URL(dedicada): http://royal3.fun\n\n🟠 URL2: http://srph.fun\n_________________________________________\n\n🌏 Link(dedicada+M3U): http://royal3.fun\n\n🌏 Link2 (M3U): http://srph.fun"
}

# Rota para entregar os dados brutos caso queira inspecionar
@app.route("/api/teste", methods=["GET"])
def obter_dados_teste():
    return [DADOS_API_TESTE]
@app.route("/", methods=["GET", "POST"])
def inicio():
    web3forms_access_key = os.environ.get(
        "WEB3FORMS_ACCESS_KEY",
        ""
    ).strip()

    if request.method == "GET":
        return render_template(
            "index.html",
            web3forms_access_key=web3forms_access_key
        )

    # Captura os dados que o cliente digitou nos campos (Método POST)
    nome = (request.form.get("name") or "").strip()
    email_cliente = (request.form.get("email") or "").strip()
    whatsapp = (request.form.get("whatsapp") or "").strip()

    if not nome or not email_cliente or not whatsapp:
        return render_template(
            "index.html",
            web3forms_access_key=web3forms_access_key,
            error="Preencha todos os campos obrigatórios."
        )

    template_pt = DADOS_API_TESTE["template"]
    
    # Limpa as linhas contínuas para o e-mail passar direto pelo firewall do Web3Forms sem ser bloqueado como Spam
    template_limpo = template_pt.replace("_", "")

    # Monta a estrutura da mensagem que vai chegar na sua caixa de entrada
    mensagem_email = (
        f"NOVA SOLICITAÇÃO DE TESTE RECEBIDA\n"
        f"=========================================\n"
        f"Nome do Cliente: {nome}\n"
        f"E-mail do Cliente: {email_cliente}\n"
        f"WhatsApp do Cliente: {whatsapp}\n"
        f"=========================================\n\n"
        f"--- CREDENCIAIS EXIBIDAS NA TELA ---\n"
        f"{template_limpo}"
    )

    payload_web3 = {
        "access_key": web3forms_access_key,
        "to": "marcio.ecofabril@gmail.com",
        "subject": f"Novo Teste Solicitado | {nome}",
        "from_name": "MDS_TI - Captura",
        "name": nome,
        "email": email_cliente,
        "message": mensagem_email
    }

    try:
        # Envio direto de servidor para servidor (Acaba com o erro de CORS/bloqueio do celular)
        resposta = requests.post("https://web3forms.com", json=payload_web3, timeout=15)
        resultado = resposta.json()
        print(f"[LOG SERVER] Status: {resposta.status_code} | Resposta: {resultado}")
    except Exception as e:
        print(f"[AVISO SERVER] Falha na comunicação com o Web3Forms: {e}")

    # Libera o acesso na tela de qualquer forma (Garante que se o e-mail atrasar, o cliente não trava)
    return render_template(
        "index.html",
        web3forms_access_key=web3forms_access_key,
        sucesso=True,
        nome_cliente=nome,
        dados_acesso=template_pt
    )
if __name__ == "__main__":

    # O Render define a porta automaticamente pela variável de ambiente PORT
    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    # Inicia o servidor Flask escutando em todas as interfaces de rede
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
