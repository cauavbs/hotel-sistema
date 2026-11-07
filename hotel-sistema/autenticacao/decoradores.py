"""Todos os usuários do sistema são administradores: basta estar logado."""
from functools import wraps

from flask import jsonify, redirect, request, session, url_for


def login_obrigatorio(view):
    @wraps(view)
    def protegida(*args, **kwargs):
        if not session.get("uid"):
            if request.path.startswith("/api/"):
                return jsonify({"erro": "Não autenticado."}), 401
            return redirect(url_for("autenticacao.pagina_login"))
        return view(*args, **kwargs)

    return protegida
