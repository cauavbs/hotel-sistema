"""Bloqueio de datas de um quarto (manutenção, uso próprio...). Funciona como uma reserva sem hóspede:
ocupa as noites de 'inicio' até o dia anterior a 'fim' e impede reservas nesse período."""
from datetime import date

from flask import Blueprint, jsonify, request

from autenticacao.decoradores import login_obrigatorio
from servicos.datas import br
from servicos.firebase_service import referencia
from servicos.trava import trava_quarto
from servicos.validacao import texto

bp = Blueprint("api_indisponiveis", __name__, url_prefix="/api/indisponiveis")
MOTIVOS = {"manutencao": "Manutenção", "uso_proprio": "Uso próprio", "outro": "Outro"}


@bp.get("")
@login_obrigatorio
def listar():
    ano, mes = request.args.get("ano", ""), request.args.get("mes", "")
    lista = [{"id": i, "motivo_texto": MOTIVOS.get(b.get("motivo"), ""), **b} for i, b in (referencia("indisponiveis").get() or {}).items()]
    if ano:
        lista = [b for b in lista if b["inicio"][:4] <= ano and b["fim"][:4] >= ano]
    if mes:
        lista = [b for b in lista if b["inicio"][:7] <= mes and b["fim"][:7] >= mes]
    return jsonify(sorted(lista, key=lambda b: b["inicio"]))


@bp.post("")
@login_obrigatorio
def criar():
    c = request.get_json(silent=True) or {}
    qid = c.get("quarto_id")
    try:
        ini, fim = date.fromisoformat(c.get("inicio") or ""), date.fromisoformat(c.get("fim") or "")
        obs = texto(c.get("observacao"), 200, "Observação")
    except ValueError as erro:
        return jsonify({"erro": "Confira as datas." if "Invalid" in str(erro) or "isoformat" in str(erro) else str(erro)}), 400
    if fim <= ini:
        return jsonify({"erro": "A data final deve ser depois da inicial (é o dia em que o quarto volta a ficar livre)."}), 400
    if c.get("motivo") not in MOTIVOS:
        return jsonify({"erro": "Escolha o motivo do bloqueio."}), 400
    with trava_quarto(qid):
        quarto = referencia(f"quartos/{qid}").get() if qid else None
        if not quarto:
            return jsonify({"erro": "Escolha um quarto."}), 400
        for r in (referencia("reservas").get() or {}).values():
            if (r.get("quarto_id") == qid and r.get("status") != "cancelada" and not r.get("excluida_em")
                    and ini < date.fromisoformat(r["checkout"]) and date.fromisoformat(r["checkin"]) < fim):
                return jsonify({"erro": f"Conflito: o quarto {quarto['numero']} tem reserva de {br(r['checkin'])} a {br(r['checkout'])} ({r['hospede']})."}), 409
        for b in (referencia("indisponiveis").get() or {}).values():
            if b.get("quarto_id") == qid and ini < date.fromisoformat(b["fim"]) and date.fromisoformat(b["inicio"]) < fim:
                return jsonify({"erro": f"Conflito: o quarto {quarto['numero']} já está bloqueado de {br(b['inicio'])} a {br(b['fim'])}."}), 409
        novo = {"quarto_id": qid, "inicio": ini.isoformat(), "fim": fim.isoformat(), "motivo": c["motivo"], "observacao": obs}
        ref = referencia("indisponiveis").push(novo)
    return jsonify({"id": ref.key, "motivo_texto": MOTIVOS[c["motivo"]], **novo}), 201


@bp.delete("/<bid>")
@login_obrigatorio
def excluir(bid):
    referencia(f"indisponiveis/{bid}").delete()
    return jsonify({"ok": True})
