"""Rotas da integração com Airbnb e Booking (iCal)."""
import hmac
import os

from flask import Blueprint, Response, abort, jsonify, request

from autenticacao.decoradores import login_obrigatorio
from servicos import ical, sincronia
from servicos.firebase_service import referencia

bp = Blueprint("api_ical", __name__)
CANAIS = sincronia.CANAIS


def _base():
    return f"{request.headers.get('X-Forwarded-Proto', request.scheme)}://{request.host}"


@bp.get("/ical/<canal>/<qid>.ics")
def calendario(canal, qid):
    """Calendário público (sem login: Airbnb e Booking precisam baixá-lo), protegido por um token secreto."""
    quarto = referencia(f"quartos/{qid}").get() if canal in CANAIS else None
    if not quarto or not hmac.compare_digest(request.args.get("t", "").encode(), sincronia.obter_token().encode()):
        abort(404)
    resp = Response(ical.gerar(f"Quarto {quarto['numero']}", sincronia.eventos_do_calendario(qid, canal)))
    resp.headers["Content-Type"] = "text/calendar; charset=utf-8"
    resp.headers["Cache-Control"] = "no-cache"
    return resp


@bp.get("/api/ical/config")
@login_obrigatorio
def config():
    token, estados = sincronia.obter_token(), referencia("ical_estado").get() or {}
    quartos = [{"id": i, "numero": q["numero"], "ical_airbnb": q.get("ical_airbnb", ""), "ical_booking": q.get("ical_booking", ""),
                "links": {c: f"{_base()}/ical/{c}/{i}.ics?t={token}" for c in CANAIS},
                "estado": {c: estados.get(f"{i}_{c}") for c in CANAIS}} for i, q in (referencia("quartos").get() or {}).items()]
    return jsonify(sorted(quartos, key=lambda q: (len(q["numero"]), q["numero"])))


@bp.put("/api/ical/quartos/<qid>")
@login_obrigatorio
def salvar_links(qid):
    if not referencia(f"quartos/{qid}").get():
        return jsonify({"erro": "Quarto não encontrado."}), 404
    corpo, campos = request.get_json(silent=True) or {}, {}
    for canal in CANAIS:
        url = str(corpo.get(f"ical_{canal}") or "").strip()
        if url:
            try:
                ical.validar_url_basica(url)
            except ValueError as e:
                return jsonify({"erro": f"{CANAIS[canal]}: {e}"}), 400
        campos[f"ical_{canal}"] = url or None           # vazio apaga o link
    referencia(f"quartos/{qid}").update(campos)
    return jsonify({"ok": True})


@bp.post("/api/ical/token/regenerar")
@login_obrigatorio
def regenerar():
    sincronia.regenerar_token()
    return jsonify({"ok": True})


@bp.post("/api/ical/sincronizar")
@login_obrigatorio
def sincronizar():
    c = request.get_json(silent=True) or {}
    return jsonify(sincronia.sincronizar(c.get("quarto_id", ""), c.get("canal", "")))


@bp.post("/api/ical/sincronizar-vencidos")
@login_obrigatorio
def sincronizar_vencidos():
    return jsonify(sincronia.sincronizar_vencidos())


@bp.get("/api/cron/ical")
def cron():
    """Chamada diária da Vercel (precisa da variável CRON_SECRET; sem ela, a rota não existe)."""
    segredo = os.environ.get("CRON_SECRET", "")
    if not segredo or not hmac.compare_digest(request.headers.get("Authorization", "").encode(), f"Bearer {segredo}".encode()):
        abort(404)
    return jsonify(sincronia.sincronizar_vencidos(minutos=0))
