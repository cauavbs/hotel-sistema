"""Exportação para Excel (CSV) e backup em JSON, além da limpeza de comprovantes sem uso."""
import csv
import io
import json
from datetime import datetime, timedelta, timezone

from flask import Blueprint, Response, jsonify, request

from autenticacao.decoradores import login_obrigatorio
from servicos.datas import FUSO, br, hoje_local
from servicos.firebase_service import referencia
from servicos.pagamentos import apagar_comprovantes, ids_comprovantes, pagamentos_de

bp = Blueprint("api_exportar", __name__)
FORMAS = {"pix": "Pix", "dinheiro": "Dinheiro", "debito": "Débito", "credito": "Crédito", "plataforma": "Repasse da plataforma"}
ORIGENS = {"airbnb": "Airbnb", "booking": "Booking", "direto": "Direto"}


def _t(valor):
    """Texto seguro para planilha: evita que '=...' ou '+...' seja executado como fórmula."""
    s = str(valor or "")
    return "'" + s if s[:1] in ("=", "+", "-", "@", "\t", "\r") else s


def _n(valor):
    return f"{float(valor or 0):.2f}".replace(".", ",")      # Excel em português lê vírgula decimal


def _csv(cabecalho, linhas, nome):
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(cabecalho)
    w.writerows(linhas)
    resp = Response("\ufeff" + buf.getvalue())                # BOM: o Excel reconhece os acentos
    resp.headers["Content-Type"] = "text/csv; charset=utf-8"
    resp.headers["Content-Disposition"] = f'attachment; filename="{nome}-{hoje_local().isoformat()}.csv"'
    return resp


@bp.get("/api/exportar/reservas.csv")
@login_obrigatorio
def reservas_csv():
    pessoais = request.args.get("pessoais") == "1"
    quartos = {i: q["numero"] for i, q in (referencia("quartos").get() or {}).items()}
    cab = ["Quarto", "Hóspede"] + (["CPF", "Telefone", "Acompanhantes"] if pessoais else []) + [
        "Check-in", "Check-out", "Noites", "Hóspedes", "Origem", "Situação", "Valor total", "Pago", "Saldo", "Formas de pagamento", "Observações"]
    linhas = []
    for r in sorted((r for r in (referencia("reservas").get() or {}).values() if not r.get("excluida_em")), key=lambda r: r["checkin"]):
        noites = (datetime.fromisoformat(r["checkout"]) - datetime.fromisoformat(r["checkin"])).days
        linhas.append([_t(quartos.get(r["quarto_id"], "?")), _t(r["hospede"])]
                      + ([_t(r.get("cpf")), _t(r.get("telefone")), _t("; ".join(a["nome"] for a in r.get("acompanhantes") or []))] if pessoais else [])
                      + [br(r["checkin"]), br(r["checkout"]), noites, r.get("hospedes") or 1, ORIGENS.get(r["origem"], r["origem"]),
                         "Cancelada" if r.get("status") == "cancelada" else "Confirmada", _n(r["valor_total"]), _n(r["valor_pago"]),
                         _n(r["valor_total"] - r["valor_pago"]), "; ".join(sorted({FORMAS.get(p["forma"], p["forma"]) for p in pagamentos_de(r)})),
                         _t(r.get("observacao"))])
    return _csv(cab, linhas, "reservas")


@bp.get("/api/exportar/custos.csv")
@login_obrigatorio
def custos_csv():
    quartos = {i: q["numero"] for i, q in (referencia("quartos").get() or {}).items()}
    linhas = [[br(c["data"]), _t(c["descricao"]), _t(quartos.get(c.get("quarto_id"), "Geral")), _n(c["valor"]), "Sim" if c.get("comprovante_id") else "Não"]
              for c in sorted((referencia("custos").get() or {}).values(), key=lambda c: c["data"])]
    return _csv(["Data", "Descrição", "Quarto", "Valor", "Comprovante"], linhas, "custos")


@bp.get("/api/exportar/backup.json")
@login_obrigatorio
def backup_json():
    """Dados do sistema, sem os arquivos de comprovante (limite de resposta da Vercel). Para tudo, use backup.py."""
    dados = {"gerado_em": datetime.now(FUSO).isoformat(timespec="seconds")}
    for nome in ("quartos", "reservas", "custos", "indisponiveis"):
        dados[nome] = referencia(nome).get() or {}
    resp = Response(json.dumps(dados, ensure_ascii=False, indent=1))
    resp.headers["Content-Type"] = "application/json; charset=utf-8"
    resp.headers["Content-Disposition"] = f'attachment; filename="backup-hotel-{hoje_local().isoformat()}.json"'
    return resp


@bp.post("/api/manutencao/comprovantes-orfaos")
@login_obrigatorio
def limpar_orfaos():
    """Apaga comprovantes que nenhuma reserva ou gasto usa (e com mais de 24 h, para não pegar um envio em andamento)."""
    em_uso = set()
    for r in (referencia("reservas").get() or {}).values():
        em_uso |= ids_comprovantes(r)
    em_uso |= {c["comprovante_id"] for c in (referencia("custos").get() or {}).values() if c.get("comprovante_id")}
    limite = datetime.now(timezone.utc) - timedelta(hours=24)
    sobra, recentes = [], 0
    for cid in (referencia("comprovantes").get(shallow=True) or {}):      # só as chaves, sem baixar os arquivos
        if cid in em_uso:
            continue
        enviado = referencia(f"comprovantes/{cid}/enviado_em").get()
        if enviado and datetime.fromisoformat(enviado) > limite:
            recentes += 1
        else:
            sobra.append(cid)
    apagar_comprovantes(sobra)
    return jsonify({"removidos": len(sobra), "recentes_mantidos": recentes})
