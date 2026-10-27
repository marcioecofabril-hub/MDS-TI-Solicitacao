import json
import os
import re
import secrets
import smtplib
import tempfile
from datetime import datetime, timezone
from email.message import EmailMessage
from html import unescape
from pathlib import Path

import fcntl
import requests
from flask import Flask, jsonify, render_template, request


app = Flask(__name__)


# ============================================================
# CAMINHOS DOS ARQUIVOS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

ARQUIVO_CLIENTES = BASE_DIR / "clientes.json"

ARQUIVO_LOCK = BASE_DIR / "clientes.lock"


# ============================================================
# CONFIGURAÇÕES GERAIS
# ============================================================

CLUB_INFINITY_API_URL = os.environ.get(
    "CLUB_INFINITY_API_URL",
    "https://clubinfinity.info/api"
).strip().rstrip("/")


# ============================================================
# FUNÇÕES BÁSICAS
# ============================================================

def obter_variavel(nome, valor_padrao=""):

    return os.environ.get(
        nome,
        valor_padrao
    ).strip()


def agora_iso():

    return datetime.now(
        timezone.utc
    ).isoformat()


def normalizar_email(email):

    return str(
        email or ""
    ).strip().lower()


def normalizar_celular(celular):

    return re.sub(
        r"\D",
        "",
        str(celular or "")
    )


def email_valido(email):

    padrao = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"

    return bool(
        re.match(
            padrao,
            email
        )
    )


def texto_seguro(valor):

    if valor is None:
        return ""

    return unescape(
        str(valor)
    ).strip()


# ============================================================
# CLIENTES.JSON
# ============================================================

def carregar_clientes():

    if not ARQUIVO_CLIENTES.exists():
        return []

    try:

        conteudo = ARQUIVO_CLIENTES.read_text(
            encoding="utf-8"
        ).strip()

        if not conteudo:
            return []

        dados = json.loads(
            conteudo
        )

        if isinstance(
            dados,
            list
        ):
            return dados

        if (
            isinstance(dados, dict)
            and isinstance(
                dados.get("clientes"),
                list
            )
        ):
            return dados["clientes"]

        print(
            "AVISO: clientes.json possui formato inválido."
        )

        return []

    except json.JSONDecodeError as erro:

        print(
            "ERRO DE JSON EM clientes.json:",
            repr(erro)
        )

        return []

    except OSError as erro:

        print(
            "ERRO AO LER clientes.json:",
            repr(erro)
        )

        return []


def salvar_clientes(clientes):

    diretorio = str(
        ARQUIVO_CLIENTES.parent
    )

    arquivo_temporario = None

    try:

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=diretorio,
            delete=False,
            suffix=".tmp"
        ) as arquivo:

            json.dump(
                clientes,
                arquivo,
                ensure_ascii=False,
                indent=4
            )

            arquivo.flush()

            os.fsync(
                arquivo.fileno()
            )

            arquivo_temporario = arquivo.name

        os.replace(
            arquivo_temporario,
            ARQUIVO_CLIENTES
        )

    finally:

        if (
            arquivo_temporario
            and os.path.exists(
                arquivo_temporario
            )
        ):

            try:

                os.remove(
                    arquivo_temporario
                )

            except OSError:
                pass


# ============================================================
# LOCK DO ARQUIVO JSON
# ============================================================

def executar_com_lock(funcao):

    ARQUIVO_LOCK.touch(
        exist_ok=True
    )

    with ARQUIVO_LOCK.open(
        "r+",
        encoding="utf-8"
    ) as arquivo_lock:

        fcntl.flock(
            arquivo_lock.fileno(),
            fcntl.LOCK_EX
        )

        try:

            return funcao()

        finally:

            fcntl.flock(
                arquivo_lock.fileno(),
                fcntl.LOCK_UN
            )


# ============================================================
# CONTROLE DE DUPLICIDADE
# ============================================================

def localizar_cliente(
    clientes,
    email,
    celular
):

    for cliente in clientes:

        email_salvo = normalizar_email(
            cliente.get("email")
        )

        celular_salvo = normalizar_celular(
            cliente.get("celular")
        )

        if (
            email_salvo
            and email_salvo == email
        ):

            return cliente, "email"

        if (
            celular_salvo
            and celular_salvo == celular
        ):

            return cliente, "celular"

    return None, None


