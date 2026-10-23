"""Valores, erros, lixeira, bloqueios, limpeza, exportação e manutenção."""
import base64
import time
from datetime import datetime, timedelta, timezone

import pytest

from servicos.datas import FUSO, hoje_local

PNG = base64.b64encode(b"\x89PNG teste").decode()


@pytest.fixture
def quartos(logado):
    return [logado.post("/api/quartos", json={"numero": n, "capacidade": 2}).json["id"] for n in ("101", "102")]


def res(qid, ini="2026-12-01", fim="2026-12-03", **extra):
    return {"quarto_id": qid, "origem": "direto", "hospede": "Ana", "checkin": ini, "checkout": fim, "valor_total": 200, **extra}


# ---- datas e valores ----
def test_hoje_local_usa_horario_de_brasilia():
    assert hoje_local() == datetime.now(FUSO).date()
    assert FUSO.utcoffset(None) == timedelta(hours=-3)


@pytest.mark.parametrize("valor", ["nan", "inf", "-5", "1e99", "abc", None, 10_000_001])
def test_valor_total_invalido_e_recusado(logado, quartos, valor):
    r = logado.post("/api/reservas", json=res(quartos[0], valor_total=valor))
    assert r.status_code == 400 and "Valor total" in r.json["erro"]


def test_valores_com_virgula_e_arredondamento(logado, quartos):
    j = logado.post("/api/reservas", json=res(quartos[0], valor_total="1234,567", pagamentos=[{"valor": "0,1", "forma": "pix"}, {"valor": 0.2, "forma": "pix"}])).json
    assert j["valor_total"] == 1234.57 and j["valor_pago"] == 0.3


def test_textos_longos_sao_recusados(logado, quartos):
    assert "Observações" in logado.post("/api/reservas", json=res(quartos[0], observacao="x" * 501)).json["erro"]
    assert "Nome do hóspede" in logado.post("/api/reservas", json=res(quartos[0], hospede="n" * 101)).json["erro"]
    assert logado.post("/api/custos", json={"data": "2026-10-01", "descricao": "d" * 201, "valor": 1}).status_code == 400
    assert logado.post("/api/custos", json={"data": "2026-10-01", "descricao": "ok", "valor": "nan"}).status_code == 400


# ---- erros ----
def test_erro_inesperado_vira_500_com_codigo_e_falha_do_banco_vira_503(logado, monkeypatch):
    import api.quartos as aq
    from firebase_admin.exceptions import UnavailableError

    class Quebra:
        def __init__(self, exc): self.exc = exc
        def get(self, *a, **k): raise self.exc

    monkeypatch.setattr(aq, "referencia", lambda p: Quebra(KeyError("bug")))
    r = logado.get("/api/quartos")
    assert r.status_code == 500 and len(r.json["codigo"]) == 8 and r.json["codigo"] in r.json["erro"]
    monkeypatch.setattr(aq, "referencia", lambda p: Quebra(UnavailableError("fora do ar")))
    r = logado.get("/api/quartos")
    assert r.status_code == 503 and "banco de dados" in r.json["erro"]


# ---- lixeira ----
def test_ciclo_da_lixeira(logado, quartos):
    cid = logado.post("/api/comprovantes", json={"nome": "p.jpg", "tipo": "image/jpeg", "dados": PNG}).json["id"]
    rid = logado.post("/api/reservas", json=res(quartos[0], pagamentos=[{"valor": 100, "forma": "pix", "comprovante_id": cid}])).json["id"]
    assert logado.delete(f"/api/reservas/{rid}?definitivo=1").status_code == 400          # não apaga direto
    assert logado.delete(f"/api/reservas/{rid}").status_code == 200
    assert logado.get("/api/reservas").json == [] and len(logado.get("/api/reservas?lixeira=1").json) == 1
    assert logado.get(f"/api/comprovantes/{cid}").status_code == 200                       # comprovante preservado
    assert logado.post("/api/reservas", json=res(quartos[0], hospede="Outro")).status_code == 201   # datas liberadas
    assert logado.post(f"/api/reservas/{rid}/restaurar").status_code == 409                # restaurar confere conflito
    outro = logado.get("/api/reservas").json[0]["id"]
    logado.delete(f"/api/reservas/{outro}"); logado.delete(f"/api/reservas/{outro}?definitivo=1")
    assert logado.post(f"/api/reservas/{rid}/restaurar").status_code == 200
    assert len(logado.get("/api/reservas").json) == 1
    logado.delete(f"/api/reservas/{rid}")
    assert logado.delete(f"/api/reservas/{rid}?definitivo=1").status_code == 200
    assert logado.get(f"/api/comprovantes/{cid}").status_code == 404 and logado.get("/api/reservas?lixeira=1").json == []


def test_lixeira_nao_entra_em_relatorio_nem_quarto_com_reserva_na_lixeira(logado, quartos):
    rid = logado.post("/api/reservas", json=res(quartos[0], "2026-10-01", "2026-10-03")).json["id"]
    logado.delete(f"/api/reservas/{rid}")
    assert logado.get("/api/relatorios?ano=2026").json["kpis"]["reservas"] == 0
    assert logado.delete(f"/api/quartos/{quartos[0]}").status_code == 409


