"""API de Reservas: hóspedes, acompanhantes, pagamentos com comprovante e conflito de datas."""
from datetime import date

from flask import Blueprint, jsonify, request

from autenticacao.decoradores import login_obrigatorio
from servicos.datas import br, noites
from servicos.firebase_service import referencia
from servicos.pagamentos import (apagar_comprovantes, cpf_valido, ids_comprovantes,
                                 pagamentos_de, so_digitos)

bp = Blueprint("api_reservas", __name__, url_prefix="/api/reservas")
ORIGENS = {"airbnb", "booking", "direto"}
FORMAS = {"pix", "dinheiro", "debito", "credito", "plataforma"}


def _situacao(r):
    if r["valor_pago"] >= r["valor_total"]:
        return "pago"
    return "parcial" if r["valor_pago"] > 0 else "pendente"


def _saida(id_, r):
    return {"id": id_, **r, "acompanhantes": r.get("acompanhantes") or [], "cpf": r.get("cpf", ""),
            "pagamentos": pagamentos_de(r), "hospedes": r.get("hospedes") or 1,
            "noites": noites(r["checkin"], r["checkout"]),
            "situacao": _situacao(r), "saldo": r["valor_total"] - r["valor_pago"]}


def _validar(c, ignorar=None):
    try:
        ini = date.fromisoformat(c.get("checkin") or "")
        fim = date.fromisoformat(c.get("checkout") or "")
        total = float(c.get("valor_total"))
    except (TypeError, ValueError):
        return None, "Confira as datas e o valor total."

    qid = c.get("quarto_id")
    quarto = referencia(f"quartos/{qid}").get() if qid else None
    nome = (c.get("hospede") or "").strip()
    status = c.get("status") if c.get("status") in ("confirmada", "cancelada") else "confirmada"

    if not quarto:
        return None, "Escolha um quarto."
    if not nome:
        return None, "Informe o nome do hóspede."
    if fim <= ini:
        return None, "O check-out deve ser depois do check-in."
    if c.get("origem") not in ORIGENS:
        return None, "Escolha a origem da reserva (Airbnb, Booking ou direto)."
    if total < 0:
        return None, "O valor total não pode ser negativo."

    cpf = so_digitos(c.get("cpf"))
    if cpf and not cpf_valido(cpf):
        return None, "CPF do hóspede inválido."

    acompanhantes = []
    for a in c.get("acompanhantes") or []:
        n = (a.get("nome") or "").strip()
        if not n:
            continue
        cp = so_digitos(a.get("cpf"))
        if cp and not cpf_valido(cp):
            return None, f"CPF de {n} inválido."
        acompanhantes.append({"nome": n, "cpf": cp})
    pessoas = 1 + len(acompanhantes)
    if pessoas > quarto.get("capacidade", 99):
        return None, f"O quarto {quarto['numero']} comporta até {quarto.get('capacidade')} hóspedes (você informou {pessoas})."

    pagamentos = []
    for p in c.get("pagamentos") or []:
        try:
            valor = float(p.get("valor") or 0)
        except (TypeError, ValueError):
            return None, "Valor de pagamento inválido."
        if valor <= 0:
            continue
        if p.get("forma") not in FORMAS:
            return None, "Escolha a forma de cada pagamento."
        item = {"valor": valor, "forma": p["forma"], "comprovante_id": "", "comprovante_nome": ""}
        if p.get("comprovante_id"):
            nome_arq = referencia(f"comprovantes/{p['comprovante_id']}/nome").get()
            if not nome_arq:
                return None, "Um comprovante não foi encontrado. Anexe o arquivo de novo."
            item.update(comprovante_id=p["comprovante_id"], comprovante_nome=nome_arq)
        pagamentos.append(item)
    pago = round(sum(p["valor"] for p in pagamentos), 2)
    if pago > round(total, 2):
        return None, "A soma dos pagamentos não pode passar do valor total."

    if status == "confirmada":
        for id_, r in (referencia("reservas").get() or {}).items():
            if id_ == ignorar or r.get("quarto_id") != qid or r.get("status") == "cancelada":
                continue
            if ini < date.fromisoformat(r["checkout"]) and date.fromisoformat(r["checkin"]) < fim:
                return None, (f"Conflito: o quarto {quarto['numero']} já está reservado de "
                              f"{br(r['checkin'])} a {br(r['checkout'])} ({r['hospede']}).")

    return {"quarto_id": qid, "checkin": ini.isoformat(), "checkout": fim.isoformat(),
            "origem": c["origem"], "hospede": nome, "cpf": cpf,
            "telefone": (c.get("telefone") or "").strip(), "acompanhantes": acompanhantes,
            "hospedes": pessoas, "valor_total": total, "valor_pago": pago,
            "pagamentos": pagamentos, "status": status,
            "observacao": (c.get("observacao") or "").strip()}, None


def _codigo(erro):
    return 409 if erro.startswith("Conflito") else 400


@bp.get("")
@login_obrigatorio
def listar():
    mes, ano = request.args.get("mes", ""), request.args.get("ano", "")  # AAAA-MM ou AAAA
    lista = [_saida(i, r) for i, r in (referencia("reservas").get() or {}).items()]
    if mes:
        lista = [r for r in lista if r["checkin"][:7] <= mes and r["checkout"][:7] >= mes]
    if ano:
        lista = [r for r in lista if r["checkin"][:4] <= ano and r["checkout"][:4] >= ano]
    lista.sort(key=lambda r: r["checkin"])
    return jsonify(lista)


@bp.post("")
@login_obrigatorio
def criar():
    dados, erro = _validar(request.get_json(silent=True) or {})
    if erro:
        return jsonify({"erro": erro}), _codigo(erro)
    ref = referencia("reservas").push(dados)
    return jsonify(_saida(ref.key, dados)), 201


@bp.put("/<rid>")
@login_obrigatorio
def atualizar(rid):
    antiga = referencia(f"reservas/{rid}").get()
    if not antiga:
        return jsonify({"erro": "Reserva não encontrada."}), 404
    dados, erro = _validar(request.get_json(silent=True) or {}, ignorar=rid)
    if erro:
        return jsonify({"erro": erro}), _codigo(erro)
    referencia(f"reservas/{rid}").set(dados)
    apagar_comprovantes(ids_comprovantes(antiga) - ids_comprovantes(dados))  # removidos da reserva
    return jsonify(_saida(rid, dados))


@bp.delete("/<rid>")
@login_obrigatorio
def excluir(rid):
    antiga = referencia(f"reservas/{rid}").get()
    if antiga:
        apagar_comprovantes(ids_comprovantes(antiga))
    referencia(f"reservas/{rid}").delete()
    return jsonify({"ok": True})
