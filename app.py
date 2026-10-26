import os
import requests
from flask import Flask, render_template, request

app = Flask(__name__)

# Banco de dados simulado com as credenciais da API em Português
DADOS_API_TESTE = {
    "key": "pt",
    "template": "Royal Platinum ⭕ ( *Servidor Premium*)\n🔺top¹\n_________________________________________\n🔐 DADOS DE ACESSO\n\n✅ *Usuário:* 8612723\n✅ *Senha:* 7665256\n\n🟠 URL(dedicada): http://royal3.fun\n\n🟠 URL2: http://srph.fun\n_________________________________________\n\n🌏 Link(dedicada+M3U): http://royal3.fun\n\n🌏 Link2 (M3U): http://srph.fun"
}

@app.route("/", methods=["GET", "POST"])
def inicio():
    # Coleta a chave salva nas variáveis de ambiente do Render
    web3forms_access_key = os.environ.get("WEB3FORMS_ACCESS_KEY", "").strip()

    if request.method == "GET":
        return render_template("index.html", web3forms_access_key=web3forms_access_key)

    # Captura os dados do POST tradicional (Formulário HTML)
    nome = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip()
    whatsapp = (request.form.get("whatsapp") or "").strip()

    if not nome or not email or not whatsapp:
        return render_template("index.html", web3forms_access_key=web3forms_access_key, error="Preencha todos os campos obrigatórios.")

    template_pt = DADOS_API_TESTE["template"]
    
    # Limpa caracteres repetidos como sublinhados para o e-mail não cair na caixa de SPAM do Web3Forms
    template_limpo = template_pt.replace("_", "")

    # Monta o e-mail que vai chegar para você
    mensagem_email = (
        f"NOVA SOLICITAÇÃO DE TESTE RECEBIDA\n"
        f"=========================================\n"
        f"Nome do Cliente: {nome}\n"
        f"E-mail do Cliente: {email}\n"
        f"WhatsApp do Cliente: {whatsapp}\n"
        f"=========================================\n\n"
        f"--- CREDENCIAIS EXIBIDAS NA TELA ---\n"
        f"{template_limpo}"
    )

    payload_web3 = {
        "access_key": web3forms_access_key,
        "to": "marcio.ecofabril@gmail.com",
        "subject": f"Novo Teste Gerado | {nome}",
        "from_name": "MDS_TI - Captura",
        "name": nome,
        "email": email,
        "message": mensagem_email
    }

    try:
        # Chamada direta do Servidor para o Web3Forms (Livre de erros de CORS do Navegador)
        resposta = requests.post("https://web3forms.com", json=payload_web3, timeout=20)
        resultado = resposta.json()
        
        if resposta.status_code == 200 and resultado.get("success"):
            # Devolve a página injetando o bloco de sucesso com as credenciais na tela
            return render_template("index.html", 
                                   web3forms_access_key=web3forms_access_key, 
                                   sucesso=True, 
                                   nome_cliente=nome, 
                                   dados_acesso=template_pt)
        else:
            erro_msg = resultado.get("message", "Chave inválida ou limite atingido.")
            return render_template("index.html", web3forms_access_key=web3forms_access_key, error=f"Erro Web3Forms: {erro_msg}")

    except Exception as e:
        return render_template("index.html", web3forms_access_key=web3forms_access_key, error="Não foi possível processar o envio pelo servidor. Tente novamente.")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
