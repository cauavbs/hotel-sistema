from datetime import timedelta

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException

from config import Config


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

    @app.errorhandler(Exception)
    def erro_inesperado(erro):
        if isinstance(erro, HTTPException):
            return erro
        app.logger.exception("Erro inesperado em %s", request.path)
        if request.path.startswith("/api/"):
            return jsonify({"erro": "Não foi possível falar com o banco de dados agora. Tente novamente."}), 503
        raise erro

    from api.custos import bp as bp_custos
    from api.quartos import bp as bp_quartos
    from api.relatorios import bp as bp_relatorios
    from api.reservas import bp as bp_reservas
    from autenticacao.rotas import bp as bp_auth
    from paginas.rotas import bp as bp_paginas

    for bp in (bp_auth, bp_paginas, bp_quartos, bp_reservas, bp_custos, bp_relatorios):
        app.register_blueprint(bp)
    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=app.config["DEBUG"], host="0.0.0.0", port=5000)