def reservar_cliente(
    nome,
    email,
    celular
):

    def executar():

        clientes = carregar_clientes()

        cliente_existente, campo = localizar_cliente(
            clientes,
            email,
            celular
        )

        if cliente_existente:

            if campo == "email":

                mensagem = (
                    "Este e-mail já realizou uma "
                    "solicitação anteriormente."
                )

            else:

                mensagem = (
                    "Este WhatsApp já realizou uma "
                    "solicitação anteriormente."
                )

            return {
                "success": False,
                "duplicate": True,
                "message": mensagem
            }

        token_reserva = secrets.token_urlsafe(
            32
        )

        novo_cliente = {
            "id": secrets.token_hex(8),
            "token_reserva": token_reserva,
            "nome": nome,
            "email": email,
            "celular": celular,
            "status": "reservado",
            "criado_em": agora_iso(),
            "confirmado_em": None
        }

        clientes.append(
            novo_cliente
        )

        salvar_clientes(
            clientes
        )

        return {
            "success": True,
            "duplicate": False,
            "token": token_reserva
        }

    return executar_com_lock(
        executar
    )


def confirmar_cliente(
    token_reserva
):

    def executar():

        clientes = carregar_clientes()

        for cliente in clientes:

            token_salvo = str(
                cliente.get(
                    "token_reserva",
                    ""
                )
            )

            if (
                token_salvo
                and secrets.compare_digest(
                    token_salvo,
                    token_reserva
                )
            ):

                cliente["status"] = "confirmado"

                cliente["confirmado_em"] = agora_iso()

                cliente.pop(
                    "token_reserva",
                    None
                )

                cliente.pop(
                    "token",
                    None
                )

                salvar_clientes(
                    clientes
                )

                return True

        return False

    return executar_com_lock(
        executar
    )


def cancelar_reserva(
    token_reserva
):

    def executar():

        clientes = carregar_clientes()

        clientes_atualizados = []

        removido = False

        for cliente in clientes:

            token_salvo = str(
                cliente.get(
                    "token_reserva",
                    ""
                )
            )

            mesmo_token = (
                token_salvo
                and secrets.compare_digest(
                    token_salvo,
                    token_reserva
                )
            )

            esta_reservado = (
                cliente.get("status")
                == "reservado"
            )

            if (
                mesmo_token
                and esta_reservado
            ):

                removido = True

                continue

            clientes_atualizados.append(
                cliente
            )

        if removido:

            salvar_clientes(
                clientes_atualizados
            )

        return removido

    return executar_com_lock(
        executar
    )


# ============================================================
# CRIAÇÃO DO TESTE
# ============================================================

def criar_teste():

    token_api = obter_variavel(
        "CLUB_INFINITY_TOKEN"
    )

    server_id = obter_variavel(
        "CLUB_INFINITY_SERVER_ID"
    )

    package_id = obter_variavel(
        "CLUB_INFINITY_PACKAGE_ID"
    )

    if not token_api:

        raise RuntimeError(
            "Token da integração não configurado."
        )

    if not server_id:

        raise RuntimeError(
            "Servidor do teste não configurado."
        )

    if not package_id:

        raise RuntimeError(
            "Pacote do teste não configurado."
        )

    cabecalhos = {
        "Authorization": f"Bearer {token_api}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-App-Version": "3.96"
    }

    payload = {
        "server_id": server_id,
        "package_id": package_id,
        "trial_hours": 4,
        "connections": 1
    }

    url = (
        f"{CLUB_INFINITY_API_URL}/customers"
    )

    try:

        resposta = requests.post(
            url,
            headers=cabecalhos,
            json=payload,
            timeout=30
        )

    except requests.Timeout as erro:

        raise RuntimeError(
            "O serviço de criação do teste demorou "
            "demais para responder."
        ) from erro

    except requests.RequestException as erro:

        print(
            "ERRO DE CONEXÃO COM A API:",
            repr(erro)
        )

        raise RuntimeError(
            "Não foi possível conectar ao serviço "
            "de criação do teste."
        ) from erro

    try:

        resultado = resposta.json()

    except ValueError as erro:

        print(
            "RESPOSTA INVÁLIDA DA API:",
            resposta.status_code,
            resposta.text[:500]
        )

        raise RuntimeError(
            "O serviço de criação retornou "
            "uma resposta inválida."
        ) from erro

    print(
        "STATUS API CLUB INFINITY:",
        resposta.status_code
    )

    if resposta.status_code == 401:

        raise RuntimeError(
            "A autorização da integração expirou "
            "ou não é válida."
        )

    if resposta.status_code == 403:

        raise RuntimeError(
            "A integração não possui autorização "
            "para criar o teste."
        )

    if not resposta.ok:

        mensagem_api = resultado.get(
            "message",
            "A criação do teste foi recusada."
        )

        if isinstance(
            mensagem_api,
            list
        ):

            mensagem_api = " ".join(
                str(item)
                for item in mensagem_api
            )

        raise RuntimeError(
            str(mensagem_api)
        )

    dados_teste = resultado.get(
        "data"
    )

    if not isinstance(
        dados_teste,
        dict
    ):

        raise RuntimeError(
            "A integração não retornou os dados do teste."
        )

    usuario = texto_seguro(
        dados_teste.get("username")
    )

    senha = texto_seguro(
        dados_teste.get("password")
    )

    if not usuario or not senha:

        raise RuntimeError(
            "O serviço não retornou usuário e senha."
        )

    return {
        "id": texto_seguro(
            dados_teste.get("id")
        ),

        "username": usuario,

        "password": senha,

        "expires_at": texto_seguro(
            dados_teste.get(
                "expires_at_tz"
            )
            or dados_teste.get(
                "expires_at"
            )
        ),

        "status": texto_seguro(
            dados_teste.get("status")
        ),

        "server": texto_seguro(
            dados_teste.get("server")
        ),

        "package": texto_seguro(
            dados_teste.get("package")
        ),

        "connections": dados_teste.get(
            "connections",
            1
        ),

        "m3u_url": texto_seguro(
            dados_teste.get("m3u_url")
        ),

        "m3u_url_short": texto_seguro(
            dados_teste.get("m3u_url_short")
        ),

        "renew_url": texto_seguro(
            dados_teste.get("renew_url")
        )
    }


