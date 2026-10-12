import os
from datetime import timedelta

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException

from config import Config
from servicos.trava import TravaOcupada

CSP = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
       "connect-src 'self'; worker-src 'self'; manifest-src 'self'; object-src 'none'; "
       "base-uri 'self'; form-action 'self'; frame-ancestors 'none'")


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    app.permanent_session_lifetime = timedelta(days=7)

    if not app.config["DEBUG"] and app.config["SECRET_KEY"] == "troque-esta-chave-em-producao":
        raise RuntimeError("SECRET_KEY não configurada. Defina uma chave aleatória no .env.")

    @app.route("/sw.js")
    def service_worker():
        resposta = send_from_directory(app.static_folder, "sw.js")
        resposta.headers["Content-Type"] = "application/javascript"
        resposta.headers["Cache-Control"] = "no-cache"
        return resposta

    @app.after_request
    def cabecalhos_de_seguranca(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "same-origin")
        resp.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), payment=()")
        if request.is_secure or request.headers.get("X-Forwarded-Proto") == "https":
            resp.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
        if resp.mimetype == "text/html":
            resp.headers.setdefault("Content-Security-Policy", CSP)
        if request.path.startswith("/api/") and not request.path.startswith("/api/comprovantes/"):
            resp.headers["Cache-Control"] = "no-store"   # dados de hóspedes não ficam em cache
        return resp

    @app.errorhandler(TravaOcupada)
    def trava_ocupada(erro):
        return jsonify({"erro": str(erro)}), 409

    @app.errorhandler(Exception)
    def erro_inesperado(erro):
        if isinstance(erro, HTTPException):
            return erro
        app.logger.exception("Erro inesperado em %s", request.path)
        if request.path.startswith("/api/"):
            return jsonify({"erro": "Não foi possível falar com o banco de dados agora. Tente novamente."}), 503
        raise erro

    from api.comprovantes import bp as bp_comprovantes
    from api.custos import bp as bp_custos
    from api.quartos import bp as bp_quartos
    from api.relatorios import bp as bp_relatorios
    from api.reservas import bp as bp_reservas
    from autenticacao.rotas import bp as bp_auth
    from paginas.rotas import bp as bp_paginas

    for bp in (bp_auth, bp_paginas, bp_quartos, bp_reservas, bp_custos, bp_relatorios, bp_comprovantes):
        app.register_blueprint(bp)
    return app


app = create_app()

if __name__ == "__main__":
    # Por padrão só este computador acessa. Para testar no celular, use FLASK_HOST=0.0.0.0 no .env
    # (nesse caso o debug é desligado: o depurador do Flask não deve ficar exposto na rede).
    host, debug = os.environ.get("FLASK_HOST", "127.0.0.1"), app.config["DEBUG"]
    if debug and host not in ("127.0.0.1", "localhost"):
        print("Aviso: debug desligado, porque FLASK_HOST expõe o servidor na rede.")
        debug = False
    app.run(debug=debug, host=host, port=5000)