# ---- bloqueios ----
def test_bloqueio_impede_reserva_e_reserva_impede_bloqueio(logado, quartos):
    q = quartos[0]
    b = logado.post("/api/indisponiveis", json={"quarto_id": q, "inicio": "2026-12-10", "fim": "2026-12-15", "motivo": "manutencao"})
    assert b.status_code == 201 and b.json["motivo_texto"] == "Manutenção"
    r = logado.post("/api/reservas", json=res(q, "2026-12-14", "2026-12-16"))
    assert r.status_code == 409 and "bloqueado" in r.json["erro"]
    assert logado.post("/api/reservas", json=res(q, "2026-12-15", "2026-12-17")).status_code == 201     # o dia final fica livre
    assert logado.post("/api/reservas", json=res(quartos[1], "2026-12-14", "2026-12-16")).status_code == 201   # outro quarto
    c = logado.post("/api/indisponiveis", json={"quarto_id": q, "inicio": "2026-12-16", "fim": "2026-12-18", "motivo": "outro"})
    assert c.status_code == 409 and "reserva" in c.json["erro"]
    assert logado.post("/api/indisponiveis", json={"quarto_id": q, "inicio": "2026-12-12", "fim": "2026-12-11", "motivo": "outro"}).status_code == 400
    assert logado.post("/api/indisponiveis", json={"quarto_id": q, "inicio": "2026-12-20", "fim": "2026-12-22", "motivo": "x"}).status_code == 400
    assert len(logado.get("/api/indisponiveis?ano=2026").json) == 1
    assert logado.delete(f"/api/indisponiveis/{b.json['id']}").status_code == 200
    assert logado.post("/api/reservas", json=res(q, "2026-12-11", "2026-12-12")).status_code == 201


# ---- limpeza ----
def test_limpeza_do_quarto(logado, quartos):
    assert all(q["limpeza"] == "limpo" for q in logado.get("/api/quartos").json)
    assert logado.patch(f"/api/quartos/{quartos[0]}/limpeza", json={"status": "a_limpar"}).status_code == 200
    assert logado.patch(f"/api/quartos/{quartos[0]}/limpeza", json={"status": "sujo"}).status_code == 400
    logado.put(f"/api/quartos/{quartos[0]}", json={"numero": "101", "nome": "Casal", "capacidade": 3})   # editar não perde a limpeza
    assert next(q for q in logado.get("/api/quartos").json if q["id"] == quartos[0])["limpeza"] == "a_limpar"


# ---- filtro por dia ----
def test_reservas_do_dia(logado, quartos):
    logado.post("/api/reservas", json=res(quartos[0], "2026-12-01", "2026-12-03"))
    logado.post("/api/reservas", json=res(quartos[1], "2026-12-03", "2026-12-05", hospede="Bia"))
    assert [r["hospede"] for r in logado.get("/api/reservas?dia=2026-12-02").json] == ["Ana"]
    assert [r["hospede"] for r in logado.get("/api/reservas?dia=2026-12-03").json] == ["Bia"]     # o dia do check-out não conta
    assert logado.get("/api/reservas?dia=2026-12-09").json == []


# ---- exportação, backup e manutenção ----
def test_exportar_csv_para_excel(logado, quartos):
    logado.post("/api/reservas", json=res(quartos[0], hospede="=CMD()", cpf="52998224725", telefone="98 9", valor_total=1500.5,
                                          acompanhantes=[{"nome": "João"}], pagamentos=[{"valor": 500, "forma": "pix"}]))
    r = logado.get("/api/exportar/reservas.csv")
    assert r.headers["Content-Type"].startswith("text/csv") and "attachment" in r.headers["Content-Disposition"]
    txt = r.get_data(as_text=True)
    assert txt.startswith("\ufeff") and ";" in txt and "'=CMD()" in txt and "1500,50" in txt and "529" not in txt     # sem CPF por padrão
    com = logado.get("/api/exportar/reservas.csv?pessoais=1").get_data(as_text=True)
    assert "52998224725" in com and "João" in com
    logado.post("/api/custos", json={"data": "2026-10-05", "descricao": "Luz", "valor": 320})
    assert "320,00" in logado.get("/api/exportar/custos.csv").get_data(as_text=True)
    bk = logado.get("/api/exportar/backup.json").get_json(force=True)
    assert set(bk) >= {"quartos", "reservas", "custos", "indisponiveis", "gerado_em"}


def test_exportar_exige_login(client):
    for rota in ("reservas.csv", "custos.csv", "backup.json"):
        assert client.get(f"/api/exportar/{rota}").status_code == 401
    assert client.post("/api/manutencao/comprovantes-orfaos").status_code == 401


def test_limpar_comprovantes_orfaos(logado, quartos, banco_limpo):
    novo = lambda nome, dias: banco_limpo["comprovantes"].update({nome: {"nome": nome, "tipo": "image/jpeg", "dados": PNG, "enviado_em": (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()}})
    banco_limpo["comprovantes"] = {}
    for nome, dias in (("usado", 5), ("velho", 5), ("recente", 0)):
        novo(nome, dias)
    logado.post("/api/reservas", json=res(quartos[0], pagamentos=[{"valor": 10, "forma": "pix", "comprovante_id": "usado"}]))
    r = logado.post("/api/manutencao/comprovantes-orfaos").json
    assert r == {"removidos": 1, "recentes_mantidos": 1} and set(banco_limpo["comprovantes"]) == {"usado", "recente"}


def test_paginas_novas_e_menu(logado):
    for rota in ("/", "/calendario", "/backup", "/quartos", "/anual"):
        assert logado.get(rota).status_code == 200, rota
    html = logado.get("/").get_data(as_text=True)
    assert "Exportar e Backup" in html and "Quartos e Bloqueios" in html and ">Hoje<" in html
