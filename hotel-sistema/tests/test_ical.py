"""Integração com Airbnb e Booking por iCal."""
import socket
from datetime import timedelta

import pytest
import requests

from servicos import ical, sincronia
from servicos.datas import hoje_local


def d(n):
    return (hoje_local() + timedelta(days=n)).isoformat()


def ics(*eventos):
    """eventos: (uid, inicio, fim, resumo[, descricao])"""
    linhas = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//teste//"]
    for uid, ini, fim, resumo, *desc in eventos:
        linhas += ["BEGIN:VEVENT", f"UID:{uid}", f"DTSTART;VALUE=DATE:{ini.replace('-', '')}", f"DTEND;VALUE=DATE:{fim.replace('-', '')}", f"SUMMARY:{resumo}"]
        if desc:
            linhas.append(f"DESCRIPTION:{desc[0]}")
        linhas.append("END:VEVENT")
    return "\r\n".join(linhas + ["END:VCALENDAR"]) + "\r\n"


@pytest.fixture
def setup(logado, monkeypatch):
    qid = logado.post("/api/quartos", json={"numero": "101", "capacidade": 2}).json["id"]
    logado.put(f"/api/ical/quartos/{qid}", json={"ical_airbnb": "https://www.airbnb.com.br/calendar/ical/1.ics?s=x", "ical_booking": "https://admin.booking.com/hotel/ical.html?t=y"})
    feed = {"texto": ics()}
    monkeypatch.setattr("servicos.ical.buscar", lambda url: feed["texto"])
    return logado, qid, feed


def reservas(c):
    return {r["id"]: r for r in c.get("/api/reservas").json}


# ---------- leitura e geração ----------
def test_ler_formatos_comuns():
    texto = ("BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nUID:a1\r\nDTSTART;VALUE=DATE:20261201\r\nDTEND;VALUE=DATE:20261205\r\nSUMMARY:Reserved\r\nDESCRIPTION:Reservation URL: https://www.airbnb.com/hosting/reser\r\n vations/details/HM123\\nPhone: 1234\r\nEND:VEVENT\r\n"
             "BEGIN:VEVENT\r\nUID:b1\r\nDTSTART:20261210T150000Z\r\nDTEND:20261212T110000Z\r\nSUMMARY:CLOSED - Not available\r\nEND:VEVENT\r\n"
             "BEGIN:VEVENT\r\nUID:c1\r\nDTSTART;VALUE=DATE:20261220\r\nSTATUS:CANCELLED\r\nEND:VEVENT\r\n"
             "BEGIN:VEVENT\r\nUID:x\r\nDTSTART:lixo\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n")
    ev = ical.ler(texto)
    assert [(e["uid"], e["inicio"], e["fim"]) for e in ev] == [("a1", "2026-12-01", "2026-12-05"), ("b1", "2026-12-10", "2026-12-12"), ("c1", "2026-12-20", "2026-12-21")]
    assert "airbnb.com/hosting/reservations/details/HM123" in ev[0]["descricao"] and ev[2]["status"] == "CANCELLED"


def test_ler_recusa_o_que_nao_e_calendario():
    with pytest.raises(ValueError):
        ical.ler("<html><body>Erro 403</body></html>")


def test_gerar_nao_vaza_dados_pessoais():
    saida = ical.gerar("Quarto 101", [{"uid": "reserva-1" + ical.MARCA, "inicio": "2026-12-01", "fim": "2026-12-03", "resumo": "Reservado"}])
    assert saida.startswith("BEGIN:VCALENDAR\r\n") and "DTSTART;VALUE=DATE:20261201" in saida and "DTEND;VALUE=DATE:20261203" in saida
    assert ical.ler(saida)[0]["inicio"] == "2026-12-01"


# ---------- segurança do link ----------
@pytest.mark.parametrize("url", ["http://www.airbnb.com/x.ics", "ftp://x/y", "https://", "javascript:alert(1)", "https://a.com/" + "x" * 700])
def test_url_precisa_ser_https(url):
    with pytest.raises(ValueError):
        ical.validar_url_basica(url)


@pytest.mark.parametrize("ip", ["127.0.0.1", "10.0.0.5", "192.168.1.9", "169.254.169.254", "0.0.0.0"])
def test_nao_acessa_rede_interna(monkeypatch, ip):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, "", (ip, 443))])
    with pytest.raises(ValueError, match="não permitido"):
        ical._url_segura("https://exemplo.com/cal.ics")


