"""Backup completo no seu computador, com os comprovantes. Uso: python3 backup.py

Cria backups/AAAA-MM-DD_HHMM/dados.json e a pasta comprovantes/. A pasta "backups" fica fora do Git
(tem dados pessoais): guarde uma cópia em um pen drive ou na nuvem, de preferência com senha.
"""
import base64
import json
import pathlib
from datetime import datetime

from servicos.firebase_service import inicializar_firebase, referencia

EXT = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "application/pdf": ".pdf"}

inicializar_firebase()
pasta = pathlib.Path("backups") / datetime.now().strftime("%Y-%m-%d_%H%M")
(pasta / "comprovantes").mkdir(parents=True)

dados = {nome: referencia(nome).get() or {} for nome in ("quartos", "reservas", "custos", "indisponiveis")}
(pasta / "dados.json").write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")

n = 0
for cid in referencia("comprovantes").get(shallow=True) or {}:
    c = referencia(f"comprovantes/{cid}").get()
    if c:
        (pasta / "comprovantes" / f"{cid}{EXT.get(c['tipo'], '')}").write_bytes(base64.b64decode(c["dados"]))
        n += 1
print(f"Backup salvo em {pasta}: {len(dados['reservas'])} reservas, {len(dados['custos'])} gastos, {n} comprovantes.")
