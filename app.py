import json
import os
import re
import secrets
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import fcntl
from flask import Flask, jsonify, render_template, request


app = Flask(__name__)


# ============================================================
# CONFIGURAÇÕES
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

ARQUIVO_CLIENTES = BASE_DIR / "clientes.json"

ARQUIVO_LOCK = BASE_DIR / "clientes.lock"


# ============================================================
# FUNÇÕES AUXILIARES
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


# ============================================================
# CARREGAMENTO DOS CLIENTES
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

        return []

    except (
        OSError,
        json.JSONDecodeError
    ) as erro:

        print(
            "ERRO AO LER clientes.json:",
            repr(erro)
        )

        return []


# ============================================================
# SALVAMENTO DOS CLIENTES
# ============================================================

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

            os.remove(
                arquivo_temporario
            )


# ============================================================
# LOCK DO ARQUIVO
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
# LOCALIZAR CLIENTE
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


# ============================================================
# PÁGINA INICIAL
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
# PÁGINA DE SOLICITAÇÃO DE TESTE
# ============================================================

@app.route(
    "/teste",
    methods=["GET"]
)
def teste():

    web3forms_access_key = os.environ.get(
        "WEB3FORMS_ACCESS_KEY",
        ""
    ).strip()

    return render_template(
        "teste.html",
        web3forms_access_key=web3forms_access_key
    )


# ============================================================
# PÁGINA DE SERVIÇOS
# ============================================================

@app.route(
    "/servicos",
    methods=["GET"]
)
def servicos():

    return render_template(
        "servicos.html"
    )


# ============================================================
# VERIFICAR CLIENTE
# ============================================================

@app.route(
    "/verificar-cliente",
    methods=["POST"]
)
def verificar_cliente():

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
        dados.get(
            "email"
        )
    )

    celular = normalizar_celular(
        dados.get(
            "celular"
        )
    )


    # --------------------------------------------------------
    # VALIDAÇÕES
    # --------------------------------------------------------

    if len(nome) < 3:

        return jsonify({
            "success": False,
            "message": "Informe seu nome completo."
        }), 400


    if (
        not email
        or "@" not in email
    ):

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


    # --------------------------------------------------------
    # VERIFICA E RESERVA
    # --------------------------------------------------------

    def verificar_e_reservar():

        clientes = carregar_clientes()

        cliente_existente, campo = localizar_cliente(
            clientes,
            email,
            celular
        )


        if cliente_existente:

            if campo == "email":

                mensagem = (
                    "Este e-mail já realizou "
                    "uma solicitação anteriormente."
                )

            else:

                mensagem = (
                    "Este WhatsApp já realizou "
                    "uma solicitação anteriormente."
                )

            return {
                "duplicado": True,
                "message": mensagem
            }


        token = secrets.token_urlsafe(
            32
        )


        novo_cliente = {

            "id":
                secrets.token_hex(
                    8
                ),

            "token":
                token,

            "nome":
                nome,

            "email":
                email,

            "celular":
                celular,

            "status":
                "reservado",

            "criado_em":
                agora_iso(),

            "confirmado_em":
                None
        }


        clientes.append(
            novo_cliente
        )


        salvar_clientes(
            clientes
        )


        return {
            "duplicado": False,
            "token": token
        }


    try:

        resultado = executar_com_lock(
            verificar_e_reservar
        )

    except Exception as erro:

        print(
            "ERRO AO VERIFICAR CLIENTE:",
            repr(erro)
        )

        return jsonify({
            "success": False,
            "message": (
                "Não foi possível verificar "
                "a solicitação."
            )
        }), 500


    if resultado["duplicado"]:

        return jsonify({
            "success": False,
            "duplicate": True,
            "message": resultado["message"]
        }), 409


    return jsonify({
        "success": True,
        "duplicate": False,
        "token": resultado["token"],
        "message": "Cliente liberado para envio."
    }), 200


# ============================================================
# CONFIRMAR CLIENTE
# ============================================================

@app.route(
    "/confirmar-cliente",
    methods=["POST"]
)
def confirmar_cliente():

    dados = request.get_json(
        silent=True
    ) or {}


    token = str(
        dados.get(
            "token",
            ""
        )
    ).strip()


    if not token:

        return jsonify({
            "success": False,
            "message": "Token de confirmação ausente."
        }), 400


    # --------------------------------------------------------
    # CONFIRMAR
    # --------------------------------------------------------

    def confirmar():

        clientes = carregar_clientes()


        for cliente in clientes:

            if secrets.compare_digest(
                str(
                    cliente.get(
                        "token",
                        ""
                    )
                ),
                token
            ):

                cliente["status"] = (
                    "confirmado"
                )

                cliente["confirmado_em"] = (
                    agora_iso()
                )

                salvar_clientes(
                    clientes
                )

                return True


        return False


    try:

        encontrado = executar_com_lock(
            confirmar
        )

    except Exception as erro:

        print(
            "ERRO AO CONFIRMAR CLIENTE:",
            repr(erro)
        )

        return jsonify({
            "success": False,
            "message": (
                "Não foi possível confirmar "
                "o registro."
            )
        }), 500


    if not encontrado:

        return jsonify({
            "success": False,
            "message": "Registro não encontrado."
        }), 404


    return jsonify({
        "success": True,
        "message": "Cliente confirmado."
    }), 200


# ============================================================
# CANCELAR RESERVA
# ============================================================

@app.route(
    "/cancelar-reserva",
    methods=["POST"]
)
def cancelar_reserva():

    dados = request.get_json(
        silent=True
    ) or {}


    token = str(
        dados.get(
            "token",
            ""
        )
    ).strip()


    if not token:

        return jsonify({
            "success": False,
            "message": "Token de reserva ausente."
        }), 400


    # --------------------------------------------------------
    # CANCELAMENTO
    # --------------------------------------------------------

    def cancelar():

        clientes = carregar_clientes()


        quantidade_antes = len(
            clientes
        )


        clientes_filtrados = [

            cliente

            for cliente in clientes

            if not (

                secrets.compare_digest(

                    str(
                        cliente.get(
                            "token",
                            ""
                        )
                    ),

                    token
                )

                and cliente.get(
                    "status"
                ) == "reservado"
            )
        ]


        if (
            len(
                clientes_filtrados
            )
            == quantidade_antes
        ):

            return False


        salvar_clientes(
            clientes_filtrados
        )


        return True


    try:

        removido = executar_com_lock(
            cancelar
        )

    except Exception as erro:

        print(
            "ERRO AO CANCELAR RESERVA:",
            repr(erro)
        )

        return jsonify({
            "success": False,
            "message": (
                "Não foi possível cancelar "
                "a reserva."
            )
        }), 500


    return jsonify({
        "success": True,
        "removed": removido
    }), 200


# ============================================================
# INICIALIZAÇÃO
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