# ============================================================
# ENVIO DE E-MAIL
# ============================================================

def enviar_email_teste(
    nome,
    email_cliente,
    celular,
    teste
):

    email_user = obter_variavel(
        "EMAIL_USER"
    )

    email_password = obter_variavel(
        "EMAIL_PASSWORD"
    )

    email_destino = obter_variavel(
        "EMAIL_DESTINO"
    )

    smtp_host = obter_variavel(
        "SMTP_HOST",
        "smtp.office365.com"
    )

    smtp_port_texto = obter_variavel(
        "SMTP_PORT",
        "587"
    )

    try:

        smtp_port = int(
            smtp_port_texto
        )

    except ValueError:

        smtp_port = 587

    if not email_user:

        raise RuntimeError(
            "EMAIL_USER não configurado no Render."
        )

    if not email_password:

        raise RuntimeError(
            "EMAIL_PASSWORD não configurado no Render."
        )

    if not email_destino:

        raise RuntimeError(
            "EMAIL_DESTINO não configurado no Render."
        )

    mensagem = EmailMessage()

    mensagem["From"] = email_user

    mensagem["To"] = email_destino

    mensagem["Reply-To"] = email_cliente

    mensagem["Subject"] = (
        f"Novo teste MDS_TI | {nome}"
    )

    conteudo = f"""
NOVO TESTE MDS_TI GERADO

=====================================
DADOS DO SOLICITANTE
=====================================

Nome: {nome}
E-mail: {email_cliente}
WhatsApp: {celular}

=====================================
DADOS DO TESTE
=====================================

ID: {teste.get("id", "")}
Usuário: {teste.get("username", "")}
Senha: {teste.get("password", "")}
Status: {teste.get("status", "")}
Validade: {teste.get("expires_at", "")}
Conexões: {teste.get("connections", "")}

Servidor:
{teste.get("server", "")}

Pacote:
{teste.get("package", "")}

Link M3U:
{teste.get("m3u_url", "")}

Link M3U curto:
{teste.get("m3u_url_short", "")}

Link de renovação:
{teste.get("renew_url", "")}

=====================================

Os dados do teste não foram gravados no clientes.json.

O clientes.json armazena somente:
- nome;
- e-mail;
- WhatsApp;
- status da solicitação;
- datas do registro.
"""

    mensagem.set_content(
        conteudo
    )

    try:

        with smtplib.SMTP(
            smtp_host,
            smtp_port,
            timeout=30
        ) as servidor:

            servidor.ehlo()

            servidor.starttls()

            servidor.ehlo()

            servidor.login(
                email_user,
                email_password
            )

            servidor.send_message(
                mensagem
            )

    except smtplib.SMTPAuthenticationError as erro:

        print(
            "ERRO DE AUTENTICAÇÃO SMTP:",
            repr(erro)
        )

        raise RuntimeError(
            "O servidor de e-mail recusou "
            "o usuário ou a senha."
        ) from erro

    except smtplib.SMTPException as erro:

        print(
            "ERRO SMTP:",
            repr(erro)
        )

        raise RuntimeError(
            "Não foi possível enviar os dados "
            "do teste para o e-mail configurado."
        ) from erro

    except OSError as erro:

        print(
            "ERRO DE CONEXÃO SMTP:",
            repr(erro)
        )

        raise RuntimeError(
            "Não foi possível conectar ao "
            "servidor de e-mail."
        ) from erro


