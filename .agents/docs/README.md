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
  ([`overview.md`](./architecture/overview.md)).
- [`guides/`](./guides/) — guias operacionais
  ([`getting-started.md`](./guides/getting-started.md)).
- [`specs/`](./specs/) — especificações funcionais por domínio:
  - [`catalogo-ativos.md`](./specs/catalogo-ativos.md) — catálogo de ativos da
    B3 (seed) e sugestão de ativos nas telas de Análise e Backtesting.
  - [`interface.md`](./specs/interface.md) — tema, navegação, formatação pt-BR
    e telas; atualização do Streamlit.
  - [`analise-ia.md`](./specs/analise-ia.md) — contrato JSON da resposta da IA.
  - [`backtesting.md`](./specs/backtesting.md) — métricas (índice de Sharpe).
  - [`persistencia.md`](./specs/persistencia.md) — migrações Alembic e consultas.

TODO: specs completas de autenticação e carteira (hoje só cobertas
indiretamente por `interface.md`).

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