def test_redirecionamento_para_rede_interna_e_barrado(monkeypatch):
    enderecos = {"publico.com": "93.184.216.34", "interno.local": "10.1.2.3"}
    monkeypatch.setattr(socket, "getaddrinfo", lambda host, *a, **k: [(2, 1, 6, "", (enderecos[host], 443))])

    class R:
        is_redirect, headers = True, {"Location": "https://interno.local/segredo"}
    monkeypatch.setattr(requests, "get", lambda *a, **k: R())
    with pytest.raises(ValueError, match="não permitido"):
        ical.buscar("https://publico.com/cal.ics")


def test_salvar_link_http_e_recusado(setup):
    c, qid, _ = setup
    r = c.put(f"/api/ical/quartos/{qid}", json={"ical_airbnb": "http://inseguro.com/a.ics"})
    assert r.status_code == 400 and "https" in r.json["erro"]


# ---------- calendário entregue às plataformas ----------
def test_calendario_exige_token_e_nao_vaza_nomes(setup, client):
    c, qid, _ = setup
    cfg = c.get("/api/ical/config").json[0]
    link_airbnb, link_booking = cfg["links"]["airbnb"], cfg["links"]["booking"]
    assert "/ical/airbnb/" in link_airbnb and "?t=" in link_airbnb
    anonimo = __import__("app").app.test_client()
    assert anonimo.get(link_airbnb.split("//")[1].split("/", 1)[1]).status_code == 200              # sem login, com token
    assert anonimo.get(f"/ical/airbnb/{qid}.ics").status_code == 404
    assert anonimo.get(f"/ical/airbnb/{qid}.ics?t=errado").status_code == 404
    assert anonimo.get(f"/ical/outro/{qid}.ics?t=x").status_code == 404
    assert anonimo.get(f"/ical/airbnb/nao-existe.ics?t={sincronia.obter_token()}").status_code == 404


def test_calendario_de_cada_plataforma_nao_devolve_as_proprias_reservas(setup):
    c, qid, _ = setup
    base = {"quarto_id": qid, "valor_total": 100}
    c.post("/api/reservas", json={**base, "origem": "direto", "hospede": "Maria Secreta", "checkin": d(10), "checkout": d(12)})
    c.post("/api/reservas", json={**base, "origem": "airbnb", "hospede": "Do Airbnb", "checkin": d(20), "checkout": d(22)})
    c.post("/api/reservas", json={**base, "origem": "booking", "hospede": "Do Booking", "checkin": d(30), "checkout": d(32)})
    c.post("/api/indisponiveis", json={"quarto_id": qid, "inicio": d(40), "fim": d(42), "motivo": "manutencao"})
    c.post("/api/reservas", json={**base, "origem": "direto", "hospede": "Cancelada", "checkin": d(50), "checkout": d(52), "status": "cancelada"})
    datas = lambda canal: {e["inicio"] for e in sincronia.eventos_do_calendario(qid, canal)}
    assert datas("airbnb") == {d(10), d(30), d(40)}           # direto + Booking + bloqueio (sem as do próprio Airbnb)
    assert datas("booking") == {d(10), d(20), d(40)}
    cfg = c.get("/api/ical/config").json[0]["links"]["airbnb"]
    texto = c.get("/" + cfg.split("/", 3)[3]).get_data(as_text=True)
    assert "Maria Secreta" not in texto and "Reservado" in texto and "Cancelada" not in texto


def test_reserva_na_lixeira_sai_do_calendario(setup):
    c, qid, _ = setup
    rid = c.post("/api/reservas", json={"quarto_id": qid, "valor_total": 1, "origem": "direto", "hospede": "A", "checkin": d(5), "checkout": d(6)}).json["id"]
    assert len(sincronia.eventos_do_calendario(qid, "airbnb")) == 1
    c.delete(f"/api/reservas/{rid}")
    assert sincronia.eventos_do_calendario(qid, "airbnb") == []


