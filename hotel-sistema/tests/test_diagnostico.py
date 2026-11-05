import diagnostico as dg


def test_explica_cada_tipo_de_erro_de_credencial():
    assert "relógio" in dg.explicar_erro_token("Invalid JWT: Token must be a short-lived token (60 minutes) and in a reasonable timeframe.")
    assert "nova" in dg.explicar_erro_token("('invalid_grant: Invalid JWT Signature.', {'error': 'invalid_grant'})")
    assert "internet" in dg.explicar_erro_token("HTTPSConnectionPool: Max retries exceeded")
    assert "Motivo informado" in dg.explicar_erro_token("algo novo")


def test_diferenca_de_relogio():
    from datetime import datetime, timedelta, timezone
    from email.utils import format_datetime
    agora = datetime.now(timezone.utc)
    assert dg.diferenca_relogio(format_datetime(agora)) < 5
    assert 590 < dg.diferenca_relogio(format_datetime(agora + timedelta(minutes=10))) < 610


def test_diagnostico_aponta_credencial_ausente(monkeypatch, capsys):
    monkeypatch.setattr(dg.Config, "FIREBASE_CREDENTIALS_JSON", "")
    monkeypatch.setattr(dg.Config, "FIREBASE_CREDENTIALS_PATH", "nao-existe.json")
    dg.contagem.update({dg.FALHA: 0, dg.ALERTA: 0})
    dg.main()
    saida = capsys.readouterr().out
    assert "[FALHA]" in saida and "nao-existe.json" in saida and "problema(s) a corrigir" in saida


def test_explica_erro_de_certificado_ssl_comum_no_windows():
    txt = dg.explicar_erro_token("HTTPSConnectionPool(host='oauth2.googleapis.com'): SSLError(CERTIFICATE_VERIFY_FAILED)", "SSLError")
    assert "certificado" in txt.lower() and "certifi" in txt


def test_diagnostico_retorna_codigo_de_saida(monkeypatch):
    monkeypatch.setattr(dg.Config, "FIREBASE_CREDENTIALS_JSON", "")
    monkeypatch.setattr(dg.Config, "FIREBASE_CREDENTIALS_PATH", "nao-existe.json")
    dg.contagem.update({dg.FALHA: 0, dg.ALERTA: 0})
    assert dg.main() == 1
    dg.contagem.update({dg.FALHA: 0, dg.ALERTA: 0})
    assert dg.resumo() == 0
