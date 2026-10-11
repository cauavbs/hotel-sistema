"""Comprovantes (imagem ou PDF) guardados no Realtime Database.

O navegador reduz as imagens antes de enviar; PDFs devem ter até ~1 MB.
Os arquivos ficam em um nó separado para não pesar as listagens.
"""
import base64
from datetime import datetime, timezone
from urllib.parse import quote

from flask import Blueprint, Response, jsonify, request

from autenticacao.decoradores import login_obrigatorio
from servicos.firebase_service import referencia

bp = Blueprint("api_comprovantes", __name__, url_prefix="/api/comprovantes")
TIPOS = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
MAX_BASE64 = 1_400_000  # ~1 MB de arquivo


@bp.post("")
@login_obrigatorio
def enviar():
    c = request.get_json(silent=True) or {}
    tipo, dados = c.get("tipo"), c.get("dados") or ""
    nome = (c.get("nome") or "comprovante").strip()[:80]
    if tipo not in TIPOS:
        return jsonify({"erro": "Envie uma imagem (JPG, PNG) ou um PDF."}), 400
    if not dados or len(dados) > MAX_BASE64:
        return jsonify({"erro": "Arquivo grande demais (máximo de cerca de 1 MB)."}), 400
    try:
        base64.b64decode(dados, validate=True)
    except ValueError:
        return jsonify({"erro": "Arquivo inválido."}), 400
    ref = referencia("comprovantes").push({
        "nome": nome, "tipo": tipo, "dados": dados,
        "enviado_em": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    return jsonify({"id": ref.key, "nome": nome}), 201


@bp.get("/<cid>")
@login_obrigatorio
def baixar(cid):
    c = referencia(f"comprovantes/{cid}").get()
    if not c:
        return jsonify({"erro": "Comprovante não encontrado."}), 404
    resp = Response(base64.b64decode(c["dados"]), mimetype=c["tipo"])
    resp.headers["Content-Disposition"] = f"inline; filename*=UTF-8''{quote(c['nome'])}"
    resp.headers["Cache-Control"] = "private, max-age=3600"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    return resp
