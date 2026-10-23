"""Sincronização por iCal: o sistema é a central; Airbnb e Booking trocam datas com ele.

Importação: cada evento do calendário da plataforma vira uma reserva "importada" (só datas; o hóspede e o valor
você completa) ou, se for "Not available"/bloqueio, um bloqueio externo. Exportação: um calendário por quarto e por
plataforma, sem as reservas que vieram dela mesma (evita eco).
"""
import re
import secrets
import time
from datetime import date, datetime, timedelta

import requests

from servicos import ical
from servicos.datas import FUSO, agora_iso, br, hoje_local
from servicos.firebase_service import referencia
from servicos.trava import trava_quarto

CANAIS = {"airbnb": "Airbnb", "booking": "Booking"}
BLOQUEIO = re.compile(r"not available|unavailable|blocked|closed|indispon|bloquead|fechad", re.I)
CODIGO_AIRBNB = re.compile(r"https://www\.airbnb\.[a-z.]+/hosting/reservations/details/[A-Z0-9]+")


# ---------- token dos links que você cola nas plataformas ----------
def obter_token():
    return referencia("config/ical_token").transaction(lambda atual: atual or secrets.token_urlsafe(24))


def regenerar_token():
    novo = secrets.token_urlsafe(24)
    referencia("config/ical_token").set(novo)
    return novo


# ---------- exportação ----------
def eventos_do_calendario(qid, canal):
    hoje, ev = hoje_local().isoformat(), []
    for rid, r in (referencia("reservas").get() or {}).items():
        if (r.get("quarto_id") != qid or r.get("status") == "cancelada" or r.get("excluida_em")
                or r.get("origem") == canal or r["checkout"] < hoje):
            continue
        ev.append({"uid": f"reserva-{rid}{ical.MARCA}", "inicio": r["checkin"], "fim": r["checkout"], "resumo": "Reservado"})
    for bid, b in (referencia("indisponiveis").get() or {}).items():
        if b.get("quarto_id") != qid or b.get("externo") == canal or b["fim"] < hoje:
            continue
        ev.append({"uid": f"bloqueio-{bid}{ical.MARCA}", "inicio": b["inicio"], "fim": b["fim"], "resumo": "Bloqueado"})
    return sorted(ev, key=lambda e: e["inicio"])


# ---------- importação ----------
def _ativa(r):
    return r.get("status") != "cancelada" and not r.get("excluida_em")


def _proprios(qid, reservas, blocos):
    return ([(r["checkin"], r["checkout"]) for r in reservas.values() if r.get("quarto_id") == qid and not r.get("importada") and _ativa(r)]
            + [(b["inicio"], b["fim"]) for b in blocos.values() if b.get("quarto_id") == qid and not b.get("externo")])


def _coberto(ini, fim, intervalos):
    d, f = date.fromisoformat(ini), date.fromisoformat(fim)
    while d < f:
        iso = d.isoformat()
        if not any(a <= iso < b for a, b in intervalos):
            return False
        d += timedelta(days=1)
    return True


def _sobrepoe(qid, ini, fim, reservas, blocos, ignorar=None):
    return (any(i != ignorar and r.get("quarto_id") == qid and _ativa(r) and ini < r["checkout"] and r["checkin"] < fim for i, r in reservas.items())
            or any(b.get("quarto_id") == qid and ini < b["fim"] and b["inicio"] < fim for b in blocos.values()))


