import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

# Os dados da sua API salvos no servidor de teste
DADOS_API_TESTE = [
    {
        "key": "pt",
        "template": "Royal Platinum ⭕ ( *Servidor Premium*)\n🔺top¹\n_________________________________________\n🔐 DADOS DE ACESSO\n\n✅ *Usuário:* 8612723\n✅ *Senha:* 7665256\n\n🟠 URL(dedicada): http://royal3.fun\n\n🟠 URL2: http://srph.fun\n_________________________________________\n\n🌏 Link(dedicada+M3U): http://royal3.fun\n\n🌏 Link2 (M3U): http://srph.fun"
    }
]

@app.route("/", methods=["GET", "POST"])
def inicio():
    web3forms_access_key = os.environ.get("WEB3FORMS_ACCESS_KEY", "").strip()

    if request.method == "GET":
        return render_template("index.html", web3forms_access_key=web3forms_access_key)

    # Coleta tradicional via POST do formulário
    nome = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip()
    whatsapp = (request.form.get("whatsapp") or "").strip()

    if not nome or not email or not whatsapp:
        return render_template("index.html", web3forms_access_key=web3forms_access_key, error="Preencha todos os campos obrigatórios.")

    # Captura e limpa o texto em português para o e-mail passar sem filtros de spam
    template_pt = DADOS_API_TESTE[0]["template"]
    template_limpo = template_pt.replace(/_+/g, "").strip()

    mensagem_email = (
        f"NOVA SOLICITAÇÃO RECEBIDA - WEB3FORMS\n"
        f"=========================================\n"
        f"Nome: {nome}\n"
        f"E-mail: {email}\n"
        f"WhatsApp: {whatsapp}\n"
        f"=========================================\n\n"
        f"--- DADOS DE ACESSO GERADOS ---\n"
        f"{template_limpo}"
    )

    payload_web3 = {
        "access_key": web3forms_access_key,
        "to": "marcio.ecofabril@gmail.com",
        "subject": f"Novo Teste Solicitado | {nome}",
        "from_name": "MDS_TI - Sistema",
        "name": nome,
        "email": email,
        "message": mensagem_email
    }

    try:
        # O próprio servidor Python faz a requisição para a API do Web3Forms
        resposta = requests.post("https://web3forms.com", json=payload_web3, timeout=20)
        resultado = resposta.json()
        
        if resposta.status_code == 200 and resultado.get("success"):
            return render_template("index.html", 
                                   web3forms_access_key=web3forms_access_key, 
                                   sucesso=True, 
                                   nome_cliente=nome, 
                                   dados_acesso=template_pt)
        else:
            erro_msg = resultado.get("message", "Chave do Web3Forms inválida ou recusada.")
            return render_template("index.html", web3forms_access_key=web3forms_access_key, error=f"Erro no Web3Forms: {erro_msg}")

    except Exception as e:
        return render_template("index.html", web3forms_access_key=web3forms_access_key, error="Não foi possível estabelecer contato com a API de e-mail.")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
