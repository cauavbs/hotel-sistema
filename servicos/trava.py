"""Trava curta por quarto.

Dois administradores salvando reservas no mesmo quarto ao mesmo tempo passariam
juntos pela checagem de conflito. Esta trava (uma transação do Realtime Database)
faz um esperar o outro terminar, então a checagem sempre enxerga a reserva mais nova.
"""
import re
import time
import uuid
from contextlib import contextmanager

from servicos.firebase_service import referencia

VALIDADE = 15   # segundos: se um servidor cair com a trava, ela expira sozinha
ESPERA = 6      # segundos tentando conseguir a trava antes de desistir


class TravaOcupada(Exception):
    """Outro administrador está gravando neste quarto agora."""


class _Segurada(Exception):
    pass


@contextmanager
def trava_quarto(quarto_id, espera=None):
    espera = ESPERA if espera is None else espera
    if not re.fullmatch(r"[\w-]+", str(quarto_id or "")):
        yield  # sem quarto válido não há o que travar; a validação recusa em seguida
        return
    ref, dono = referencia(f"bloqueios/{quarto_id}"), uuid.uuid4().hex
    limite = time.time() + espera
    while True:
        agora = time.time()

        def tomar(atual):
            if atual and atual.get("ate", 0) > agora and atual.get("dono") != dono:
                raise _Segurada()
            return {"dono": dono, "ate": agora + VALIDADE}

        try:
            ref.transaction(tomar)
            break
        except _Segurada:
            if time.time() >= limite:
                raise TravaOcupada("Outro administrador está salvando uma reserva neste quarto agora. Tente de novo em instantes.")
            time.sleep(0.25)
    try:
        yield
    finally:
        def soltar(atual):
            if atual and atual.get("dono") == dono:
                return None          # apaga a trava
            raise _Segurada()

        try:
            ref.transaction(soltar)
        except Exception:            # a trava expira sozinha se não der para soltar
            pass