# ---------- importação ----------
def test_importa_reserva_so_com_datas_e_nao_duplica(setup):
    c, qid, feed = setup
    feed["texto"] = ics(("air-1", d(5), d(8), "Reserved", "Reservation URL: https://www.airbnb.com/hosting/reservations/details/HMABC123"))
    r = c.post("/api/ical/sincronizar", json={"quarto_id": qid, "canal": "airbnb"}).json
    assert r["criadas"] == 1
    res = next(iter(reservas(c).values()))
    assert (res["origem"], res["checkin"], res["checkout"], res["hospede"]) == ("airbnb", d(5), d(8), "Reserva Airbnb")
    assert res["incompleta"] and res["valor_total"] == 0 and "HMABC123" in res["observacao"] and res["importada"]["uid"] == "air-1"
    assert c.post("/api/ical/sincronizar", json={"quarto_id": qid, "canal": "airbnb"}).json["criadas"] == 0
    assert len(reservas(c)) == 1


def test_data_alterada_na_plataforma_atualiza(setup):
    c, qid, feed = setup
    feed["texto"] = ics(("air-1", d(5), d(8), "Reserved"))
    c.post("/api/ical/sincronizar", json={"quarto_id": qid, "canal": "airbnb"})
    feed["texto"] = ics(("air-1", d(6), d(9), "Reserved"))
    assert c.post("/api/ical/sincronizar", json={"quarto_id": qid, "canal": "airbnb"}).json["atualizadas"] == 1
    assert [(r["checkin"], r["checkout"]) for r in reservas(c).values()] == [(d(6), d(9))]


def test_cancelada_na_plataforma_so_se_for_chegada_futura(setup):
    c, qid, feed = setup
    feed["texto"] = ics(("futura", d(10), d(12), "Reserved"), ("andamento", d(-1), d(2), "Reserved"), ("f2", d(20), d(21), "Reserved"), ("f3", d(30), d(31), "Reserved"))
    c.post("/api/ical/sincronizar", json={"quarto_id": qid, "canal": "airbnb"})
    feed["texto"] = ics(("f2", d(20), d(21), "Reserved"), ("f3", d(30), d(31), "Reserved"))
    assert c.post("/api/ical/sincronizar", json={"quarto_id": qid, "canal": "airbnb"}).json["canceladas"] == 1
    por = {r["importada"]["uid"]: r["status"] for r in c.get("/api/reservas").json}
    assert por == {"futura": "cancelada", "andamento": "confirmada", "f2": "confirmada", "f3": "confirmada"}
    feed["texto"] = ics(("futura", d(10), d(12), "Reserved"), ("f2", d(20), d(21), "Reserved"), ("f3", d(30), d(31), "Reserved"))   # voltou
    c.post("/api/ical/sincronizar", json={"quarto_id": qid, "canal": "airbnb"})
    assert {r["importada"]["uid"]: r["status"] for r in c.get("/api/reservas").json}["futura"] == "confirmada"


def test_calendario_vazio_nao_apaga_tudo(setup):
    c, qid, feed = setup
    feed["texto"] = ics(*[(f"u{i}", d(10 + i * 3), d(12 + i * 3), "Reserved") for i in range(3)])
    c.post("/api/ical/sincronizar", json={"quarto_id": qid, "canal": "airbnb"})
    feed["texto"] = ics()
    r = c.post("/api/ical/sincronizar", json={"quarto_id": qid, "canal": "airbnb"}).json
    assert r["canceladas"] == 0 and "vazio" in r["aviso"] and all(x["status"] == "confirmada" for x in reservas(c).values())


def test_falha_de_rede_nao_altera_nada_e_guarda_o_estado(setup, monkeypatch):
    c, qid, feed = setup
    feed["texto"] = ics(("a", d(10), d(12), "Reserved"))
    c.post("/api/ical/sincronizar", json={"quarto_id": qid, "canal": "airbnb"})
    for exc, trecho in ((requests.exceptions.Timeout(), "demorou"), (requests.exceptions.ConnectionError(), "acessar"), (ValueError("O link não devolveu um calendário (.ics) válido."), "calendário")):
        def quebra(url, exc=exc): raise exc
        monkeypatch.setattr("servicos.ical.buscar", quebra)
        r = c.post("/api/ical/sincronizar", json={"quarto_id": qid, "canal": "airbnb"}).json
        assert trecho in r["erro"] and "https" not in r["erro"]
    assert len(reservas(c)) == 1 and c.get("/api/ical/config").json[0]["estado"]["airbnb"]["ok"] is False


