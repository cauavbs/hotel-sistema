"""API de Reservas: valida datas, conflito de quarto e pagamento."""
from datetime import date

from flask import Blueprint, jsonify, request

from autenticacao.decoradores import login_obrigatorio
from servicos.datas import br, noites
from servicos.firebase_service import referencia

bp = Blueprint("api_reservas", __name__, url_prefix="/api/reservas")
ORIGENS = {"airbnb", "booking", "direto"}
FORMAS = {"pix", "dinheiro", "debito", "credito", "plataforma"}


def _situacao(r):
    if r["valor_pago"] >= r["valor_total"]:
        return "pago"
    return "parcial" if r["valor_pago"] > 0 else "pendente"


def _saida(id_, r):
    return {"id": id_, **r, "noites": noites(r["checkin"], r["checkout"]),
            "situacao": _situacao(r), "saldo": r["valor_total"] - r["valor_pago"]}


def _validar(c, ignorar=None):
    try:
        ini = date.fromisoformat(c.get("checkin") or "")
        fim = date.fromisoformat(c.get("checkout") or "")
        total = float(c.get("valor_total"))
        pago = float(c.get("valor_pago") or 0)
        pessoas = int(c.get("hospedes") or 1)
    except (TypeError, ValueError):
        return None, "Confira as datas, o valor total e o número de hóspedes."

    qid = c.get("quarto_id")
    quarto = referencia(f"quartos/{qid}").get() if qid else None
    nome = (c.get("hospede") or "").strip()
    forma = (c.get("forma_pagamento") or "").strip()
    status = c.get("status") if c.get("status") in ("confirmada", "cancelada") else "confirmada"

    if not quarto:
        return None, "Escolha um quarto."
    if not nome:
        return None, "Informe o nome do hóspede."
    if fim <= ini:
        return None, "O check-out deve ser depois do check-in."
    if c.get("origem") not in ORIGENS:
        return None, "Escolha a origem da reserva (Airbnb, Booking ou direto)."
    if total < 0 or pago < 0 or pago > total:
        return None, "Valores inválidos: o valor pago não pode passar do total."
    if pago > 0 and forma not in FORMAS:
        return None, "Informe a forma de pagamento."
    if not 1 <= pessoas <= quarto.get("capacidade", 99):
        return None, f"O quarto {quarto['numero']} comporta até {quarto.get('capacidade')} hóspedes."

    if status == "confirmada":
        for id_, r in (referencia("reservas").get() or {}).items():
            if id_ == ignorar or r.get("quarto_id") != qid or r.get("status") == "cancelada":
                continue
            if ini < date.fromisoformat(r["checkout"]) and date.fromisoformat(r["checkin"]) < fim:
                return None, (f"Conflito: o quarto {quarto['numero']} já está reservado de "
                              f"{br(r['checkin'])} a {br(r['checkout'])} ({r['hospede']}).")

    return {"quarto_id": qid, "checkin": ini.isoformat(), "checkout": fim.isoformat(),
            "origem": c["origem"], "hospede": nome, "telefone": (c.get("telefone") or "").strip(),
            "hospedes": pessoas, "valor_total": total, "valor_pago": pago,
            "forma_pagamento": forma, "status": status,
            "observacao": (c.get("observacao") or "").strip()}, None


@bp.get("")
@login_obrigatorio
def listar():
    mes = request.args.get("mes", "")  # YYYY-MM: reservas que tocam o mês
    lista = [_saida(i, r) for i, r in (referencia("reservas").get() or {}).items()]
    if mes:
        lista = [r for r in lista if r["checkin"][:7] <= mes and r["checkout"][:7] >= mes]
    lista.sort(key=lambda r: r["checkin"])
    return jsonify(lista)


@bp.post("")
@login_obrigatorio
def criar():
    dados, erro = _validar(request.get_json(silent=True) or {})
    if erro:
        return jsonify({"erro": erro}), 409 if erro.startswith("Conflito") else 400
    ref = referencia("reservas").push(dados)
    return jsonify(_saida(ref.key, dados)), 201


@bp.put("/<rid>")
@login_obrigatorio
def atualizar(rid):
    dados, erro = _validar(request.get_json(silent=True) or {}, ignorar=rid)
    if erro:
        return jsonify({"erro": erro}), 409 if erro.startswith("Conflito") else 400
    referencia(f"reservas/{rid}").set(dados)
    return jsonify(_saida(rid, dados))


@bp.delete("/<rid>")
@login_obrigatorio
def excluir(rid):
    referencia(f"reservas/{rid}").delete()
    return jsonify({"ok": True})
