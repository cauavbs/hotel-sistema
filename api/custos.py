"""API de Insumos e Custos (limpeza, produtos, contas, manutenção...)."""
from datetime import date

from flask import Blueprint, jsonify, request

from autenticacao.decoradores import login_obrigatorio
from servicos.firebase_service import referencia

bp = Blueprint("api_custos", __name__, url_prefix="/api/custos")
CATEGORIAS = {"limpeza", "produtos", "contas", "manutencao", "lavanderia", "outros"}


@bp.get("")
@login_obrigatorio
def listar():
    mes = request.args.get("mes", "")
    lista = [{"id": i, **v} for i, v in (referencia("custos").get() or {}).items()]
    if mes:
        lista = [c for c in lista if c["data"][:7] == mes]
    lista.sort(key=lambda c: c["data"], reverse=True)
    return jsonify(lista)


@bp.post("")
@login_obrigatorio
def criar():
    c = request.get_json(silent=True) or {}
    try:
        data = date.fromisoformat(c.get("data") or "").isoformat()
        valor = float(c.get("valor"))
    except (TypeError, ValueError):
        return jsonify({"erro": "Confira a data e o valor."}), 400
    descricao = (c.get("descricao") or "").strip()
    if not descricao or valor < 0 or c.get("categoria") not in CATEGORIAS:
        return jsonify({"erro": "Informe categoria, descrição e um valor válido."}), 400
    novo = {"data": data, "categoria": c["categoria"], "descricao": descricao,
            "valor": valor, "quarto_id": c.get("quarto_id") or ""}
    ref = referencia("custos").push(novo)
    return jsonify({"id": ref.key, **novo}), 201


@bp.delete("/<cid>")
@login_obrigatorio
def excluir(cid):
    referencia(f"custos/{cid}").delete()
    return jsonify({"ok": True})
