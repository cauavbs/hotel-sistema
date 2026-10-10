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
    lista = [{"id": i, **v} for i, v in (referencia("quartos").get() or {}).items()]
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
    ref = referencia("quartos").push(dados)
    return jsonify({"id": ref.key, **dados}), 201


@bp.put("/<qid>")
@login_obrigatorio
def atualizar(qid):
    dados = _ler(request.get_json(silent=True) or {})
    if not dados:
        return jsonify({"erro": "Informe o número e a capacidade do quarto."}), 400
    referencia(f"quartos/{qid}").set(dados)
    return jsonify({"id": qid, **dados})


@bp.delete("/<qid>")
@login_obrigatorio
def excluir(qid):
    if any(r.get("quarto_id") == qid for r in (referencia("reservas").get() or {}).values()):
        return jsonify({"erro": "Este quarto tem reservas. Remova ou mova as reservas antes."}), 409
    referencia(f"quartos/{qid}").delete()
    return jsonify({"ok": True})
