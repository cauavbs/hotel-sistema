"""Pagamentos, comprovantes e CPF."""
import re

from servicos.firebase_service import referencia


def so_digitos(txt) -> str:
    return re.sub(r"\D", "", str(txt or ""))


def cpf_valido(cpf: str) -> bool:
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    for n in (9, 10):
        soma = sum(int(cpf[i]) * (n + 1 - i) for i in range(n))
        if int(cpf[n]) != (soma * 10 % 11) % 10:
            return False
    return True


def pagamentos_de(r: dict) -> list:
    """Lista de pagamentos da reserva (reservas antigas tinham um pagamento só)."""
    if r.get("pagamentos"):
        return list(r["pagamentos"])
    if r.get("valor_pago"):
        return [{"valor": r["valor_pago"], "forma": r.get("forma_pagamento") or "outros",
                 "comprovante_id": "", "comprovante_nome": ""}]
    return []


def ids_comprovantes(r: dict) -> set:
    return {p["comprovante_id"] for p in pagamentos_de(r) if p.get("comprovante_id")}


def apagar_comprovantes(ids) -> None:
    for cid in ids:
        referencia(f"comprovantes/{cid}").delete()
