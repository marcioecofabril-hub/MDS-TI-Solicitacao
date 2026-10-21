import os
import smtplib
import ssl
from email.message import EmailMessage
from flask import Flask, render_template, request

app = Flask(__name__)

@app.route('/', methods=['GET'])
def inicio():
    return render_template('index.html', sucesso=False, erro=None)

@app.route('/solicitar', methods=['POST'])
def solicitar():
    nome = request.form.get('nome', '').strip()
    email = request.form.get('email', '').strip()
    whatsapp = request.form.get('whatsapp', '').strip()

    if not nome or not email or not whatsapp:
        return render_template('index.html', sucesso=False, erro='Preencha nome, e-mail e WhatsApp corretamente.')

    email_user = os.environ.get('EMAIL_USER', '').strip()
    email_password = os.environ.get('EMAIL_PASSWORD', '').replace(' ', '')
    email_destino = os.environ.get('EMAIL_DESTINO', '').strip()

    if not email_user or not email_password or not email_destino:
        return render_template('index.html', sucesso=False, erro='Configuracao de e-mail nao definida. Configure EMAIL_USER, EMAIL_PASSWORD e EMAIL_DESTINO.')

    mensagem = EmailMessage()
    mensagem['From'] = email_user
    mensagem['To'] = email_destino
    mensagem['Reply-To'] = email
    mensagem['Subject'] = f'Nova Solicitacao de Teste | {nome}'
    mensagem.set_content(f'''NOVA SOLICITACAO DE TESTE - MDS_TI\n\nNome: {nome}\nE-mail: {email}\nWhatsApp: {whatsapp}\n\nEntre em contato pelo WhatsApp para concluir os detalhes do teste.\n''')

    try:
        contexto_ssl = ssl.create_default_context()
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=contexto_ssl, timeout=30) as servidor:
            servidor.login(email_user, email_password)
            servidor.send_message(mensagem)
        return render_template('index.html', sucesso=True, nome=nome, erro=None)
    except smtplib.SMTPAuthenticationError:
        return render_template('index.html', sucesso=False, erro='Falha de autenticacao no Gmail. Verifique a senha de app.')
    except Exception as erro:
        print('ERRO AO ENVIAR EMAIL:', repr(erro))
        return render_template('index.html', sucesso=False, erro='Nao foi possivel enviar a solicitacao. Tente novamente.')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
