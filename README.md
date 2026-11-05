# Sistema do Hotel

Painel de gestão para um pequeno hotel: reservas, calendários, hóspedes e acompanhantes, pagamentos com comprovante, custos,
relatórios e sincronização com **Airbnb** e **Booking**. É feito em **Python (Flask)**, usa o **Firebase** (login e banco de dados
Realtime Database) e pode ser publicado na **Vercel**. Funciona no celular, no tablet e no computador.

**Neste guia:** [Telas](#1-telas) · [Requisitos](#2-requisitos) · [Firebase](#3-configurar-o-firebase-uma-vez) · [Ubuntu](#4-instalar-e-rodar-no-ubuntu) · [Windows](#5-instalar-e-rodar-no-windows) ·
[.env](#6-o-arquivo-env) · [Administradores](#7-primeiro-acesso-criar-administradores) · [Atualizar](#8-atualizar-o-sistema) · [Git](#9-conectar-ao-git) ·
[Vercel](#10-publicar-na-vercel) · [Dia a dia](#11-dia-a-dia) · [Airbnb e Booking](#12-airbnb-e-booking) · [Segurança](#13-segurança) · [Problemas](#14-problemas-comuns) · [Estrutura](#15-estrutura-do-projeto)

---

## 1. Telas

| Tela | Endereço | Para quê |
|---|---|---|
| **Hoje** (inicial) | `/` | Chegadas e saídas de hoje e amanhã, quem está na casa, saldos a receber, estado e limpeza de cada quarto, avisos de reservas importadas e conflitos |
| Calendário | `/calendario` | Quartos nas linhas e dias nas colunas; cor por origem (Airbnb, Booking, direto) e faixa amarela para pagamento pendente |
| Calendário Anual | `/anual` | Os 12 meses. Dia livre abre a nova reserva; dia parcialmente ocupado deixa escolher entre reservar ou ver os quartos ocupados; dia lotado abre as reservas daquele dia |
| Reservas | `/reservas` | Hóspede (nome, CPF opcional, telefone), acompanhantes, valor livre por reserva, pagamentos (Pix, dinheiro, débito, crédito, repasse) com comprovante |
| Histórico | `/historico` | Concluídas, em andamento, futuras, canceladas e **lixeira**; busca por nome, CPF ou telefone; filtros por ano e quarto; totais |
| Quartos e Bloqueios | `/quartos` | Cadastro de quartos e bloqueio de datas (manutenção, uso próprio) |
| Insumos e Custos | `/custos` | Gastos com descrição livre e comprovante opcional |
| Relatórios e Gráficos | `/relatorios` | Receita, custos, lucro, ocupação, época do ano, ranking de quartos, origem, formas de pagamento, maiores gastos |
| Airbnb e Booking | `/integracoes` | Sincronização dos calendários (seção 12) |
| Exportar e Backup | `/backup` | CSV para Excel, backup JSON e limpeza de comprovantes sem uso |

Todos os usuários são **administradores**: só entra quem tem o perfil `admin` no banco (seção 7).

## 2. Requisitos

- **Python 3.11 ou mais novo** (o projeto roda no 3.14).
- **Git** (para guardar e publicar o código).
- Uma conta no **Firebase** (plano gratuito basta) e, para publicar, uma conta na **Vercel**.
- Um editor, como o VS Code.

## 3. Configurar o Firebase (uma vez)

Crie um projeto **só para o hotel** em <https://console.firebase.google.com>. Depois:

1. **Authentication** → *Começar* → *E-mail/senha* → ative e salve. Se aparecer, desative a criação de contas por cadastro (Configurações, Ações do usuário).
2. **Realtime Database** → *Criar banco de dados* → modo **bloqueado**. Na aba *Regras*, deixe: `{ "rules": { ".read": false, ".write": false } }`. Só o servidor acessa o banco.
3. **Chave de API da Web**: Configurações do projeto (engrenagem) → *Geral* → *Seus aplicativos* → ícone `</>` → registre um app Web (sem Hosting) e copie o `apiKey` (começa com `AIza`).
4. **Chave de serviço**: Configurações do projeto → *Contas de serviço* → *Gerar nova chave privada*. Salve o arquivo na raiz do projeto com o nome **`firebase-credentials.json`**.
5. **URL do banco**: no topo da tela de dados do Realtime Database (termina em `firebaseio.com` ou `firebasedatabase.app`).

## 4. Instalar e rodar no Ubuntu

```bash
# 1) programas necessários (uma vez)
sudo apt update && sudo apt install -y python3 python3-venv git

# 2) entrar na pasta do projeto e criar o ambiente virtual
cd ~/hotel-sistema
python3 -m venv venv
source venv/bin/activate                 # o prompt passa a começar com (venv)

# 3) instalar as dependências
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt      # opcional: só para rodar os testes

# 4) configurar (veja a seção 6 e coloque o firebase-credentials.json na pasta)
cp .env.example .env
nano .env                                # ou abra no VS Code: code .env

# 5) conferir, criar o administrador e rodar
python3 diagnostico.py                   # explica o que estiver errado
python3 criar_admin.py seuemail@exemplo.com SuaSenha "Seu Nome"
python3 app.py                           # abra http://localhost:5000
```

Nas próximas vezes: `cd ~/hotel-sistema`, `source venv/bin/activate` e `python3 app.py`.

## 5. Instalar e rodar no Windows

Instale o **Python** em <https://www.python.org/downloads> marcando **"Add python.exe to PATH"** na primeira tela, e o **Git** em <https://git-scm.com/download/win>.
Extraia o projeto em uma pasta do seu usuário, como `C:\Users\SEU_NOME\hotel-sistema` (evite a raiz do `C:\`, onde o Windows pode negar a gravação de arquivos).

**Jeito rápido:** dê dois cliques em **`iniciar.bat`**. Na primeira vez ele cria o ambiente e instala as dependências; depois roda o diagnóstico e,
se estiver tudo certo, abre o sistema no navegador. Se houver problema, ele mostra o que corrigir e não abre o sistema.

**Passo a passo manual** (PowerShell, dentro da pasta do projeto):

```powershell
# 1) ambiente virtual
cd $HOME\hotel-sistema
python -m venv venv
venv\Scripts\Activate.ps1                # se o PowerShell bloquear: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
                                         # o prompt passa a começar com (venv)

# 2) dependências
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt      # opcional: só para rodar os testes

# 3) configuração (veja a seção 6 e coloque o firebase-credentials.json na pasta)
copy .env.example .env
notepad .env

# 4) conferir, criar o administrador e rodar
python diagnostico.py
python criar_admin.py seuemail@exemplo.com SuaSenha "Seu Nome"
python app.py                            # abra http://localhost:5000
```

No Windows use `python` (no Ubuntu, `python3`). Em cada terminal novo, reative com `venv\Scripts\Activate.ps1` antes de rodar `python app.py`.

## 6. O arquivo `.env`

Fica na raiz do projeto, **nunca vai para o Git**. Cada linha é `NOME=valor`, sem aspas, sem espaços em volta e sem `<` `>`.

| Variável | O que é | Exemplo |
|---|---|---|
| `SECRET_KEY` | Assina o login. Gere um valor aleatório: `python -c "import secrets; print(secrets.token_hex(32))"` | `9ca2…` (64 caracteres) |
| `FIREBASE_API_KEY` | Chave de API da Web (passo 3 da seção 3) | `AIzaSy…` |
| `FIREBASE_DATABASE_URL` | Endereço do Realtime Database | `https://hotel-xxxxx-default-rtdb.firebaseio.com` |
| `FIREBASE_CREDENTIALS_PATH` | Arquivo da chave de serviço | `firebase-credentials.json` |
| `FIREBASE_CREDENTIALS_JSON` | Opcional: o conteúdo do JSON em uma linha. **Tem prioridade sobre o arquivo**; é o que se usa na Vercel | — |
| `FLASK_DEBUG` | `true` no seu computador, **`false` na Vercel** | `true` |
| `FLASK_HOST` | `127.0.0.1` = só este computador. `0.0.0.0` = acessível por outros aparelhos da rede (o debug é desligado sozinho) | `127.0.0.1` |
| `SESSION_COOKIE_SECURE` | `false` para testar em `http://localhost`. Na Vercel, deixe sem definir | `false` |
| `CRON_SECRET` | Opcional: ativa a sincronização diária com Airbnb e Booking pela Vercel | valor aleatório |

Para abrir pelo celular na mesma rede Wi-Fi: ponha `FLASK_HOST=0.0.0.0`, descubra o IP do computador (`hostname -I` no Ubuntu, `ipconfig` no Windows) e abra `http://SEU_IP:5000`.
No Windows, o firewall pergunta na primeira vez: permita para redes privadas.

## 7. Primeiro acesso: criar administradores

```bash
python3 criar_admin.py email@exemplo.com SenhaForte "Nome"      # Windows: python criar_admin.py ...
```

- Funciona também para um e-mail que já existe no Firebase: atualiza a senha e dá o perfil de administrador (serve para **trocar a senha**).
- Quem tem conta no Firebase mas **não** tem o perfil `admin` não consegue entrar.
- Crie um por pessoa (por exemplo, os dois administradores do hotel).

## 8. Atualizar o sistema

**Pelo Git** (quando as alterações estão no repositório):

```bash
git pull
pip install -r requirements.txt          # só se o requirements.txt mudou
```

**Por arquivo `.patch`** (alterações enviadas em um arquivo):

```bash
# Ubuntu
git apply --check ~/Downloads/arquivo.patch      # só confere; sem mensagem = ok
git apply ~/Downloads/arquivo.patch
```

```powershell
# Windows
git apply --check --ignore-whitespace "$HOME\Downloads\arquivo.patch"
git apply --ignore-whitespace "$HOME\Downloads\arquivo.patch"
```

Se o Git do Windows travar com *"Unlink of file ... failed"* ou o arquivo estiver bloqueado, use o aplicador que vem no projeto. Ele escreve por cima do arquivo,
mantém o final de linha de cada um e pode ser repetido sem problema (o que já foi aplicado é pulado):

```powershell
python aplicar_patch.py "$HOME\Downloads\arquivo.patch" --verificar                      # só confere
python aplicar_patch.py "$HOME\Downloads\arquivo.patch"                                  # aplica
python aplicar_patch.py "$HOME\Downloads\arquivo.patch" --liberar-somente-leitura        # se o erro disser "somente leitura"
```

Depois de aplicar: `python diagnostico.py`, `python app.py` para testar e, se estiver tudo certo, envie ao Git (seção 9).

## 9. Conectar ao Git

Faça uma vez no computador:

```bash
git config --global user.name "Seu Nome"
git config --global user.email "seu@email.com"
```

**Projeto novo, ligado a um repositório vazio do GitHub** (crie antes em github.com/new, privado e sem README):

```bash
cd hotel-sistema
git init -b main
git add .
git status --short                       # CONFIRA a lista (veja o aviso abaixo)
git commit -m "Primeira versão do sistema do hotel"
git remote add origin https://github.com/SEU_USUARIO/hotel.git
git push -u origin main
```

**Repositório que já existe** (outro computador, ou pasta nova):

```bash
git clone https://github.com/SEU_USUARIO/hotel.git
cd hotel
# copie para cá o .env e o firebase-credentials.json (eles não vêm no clone), depois siga a seção 4 ou 5
```

**Todo dia** (dentro da pasta do projeto): `git status --short`, `git add .`, `git commit -m "o que mudou"` e `git push`. A Vercel publica sozinha depois do push.

> **Aviso:** no `git status --short` **não podem aparecer** `.env`, `firebase-credentials.json`, `venv/`, `backups/` nem arquivos `.patch`. O `.gitignore` já os protege; se algum aparecer, não faça o commit.
> Rode os comandos do Git sempre **dentro** da pasta do projeto, nunca em uma pasta acima (isso cria repositórios aninhados).
> Na primeira vez, o GitHub pede login: use o navegador que o Git abre ou, se pedir senha no terminal, um **token de acesso pessoal** (GitHub → Settings → Developer settings → Personal access tokens, permissão `repo`).

## 10. Publicar na Vercel

1. Suba o código para o GitHub (seção 9).
2. Em <https://vercel.com> → *Add New* → *Project* → importe o repositório. O *Framework Preset* é reconhecido como Flask; não mexa em Build, Output nem Install.
3. Em *Environment Variables*, crie:

| Nome | Valor |
|---|---|
| `SECRET_KEY` | um valor aleatório novo (não use o do seu computador) |
| `FIREBASE_API_KEY` | a chave de API da Web |
| `FIREBASE_DATABASE_URL` | o endereço do Realtime Database |
| `FIREBASE_CREDENTIALS_JSON` | o JSON da chave de serviço em **uma linha** (veja abaixo). Marque como *Sensitive* |
| `FLASK_DEBUG` | `false` |
| `CRON_SECRET` | opcional, para a sincronização diária (seção 12) |

Não crie `SESSION_COOKIE_SECURE`: na Vercel o site é HTTPS e o padrão já é o certo.

Para gerar o JSON em uma linha: `python -c "import json; print(json.dumps(json.load(open('firebase-credentials.json'))))"` e copie a saída inteira.

4. Clique em **Deploy**. Abra o endereço mostrado seguido de `/login`.

Se der erro 500: *Deployments* → o deploy → *Logs*. Mudou uma variável? Faça **Redeploy**. O plano *Hobby* da Vercel é para uso não comercial: se o hotel for um negócio, confira os termos ou use o plano pago.

## 11. Dia a dia

| Preciso de… | Comando (Ubuntu / Windows) |
|---|---|
| Descobrir por que não conecta | `python3 diagnostico.py` / `python diagnostico.py` |
| Backup completo, com comprovantes | `python3 backup.py` — cria `backups/AAAA-MM-DD_HHMM/`. Guarde uma cópia fora do computador; a pasta tem dados pessoais |
| Anonimizar reservas antigas (LGPD) | `python3 anonimizar_antigos.py --meses 60` (só simula; acrescente `--aplicar` para gravar). Confirme o prazo com o contador |
| Rodar os testes | `pytest` (precisa de `pip install -r requirements-dev.txt`) |
| Planilha das reservas ou dos custos | aba **Exportar e Backup** |

O `diagnostico.py` confere o `.env`, a chave de serviço (projeto e conta), o relógio do computador, a conexão segura com o Google, se o Google aceita a chave e se o banco responde.
Ele não mostra senhas nem chaves.

## 12. Airbnb e Booking

A aba **Airbnb e Booking** liga o sistema às duas plataformas por **calendário (iCal)**, sem API. O sistema é a central:

- **Entrada:** por quarto, você cola o link de calendário do Airbnb e o do Booking. O sistema lê esses links e cria as reservas como *importadas*, só com as datas e marcadas com "⚠ completar"; você preenche hóspede e valor.
  Bloqueios "Not available" da plataforma viram bloqueios no sistema. Reservas que você já lançou à mão (mesmo quarto, canal e datas) são vinculadas, sem duplicar.
  Se a reserva some do calendário da plataforma (cancelada) e a chegada é futura, ela é cancelada aqui; estadias em andamento nunca são canceladas sozinhas.
- **Saída:** para cada quarto há um link por plataforma ("Entregar ao Airbnb/Booking"), com as reservas diretas, as da outra plataforma e os bloqueios. Não leva nomes nem valores.
  As reservas que vieram de uma plataforma não voltam para ela. Os links têm um token secreto; "Gerar novos links" troca o token.
- **Quando sincroniza:** ao abrir a página Hoje (o que estiver há mais de 30 minutos sem sincronizar), no botão *Sincronizar tudo agora* e, se existir `CRON_SECRET` na Vercel, uma vez por dia.
- **Primeiro uso:** cole os links das plataformas, sincronize, confira a página Hoje e **só depois** cole os links "Entregar" nas plataformas.
- **Limites:** cada plataforma decide de quanto em quanto tempo lê o seu link, então pode haver atraso de algumas horas. Reserva importada que bate com outra aparece em *Conflitos de datas* na página Hoje.
  Nome do hóspede e valor não passam por calendário. Excluir no sistema uma reserva que ainda existe na plataforma não a cancela lá: ela volta na próxima sincronização. Cancele sempre na plataforma.
  Os links das plataformas são tratados como segredos (entram no backup JSON). Só são aceitos links `https`, nunca para a rede interna.

## 13. Segurança

- **Login:** só contas com `perfil: "admin"` entram. Limite de 5 falhas por IP e 10 por e-mail a cada 15 minutos, guardado no banco (só com hashes).
- **Reservas simultâneas:** salvar uma reserva trava o quarto por instantes, então dois administradores nunca passam juntos pela checagem de conflito. Se aparecer *"Outro administrador está salvando..."*, é só repetir.
- **Cabeçalhos de segurança e CSP:** configurados no `app.py`. Por causa da CSP, não use `<script>` nem `onclick=` dentro dos templates; o código vai em `static/js/`.
- **Segredos:** `.env` e `firebase-credentials.json` ficam só no seu computador e na Vercel, nunca no Git, e-mail ou chat. Se vazarem: Firebase → Configurações do projeto → Contas de serviço → *Gerar nova chave privada*;
  troque o arquivo e a variável `FIREBASE_CREDENTIALS_JSON` (faça *Redeploy*); depois apague a chave antiga em *Gerenciar permissões da conta de serviço* → aba *Chaves*. Troque também as senhas dos administradores com `criar_admin.py`.
- **Repositório público?** Só depois de conferir que nenhum segredo passou pelo histórico: `git log --all --oneline -- .env firebase-credentials.json` deve ficar vazio. Todo commit mostra o nome e o e-mail configurados no Git.
- **Dados pessoais:** CPF e dados de acompanhantes (que podem ser menores) pedem aviso ao hóspede, prazo de retenção e controle de quem acessa. Veja `anonimizar_antigos.py`.

## 14. Problemas comuns

| O que aparece | Causa provável e o que fazer |
|---|---|
| *"Erro interno do sistema (código xxxxxxxx)"* | Procure o mesmo código entre colchetes no terminal (ou nos Logs da Vercel) e rode `diagnostico.py` |
| *"O Firebase recusou a chave de serviço"* | A chave foi apagada ou revogada, ou o arquivo é antigo. Gere uma nova (seção 13), troque o `firebase-credentials.json` e reinicie |
| Diagnóstico: *falha de certificado SSL* | Antivírus com verificação de HTTPS ou certificados do Python desatualizados: `pip install --upgrade certifi` e, se continuar, desligue por alguns minutos a verificação de HTTPS do antivírus para testar |
| Erro `404` ao ler o banco | O Realtime Database não foi criado ou a `FIREBASE_DATABASE_URL` está errada |
| *"Esta conta não tem acesso ao sistema"* | A conta existe, mas sem perfil de administrador: rode `criar_admin.py` para ela |
| *"E-mail ou senha incorretos"* com a senha certa | O provedor E-mail/senha não está ativo, a `FIREBASE_API_KEY` é de outro projeto, ou a conta é de outro projeto (por exemplo, a da barbearia) |
| O login não "gruda" em `http://localhost` | Falta `SESSION_COOKIE_SECURE=false` no `.env` |
| *"Muitas tentativas"* | Espere 15 minutos |
| `python` não é reconhecido (Windows) | Reinstale o Python marcando *Add python.exe to PATH*; no Ubuntu use `python3` |
| PowerShell: *execução de scripts desabilitada* | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` e ative o ambiente de novo |
| `git apply`: *Unlink of file ... failed* (Windows) | Use `python aplicar_patch.py` (seção 8); feche o arquivo no editor |
| *"Outro administrador está salvando..."* | Outro salvamento no mesmo quarto estava em andamento: repita |
| Reserva importada "⚠ completar" | Abra a reserva e preencha hóspede e valor |

## 15. Estrutura do projeto

```
hotel-sistema/
├── app.py                  # inicia o sistema, cabeçalhos de segurança e tratamento de erros
├── config.py               # lê o .env
├── api/                    # rotas da API: quartos, reservas, custos, bloqueios, relatórios, exportação, comprovantes, iCal
├── autenticacao/           # login e proteção das páginas
├── paginas/                # rotas das telas
├── servicos/               # Firebase, trava por quarto, limite de login, iCal, sincronização, validações
├── templates/              # páginas HTML
├── static/                 # estilos, JavaScript, ícones e Chart.js (static/vendor)
├── tests/                  # testes automáticos (banco simulado, não usam o Firebase real)
├── criar_admin.py          # cria/atualiza administradores
├── diagnostico.py          # confere a configuração
├── backup.py               # backup completo
├── anonimizar_antigos.py   # anonimização de reservas antigas
├── aplicar_patch.py        # aplica arquivos .patch sem o git (útil no Windows)
├── iniciar.bat             # instala e abre o sistema no Windows (dois cliques)
├── requirements.txt        # dependências do sistema
├── requirements-dev.txt    # dependências dos testes
├── vercel.json             # configuração da Vercel
└── .env.example            # modelo do .env
```

**Dados no Realtime Database:** `quartos`, `reservas`, `custos`, `indisponiveis` (bloqueios), `usuarios`, `comprovantes`, `config`, `ical_estado`, `tentativas` e `bloqueios` (travas curtas).
