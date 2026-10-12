"""Anonimiza dados pessoais de reservas antigas (prazo de retenção).

Remove CPF, telefone, acompanhantes e observações, e reduz o nome às iniciais.
Valores e comprovantes ficam, para a contabilidade. Por padrão só SIMULA.

  python3 anonimizar_antigos.py --meses 60            # mostra o que seria alterado
  python3 anonimizar_antigos.py --meses 60 --aplicar  # grava a alteração

O prazo certo depende das suas obrigações legais: confirme com o contador.
"""
import argparse
from datetime import date, timedelta

from servicos.firebase_service import inicializar_firebase, referencia

ap = argparse.ArgumentParser()
ap.add_argument("--meses", type=int, required=True, help="anonimiza reservas com check-out anterior a N meses")
ap.add_argument("--aplicar", action="store_true", help="grava de verdade (sem isso, só simula)")
args = ap.parse_args()

corte = (date.today() - timedelta(days=30 * args.meses)).isoformat()
inicializar_firebase()
alvo = [(i, r) for i, r in (referencia("reservas").get() or {}).items()
        if r["checkout"] < corte and not r.get("anonimizado")]

for rid, r in alvo:
    if args.aplicar:
        iniciais = " ".join(p[0].upper() + "." for p in r["hospede"].split()) or "—"
        referencia(f"reservas/{rid}").update({"hospede": iniciais, "cpf": "", "telefone": "", "observacao": "",
                                              "acompanhantes": None, "anonimizado": True})
print(f"{len(alvo)} reserva(s) com check-out antes de {corte}: {'anonimizadas.' if args.aplicar else 'seriam anonimizadas (simulação; use --aplicar).'}")
