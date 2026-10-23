"""Validação de valores e textos vindos do navegador."""
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

MAXIMO = Decimal("10000000")


def dinheiro(valor, campo="Valor") -> float:
    """Aceita 1234.5 ou '1234,50'; recusa 'nan', negativos e valores absurdos; arredonda em centavos."""
    try:
        d = Decimal(str(valor).strip().replace(",", "."))
    except InvalidOperation:
        raise ValueError(f"{campo} inválido.")
    if not d.is_finite() or d < 0 or d > MAXIMO:
        raise ValueError(f"{campo} deve estar entre 0 e 10.000.000.")
    return float(d.quantize(Decimal("0.01"), ROUND_HALF_UP))


def texto(valor, maximo, campo) -> str:
    t = str(valor or "").strip()
    if len(t) > maximo:
        raise ValueError(f"{campo}: no máximo {maximo} caracteres.")
    return t
