"""API de Quartos."""
from flask import Blueprint, jsonify, request

from autenticacao.decoradores import login_obrigatorio
from servicos.firebase_service import referencia

bp = Blueprint("api_quartos", __name__, url_prefix="/api/quartos")


def _ler(corpo):
    numero = str(corpo.get("numero") or "").strip()
    try:
        capacidade = int(corpo.get("capacidade"))
    except (TypeError, ValueError):
        capacidade = 0
    if not numero or capacidade < 1:
        return None
    return {"numero": numero, "nome": (corpo.get("nome") or "").strip(), "capacidade": capacidade}


@bp.get("")
@login_obrigatorio
def listar():
    lista = [{"id": i, "limpeza": "limpo", **v} for i, v in (referencia("quartos").get() or {}).items()]
    lista.sort(key=lambda q: (len(q["numero"]), q["numero"]))
    return jsonify(lista)


@bp.post("")
@login_obrigatorio
def criar():
    dados = _ler(request.get_json(silent=True) or {})
    if not dados:
        return jsonify({"erro": "Informe o número e a capacidade do quarto."}), 400
    if any(q.get("numero") == dados["numero"] for q in (referencia("quartos").get() or {}).values()):
        return jsonify({"erro": f"O quarto {dados['numero']} já existe."}), 409
    ref = referencia("quartos").push({**dados, "limpeza": "limpo"})
    return jsonify({"id": ref.key, **dados, "limpeza": "limpo"}), 201


@bp.put("/<qid>")
@login_obrigatorio
def atualizar(qid):
    dados = _ler(request.get_json(silent=True) or {})
    if not dados:
        return jsonify({"erro": "Informe o número e a capacidade do quarto."}), 400
    anterior = referencia(f"quartos/{qid}").get()
    if not anterior:
        return jsonify({"erro": "Quarto não encontrado."}), 404
    dados["limpeza"] = anterior.get("limpeza", "limpo")
    for campo in ("ical_airbnb", "ical_booking"):
        if anterior.get(campo):
            dados[campo] = anterior[campo]
    referencia(f"quartos/{qid}").set(dados)
    return jsonify({"id": qid, **dados})


@bp.patch("/<qid>/limpeza")
@login_obrigatorio
def limpeza(qid):
    status = (request.get_json(silent=True) or {}).get("status")
    if status not in ("limpo", "a_limpar"):
        return jsonify({"erro": "Status de limpeza inválido."}), 400
    if not referencia(f"quartos/{qid}").get():
        return jsonify({"erro": "Quarto não encontrado."}), 404
    referencia(f"quartos/{qid}").update({"limpeza": status})
    return jsonify({"id": qid, "limpeza": status})


@bp.delete("/<qid>")
@login_obrigatorio
def excluir(qid):
    if any(r.get("quarto_id") == qid for r in (referencia("reservas").get() or {}).values()):
        return jsonify({"erro": "Este quarto tem reservas (inclusive na lixeira). Exclua-as de vez ou mova-as antes."}), 409
    referencia(f"quartos/{qid}").delete()
    return jsonify({"ok": True})
