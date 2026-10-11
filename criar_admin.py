"""Cria (ou atualiza) um administrador. Uso: python3 criar_admin.py email senha "Nome" """
import sys

from firebase_admin import auth

from servicos.firebase_service import inicializar_firebase, referencia

email, senha, nome = sys.argv[1], sys.argv[2], sys.argv[3]
inicializar_firebase()

try:
    u = auth.create_user(email=email, password=senha)
except auth.EmailAlreadyExistsError:
    # Usuário já existe no Authentication: só atualiza a senha e completa o perfil.
    u = auth.get_user_by_email(email)
    auth.update_user(u.uid, password=senha)

referencia(f"usuarios/{u.uid}").set({"email": email, "nome": nome, "perfil": "admin"})
print("Administrador pronto:", email)
