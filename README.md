# InvestIA

Sistema de apoio à decisão para investidores iniciantes em ações da B3, desenvolvido
como TCC. O usuário escolhe uma ação; o sistema busca o histórico de preços no Yahoo
Finance, calcula indicadores técnicos (RSI, MACD e médias móveis de 20 e 50 períodos)
e envia tudo para uma IA (Gemini por padrão, ou Claude). A IA responde **COMPRA**,
**VENDA** ou **MANTER** e explica em linguagem simples o que a empresa faz, por que os
indicadores apontam para essa decisão e quais são os riscos.

Também há login, uma carteira de ações com cotação atual e um backtesting da estratégia
MACD + RSI comparado ao buy and hold.

> As recomendações são apoio à decisão para fins acadêmicos e não garantem retorno.

---

## Sumário

1. [Pré-requisitos](#1-pré-requisitos)
2. [Instalação passo a passo](#2-instalação-passo-a-passo)
3. [Banco de dados e pgAdmin](#3-banco-de-dados-e-pgadmin)
4. [Testes](#4-testes)
5. [Diagnóstico das integrações](#5-diagnóstico-das-integrações)
6. [Comandos do dia a dia](#6-comandos-do-dia-a-dia)
7. [Problemas comuns](#7-problemas-comuns)
8. [Estrutura do projeto](#8-estrutura-do-projeto)

---

## 1. Pré-requisitos

| Ferramenta | Para quê |
| ---------- | -------- |
| [Git](https://git-scm.com/) | clonar o repositório |
| [Docker](https://docs.docker.com/get-docker/) com Docker Compose v2 | rodar app, banco e pgAdmin |
| Chave da API do Gemini | gerar as recomendações ([Google AI Studio](https://aistudio.google.com/apikey)) |

Não é preciso instalar Python nem PostgreSQL na máquina: tudo roda em containers.

## 2. Instalação passo a passo

```sh
# 1. Clonar (a branch principal é a master)
git clone https://github.com/if-jovi/Invest-IA.git
cd Invest-IA

# 2. Criar o arquivo de configuração a partir do exemplo
cp .env.example .env
```

3. Abra o `.env` e preencha a chave:

   ```
   GEMINI_API_KEY=cole_sua_chave_aqui
   ```

   As demais variáveis já vêm com valores que funcionam no Docker.

4. Suba os containers:

   ```sh
   docker compose up -d --build
   ```

   Na primeira vez o build leva alguns minutos (instala as dependências Python).

5. Acesse:

   | Serviço | Endereço | Login |
   | ------- | -------- | ----- |
   | InvestIA | http://localhost:8501 | crie uma conta na aba **Criar conta** |
   | pgAdmin | http://localhost:5051 | `admin@admin.com` / `admin` |

O projeto sobe isolado de outros ambientes Docker da máquina: projeto Compose
`invest-ia`, containers `invest_ia_*`, rede e volume próprios. O PostgreSQL **não**
expõe porta no host, então não conflita com outro Postgres na 5432.

## 3. Banco de dados e pgAdmin

### O banco é criado sozinho

Você **não** precisa criar banco nem tabelas manualmente:

- o container `db` (PostgreSQL 16) cria o banco `invest_ia` na primeira subida;
- o app cria as tabelas (`usuarios`, `carteiras`, `itens_b3`, `itens_carteiras`,
  `operacoes`, `recomendacoes`) quando é iniciado.

Os dados ficam no volume Docker `invest-ia_postgres_data` e sobrevivem a
`docker compose down`/`up`.

### Acessando pelo pgAdmin

O servidor já vem cadastrado (arquivo [`docker/pgadmin/servers.json`](docker/pgadmin/servers.json)):

1. Abra http://localhost:5051 e entre com `admin@admin.com` / `admin`.
2. No painel à esquerda, expanda **Servers → InvestIA → InvestIA (Docker)**.
3. Quando pedir a senha do banco, digite `postgres` (marque *Save password* para não
   pedir de novo).
4. As tabelas ficam em **Databases → invest_ia → Schemas → public → Tables**.
5. Para consultas, clique com o botão direito em `invest_ia` → **Query Tool**, por exemplo:

   ```sql
   SELECT item, recomendacao, data_referencia, gerado_em
   FROM recomendacoes
   ORDER BY gerado_em DESC;
   ```

### Cadastrando o servidor manualmente (se ele não aparecer)

Clique com o botão direito em **Servers → Register → Server...** e preencha:

| Aba | Campo | Valor |
| --- | ----- | ----- |
| General | Name | `InvestIA` |
| Connection | Host name/address | `db` |
| Connection | Port | `5432` |
| Connection | Maintenance database | `invest_ia` |
| Connection | Username | `postgres` |
| Connection | Password | `postgres` |

O host é `db` (nome do serviço no Docker), **não** `localhost`: o pgAdmin roda dentro
da mesma rede Docker que o banco.

### Pelo terminal (sem pgAdmin)

```sh
docker compose exec db psql -U postgres -d invest_ia
```

### Zerar o banco

Apaga **todos** os dados (usuários, carteiras, recomendações):

```sh
docker compose down -v
docker compose up -d
```

O script [`schema.sql`](schema.sql) documenta a estrutura das tabelas; não é preciso
rodá-lo.

## 4. Testes

Com os containers rodando:

```sh
docker compose exec app python -m tests.executar_todos
```

Saída esperada:

```
[PASSOU] Regras de negócio e banco de dados
[PASSOU] Integração com o yfinance
[PASSOU] Integração com a API da Claude
[PASSOU] Integração com a API do Gemini
[PASSOU] Interface Streamlit de ponta a ponta

5/5 baterias passaram
```

Os testes **não acessam a internet nem gastam créditos da IA**: usam um banco SQLite
temporário e simulam o Yahoo Finance, o Gemini e o Claude. Também não tocam no banco
PostgreSQL do sistema.

Para rodar uma bateria isolada:

```sh
docker compose exec app python tests/teste_logica.py
```

| Bateria | O que cobre |
| ------- | ----------- |
| `teste_logica.py` | cadastro, login, carteira, compra/venda, cache da IA, backtest, horário de Brasília |
| `teste_yfinance.py` | biblioteca yfinance real com respostas HTTP simuladas (sucesso, 429, rede fora, ticker inexistente) |
| `teste_claude.py` | SDK da Anthropic contra um servidor local (401, 403, 404, 429, 500, timeout, formato) |
| `teste_gemini.py` | SDK do Gemini com cliente simulado (resposta, formato inválido, bloqueio, erros da API) |
| `teste_interface.py` | o app Streamlit inteiro (AppTest), do cadastro ao backtesting |

## 5. Diagnóstico das integrações

Os testes usam simulações; para conferir as conexões **reais** (banco, Yahoo e a IA
com a sua chave):

```sh
docker compose exec app python -m src.scripts.Diagnostico
docker compose exec app python -m src.scripts.Diagnostico --completo
```

Cada etapa mostra `[ OK ]` ou `[FALHA]` com a dica de correção. Com `--completo`,
roda uma análise inteira da PETR4 (faz uma chamada real à IA).

## 6. Comandos do dia a dia

| Ação | Comando |
| ---- | ------- |
| Subir | `docker compose up -d` |
| Parar | `docker compose down` |
| Ver logs do app | `docker compose logs -f app` |
| Reiniciar o app após mudar o `.env` | `docker compose restart app` |
| Rebuild após mudar `requirements.txt` | `docker compose up -d --build` |

O código fica montado no container (`.:/app`): alterações nos arquivos `.py` aparecem
ao recarregar a página do Streamlit.

## 7. Problemas comuns

| Sintoma | Causa e solução |
| ------- | --------------- |
| `port is already allocated` ao subir | outra aplicação usa a 8501 ou a 5051. Pare-a ou troque a porta da esquerda em `docker-compose.yml` (ex.: `"8502:8501"`). |
| "O projeto desta chave do Gemini não tem acesso ao plano gratuito" | o projeto Google da chave exige faturamento. Ative em https://aistudio.google.com/billing ou gere a chave em outro projeto. |
| "O modelo '...' não foi encontrado" | defina um modelo disponível em `GEMINI_MODEL` no `.env` e rode `docker compose restart app`. |
| "Limite de uso do Gemini atingido" | limite do plano gratuito; aguarde cerca de um minuto. |
| "O Yahoo Finance limitou as requisições (erro 429)" | aguarde alguns minutos. |
| "Não foi possível conectar ao banco de dados" | verifique `docker compose ps`; o `db` precisa estar `healthy`. |
| Servidor não aparece no pgAdmin | o `servers.json` só é importado na primeira subida do pgAdmin. Rode `docker compose up -d --force-recreate -V pgadmin` ou cadastre manualmente (seção 3). |

### Variáveis do `.env`

| Variável | Padrão | Uso |
| -------- | ------ | --- |
| `IA_PROVEDOR` | `gemini` | `gemini` ou `claude` |
| `GEMINI_API_KEY` | — | chave do Google AI Studio |
| `GEMINI_MODEL` | `gemini-3.8-flash` | modelo do Gemini |
| `ANTHROPIC_API_KEY` | — | só com `IA_PROVEDOR=claude` |
| `CLAUDE_MODEL` | `claude-sonnet-5-5` | modelo do Claude |
| `DB_*` | `postgres`/`invest_ia` | conexão com o banco (no Docker, o `docker-compose.yml` já define) |

## 8. Estrutura do projeto

```
src/
  controllers/   validam a entrada (Auth, Carteira, ItensCarteira, Analise, Backtest)
  models/
    base.py      conexão, sessão, horário de Brasília e criarTabelas()
    entities/    tabelas SQLAlchemy + dados temporários do yfinance
    services/    regra de negócio: Yahoo, indicadores, IA (Gemini/Claude), carteira, backtest
  public/
    Main.py      ponto de entrada do Streamlit
    views/       telas: Login, Carteira, Análise, Backtesting, gráficos
  scripts/       Diagnostico e SeedItensB3
tests/           baterias automatizadas
docker/          configuração do pgAdmin
.agents/docs/    documentação técnica e especificações (SDD)
```

Fluxo: **View → Controller → Service → Entity**. Detalhes em
[`.agents/docs/`](.agents/docs/README.md).
