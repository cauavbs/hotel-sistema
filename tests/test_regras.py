"""Regras de negócio: reservas, hóspedes, pagamentos, comprovantes, custos e relatórios."""
import base64

import pytest

PNG = base64.b64encode(b"\x89PNG teste").decode()


@pytest.fixture
def quartos(logado):
    return [logado.post("/api/quartos", json={"numero": n, "capacidade": c}).json["id"] for n, c in (("101", 3), ("102", 2))]


def reserva(qid, **extra):
    return {"quarto_id": qid, "origem": "airbnb", "hospede": "Maria Silva", "cpf": "529.982.247-25", "telefone": "98 99999-0000",
            "checkin": "2026-10-10", "checkout": "2026-10-13", "valor_total": 900, **extra}


def test_reserva_com_acompanhantes_e_pagamentos(logado, quartos):
    r = logado.post("/api/reservas", json=reserva(quartos[0], acompanhantes=[{"nome": "João"}, {"nome": "Ana", "cpf": "529.982.247-25"}],
                                                  pagamentos=[{"valor": 300, "forma": "pix"}, {"valor": 200, "forma": "dinheiro"}]))
    assert r.status_code == 201
    j = r.json
    assert (j["hospedes"], j["valor_pago"], j["situacao"], j["cpf"]) == (3, 500, "parcial", "52998224725")


@pytest.mark.parametrize("extra,msg", [
    ({"acompanhantes": [{"nome": "A"}, {"nome": "B"}, {"nome": "C"}]}, "comporta até"),
    ({"valor_total": 100, "pagamentos": [{"valor": 200, "forma": "pix"}]}, "não pode passar"),
    ({"pagamentos": [{"valor": 10, "forma": "pix", "comprovante_id": "nao-existe"}]}, "comprovante"),
    ({"pagamentos": [{"valor": 10, "forma": "cheque"}]}, "forma"),
])
def test_validacoes(logado, quartos, extra, msg):
    r = logado.post("/api/reservas", json=reserva(quartos[1], checkin="2026-11-01", checkout="2026-11-02", **extra))
    assert r.status_code == 400 and msg.lower() in r.json["erro"].lower()


def test_comprovante_ciclo_de_vida(logado, quartos, client):
    cid = logado.post("/api/comprovantes", json={"nome": "pix.jpg", "tipo": "image/jpeg", "dados": PNG}).json["id"]
    assert logado.get(f"/api/comprovantes/{cid}").status_code == 200
    rid = logado.post("/api/reservas", json=reserva(quartos[0], pagamentos=[{"valor": 300, "forma": "pix", "comprovante_id": cid}])).json["id"]
    editada = {**reserva(quartos[0]), "pagamentos": [{"valor": 900, "forma": "pix"}]}
    assert logado.put(f"/api/reservas/{rid}", json=editada).json["situacao"] == "pago"
    assert logado.get(f"/api/comprovantes/{cid}").status_code == 404      # tirado da reserva, apagado
    assert logado.post("/api/comprovantes", json={"nome": "x", "tipo": "application/x-msdownload", "dados": PNG}).status_code == 400
    assert logado.post("/api/comprovantes", json={"nome": "g", "tipo": "application/pdf", "dados": "A" * 1_500_000}).status_code == 400


def test_comprovante_exige_login(client, logado):
    cid = logado.post("/api/comprovantes", json={"nome": "a", "tipo": "application/pdf", "dados": PNG}).json["id"]
    from app import app
    assert app.test_client().get(f"/api/comprovantes/{cid}").status_code == 401


def test_reserva_antiga_sem_lista_de_pagamentos_continua_valida(logado, quartos, banco_limpo):
    banco_limpo["reservas"] = {"velha": {"quarto_id": quartos[1], "checkin": "2026-10-01", "checkout": "2026-10-03", "origem": "direto",
                                         "hospede": "Antigo", "hospedes": 1, "valor_total": 200, "valor_pago": 200, "forma_pagamento": "pix", "status": "confirmada"}}
    lista = logado.get("/api/reservas?ano=2026").json
    assert lista[0]["pagamentos"][0]["forma"] == "pix" and logado.get("/api/reservas?ano=2027").json == []


def test_custos_sem_categoria_com_comprovante_e_relatorio(logado, quartos):
    cid = logado.post("/api/comprovantes", json={"nome": "luz.pdf", "tipo": "application/pdf", "dados": PNG}).json["id"]
    c = logado.post("/api/custos", json={"data": "2026-10-05", "descricao": "Conta de luz", "valor": 320, "comprovante_id": cid})
    assert c.status_code == 201 and c.json["comprovante_nome"] == "luz.pdf"
    logado.post("/api/custos", json={"data": "2026-10-06", "descricao": "conta de LUZ", "valor": 10})
    assert logado.post("/api/custos", json={"data": "2026-10-05", "descricao": " ", "valor": 5}).status_code == 400
    assert logado.get("/api/relatorios?ano=2026").json["maiores_gastos"] == {"Conta de luz": 330.0}
    logado.delete(f"/api/custos/{c.json['id']}")
    assert logado.get(f"/api/comprovantes/{cid}").status_code == 404


def test_paginas_carregam(logado):
    for rota in ("/", "/anual", "/reservas", "/historico", "/quartos", "/custos", "/relatorios"):
        assert logado.get(rota).status_code == 200, rota
