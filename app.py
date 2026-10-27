import json
import os
import re
import secrets
import smtplib
import tempfile
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

import fcntl
import requests
from flask import Flask, jsonify, render_template, request


app = Flask(__name__)


# ============================================================
# CAMINHOS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

ARQUIVO_CLIENTES = BASE_DIR / "clientes.json"

ARQUIVO_LOCK = BASE_DIR / "clientes.lock"


# ============================================================
# CONFIGURAÇÕES DA API
# ============================================================

CLUB_INFINITY_API_URL = os.environ.get(
    "CLUB_INFINITY_API_URL",
    "https://clubinfinity.info/api"
).strip().rstrip("/")


# ============================================================
# FUNÇÕES BÁSICAS
# ============================================================

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


def obter_variavel(nome):
    return os.environ.get(
        nome,
        ""
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
            "AVISO: formato inválido em clientes.json."
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
# BLOQUEIO DO ARQUIVO
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
# VERIFICAÇÃO DE DUPLICIDADE
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

        clientes.append({
            "id": secrets.token_hex(8),
            "token_reserva": token_reserva,
            "nome": nome,
            "email": email,
            "celular": celular,
            "status": "reservado",
            "criado_em": agora_iso(),
            "confirmado_em": None
        })

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

        novos_clientes = []

        removido = False

        for cliente in clientes:

            token_salvo = str(
                cliente.get(
                    "token_reserva",
                    ""
                )
            )

            corresponde = (
                token_salvo
                and secrets.compare_digest(
                    token_salvo,
                    token_reserva
                )
            )

            reservado = (
                cliente.get("status")
                == "reservado"
            )

            if corresponde and reservado:

                removido = True

                continue

            novos_clientes.append(
                cliente
            )

        if removido:

            salvar_clientes(
                novos_clientes
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
            "CLUB_INFINITY_TOKEN não configurado."
        )

    if not server_id:

        raise RuntimeError(
            "CLUB_INFINITY_SERVER_ID não configurado."
        )

    if not package_id:

        raise RuntimeError(
            "CLUB_INFINITY_PACKAGE_ID não configurado."
        )

    headers = {
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
            headers=headers,
            json=payload,
            timeout=30
        )

    except requests.Timeout as erro:

        raise RuntimeError(
            "A criação do teste demorou para responder."
        ) from erro

    except requests.RequestException as erro:

        raise RuntimeError(
            "Não foi possível conectar ao serviço do teste."
        ) from erro

    try:

        resultado = resposta.json()

    except ValueError as erro:

        print(
            "RESPOSTA NÃO JSON DA API:",
            resposta.status_code,
            resposta.text[:500]
        )

        raise RuntimeError(
            "O serviço do teste retornou uma resposta inválida."
        ) from erro

    print(
        "STATUS DA CRIAÇÃO DO TESTE:",
        resposta.status_code
    )

    if resposta.status_code in (
        401,
        403
    ):

        raise RuntimeError(
            "A autorização da API expirou ou foi recusada."
        )

    if not resposta.ok:

        mensagem_api = str(
            resultado.get(
                "message",
                "A API recusou a criação do teste."
            )
        )

        raise RuntimeError(
            mensagem_api
        )

    dados_teste = resultado.get(
        "data"
    )

    if not isinstance(
        dados_teste,
        dict
    ):

        raise RuntimeError(
            "A API não retornou os dados do teste."
        )

    username = str(
        dados_teste.get(
            "username",
            ""
        )
    ).strip()

    password = str(
        dados_teste.get(
            "password",
            ""
        )
    ).strip()

    if not username or not password:

        raise RuntimeError(
            "A API não retornou usuário e senha."
        )

    return {
        "id": str(
            dados_teste.get(
                "id",
                ""
            )
        ).strip(),

        "username": username,

        "password": password,

        "expires_at": str(
            dados_teste.get(
                "expires_at_tz",
                dados_teste.get(
                    "expires_at",
                    ""
                )
            )
        ).strip(),

        "status": str(
            dados_teste.get(
                "status",
                ""
            )
        ).strip(),

        "server": str(
            dados_teste.get(
                "server",
                ""
            )
        ).strip(),

        "package": str(
            dados_teste.get(
                "package",
                ""
            )
        ).strip(),

        "connections": dados_teste.get(
            "connections",
            1
        ),

        "m3u_url": str(
            dados_teste.get(
                "m3u_url",
                ""
            )
        ).replace(
            "&amp;",
            "&"
        ).strip(),

        "m3u_url_short": str(
            dados_teste.get(
                "m3u_url_short",
                ""
            )
        ).replace(
            "&amp;",
            "&"
        ).strip()
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
        "SMTP_HOST"
    ) or "smtp.office365.com"

    smtp_port_texto = obter_variavel(
        "SMTP_PORT"
    ) or "587"

    try:

        smtp_port = int(
            smtp_port_texto
        )

    except ValueError:

        smtp_port = 587

    if not email_user:

        raise RuntimeError(
            "EMAIL_USER não configurado."
        )

    if not email_password:

        raise RuntimeError(
            "EMAIL_PASSWORD não configurado."
        )

    if not email_destino:

        raise RuntimeError(
            "EMAIL_DESTINO não configurado."
        )

    mensagem = EmailMessage()

    mensagem["From"] = email_user

    mensagem["To"] = email_destino

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

=====================================

Os dados acima não foram gravados no clientes.json.
O clientes.json contém somente os dados necessários
para impedir solicitações repetidas.
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

        raise RuntimeError(
            "O servidor de e-mail recusou "
            "o usuário ou a senha."
        ) from erro

    except (
        smtplib.SMTPException,
        OSError
    ) as erro:

        raise RuntimeError(
            "Não foi possível enviar os dados "
            "do teste por e-mail."
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
# SOLICITAR TESTE
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
                    "Solicitação já realizada."
                )
            }), 409

        token_reserva = resultado_reserva[
            "token"
        ]

        teste = criar_teste()

        teste_gerado = True

        enviar_email_teste(
            nome=nome,
            email_cliente=email,
            celular=celular,
            teste=teste
        )

        confirmar_cliente(
            token_reserva
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

        /*
        Este comentário não deve existir em Python.
        */

        if token_reserva:

            if teste_gerado:

                /*
                Se o teste já foi criado, não removemos
                a reserva. Isso evita gerar outro teste
                repetido caso somente o e-mail tenha falhado.
                */

                confirmar_cliente(
                    token_reserva
                )

            else:

                cancelar_reserva(
                    token_reserva
                )

        return jsonify({
            "success": False,
            "message": str(
                erro
            ) or (
                "Não foi possível processar "
                "a solicitação."
            )
        }), 500


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
