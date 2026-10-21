import json
import os
import urllib.error
import urllib.request

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

    # ==========================================
    # DADOS RECEBIDOS DO FORMULÁRIO
    # ==========================================

    nome = request.form.get("nome", "").strip()
    email = request.form.get("email", "").strip()
    whatsapp = request.form.get("whatsapp", "").strip()


    # ==========================================
    # VALIDAÇÃO DOS CAMPOS
    # ==========================================

    if not nome or not email or not whatsapp:

        return render_template(
            "index.html",
            sucesso=False,
            erro="Preencha nome, e-mail e WhatsApp corretamente."
        )


    # ==========================================
    # ACCESS KEY DO WEB3FORMS
    # ==========================================

    access_key = os.environ.get(
        "WEB3FORMS_ACCESS_KEY",
        ""
    ).strip()


    if not access_key:

        print(
            "ERRO: WEB3FORMS_ACCESS_KEY "
            "não configurada no Render."
        )

        return render_template(
            "index.html",
            sucesso=False,
            erro=(
                "O serviço de envio ainda não está configurado. "
                "Tente novamente."
            )
        )


    # ==========================================
    # DADOS QUE SERÃO ENVIADOS
    # ==========================================

    dados = {
        "access_key": access_key,

        "subject": (
            f"Nova Solicitação de Teste | {nome}"
        ),

        "from_name": (
            "MDS_TI - Solicitação de Testes"
        ),

        "name": nome,

        "email": email,

        "WhatsApp": whatsapp,

        "message": (
            "NOVA SOLICITAÇÃO DE TESTE - MDS_TI\n\n"

            f"Nome: {nome}\n"
            f"E-mail: {email}\n"
            f"WhatsApp: {whatsapp}\n\n"

            "Entrar em contato com o solicitante "
            "pelo WhatsApp para entender a necessidade "
            "e concluir os detalhes do teste."
        )
    }


    # ==========================================
    # CONVERTE PARA JSON
    # ==========================================

    corpo = json.dumps(
        dados
    ).encode("utf-8")


    # ==========================================
    # REQUISIÇÃO HTTPS PARA WEB3FORMS
    # ==========================================

    requisicao = urllib.request.Request(
        url="https://api.web3forms.com/submit",
        data=corpo,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    )


    try:

        # ======================================
        # ENVIA A SOLICITAÇÃO
        # ======================================

        with urllib.request.urlopen(
            requisicao,
            timeout=30
        ) as resposta:

            conteudo = resposta.read().decode(
                "utf-8"
            )


        resultado = json.loads(
            conteudo
        )


        # ======================================
        # SUCESSO
        # ======================================

        if resultado.get("success") is True:

            print(
                "SOLICITAÇÃO ENVIADA COM SUCESSO:"
            )

            print(
                f"Nome: {nome}"
            )

            print(
                f"E-mail: {email}"
            )

            print(
                f"WhatsApp: {whatsapp}"
            )


            return render_template(
                "index.html",
                sucesso=True,
                nome=nome,
                erro=None
            )


        # ======================================
        # WEB3FORMS RESPONDEU, MAS RECUSOU
        # ======================================

        mensagem_erro = resultado.get(
            "message",
            "Erro desconhecido no Web3Forms."
        )

        print(
            "WEB3FORMS RECUSOU A SOLICITAÇÃO:",
            mensagem_erro
        )


        return render_template(
            "index.html",
            sucesso=False,
            erro=(
                "Não foi possível enviar a solicitação. "
                "Por favor, tente novamente."
            )
        )


    # ==========================================
    # ERRO HTTP
    # ==========================================

    except urllib.error.HTTPError as erro:

        try:

            resposta_erro = erro.read().decode(
                "utf-8"
            )

        except Exception:

            resposta_erro = ""


        print(
            "ERRO HTTP WEB3FORMS:",
            erro.code,
            resposta_erro
        )


        return render_template(
            "index.html",
            sucesso=False,
            erro=(
                "O serviço não conseguiu enviar "
                "a solicitação. Tente novamente."
            )
        )


    # ==========================================
    # ERRO DE CONEXÃO
    # ==========================================

    except urllib.error.URLError as erro:

        print(
            "ERRO DE CONEXÃO COM WEB3FORMS:",
            repr(erro)
        )


        return render_template(
            "index.html",
            sucesso=False,
            erro=(
                "Não foi possível conectar ao serviço "
                "de envio. Tente novamente."
            )
        )


    # ==========================================
    # QUALQUER OUTRO ERRO
    # ==========================================

    except Exception as erro:

        print(
            "ERRO INESPERADO:",
            repr(erro)
        )


        return render_template(
            "index.html",
            sucesso=False,
            erro=(
                "Não foi possível enviar a solicitação. "
                "Tente novamente."
            )
        )


# ==============================================
# EXECUÇÃO LOCAL
# ==============================================

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