def test_bloqueio_externo_e_eco_das_nossas_datas(setup):
    c, qid, feed = setup
    c.post("/api/reservas", json={"quarto_id": qid, "valor_total": 1, "origem": "direto", "hospede": "Maria", "checkin": d(10), "checkout": d(13)})
    feed["texto"] = ics(("eco", d(10), d(13), "Airbnb (Not available)"), ("real", d(20), d(23), "Airbnb (Not available)"))
    r = c.post("/api/ical/sincronizar", json={"quarto_id": qid, "canal": "airbnb"}).json
    assert (r["ignoradas"], r["bloqueios"]) == (1, 1)
    blq = c.get("/api/indisponiveis").json
    assert len(blq) == 1 and blq[0]["inicio"] == d(20) and blq[0]["externo"] == "airbnb"
    assert {e["inicio"] for e in sincronia.eventos_do_calendario(qid, "airbnb")} == {d(10)}     # o bloqueio do Airbnb não volta para ele
    assert d(20) in {e["inicio"] for e in sincronia.eventos_do_calendario(qid, "booking")}      # mas vai para o Booking
    feed["texto"] = ics()
    c.post("/api/ical/sincronizar", json={"quarto_id": qid, "canal": "airbnb"})
    assert c.get("/api/indisponiveis").json == []


def test_conflito_entre_canais_e_marcado(setup):
    c, qid, feed = setup
    feed["texto"] = ics(("a", d(10), d(13), "Reserved"))
    c.post("/api/ical/sincronizar", json={"quarto_id": qid, "canal": "airbnb"})
    feed["texto"] = ics(("b", d(12), d(14), "Booking.com reservation"))
    r = c.post("/api/ical/sincronizar", json={"quarto_id": qid, "canal": "booking"}).json
    assert r["criadas"] == 1 and r["conflitos"] == 1
    assert [x["origem"] for x in c.get("/api/reservas").json if x.get("conflito")] == ["booking"]


def test_eventos_do_proprio_sistema_e_passados_sao_ignorados(setup):
    c, qid, feed = setup
    feed["texto"] = ics((f"reserva-9{ical.MARCA}", d(5), d(6), "Reservado"), ("passada", d(-10), d(-5), "Reserved"))
    assert c.post("/api/ical/sincronizar", json={"quarto_id": qid, "canal": "airbnb"}).json["criadas"] == 0


def test_reserva_excluida_mas_ainda_na_plataforma_volta(setup):
    c, qid, feed = setup
    feed["texto"] = ics(("a", d(10), d(12), "Reserved"))
    c.post("/api/ical/sincronizar", json={"quarto_id": qid, "canal": "airbnb"})
    rid = next(iter(reservas(c)))
    c.delete(f"/api/reservas/{rid}")
    assert c.post("/api/ical/sincronizar", json={"quarto_id": qid, "canal": "airbnb"}).json["restauradas"] == 1
    assert rid in reservas(c)


# ---------- edição não perde a marca de importação nem os links ----------
def test_editar_reserva_importada_e_quarto_preserva_dados(setup):
    c, qid, feed = setup
    feed["texto"] = ics(("a", d(10), d(12), "Reserved"))
    c.post("/api/ical/sincronizar", json={"quarto_id": qid, "canal": "airbnb"})
    r = next(iter(reservas(c).values()))
    ed = c.put(f"/api/reservas/{r['id']}", json={**r, "hospede": "Maria Souza", "valor_total": 500, "pagamentos": [{"valor": 500, "forma": "pix"}]}).json
    assert ed["importada"]["uid"] == "a" and not ed.get("incompleta") and ed["situacao"] == "pago"
    c.put(f"/api/quartos/{qid}", json={"numero": "101", "nome": "Casal", "capacidade": 3})
    cfg = c.get("/api/ical/config").json[0]
    assert cfg["ical_airbnb"].startswith("https://www.airbnb") and cfg["ical_booking"].startswith("https://admin.booking")
    assert c.post("/api/ical/sincronizar", json={"quarto_id": qid, "canal": "airbnb"}).json["criadas"] == 0     # não recria


# ---------- sincronização automática ----------
def test_sincronizar_vencidos_respeita_o_intervalo(setup):
    c, qid, feed = setup
    feed["texto"] = ics(("a", d(10), d(12), "Reserved"))
    r1 = c.post("/api/ical/sincronizar-vencidos").json
    assert r1["sincronizados"] == 2 and r1["mudancas"] == 2                  # Airbnb e Booking (o teste devolve o mesmo calendário aos dois)
    assert c.post("/api/ical/sincronizar-vencidos").json["sincronizados"] == 0     # acabou de sincronizar


