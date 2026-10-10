"""Login por e-mail/senha via API REST do Firebase + sessão por cookie assinado."""
import time
from collections import defaultdict

import requests
from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

from autenticacao.decoradores import login_obrigatorio
from config import Config
from servicos.firebase_service import inicializar_firebase, referencia

bp = Blueprint("autenticacao", __name__)
URL_LOGIN = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
MAX_TENTATIVAS, JANELA = 5, 300
_tentativas = defaultdict(list)


def _bloqueado(ip):
    agora = time.time()
    _tentativas[ip][:] = [t for t in _tentativas[ip] if agora - t < JANELA]
    return len(_tentativas[ip]) >= MAX_TENTATIVAS


@bp.get("/login")
def pagina_login():
    if session.get("uid"):
        return redirect(url_for("paginas.calendario"))
    return render_template("login.html")


@bp.post("/login")
def fazer_login():
    ip = request.remote_addr or "?"
    if _bloqueado(ip):
        return jsonify({"erro": "Muitas tentativas. Aguarde alguns minutos."}), 429
    try:
        inicializar_firebase()
    except RuntimeError as erro:
        return jsonify({"erro": f"Erro de configuração no servidor: {erro}"}), 500

    corpo = request.get_json(silent=True) or {}
    email, senha = (corpo.get("email") or "").strip(), corpo.get("senha") or ""
    if not email or not senha:
        return jsonify({"erro": "Informe e-mail e senha."}), 400
    try:
        r = requests.post(URL_LOGIN, params={"key": Config.FIREBASE_API_KEY},
                          json={"email": email, "password": senha, "returnSecureToken": True}, timeout=10)
    except requests.exceptions.RequestException as erro:
        return jsonify({"erro": f"Não foi possível conectar ao Firebase: {erro}"}), 502

    if r.status_code != 200:
        _tentativas[ip].append(time.time())
        return jsonify({"erro": "E-mail ou senha incorretos."}), 401

    uid = r.json()["localId"]
    perfil = referencia(f"usuarios/{uid}").get() or {}
    session.clear()
    session.update(uid=uid, email=email, nome=perfil.get("nome", email))
    session.permanent = True
    _tentativas.pop(ip, None)
    return jsonify({"ok": True})


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("autenticacao.pagina_login"))


@bp.route("/api/me")
@login_obrigatorio
def eu():
    return jsonify({"uid": session["uid"], "email": session["email"], "nome": session["nome"]})
