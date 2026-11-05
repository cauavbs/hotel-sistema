import time
from types import SimpleNamespace

import pytest

from servicos import trava
from servicos.trava import TravaOcupada, trava_quarto


class Resposta(SimpleNamespace):
    def json(self):
        return {"localId": self.uid}


@pytest.fixture
def firebase_auth(monkeypatch):
    """Simula a API de login do Firebase: senha 'certa' funciona, qualquer outra falha."""
    def post(url, params=None, json=None, timeout=None):
        ok = json["password"] == "certa"
        return Resposta(status_code=200 if ok else 400, uid="uid-" + json["email"])
    monkeypatch.setattr("autenticacao.rotas.requests.post", post)


def entrar(c, email="a@b.com", senha="certa", ip="1.1.1.1"):
    return c.post("/login", json={"email": email, "senha": senha}, headers={"X-Forwarded-For": ip})


# ---- item 1: só administradores ----
def test_conta_sem_perfil_admin_nao_entra(client, firebase_auth, banco_limpo):
    r = entrar(client)
    assert r.status_code == 403 and "acesso" in r.json["erro"]
    assert client.get("/api/quartos").status_code == 401


def test_admin_entra(client, firebase_auth, banco_limpo):
    banco_limpo["usuarios"] = {"uid-a@b.com": {"perfil": "admin", "nome": "A"}}
    assert entrar(client).status_code == 200
    assert client.get("/api/quartos").status_code == 200


def test_perfil_que_nao_e_admin_nao_entra(client, firebase_auth, banco_limpo):
    banco_limpo["usuarios"] = {"uid-a@b.com": {"perfil": "recepcao"}}
    assert entrar(client).status_code == 403


# ---- item 3: limite de tentativas ----
def test_bloqueia_apos_5_falhas_do_mesmo_ip_e_nao_afeta_outro_ip(client, firebase_auth, banco_limpo):
    for i in range(5):
        assert entrar(client, f"x{i}@b.com", "errada", ip="9.9.9.9").status_code == 401
    assert entrar(client, "novo@b.com", "errada", ip="9.9.9.9").status_code == 429
    assert entrar(client, "novo@b.com", "errada", ip="8.8.8.8").status_code == 401


def test_bloqueio_por_email_e_guardado_com_hash(client, firebase_auth, banco_limpo):
    for i in range(10):
        entrar(client, "alvo@b.com", "errada", ip=f"7.7.7.{i}")
    assert entrar(client, "alvo@b.com", "errada", ip="6.6.6.6").status_code == 429
    chaves = " ".join(banco_limpo["tentativas"])
    assert "alvo@b.com" not in chaves and "7.7.7" not in chaves


def test_login_correto_zera_falhas_do_email(client, firebase_auth, banco_limpo):
    banco_limpo["usuarios"] = {"uid-a@b.com": {"perfil": "admin"}}
    for _ in range(3):
        entrar(client, "a@b.com", "errada", ip="5.5.5.5")
    assert entrar(client, "a@b.com", "certa", ip="4.4.4.4").status_code == 200
    assert not any(k.startswith("email_") for k in banco_limpo["tentativas"])


# ---- item 4: cabeçalhos ----
def test_cabecalhos_de_seguranca(logado):
    r = logado.get("/relatorios")
    csp = r.headers["Content-Security-Policy"]
    assert "script-src 'self'" in csp and "frame-ancestors 'none'" in csp and "cdn" not in csp
    assert r.headers["X-Frame-Options"] == "DENY" and r.headers["X-Content-Type-Options"] == "nosniff"
    assert "cdn.jsdelivr" not in r.get_data(as_text=True)
    assert logado.get("/api/quartos").headers["Cache-Control"] == "no-store"


def test_paginas_nao_tem_script_inline(client):
    html = client.get("/login").get_data(as_text=True)
    assert "<script>" not in html and "onclick=" not in html


# ---- item 7: trava por quarto ----
def test_trava_segura_o_segundo_administrador(banco_limpo, monkeypatch):
    with trava_quarto("q1"):
        with pytest.raises(TravaOcupada):
            with trava_quarto("q1", espera=0.3):
                pass
        with trava_quarto("q2", espera=0.3):      # outro quarto não é afetado
            pass
    with trava_quarto("q1", espera=0.3):          # liberada ao terminar
        pass
    assert "q1" not in banco_limpo.get("bloqueios", {})


def test_trava_expirada_nao_prende_ninguem(banco_limpo):
    banco_limpo["bloqueios"] = {"q1": {"dono": "servidor-que-caiu", "ate": time.time() - 1}}
    with trava_quarto("q1", espera=0.3):
        pass


def test_trava_e_liberada_mesmo_com_erro(banco_limpo):
    with pytest.raises(ValueError):
        with trava_quarto("q1"):
            raise ValueError("falha")
    assert "q1" not in banco_limpo.get("bloqueios", {})


def test_reserva_recusada_com_409_se_outro_admin_esta_gravando(logado, banco_limpo, monkeypatch):
    qid = logado.post("/api/quartos", json={"numero": "101", "capacidade": 2}).json["id"]
    monkeypatch.setattr(trava, "ESPERA", 0.3)
    banco_limpo["bloqueios"] = {qid: {"dono": "outro-admin", "ate": time.time() + 10}}
    r = logado.post("/api/reservas", json={"quarto_id": qid, "origem": "direto", "hospede": "Ana", "checkin": "2026-12-01", "checkout": "2026-12-03", "valor_total": 200})
    assert r.status_code == 409 and "Outro administrador" in r.json["erro"]
    assert not banco_limpo.get("reservas")


def test_conflito_continua_sendo_detectado_dentro_da_trava(logado, banco_limpo):
    qid = logado.post("/api/quartos", json={"numero": "101", "capacidade": 2}).json["id"]
    base = {"quarto_id": qid, "origem": "direto", "hospede": "Ana", "valor_total": 200}
    assert logado.post("/api/reservas", json={**base, "checkin": "2026-12-01", "checkout": "2026-12-03"}).status_code == 201
    r = logado.post("/api/reservas", json={**base, "checkin": "2026-12-02", "checkout": "2026-12-04"})
    assert r.status_code == 409 and r.json["erro"].startswith("Conflito")
    assert logado.post("/api/reservas", json={**base, "checkin": "2026-12-03", "checkout": "2026-12-05"}).status_code == 201
    assert not banco_limpo.get("bloqueios")        # nenhuma trava ficou presa
