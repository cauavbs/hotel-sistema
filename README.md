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

## Segurança e operação

- **Quem entra:** só contas com `perfil: "admin"` em `usuarios/{uid}`. Crie ou atualize cada administrador com
  `python3 criar_admin.py email senha "Nome"` (funciona também para e-mail já existente, e serve para trocar a senha).
  No Firebase, em Authentication > Configurações > Ações do usuário, desative a criação de contas por cadastro, se a opção existir.
- **Testar no celular:** por padrão o servidor só aceita este computador (`127.0.0.1`). Para abrir pelo celular, ponha
  `FLASK_HOST=0.0.0.0` no `.env`; o debug é desligado automaticamente nesse modo.
- **Tentativas de login:** limite de 5 falhas por IP e 10 por e-mail a cada 15 minutos, guardado no banco (nó `tentativas`, só com hashes).
- **Reservas simultâneas:** cada gravação de reserva trava o quarto por instantes (nó `bloqueios`), então dois
  administradores nunca passam juntos pela checagem de conflito. Se um deles receber "Outro administrador está salvando...", basta repetir.
- **Cabeçalhos de segurança:** CSP e outros em `app.py`. O Chart.js fica em `static/vendor/` (sem CDN).
  Por causa da CSP, não use `<script>` nem `onclick=` dentro dos templates: ponha o código em `static/js/`.
- **Dados pessoais (LGPD):** `python3 anonimizar_antigos.py --meses N` simula a anonimização de reservas antigas
  (`--aplicar` grava). Confirme o prazo com o contador.
- **Trocar a chave do Firebase:** Contas de serviço > Gerar nova chave privada; substitua `firebase-credentials.json` e a variável
  `FIREBASE_CREDENTIALS_JSON` na Vercel (Redeploy); depois apague a chave antiga em "Gerenciar permissões da conta de serviço" > Chaves.
- **Testes:** `pip install -r requirements-dev.txt && pytest` (usam um banco simulado, não tocam no Firebase).

## Hoje, bloqueios, lixeira e backup

- **Hoje (página inicial):** chegadas e saídas de hoje e amanhã, quem está na casa, saldos a receber e o estado de cada quarto,
  com o controle de limpeza (Limpo / A limpar). O calendário mensal ficou em `/calendario`.
- **Bloqueio de datas:** na aba Quartos e Bloqueios. Bloqueia o quarto por um período (manutenção, uso próprio) e impede reservas nele;
  aparece em cinza no calendário e conta como indisponível no Calendário Anual.
- **Calendário Anual:** dia livre abre a nova reserva já com o quarto e as datas; dia parcialmente ocupado deixa escolher entre
  reservar ou ver os quartos ocupados; dia lotado abre as reservas daquele dia (`/reservas?dia=AAAA-MM-DD`).
- **Lixeira:** "Excluir" uma reserva a move para a lixeira (aba Histórico), de onde dá para restaurar ou excluir de vez
  (só então os comprovantes são apagados). Ao restaurar, o conflito de datas é conferido de novo.
- **Exportar e Backup:** CSV para Excel (reservas e custos), backup JSON dos dados e limpeza de comprovantes sem uso.
  O backup completo, com os comprovantes, é `python3 backup.py` (cria a pasta `backups/`, que fica fora do Git).
- **Datas:** o sistema usa o horário de Brasília (UTC-3) para "hoje", no navegador e no servidor.
- **Valores:** aceitam vírgula, são arredondados em centavos, e `nan`, negativos e acima de R$ 10.000.000 são recusados.
- **Erros:** falha do banco mostra "não foi possível falar com o banco"; qualquer outro erro mostra um código de 8 caracteres
  que também aparece nos Logs da Vercel.

## Airbnb e Booking (sincronização por iCal)

A aba **Airbnb e Booking** liga o sistema às duas plataformas por calendário (iCal). O sistema é a central:

- **Entrada:** você cola, por quarto, o link de calendário que o Airbnb e o Booking oferecem (campo "Link do Airbnb/Booking").
  O sistema lê esses links e cria as reservas como *importadas* (só com as datas, marcadas com "⚠ completar"); você preenche hóspede e valor.
  Reservas que você já lançou à mão (mesmo quarto, canal e datas) são vinculadas, sem duplicar.
  Bloqueios "Not available" da plataforma viram bloqueios no sistema. Se a reserva some do calendário da plataforma (cancelada) e a chegada
  ainda é futura, ela é cancelada aqui; estadias já em andamento nunca são canceladas sozinhas.
- **Saída:** para cada quarto há um link por plataforma ("Entregar ao Airbnb/Booking"), com as reservas diretas, as da outra plataforma e os bloqueios.
  Não leva nomes nem valores. As reservas que vieram de uma plataforma não voltam para ela (evita eco). Os links têm um token secreto;
  "Gerar novos links" troca o token (e obriga a colar os novos nas plataformas).
- **Quando sincroniza:** ao abrir a página Hoje (o que estiver há mais de 30 minutos sem sincronizar), no botão "Sincronizar tudo agora" e,
  se você criar a variável `CRON_SECRET` na Vercel, também uma vez por dia (limite do plano Hobby).
- **Limites:** cada plataforma decide de quanto em quanto tempo lê o seu link, então pode haver atraso de algumas horas. Reserva importada que bate
  com outra aparece em "Conflitos de datas" na página Hoje. Excluir no sistema uma reserva que ainda existe na plataforma não a cancela lá:
  ela volta na próxima sincronização. Cancele sempre na plataforma.
- **Segurança:** só links https, nunca para endereços da rede interna; os links das plataformas são tratados como segredos (entram no backup JSON).