def test_cron_so_funciona_com_segredo(setup, monkeypatch):
    c, qid, feed = setup
    anonimo = __import__("app").app.test_client()
    assert anonimo.get("/api/cron/ical").status_code == 404
    monkeypatch.setenv("CRON_SECRET", "segredo123")
    assert anonimo.get("/api/cron/ical", headers={"Authorization": "Bearer errado"}).status_code == 404
    assert anonimo.get("/api/cron/ical", headers={"Authorization": "Bearer segredo123"}).status_code == 200


def test_regenerar_token_invalida_links_antigos(setup):
    c, qid, _ = setup
    antigo = sincronia.obter_token()
    assert c.post("/api/ical/token/regenerar").status_code == 200 and sincronia.obter_token() != antigo
    assert __import__("app").app.test_client().get(f"/ical/airbnb/{qid}.ics?t={antigo}").status_code == 404


def test_paginas_da_integracao(logado):
    for rota in ("/integracoes", "/"):
        assert logado.get(rota).status_code == 200
    assert "Airbnb e Booking" in logado.get("/").get_data(as_text=True)


# ---------- download (rede simulada) ----------
class _Resp:
    def __init__(self, corpo=b"", redirect=None):
        self.is_redirect, self.headers = bool(redirect), ({"Location": redirect} if redirect else {})
        self._corpo = corpo
        self.raw = self

    def read(self, n, decode_content=True):
        return self._corpo[:n]

    def raise_for_status(self):
        pass


def test_buscar_baixa_segue_redirecionamento_e_limita_tamanho(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [(2, 1, 6, "", ("93.184.216.34", 443))])
    respostas = iter([_Resp(redirect="/novo.ics"), _Resp("BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n".encode())])
    monkeypatch.setattr(requests, "get", lambda *a, **k: next(respostas))
    assert "VCALENDAR" in ical.buscar("https://www.airbnb.com/calendar/ical/1.ics")
    monkeypatch.setattr(requests, "get", lambda *a, **k: _Resp(b"x" * (ical.LIMITE_BYTES + 5)))
    with pytest.raises(ValueError, match="grande demais"):
        ical.buscar("https://www.airbnb.com/calendar/ical/1.ics")
    monkeypatch.setattr(requests, "get", lambda *a, **k: _Resp(redirect="/loop"))
    with pytest.raises(ValueError, match="Redirecionamentos"):
        ical.buscar("https://www.airbnb.com/calendar/ical/1.ics")


def test_reserva_lancada_a_mao_e_vinculada_sem_duplicar(setup):
    c, qid, feed = setup
    mao = c.post("/api/reservas", json={"quarto_id": qid, "origem": "airbnb", "hospede": "Maria Souza", "valor_total": 800, "checkin": d(10), "checkout": d(13),
                                        "pagamentos": [{"valor": 800, "forma": "plataforma"}]}).json["id"]
    outra = c.post("/api/reservas", json={"quarto_id": qid, "origem": "booking", "hospede": "Outra", "valor_total": 1, "checkin": d(10 + 20), "checkout": d(12 + 20)}).json["id"]
    feed["texto"] = ics(("air-9", d(10), d(13), "Reserved"), ("air-10", d(30), d(32), "Reserved"))
    r = c.post("/api/ical/sincronizar", json={"quarto_id": qid, "canal": "airbnb"}).json
    assert (r["vinculadas"], r["criadas"]) == (1, 1)                          # a de Maria vinculou; a de d(30) é nova e bate com a "Outra" (Booking)
    todas = reservas(c)
    assert todas[mao]["hospede"] == "Maria Souza" and todas[mao]["importada"]["uid"] == "air-9" and not todas[mao].get("incompleta")
    assert c.post("/api/ical/sincronizar", json={"quarto_id": qid, "canal": "airbnb"}).json["criadas"] == 0
    feed["texto"] = ics(("air-10", d(30), d(32), "Reserved"))                 # Maria cancelou no Airbnb
    assert c.post("/api/ical/sincronizar", json={"quarto_id": qid, "canal": "airbnb"}).json["canceladas"] == 1
    assert reservas(c)[mao]["status"] == "cancelada" and reservas(c)[mao]["hospede"] == "Maria Souza"     # cancelada, mas com os dados preservados