def _aplicar(qid, canal, eventos):
    nome, hoje = CANAIS[canal], hoje_local().isoformat()
    eventos = [e for e in eventos if e["fim"] > hoje and e["status"] != "CANCELLED" and ical.MARCA not in e["uid"]]
    reservas, blocos = referencia("reservas").get() or {}, referencia("indisponiveis").get() or {}
    proprios = _proprios(qid, reservas, blocos)
    imp_res = {r["importada"]["uid"]: (i, r) for i, r in reservas.items() if r.get("quarto_id") == qid and (r.get("importada") or {}).get("canal") == canal}
    imp_blq = {b["uid"]: (i, b) for i, b in blocos.items() if b.get("quarto_id") == qid and b.get("externo") == canal}
    c = {"criadas": 0, "atualizadas": 0, "canceladas": 0, "bloqueios": 0, "restauradas": 0, "vinculadas": 0, "ignoradas": 0, "conflitos": 0}
    vistos = set()

    for e in eventos:
        vistos.add(e["uid"])
        if BLOQUEIO.search(e["resumo"]):
            if _coberto(e["inicio"], e["fim"], proprios):          # é o eco das nossas próprias datas
                c["ignoradas"] += 1
                continue
            dados = {"quarto_id": qid, "inicio": e["inicio"], "fim": e["fim"], "motivo": "outro", "observacao": f"Bloqueado no {nome}", "externo": canal, "uid": e["uid"]}
            if e["uid"] in imp_blq:
                i, b = imp_blq[e["uid"]]
                if (b["inicio"], b["fim"]) != (e["inicio"], e["fim"]):
                    referencia(f"indisponiveis/{i}").update({"inicio": e["inicio"], "fim": e["fim"]})
                    c["atualizadas"] += 1
            else:
                blocos[referencia("indisponiveis").push(dados).key] = dados
                c["bloqueios"] += 1
            continue

        if e["uid"] in imp_res:
            i, r = imp_res[e["uid"]]
            mudar = {}
            if (r["checkin"], r["checkout"]) != (e["inicio"], e["fim"]):
                mudar.update(checkin=e["inicio"], checkout=e["fim"])
            if r.get("status") == "cancelada" and r.get("cancelada_por_sync"):
                mudar.update(status="confirmada", cancelada_por_sync=None)
            if r.get("excluida_em"):                                # continua na plataforma: volta para o calendário
                mudar.update(excluida_em=None, excluida_por=None)
                c["restauradas"] += 1
            if mudar:
                referencia(f"reservas/{i}").update(mudar)
                copia = dict(r)
                for k, v in mudar.items():
                    copia.pop(k, None) if v is None else copia.__setitem__(k, v)
                reservas[i] = copia
                c["atualizadas"] += 0 if r.get("excluida_em") and set(mudar) <= {"excluida_em", "excluida_por"} else 1
            atual = reservas[i]
            conflito = _sobrepoe(qid, atual["checkin"], atual["checkout"], reservas, blocos, ignorar=i) if _ativa(atual) else False
            if bool(r.get("conflito")) != conflito:
                referencia(f"reservas/{i}").update({"conflito": conflito or None})
            c["conflitos"] += 1 if conflito else 0
            continue

        # Reserva que você já lançou à mão (mesmo quarto, canal e datas): vincula em vez de duplicar.
        manual = next(((i, r) for i, r in reservas.items() if r.get("quarto_id") == qid and r.get("origem") == canal and not r.get("importada")
                       and _ativa(r) and (r["checkin"], r["checkout"]) == (e["inicio"], e["fim"])), None)
        if manual:
            i, r = manual
            marca = {"canal": canal, "uid": e["uid"], "em": agora_iso()}
            referencia(f"reservas/{i}").update({"importada": marca})
            reservas[i] = {**r, "importada": marca}
            c["vinculadas"] += 1
            continue

        codigo = CODIGO_AIRBNB.search(e["descricao"] or "")
        obs = f"Importada do {nome} em {br(hoje)[:5]}. Complete o hóspede e o valor." + (f" {codigo.group(0)}" if codigo else "")
        conflito = _sobrepoe(qid, e["inicio"], e["fim"], reservas, blocos)
        nova = {"quarto_id": qid, "checkin": e["inicio"], "checkout": e["fim"], "origem": canal, "hospede": f"Reserva {nome}", "cpf": "", "telefone": "",
                "hospedes": 1, "valor_total": 0.0, "valor_pago": 0.0, "status": "confirmada", "observacao": obs,
                "importada": {"canal": canal, "uid": e["uid"], "em": agora_iso()}, "incompleta": True}
        if conflito:
            nova["conflito"] = True
            c["conflitos"] += 1
        reservas[referencia("reservas").push(nova).key] = nova
        c["criadas"] += 1

    # Some do calendário da plataforma = cancelada lá. Só mexe em chegadas futuras (as que já começaram o calendário pode ter omitido).
    futuras = [(u, i, r) for u, (i, r) in imp_res.items() if u not in vistos and _ativa(r) and r["checkin"] > hoje]
    if not eventos and len(futuras) >= 3:
        c["aviso"] = "O calendário veio vazio; as reservas importadas foram mantidas por segurança."
    else:
        for u, i, r in futuras:
            referencia(f"reservas/{i}").update({"status": "cancelada", "cancelada_por_sync": True, "observacao": (r.get("observacao", "") + f" [Cancelada no {nome}]").strip()})
            c["canceladas"] += 1
    for u, (i, b) in imp_blq.items():
        if u not in vistos and b["fim"] > hoje:
            referencia(f"indisponiveis/{i}").delete()
            c["atualizadas"] += 1
    return c


def sincronizar(qid, canal, fetch=None):
    """Sincroniza um quarto com uma plataforma. Nunca levanta erro de rede: devolve {'erro': ...} e guarda o estado."""
    quarto = referencia(f"quartos/{qid}").get()
    url = (quarto or {}).get(f"ical_{canal}")
    if canal not in CANAIS or not url:
        return {"erro": f"Este quarto não tem o link do {CANAIS.get(canal, canal)} configurado."}
    estado = referencia(f"ical_estado/{qid}_{canal}")
    try:
        eventos = ical.ler((fetch or ical.buscar)(url))
    except requests.exceptions.HTTPError as e:
        msg = f"O site respondeu com erro {getattr(e.response, 'status_code', '')}."
    except requests.exceptions.Timeout:
        msg = "O site demorou demais para responder."
    except requests.exceptions.RequestException:
        msg = "Não foi possível acessar o link."
    except ValueError as e:
        msg = str(e)
    else:
        with trava_quarto(qid):
            resumo = _aplicar(qid, canal, eventos)
        estado.set({"ultima": agora_iso(), "ok": True, **resumo})
        return resumo
    estado.set({"ultima": agora_iso(), "ok": False, "erro": msg})
    return {"erro": msg}


def sincronizar_vencidos(minutos=30, orcamento=8.0, fetch=None):
    """Sincroniza o que está atrasado, do mais antigo para o mais novo, dentro de um limite de tempo."""
    inicio, estados, alvos = time.monotonic(), referencia("ical_estado").get() or {}, []
    for qid, q in (referencia("quartos").get() or {}).items():
        for canal in CANAIS:
            if q.get(f"ical_{canal}"):
                alvos.append(((estados.get(f"{qid}_{canal}") or {}).get("ultima", ""), qid, canal))
    agora, out = datetime.now(FUSO), {"sincronizados": 0, "mudancas": 0, "erros": 0}
    for ultima, qid, canal in sorted(alvos):
        if time.monotonic() - inicio > orcamento:
            break
        if ultima and agora - datetime.fromisoformat(ultima) < timedelta(minutes=minutos):
            continue
        r = sincronizar(qid, canal, fetch)
        out["sincronizados"] += 1
        out["erros"] += 1 if r.get("erro") else 0
        out["mudancas"] += sum(r.get(k, 0) for k in ("criadas", "atualizadas", "canceladas", "bloqueios", "restauradas"))
    return out
