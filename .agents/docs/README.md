# Documentação do InvestIA

Documentação interna do InvestIA (sistema de recomendação de ações da B3 com
análise técnica interpretada por IA — TCC), organizada em estilo
**Spec-Driven Development (SDD)**: as especificações descrevem o
comportamento esperado e direcionam a evolução do código. Quando código e
spec divergem, um dos dois precisa ser corrigido (e o commit/PR deve
registrar qual). `.agents/docs` indica que a estrutura também foi pensada para
consumo por agentes/assistentes IA.

## Estrutura

- [`overview.md`](./overview.md) — produto, audiência, stack e domínios.
- [`architecture/`](./architecture/) — arquitetura atual
  ([`overview.md`](./architecture/overview.md)) e relatório completo de como o sistema
  funciona hoje ([`relatorio-sistema.md`](./architecture/relatorio-sistema.md)).
- [`guides/`](./guides/) — guias operacionais
  ([`getting-started.md`](./guides/getting-started.md)).
- [`specs/`](./specs/) — especificações funcionais por domínio:
  - [`catalogo-ativos.md`](./specs/catalogo-ativos.md) — catálogo completo de
    ações da B3 (JSON da brapi, seed offline) e autocomplete dos campos de ativo.
  - [`interface.md`](./specs/interface.md) — paleta, login, dashboard,
    navegação, formatação pt-BR; atualização do Streamlit.
  - [`carteira.md`](./specs/carteira.md) — cotação atualizada (yfinance em
    lote, cache curto, atualização automática) e variação do dia.
  - [`analise-multipla.md`](./specs/analise-multipla.md) — análise de até 5
    ativos de uma vez, com quadro comparativo.
  - [`provedor-openrouter.md`](./specs/provedor-openrouter.md) — OpenRouter
    com modelos NVIDIA gratuitos como provedor padrão de IA.
  - [`analise-ia.md`](./specs/analise-ia.md) — contrato JSON da resposta da IA.
  - [`analise-periodo.md`](./specs/analise-periodo.md) — resumo do período no
    prompt da IA e cache por ativo + data + período.
  - [`backtesting.md`](./specs/backtesting.md) — Sharpe anualizado, custos da
    B3 e posição aberta no fim.
  - [`historico-aquecimento.md`](./specs/historico-aquecimento.md) — pregões
    extras antes do período para o cálculo dos indicadores.
  - [`comparacao-ibovespa.md`](./specs/comparacao-ibovespa.md) — retorno do
    ativo comparado ao Ibovespa (análise, prompt e backtesting).
  - [`desempenho-ia.md`](./specs/desempenho-ia.md) — taxa de acerto das
    recomendações da IA (avaliação histórica e uso no app).
  - [`persistencia.md`](./specs/persistencia.md) — migrações Alembic e consultas.

TODO: spec completa de autenticação (hoje coberta indiretamente por
`interface.md`).

## Como contribuir

Ao alterar código que muda comportamento observável, atualize a spec
correspondente no mesmo commit/PR. Fluxo: View → Controller → Service →
Entity (ver [`architecture/overview.md`](./architecture/overview.md)).

## Convenções de estilo (todos os arquivos)

- Idioma: pt-BR. Identificadores seguem o código (camelCase em português).
- Cada arquivo começa com **Objetivo / Audiência**.
- Cada arquivo termina com **Referências** apontando para caminhos de código.
- Diagramas só quando esclarecem; preferir prosa curta.

## Verificação de integridade

Para checar se nenhum link relativo dentro de `.agents/docs/**/*.md` aponta
para arquivo inexistente, rode na raiz do repositório:

```sh
find .agents/docs -name '*.md' | while read f; do
  dir=$(dirname "$f")
  grep -oE '\]\([^)]+\)' "$f" | sed -E 's/^\]\(([^)]+)\)$/\1/' | \
  while read link; do
    case "$link" in
      http://*|https://*|mailto:*|tel:*|\#*) continue ;;
    esac
    target="${link%#*}"
    target="${target%\?*}"
    [ -z "$target" ] && continue
    [ ! -e "$dir/$target" ] && echo "BROKEN: $f → $link"
  done
done
```

Saída vazia = todos os links resolvem.
