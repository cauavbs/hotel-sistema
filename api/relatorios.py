"""Estatísticas do hotel: ocupação, receita, sazonalidade, origem, pagamento e custos.

A receita de cada reserva é rateada pelas noites, então uma estadia que
cruza dois meses (ou anos) entra proporcionalmente em cada um.
"""
import calendar
from collections import defaultdict
from datetime import date, timedelta

from flask import Blueprint, jsonify, request

from autenticacao.decoradores import login_obrigatorio
from servicos.pagamentos import pagamentos_de
from servicos.firebase_service import referencia

bp = Blueprint("api_relatorios", __name__, url_prefix="/api/relatorios")


@bp.get("")
@login_obrigatorio
def relatorio():
    try:
        ano = int(request.args.get("ano") or date.today().year)
    except ValueError:
        return jsonify({"erro": "Ano inválido."}), 400

    quartos = referencia("quartos").get() or {}
    reservas = [r for r in (referencia("reservas").get() or {}).values() if r.get("status") != "cancelada"]
    custos = [c for c in (referencia("custos").get() or {}).values() if c["data"][:4] == str(ano)]

    receita, noites_mes, sazonalidade = [0.0] * 12, [0] * 12, [0] * 12
    por_quarto = {i: {"quarto": q["numero"], "reservas": 0, "noites": 0, "receita": 0.0} for i, q in quartos.items()}
    por_origem = defaultdict(lambda: {"reservas": 0, "noites": 0, "receita": 0.0})
    formas = defaultdict(float)
    n_res = rec_ano = recebido = 0.0

    for r in reservas:
        ini, fim = date.fromisoformat(r["checkin"]), date.fromisoformat(r["checkout"])
        n = (fim - ini).days
        diaria = r["valor_total"] / n
        no_ano = 0
        for i in range(n):
            d = ini + timedelta(days=i)
            sazonalidade[d.month - 1] += 1           # todos os anos juntos
            if d.year == ano:
                noites_mes[d.month - 1] += 1
                receita[d.month - 1] += diaria
                no_ano += 1
        if not no_ano:
            continue
        parte = no_ano / n
        n_res += 1
        rec_ano += r["valor_total"] * parte
        recebido += r["valor_pago"] * parte
        for pg in pagamentos_de(r):
            formas[pg.get("forma") or "outros"] += pg["valor"] * parte
        for alvo in (por_origem[r["origem"]], por_quarto.get(r["quarto_id"])):
            if alvo is not None:
                alvo["reservas"] += 1
                alvo["noites"] += no_ano
                alvo["receita"] += r["valor_total"] * parte

    custo_mes, gastos = [0.0] * 12, defaultdict(float)
    for c in custos:
        custo_mes[int(c["data"][5:7]) - 1] += c["valor"]
        gastos[c["descricao"].strip().lower().capitalize()] += c["valor"]

    n_quartos = len(quartos) or 1
    dias_mes = [calendar.monthrange(ano, m)[1] for m in range(1, 13)]
    total_noites, total_custo = sum(noites_mes), sum(custo_mes)
    return jsonify({
        "ano": ano,
        "kpis": {
            "receita": rec_ano, "recebido": recebido, "a_receber": rec_ano - recebido,
            "custos": total_custo, "lucro": rec_ano - total_custo, "reservas": int(n_res),
            "noites": total_noites,
            "ocupacao": total_noites / (n_quartos * sum(dias_mes)) * 100,
            "diaria_media": rec_ano / total_noites if total_noites else 0,
            "ticket_medio": rec_ano / n_res if n_res else 0,
            "permanencia_media": total_noites / n_res if n_res else 0,
        },
        "meses": {
            "receita": receita, "custos": custo_mes, "lucro": [a - b for a, b in zip(receita, custo_mes)],
            "noites": noites_mes, "ocupacao": [n / (n_quartos * d) * 100 for n, d in zip(noites_mes, dias_mes)],
            "sazonalidade": sazonalidade,
        },
        "por_quarto": sorted(por_quarto.values(), key=lambda x: -x["reservas"]),
        "por_origem": por_origem, "formas_pagamento": formas, "maiores_gastos": dict(sorted(gastos.items(), key=lambda g: -g[1])[:8]),
    })
