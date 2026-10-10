# Sistema Hotel

Mesma arquitetura da barbearia: Flask + templates Jinja, login por e-mail/senha do Firebase,
Firebase Realtime Database acessado só pelo servidor. Os dois administradores têm acesso total.

| Página | Rota | API |
|---|---|---|
| Calendário (quartos x dias, cor por origem, faixa amarela = pagamento pendente) | `/` | `/api/reservas` |
| Reservas (Airbnb, Booking, direto; valor livre; pago/parcial/pendente; forma de pagamento) | `/reservas` | `/api/reservas` |
| Quartos | `/quartos` | `/api/quartos` |
| Insumos e Custos (limpeza, produtos, contas, manutenção...) | `/custos` | `/api/custos` |
| Relatórios e Gráficos | `/relatorios` | `/api/relatorios` |

Regra de conflito: uma reserva ocupa as noites de check-in até o dia anterior ao check-out;
o dia do check-out fica livre para outro check-in. Reservas canceladas não bloqueiam datas.

## Rodar no Ubuntu
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # preencha (veja abaixo)
python3 criar_admin.py email1@exemplo.com SENHA "Nome 1"
python3 criar_admin.py email2@exemplo.com SENHA "Nome 2"
python3 app.py              # http://localhost:5000/login
```

## Firebase (crie um projeto NOVO para o hotel)
1. Authentication > Método de login > ative **E-mail/senha**.
2. Realtime Database > criar banco; copie a URL para `FIREBASE_DATABASE_URL`.
3. Configurações do projeto > Geral > **Chave de API da Web** vai em `FIREBASE_API_KEY`.
4. Contas de serviço > Gerar nova chave privada, salvar como `firebase-credentials.json` na raiz.
5. Regras do Realtime Database: `{ "rules": { ".read": false, ".write": false } }` (só o servidor acessa).

## Deploy na Vercel
Suba para o GitHub, importe na Vercel e crie as variáveis `SECRET_KEY`, `FIREBASE_API_KEY`,
`FIREBASE_DATABASE_URL` e `FIREBASE_CREDENTIALS_JSON` (conteúdo do JSON da conta de serviço).
Defina `FLASK_DEBUG=false`.

## Dados (Realtime Database)
`quartos`, `reservas` (datas em AAAA-MM-DD), `custos`, `usuarios`.
