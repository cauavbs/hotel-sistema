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

## Rodar no Windows (PowerShell, na pasta do projeto)

```powershell
python -m venv venv
venv\Scripts\Activate.ps1          # se o PowerShell bloquear: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt
copy .env.example .env             # depois edite o .env (veja os comentários dentro dele)
python criar_admin.py email senha "Nome"
python app.py                      # http://localhost:5000
python diagnostico.py              # se o login der erro: explica o que está errado na configuração
```

No Windows use `python` (não `python3`). Para testar em `http://localhost` ponha `SESSION_COOKIE_SECURE=false` no `.env`.
Os testes: `pip install -r requirements-dev.txt` e depois `pytest`.

## Se o login der "Erro interno" ou "Não foi possível conectar"
Rode `python diagnostico.py`. Ele confere o `.env`, a chave de serviço (projeto e conta), o relógio do computador, se o Google aceita a chave
e se o banco responde, e diz o que corrigir. Os motivos mais comuns: chave de serviço antiga ou apagada (gere outra), chave de outro projeto,
relógio fora de hora e Realtime Database não criado.
