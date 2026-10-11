"""API de Insumos e Custos: descrição livre, valor e comprovante opcional."""
from datetime import date

from flask import Blueprint, jsonify, request

from autenticacao.decoradores import login_obrigatorio
from servicos.firebase_service import referencia
from servicos.pagamentos import apagar_comprovantes

bp = Blueprint("api_custos", __name__, url_prefix="/api/custos")


@bp.get("")
@login_obrigatorio
def listar():
    mes = request.args.get("mes", "")
    lista = [{"id": i, "comprovante_id": "", "comprovante_nome": "", **v}
             for i, v in (referencia("custos").get() or {}).items()]
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
    if not descricao or valor < 0:
        return jsonify({"erro": "Escreva o que foi o gasto e informe um valor válido."}), 400
    novo = {"data": data, "descricao": descricao, "valor": valor,
            "quarto_id": c.get("quarto_id") or "", "comprovante_id": "", "comprovante_nome": ""}
    if c.get("comprovante_id"):
        nome_arq = referencia(f"comprovantes/{c['comprovante_id']}/nome").get()
        if not nome_arq:
            return jsonify({"erro": "Comprovante não encontrado. Anexe o arquivo de novo."}), 400
        novo.update(comprovante_id=c["comprovante_id"], comprovante_nome=nome_arq)
    ref = referencia("custos").push(novo)
    return jsonify({"id": ref.key, **novo}), 201


@bp.delete("/<cid>")
@login_obrigatorio
def excluir(cid):
    antigo = referencia(f"custos/{cid}").get()
    if antigo and antigo.get("comprovante_id"):
        apagar_comprovantes([antigo["comprovante_id"]])
    referencia(f"custos/{cid}").delete()
    return jsonify({"ok": True})
