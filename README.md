# InvestIA

Sistema de apoio à decisão para investidores iniciantes em ações da B3, desenvolvido
como TCC. O usuário escolhe uma ação; o sistema busca o histórico de preços no Yahoo
Finance, calcula indicadores técnicos (RSI, MACD e médias móveis de 20 e 50 períodos)
e envia tudo para uma IA (por padrão um modelo **NVIDIA Nemotron gratuito via
OpenRouter**; Gemini e Claude são opcionais). A IA responde **COMPRA**,
**VENDA** ou **MANTER** e explica em linguagem simples o que a empresa faz, por que os
indicadores apontam para essa decisão e quais são os riscos.

Dá para analisar **até 5 ações de uma vez**, com um quadro comparativo. Os campos de
ativo têm **autocomplete** com as ~377 ações da B3. Também há login, uma carteira com
**cotação atualizada a cada minuto** (Yahoo Finance, atraso de até 15 min) e um
backtesting da estratégia MACD + RSI comparado ao buy and hold.

> As recomendações são apoio à decisão para fins acadêmicos e não garantem retorno.

---

## Sumário

1. [Pré-requisitos](#1-pré-requisitos)
2. [Instalação passo a passo](#2-instalação-passo-a-passo)
3. [Banco de dados e pgAdmin](#3-banco-de-dados-e-pgadmin)
4. [Testes](#4-testes)
5. [Diagnóstico das integrações](#5-diagnóstico-das-integrações)
6. [Comandos do dia a dia](#6-comandos-do-dia-a-dia)
7. [Acessando de fora (túnel público)](#7-acessando-de-fora-túnel-público)
8. [Problemas comuns](#8-problemas-comuns)
9. [Estrutura do projeto](#9-estrutura-do-projeto)

---

## 1. Pré-requisitos

| Ferramenta | Para quê |
| ---------- | -------- |
| [Git](https://git-scm.com/) | clonar o repositório |
| [Docker](https://docs.docker.com/get-docker/) com Docker Compose v2 | rodar app, banco e pgAdmin |
| Chave da API do OpenRouter | gerar as recomendações com modelo gratuito ([openrouter.ai/keys](https://openrouter.ai/keys)) |

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
   OPENROUTER_API_KEY=cole_sua_chave_aqui
   ```

   As demais variáveis já vêm com valores que funcionam no Docker. Só modelos
   gratuitos (terminados em `:free`) são aceitos; na conta gratuita o OpenRouter
   limita a cerca de 50 análises por dia (a recomendação do mesmo ativo no mesmo dia
   é reaproveitada e não conta de novo).

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
  `operacoes`, `recomendacoes`) quando é iniciado e carrega o catálogo de ações
  (`itens_b3`) a partir de [`src/data/ativos_b3.json`](src/data/ativos_b3.json), sem
  acessar a internet.

### Atualizando a lista de ações da B3

O arquivo `src/data/ativos_b3.json` é gerado a partir da API pública da
[brapi.dev](https://brapi.dev). Para atualizá-lo (raramente necessário):

```sh
docker compose exec app python -m src.scripts.AtualizarCatalogoB3
docker compose exec app python -m src.scripts.SeedItensB3   # grava as novas no banco
```

Se a brapi falhar, o arquivo atual não é alterado.

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
[PASSOU] Integração com o OpenRouter
[PASSOU] Catálogo de ativos da B3
[PASSOU] Análise de vários ativos
[PASSOU] Tema, paleta e formatação
[PASSOU] Interface Streamlit de ponta a ponta

9/9 baterias passaram
```

Os testes **não acessam a internet nem gastam créditos da IA**: usam um banco SQLite
temporário e simulam o Yahoo Finance, o OpenRouter, o Gemini, o Claude e a brapi. Também não tocam no banco
PostgreSQL do sistema.

Para rodar uma bateria isolada:

```sh
docker compose exec app python tests/teste_logica.py
```

| Bateria | O que cobre |
| ------- | ----------- |
| `teste_logica.py` | cadastro, login, carteira (variação do dia), compra/venda, cache da IA, backtest, horário de Brasília |
| `teste_yfinance.py` | yfinance com respostas simuladas: histórico, 429, rede fora, ticker inexistente e cotações em lote com cache |
| `teste_openrouter.py` | OpenRouter com transporte HTTP simulado (modelo `:free`, 401, 402, 404, 429, 5xx, timeout) |
| `teste_catalogo.py` | catálogo da B3: JSON versionado, seed offline, script da brapi |
| `teste_analise_multipla.py` | análise de até 5 ativos, falha isolada, 2 em paralelo, cache |
| `teste_estilo.py` | dependências, tema, paleta, formatação pt-BR, gráficos |
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
| Abrir o app fora da máquina (túnel) | `docker compose --profile tunnel up -d ngrok` |

O código fica montado no container (`.:/app`): alterações nos arquivos `.py` aparecem
ao recarregar a página do Streamlit.

## 7. Acessando de fora (túnel público)

Para abrir o InvestIA no celular, mostrar ao orientador ou projetar um QR code na
apresentação, o app precisa de um endereço público. Há dois serviços de túnel no
`docker-compose.yml`; **nenhum dos dois sobe no `docker compose up` normal** — eles
usam *profiles* e só iniciam quando chamados.

Quem acessa o link **não** precisa estar na mesma rede do servidor: o tráfego passa
pela nuvem do serviço de túnel até o container `app`.

### ngrok (URL fixa)

1. Crie a conta em [ngrok.com](https://dashboard.ngrok.com/signup) e copie o token em
   [dashboard.ngrok.com/get-started/your-authtoken](https://dashboard.ngrok.com/get-started/your-authtoken).
2. Reserve o domínio gratuito em [dashboard.ngrok.com/domains](https://dashboard.ngrok.com/domains).
   O plano Free inclui **um** domínio estático, com nome gerado pelo próprio ngrok —
   não dá para escolher as palavras (isso é recurso de plano pago, `ERR_NGROK_313`).
3. Preencha o `.env`:

   ```
   NGROK_AUTHTOKEN=cole_o_token_aqui
   NGROK_DOMAIN=nome-gerado.ngrok-free.dev
   ```

   Sem `NGROK_DOMAIN`, o túnel sobe com uma URL aleatória que muda a cada reinício.

4. Suba e confira a URL:

   ```sh
   docker compose --profile tunnel up -d ngrok
   docker compose --profile tunnel logs ngrok
   ```

   A linha `url=https://...` é o endereço público.

5. O inspetor de requisições fica em http://localhost:4040.

Para parar: `docker compose --profile tunnel stop ngrok`.

No plano gratuito, a **primeira visita de cada navegador** mostra uma página do ngrok
("You are about to visit…"); basta clicar em **Visit Site**. Também é permitida apenas
**uma sessão** de agente por vez: se houver outro ngrok aberto na máquina, o container
falha com `ERR_NGROK_108`.

### Gerar um QR code da URL

```sh
python -m pip install --user "qrcode[pil]"
```

```python
import qrcode

qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_Q, box_size=20, border=4)
qr.add_data("https://SEU-ENDERECO")
qr.make(fit=True)
qr.make_image().save("qrcode.png")   # ~900 px; use box_size maior para telão
```

Para slide, gere também em SVG (vetorial, não serrilha):
`qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage).save("qrcode.svg")`.

### Cuidados

| Ponto | Por quê |
| ----- | ------- |
| **Não tunele o pgAdmin (5051)** | ele está com `admin`/`admin`; expor isso é entregar o banco |
| Pare o túnel quando não estiver usando | qualquer pessoa com o link chega ao login e consome a cota da IA |
| Deixe o notebook ligado e sem suspender | o app roda na sua máquina, não na nuvem |
| Evite divulgar o link publicamente | o cadastro é aberto e cada visitante abre uma sessão Streamlit |
| Não commite o `.env` | já está no `.gitignore`; ele guarda o token e a chave da IA |

## 8. Problemas comuns

| Sintoma | Causa e solução |
| ------- | --------------- |
| `port is already allocated` ao subir | outra aplicação usa a 8501 ou a 5051. Pare-a ou troque a porta da esquerda em `docker-compose.yml` (ex.: `"8502:8501"`). |
| "Limite de uso do modelo gratuito atingido no OpenRouter" | limite do plano gratuito (por minuto e por dia). Aguarde ou analise menos ativos de uma vez. |
| "Apenas modelos gratuitos do OpenRouter são permitidos" | `OPENROUTER_MODEL` precisa terminar em `:free`. |
| "O projeto desta chave do Gemini não tem acesso ao plano gratuito" | o projeto Google da chave exige faturamento. Ative em https://aistudio.google.com/billing ou gere a chave em outro projeto. |
| "O modelo '...' não foi encontrado" | defina um modelo disponível em `GEMINI_MODEL` no `.env` e rode `docker compose restart app`. |
| "Limite de uso do Gemini atingido" | limite do plano gratuito; aguarde cerca de um minuto. |
| "O Yahoo Finance limitou as requisições (erro 429)" | aguarde alguns minutos. |
| "Não foi possível conectar ao banco de dados" | verifique `docker compose ps`; o `db` precisa estar `healthy`. |
| Servidor não aparece no pgAdmin | o `servers.json` só é importado na primeira subida do pgAdmin. Rode `docker compose up -d --force-recreate -V pgadmin` ou cadastre manualmente (seção 3). |
| `ERR_NGROK_313` ao subir o túnel | `NGROK_DOMAIN` tem um subdomínio escolhido à mão. No plano gratuito só funciona o domínio atribuído em [dashboard.ngrok.com/domains](https://dashboard.ngrok.com/domains) |
| `ERR_NGROK_108` | já existe uma sessão do ngrok aberta nesta máquina; pare a outra antes de subir o container |
| Streamlit fica em "Please wait…" pelo túnel | WebSocket comprimido: acrescente `[server]` com `enableWebsocketCompression = false` ao `.streamlit/config.toml` e rode `docker compose restart app` |

### Variáveis do `.env`

| Variável | Padrão | Uso |
| -------- | ------ | --- |
| `IA_PROVEDOR` | `openrouter` | `openrouter`, `gemini` ou `claude` |
| `OPENROUTER_API_KEY` | — | chave do OpenRouter |
| `OPENROUTER_MODEL` | `nvidia/nemotron-3.5-super-vl:free` | modelo gratuito (precisa terminar em `:free`) |
| `GEMINI_API_KEY` | — | só com `IA_PROVEDOR=gemini` |
| `GEMINI_MODEL` | `gemini-3.8-flash` | modelo do Gemini |
| `ANTHROPIC_API_KEY` | — | só com `IA_PROVEDOR=claude` |
| `CLAUDE_MODEL` | `claude-sonnet-5-5` | modelo do Claude |
| `NGROK_AUTHTOKEN` | — | token do ngrok; usado só pelo serviço de túnel |
| `NGROK_DOMAIN` | — | domínio fixo do ngrok; vazio = URL aleatória a cada início |
| `DB_*` | `postgres`/`invest_ia` | conexão com o banco (no Docker, o `docker-compose.yml` já define) |

## 9. Estrutura do projeto

```
src/
  controllers/   validam a entrada (Auth, Carteira, ItensCarteira, Analise, Backtest)
  models/
    base.py      conexão, sessão, horário de Brasília e criarTabelas()
    entities/    tabelas SQLAlchemy + dados temporários do yfinance
    services/    regra de negócio: Yahoo, indicadores, IA (OpenRouter/Gemini/Claude), carteira, backtest
  data/          ativos_b3.json (lista de ações da B3)
  public/
    Main.py      ponto de entrada do Streamlit (login + navegação)
    paginas/     páginas do menu: carteira, analise, backtesting
    views/       telas, Estilo (paleta/CSS), Seletores (autocomplete), gráficos
  scripts/       Diagnostico, SeedItensB3 e AtualizarCatalogoB3
.streamlit/      tema (config.toml)
tests/           baterias automatizadas
docker/          configuração do pgAdmin
```

Fluxo: **View → Controller → Service → Entity**.

---

Projeto acadêmico desenvolvido como Trabalho de Conclusão de Curso. Todos os
direitos reservados ao autor.
