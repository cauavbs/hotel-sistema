from google.auth.exceptions import RefreshError


def test_chave_recusada_vira_mensagem_clara_no_login(client, monkeypatch):
    import servicos.limite_login as ll

    class Quebra:
        def get(self, *a, **k):
            raise RefreshError("invalid_grant: Invalid JWT Signature.")

    monkeypatch.setattr(ll, "referencia", lambda p: Quebra())
    r = client.post("/login", json={"email": "a@b.com", "senha": "x"})
    assert r.status_code == 503 and r.is_json and "chave de serviço" in r.json["erro"] and len(r.json["codigo"]) == 8
