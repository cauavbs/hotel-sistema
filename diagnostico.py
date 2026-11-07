"""Confere a configuração e explica, em português, por que o sistema não conecta ao Firebase.

Uso (na pasta do projeto, com o ambiente virtual ativo):   python diagnostico.py
Não mostra senhas nem chaves.
"""
import json
import os
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import requests

from config import Config

OK, ALERTA, FALHA = "[ OK  ]", "[ !!  ]", "[FALHA]"
contagem = {FALHA: 0, ALERTA: 0}


def linha(estado, texto):
    contagem[estado] = contagem.get(estado, 0) + 1
    print(f"{estado} {texto}")


def explicar_erro_token(msg: str) -> str:
    m = msg.lower()
    if "short-lived" in m or "iat" in m or "reasonable timeframe" in m:
        return "O relógio do computador está fora de hora. Sincronize a data e a hora do Windows (Configurações, Hora e idioma, Sincronizar agora)."
    if "invalid_grant" in m or "invalid jwt signature" in m or "account not found" in m:
        return ("O Google recusou a chave: ela foi apagada ou revogada, ou o arquivo é de uma chave antiga. "
                "Gere uma nova (Firebase, Configurações do projeto, Contas de serviço, Gerar nova chave privada) e troque o arquivo.")
    if any(t in m for t in ("connection", "max retries", "timed out", "name resolution", "proxy")):
        return "Sem acesso ao Google. Confira a internet, o antivírus, o firewall ou o proxy."
    return "Motivo informado pelo Google: " + msg[:200]


def diferenca_relogio(data_http: str) -> float:
    """Segundos de diferença entre este computador e a hora do servidor (cabeçalho Date)."""
    return abs((parsedate_to_datetime(data_http) - datetime.now(timezone.utc)).total_seconds())


def conferir_env():
    if Config.SECRET_KEY == "troque-esta-chave-em-producao":
        linha(ALERTA, "SECRET_KEY não definida no .env (aceitável só com FLASK_DEBUG=true).")
    else:
        linha(OK, "SECRET_KEY definida.")
    k = Config.FIREBASE_API_KEY
    if not k or any(s in k.lower() for s in ("cole", "<", ">", "seu-")):
        linha(FALHA, "FIREBASE_API_KEY vazia ou ainda com o texto de exemplo (Firebase, Configurações do projeto, Geral, Chave de API da Web).")
    elif not k.startswith("AIza"):
        linha(ALERTA, "FIREBASE_API_KEY não começa com 'AIza'. Confira se copiou a Chave de API da Web.")
    else:
        linha(OK, "FIREBASE_API_KEY preenchida.")
    u = Config.FIREBASE_DATABASE_URL
    if not u.startswith("https://") or not any(d in u for d in ("firebaseio.com", "firebasedatabase.app")):
        linha(FALHA, "FIREBASE_DATABASE_URL ausente ou inválida (use o endereço mostrado no topo do Realtime Database).")
    else:
        linha(OK, "FIREBASE_DATABASE_URL com formato válido.")
    if Config.SESSION_COOKIE_SECURE:
        linha(ALERTA, "SESSION_COOKIE_SECURE está ligado: para testar em http://localhost ponha SESSION_COOKIE_SECURE=false no .env (na Vercel deixe ligado).")


def ler_credencial():
    if Config.FIREBASE_CREDENTIALS_JSON:
        return json.loads(Config.FIREBASE_CREDENTIALS_JSON), "variável FIREBASE_CREDENTIALS_JSON (tem prioridade sobre o arquivo)"
    if not os.path.exists(Config.FIREBASE_CREDENTIALS_PATH):
        raise FileNotFoundError(f"Arquivo '{Config.FIREBASE_CREDENTIALS_PATH}' não encontrado.")
    with open(Config.FIREBASE_CREDENTIALS_PATH, encoding="utf-8") as f:
        return json.load(f), f"arquivo {Config.FIREBASE_CREDENTIALS_PATH}"


def main():
    print("Diagnóstico do sistema do hotel\n")
    conferir_env()
    try:
        info, origem = ler_credencial()
    except (OSError, ValueError) as e:
        linha(FALHA, f"Chave de serviço: {e}")
        return resumo()
    faltando = [c for c in ("type", "project_id", "client_email", "private_key") if not info.get(c)]
    if faltando or info.get("type") != "service_account":
        linha(FALHA, f"A chave de serviço está incompleta ou não é do tipo service_account (faltando: {', '.join(faltando) or 'tipo'}).")
        return resumo()
    linha(OK, f"Chave de serviço lida de: {origem}. Projeto: {info['project_id']} | conta: {info['client_email']}")
    if info["project_id"] not in Config.FIREBASE_DATABASE_URL:
        linha(ALERTA, f"O endereço do banco não cita o projeto '{info['project_id']}'. Se a chave é do hotel, o banco deve ser o do hotel (confira também o .env).")

    try:
        dif = diferenca_relogio(requests.head("https://www.google.com", timeout=8).headers["Date"])
        linha(OK if dif < 120 else FALHA, "Relógio do computador em dia." if dif < 120 else f"Relógio {int(dif)} s fora de hora: o Google recusa chaves assim. Sincronize a hora.")
    except Exception:
        linha(ALERTA, "Não consegui comparar o relógio (sem acesso à internet?).")

    from firebase_admin import credentials
    try:
        credentials.Certificate(info).get_access_token()
        linha(OK, "O Google aceitou a chave de serviço.")
    except Exception as e:
        linha(FALHA, "O Google recusou a chave. " + explicar_erro_token(str(e)))
        return resumo()

    try:
        from servicos.firebase_service import referencia
        quartos = referencia("quartos").get() or {}
        linha(OK, f"Banco de dados acessível ({len(quartos)} quarto(s) cadastrado(s)).")
        admins = [u for u in (referencia("usuarios").get() or {}).values() if u.get("perfil") == "admin"]
        linha(OK if admins else FALHA, f"{len(admins)} administrador(es) com perfil no banco." if admins else "Nenhum administrador no banco: rode python criar_admin.py e-mail senha \"Nome\".")
    except Exception as e:
        linha(FALHA, "Não consegui ler o banco: " + explicar_erro_token(str(e)) + " (Se for 404: o Realtime Database não foi criado ou a URL está errada.)")
    return resumo()


def resumo():
    print()
    if contagem[FALHA]:
        print(f"{contagem[FALHA]} problema(s) a corrigir, na ordem acima.")
    else:
        print("Tudo certo." + (f" ({contagem[ALERTA]} aviso(s) para ler.)" if contagem[ALERTA] else ""))


if __name__ == "__main__":
    main()