# ============================================================
# PÁGINA PRINCIPAL
# ============================================================

@app.route(
    "/",
    methods=["GET"]
)
def inicio():

    return render_template(
        "index.html"
    )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route(
    "/health",
    methods=["GET"]
)
def health():

    return jsonify({
        "success": True,
        "status": "online"
    }), 200


# ============================================================
# SOLICITAÇÃO DO TESTE
# ============================================================

@app.route(
    "/solicitar-teste",
    methods=["POST"]
)
def solicitar_teste():

    dados = request.get_json(
        silent=True
    ) or {}

    nome = str(
        dados.get(
            "nome",
            ""
        )
    ).strip()

    email = normalizar_email(
        dados.get("email")
    )

    celular = normalizar_celular(
        dados.get("celular")
    )

    if len(nome) < 3:

        return jsonify({
            "success": False,
            "message": "Informe seu nome completo."
        }), 400

    if not email_valido(email):

        return jsonify({
            "success": False,
            "message": "Informe um e-mail válido."
        }), 400

    if len(celular) not in (
        10,
        11
    ):

        return jsonify({
            "success": False,
            "message": (
                "Informe um WhatsApp válido com DDD."
            )
        }), 400

    token_reserva = ""

    teste_gerado = False

    try:

        resultado_reserva = reservar_cliente(
            nome,
            email,
            celular
        )

        if not resultado_reserva.get(
            "success"
        ):

            return jsonify({
                "success": False,
                "duplicate": True,
                "message": resultado_reserva.get(
                    "message",
                    "Esta solicitação já foi realizada."
                )
            }), 409

        token_reserva = resultado_reserva.get(
            "token",
            ""
        )

        teste = criar_teste()

        teste_gerado = True

        enviar_email_teste(
            nome=nome,
            email_cliente=email,
            celular=celular,
            teste=teste
        )

        confirmado = confirmar_cliente(
            token_reserva
        )

        if not confirmado:

            print(
                "AVISO: teste enviado, mas o registro "
                "do cliente não foi confirmado."
            )

        return jsonify({
            "success": True,
            "message": (
                "Solicitação realizada com sucesso."
            ),
            "template": (
                "Seu teste foi gerado com sucesso. "
                "Aguarde o atendimento para receber "
                "os dados de acesso."
            )
        }), 201

    except Exception as erro:

        print(
            "ERRO EM /solicitar-teste:",
            repr(erro)
        )

        if token_reserva:

            if teste_gerado:

                # O teste já foi criado.
                # O registro é confirmado para impedir
                # uma segunda criação do mesmo cliente.

                try:

                    confirmar_cliente(
                        token_reserva
                    )

                except Exception as erro_confirmacao:

                    print(
                        "ERRO AO CONFIRMAR APÓS FALHA:",
                        repr(erro_confirmacao)
                    )

            else:

                # Nenhum teste foi criado.
                # A reserva pode ser removida para permitir
                # uma nova tentativa.

                try:

                    cancelar_reserva(
                        token_reserva
                    )

                except Exception as erro_cancelamento:

                    print(
                        "ERRO AO CANCELAR RESERVA:",
                        repr(erro_cancelamento)
                    )

        mensagem_erro = str(
            erro
        ).strip()

        if not mensagem_erro:

            mensagem_erro = (
                "Não foi possível processar "
                "a solicitação."
            )

        return jsonify({
            "success": False,
            "message": mensagem_erro
        }), 500


# ============================================================
# ERRO 404
# ============================================================

@app.errorhandler(404)
def pagina_nao_encontrada(erro):

    return jsonify({
        "success": False,
        "message": "Rota não encontrada."
    }), 404


# ============================================================
# ERRO 405
# ============================================================

@app.errorhandler(405)
def metodo_nao_permitido(erro):

    return jsonify({
        "success": False,
        "message": "Método não permitido nesta rota."
    }), 405


# ============================================================
# EXECUÇÃO LOCAL
# ============================================================

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
