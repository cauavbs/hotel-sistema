"""Limite de tentativas de login guardado no banco (vale para todas as instâncias da Vercel).

Guarda só um hash do IP e do e-mail, nunca os valores em texto.
"""
import hashlib
import time

from servicos.firebase_service import referencia

JANELA = 900                            # 15 minutos
LIMITES = {"ip": 5, "email": 10}        # falhas permitidas por janela


def _ref(tipo, valor):
    return referencia(f"tentativas/{tipo}_{hashlib.sha256(valor.lower().encode()).hexdigest()[:32]}")


def _vigente(tipo, valor):
    d = _ref(tipo, valor).get() or {}
    return d if time.time() - d.get("inicio", 0) < JANELA else {}


def bloqueado(ip, email):
    return any(_vigente(t, v).get("n", 0) >= LIMITES[t] for t, v in (("ip", ip), ("email", email)))


def registrar_falha(ip, email):
    agora = time.time()
    for tipo, valor in (("ip", ip), ("email", email)):
        def somar(atual):
            if not atual or agora - atual.get("inicio", 0) >= JANELA:
                return {"n": 1, "inicio": agora}
            return {"n": atual.get("n", 0) + 1, "inicio": atual["inicio"]}
        _ref(tipo, valor).transaction(somar)


def limpar(email):
    _ref("email", email).delete()
