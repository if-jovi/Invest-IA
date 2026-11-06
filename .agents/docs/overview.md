# InvestIA — Visão geral

## Objetivo

Apresentar o produto, a audiência, a stack e os domínios em um único arquivo,
suficiente para alguém novo (humano ou agente IA) entender o escopo antes de
aprofundar em `architecture/`, `guides/` e `specs/`.

## Audiência

- **Autor do TCC / devs** — manutenção e evolução do sistema.
- **Assistentes/agentes IA** — cada arquivo tem **Objetivo** + **Audiência** no
  topo e **Referências** para caminhos de código no fim.

## O que é o InvestIA

Sistema web de apoio à decisão para investidores iniciantes em ações da B3,
desenvolvido como TCC. O usuário escolhe um ativo; o sistema busca o histórico
de preços no Yahoo Finance (biblioteca `yfinance`), calcula indicadores
técnicos (RSI, MACD, médias móveis de 20 e 50 períodos) e envia os dados a uma
LLM (OpenRouter com modelo NVIDIA gratuito por padrão; Gemini e Claude
opcionais). A LLM devolve COMPRA, VENDA ou
MANTER, explica o que a empresa faz e justifica a recomendação em linguagem
simples, listando os riscos.

Além da análise, o usuário tem login, uma carteira (compras, vendas e preço
médio, com cotação atual) e um backtesting da estratégia MACD + RSI comparado
ao buy and hold. A recomendação é apoio à decisão, nunca garantia de retorno.

## Stack resumido

- **Interface**: Streamlit ([`src/public/`](../../src/public/))
- **Regra de negócio**: Python 3.11, controllers + services
  ([`src/controllers/`](../../src/controllers/),
  [`src/models/services/`](../../src/models/services/))
- **Persistência**: PostgreSQL 16 via SQLAlchemy 2
  ([`src/models/entities/`](../../src/models/entities/),
  [`schema.sql`](../../schema.sql))
- **Integrações**: Yahoo Finance (`yfinance`), OpenRouter (modelos NVIDIA
  `:free`, via `httpx`), Google Gemini (`google-genai`), Anthropic Claude
  (`anthropic`); lista de ações da B3 obtida da brapi.dev (só no script de
  atualização do catálogo)
- **Deploy**: Docker Compose com app, banco e pgAdmin
  ([`docker-compose.yml`](../../docker-compose.yml))

## Padrão arquitetural vigente

MVC em camadas: View (Streamlit) → Controller (validação de entrada) →
Service (regra de negócio e banco) → Entity (tabelas SQLAlchemy). Detalhes em
[`architecture/overview.md`](./architecture/overview.md).

## Domínios principais

| Domínio            | Foco                                              | Doc |
| ------------------ | ------------------------------------------------- | --- |
| Catálogo de ativos | Ativos da B3 pré-cadastrados e sugeridos nas telas | [`specs/catalogo-ativos.md`](./specs/catalogo-ativos.md) |
| Interface          | Tema, navegação, formatação pt-BR, telas           | [`specs/interface.md`](./specs/interface.md) |
| Análise com IA     | Indicadores técnicos + recomendação da LLM (JSON)  | [`specs/analise-ia.md`](./specs/analise-ia.md) |
| Análise múltipla   | Até 5 ativos por vez, quadro comparativo           | [`specs/analise-multipla.md`](./specs/analise-multipla.md) |
| Provedor de IA     | OpenRouter + NVIDIA Nemotron gratuito (padrão)     | [`specs/provedor-openrouter.md`](./specs/provedor-openrouter.md) |
| Backtesting        | MACD + RSI vs buy and hold, custos, Sharpe anual.  | [`specs/backtesting.md`](./specs/backtesting.md) |
| Persistência       | Migrações Alembic, tipos e consultas               | [`specs/persistencia.md`](./specs/persistencia.md) |
| Autenticação       | Cadastro e login (PBKDF2)                          | TODO |
| Carteira           | Posições, preço médio, cotação atualizada          | [`specs/carteira.md`](./specs/carteira.md) |
| Aquecimento        | Pregões extras para os indicadores                 | [`specs/historico-aquecimento.md`](./specs/historico-aquecimento.md) |
| Ibovespa           | Comparação do ativo com o mercado                  | [`specs/comparacao-ibovespa.md`](./specs/comparacao-ibovespa.md) |
| Desempenho da IA   | Taxa de acerto, margem de erro, teste estatístico  | [`specs/desempenho-ia.md`](./specs/desempenho-ia.md) |

## Glossário

| Termo       | Significado |
| ----------- | ----------- |
| Item / ativo | Código de negociação na B3, ex.: `PETR4` (sem o sufixo `.SA` do Yahoo) |
| Catálogo    | Tabela `itens_b3`: ativos conhecidos pelo sistema |
| RSI         | Índice de força relativa (14 períodos); >70 sobrecompra, <30 sobrevenda |
| MACD        | Diferença entre médias exponenciais de 12 e 26 períodos, com sinal de 9 |
| SMA         | Média móvel simples (20 e 50 períodos) |

## Referências

- Ponto de entrada: [`src/public/Main.py`](../../src/public/Main.py)
- Configuração: [`config/settings.py`](../../config/settings.py),
  [`.env.example`](../../.env.example)
- Instruções de uso: [`README.md`](../../README.md)
