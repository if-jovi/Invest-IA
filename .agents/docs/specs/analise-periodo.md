# Spec — Análise considerando o período escolhido

## Objetivo

Fazer o período escolhido na análise (3 meses, 6 meses, 1 ano, 2 anos)
influenciar de fato a recomendação: a IA passa a receber um resumo do
comportamento do ativo no período, e o cache de recomendações passa a
diferenciar períodos.

## Audiência

- **Autor / devs** — critérios de aceite para implementar e testar.
- **Assistentes/agentes IA** — definição do resumo do período e da chave do cache.

---

> **Status:** implementada em 06/11/2026 (PE1–PE9 e PE11 em
> `tests/teste_analise_periodo.py`, PE10 em `tests/teste_interface.py`).
>
> - **Resumo:** `IndicatorsService.resumirPeriodo(historico)`, preenchido por
>   `calcular(item, historico, periodo)` em `ind.periodo` e `ind.resumo_periodo`.
> - **Cache:** `RecomendacoesService.buscarPorItemDataEPeriodo`.
> - **Banco:** migração `0004`, com o índice `ix_recomendacoes_item_data_periodo`.
>   A migração em PostgreSQL e SQLite (PE7) é coberta por `teste_persistencia.py`.
> - **Rótulos:** `Parametros.ROTULOS_PERIODO`.
> - **Na tela:** bloco "Comportamento em <período>", com Retorno no período,
>   Máxima do período, Mínima do período, Volatilidade anualizada e Drawdown
>   máximo.

## Contexto atual (antes da implementação)

Funcionamento completo do sistema hoje (seção 8 = análise):
[`architecture/relatorio-sistema.md`](../architecture/relatorio-sistema.md). Em resumo:

- `AnaliseService.analisar` busca o histórico do período, mas
  `IndicatorsService.calcular` descarta os ~50 primeiros pregões (`dropna`
  para a SMA50) e a IA recebe só os indicadores do **último dia** (RSI, MACD,
  SMA20/50). Como esses indicadores dependem de janelas curtas, a
  recomendação praticamente não muda com o período.
- O cache (`RecomendacoesService.buscarPorItemEData`) usa **ativo + data de
  referência**: uma análise de 3 meses no mesmo dia reaproveita a de 1 ano.
- A "Variação no período" exibida na tela (`AnaliseView.variacaoPeriodo`) é
  calculada sobre o histórico já cortado pelo `dropna`: com 3 meses ela cobre
  só uns 12 pregões, não o período escolhido.

## Escopo

**Entra:**

1. Resumo do período calculado sobre o histórico **completo** do período
   (antes do `dropna`), com as métricas definidas abaixo.
2. Resumo e horizonte (rótulo do período) incluídos no prompt da IA, com a
   instrução de considerar esse horizonte na recomendação.
3. Coluna `periodo` em `recomendacoes`, gravada em cada recomendação nova.
4. Cache por **ativo + data de referência + período**.
5. Tela de análise: "Variação no período" passa a usar o retorno do resumo;
   o detalhe do ativo mostra o resumo do período; o histórico de
   recomendações mostra o período de cada uma.

**Fica de fora:**

- Persistir as métricas do resumo (só o `periodo` é gravado).
- Mudar a estratégia ou as métricas do backtesting.
- Buscar dias extras de "aquecimento" para os indicadores técnicos.
- O contrato JSON da resposta ([`analise-ia.md`](./analise-ia.md)); esta spec
  só acrescenta conteúdo ao prompt e vale para qualquer formato de resposta.

**Pré-requisito:** [`persistencia.md`](./persistencia.md) implementada
(Alembic). A coluna nova entra como uma migração dessa cadeia.

## Definição do resumo do período

Calculado sobre os fechamentos (`Close`) dos pregões do período, do primeiro
ao último. Os pregões de aquecimento dos indicadores não entram (ver
[`historico-aquecimento.md`](./historico-aquecimento.md), revisão de
06/11/2026). Valores em %,
arredondados a 2 casas.

| Métrica | Definição |
| ------- | --------- |
| `retornoPct` | `(último / primeiro − 1) × 100` |
| `maxima` / `minima` | maior e menor fechamento do período (R$, 2 casas) |
| `distanciaMaximaPct` | `(último / máxima − 1) × 100` (≤ 0) |
| `distanciaMinimaPct` | `(último / mínima − 1) × 100` (≥ 0) |
| `volatilidadeAnualPct` | desvio padrão amostral dos retornos diários × √252 × 100 |
| `drawdownMaximoPct` | menor valor de `(fechamento / máximo acumulado até o dia − 1) × 100` (≤ 0) |

Rótulos do período: `3mo` → "3 meses", `6mo` → "6 meses", `1y` → "1 ano",
`2y` → "2 anos" (os mesmos da tela, definidos num único lugar).

No prompt, uma seção nova após os indicadores técnicos, por exemplo:

```
## Comportamento no período analisado (horizonte: 3 meses)
- Retorno no período: +8,40%
- Máxima: R$ 41,20 (preço atual 3,10% abaixo) | Mínima: R$ 35,00 (preço atual 14,00% acima)
- Volatilidade anualizada: 27,50%
- Maior queda (drawdown máximo): -9,80%
```

E uma regra a mais: "Considere o horizonte informado: a recomendação vale
para quem acompanha o ativo nessa janela de tempo."

## Critérios de aceite

| ID | Critério |
| -- | -------- |
| PE1 | Para uma série sintética conhecida, todas as métricas do resumo batem com os valores calculados à mão no teste (tolerância 0,01). |
| PE2 | O resumo usa o histórico completo do período: numa série cuja máxima está nos primeiros 50 pregões (descartados pelo `dropna`), `maxima` é essa máxima e `retornoPct` usa o primeiro fechamento do período. |
| PE3 | O prompt enviado à IA contém o rótulo do horizonte e os seis valores do resumo, formatados em pt-BR. Vale para Claude, Gemini e OpenRouter (verificado na requisição simulada). |
| PE4 | Mesmo ativo e mesma data de referência com períodos diferentes → a IA é chamada de novo; com o mesmo período → a recomendação é reaproveitada (`doCache` verdadeiro) sem chamar a IA. |
| PE5 | Toda recomendação nova é gravada com `periodo` preenchido com o código do período (`3mo`, `6mo`, `1y`, `2y`). |
| PE6 | Recomendações antigas (`periodo` nulo) nunca são reaproveitadas pelo cache, mas continuam no histórico, exibidas com período "—". |
| PE7 | A migração adiciona `periodo` (nulo permitido) e inclui o período no índice do cache, sem perder linhas existentes, em PostgreSQL e SQLite. |
| PE8 | "Gerar nova análise" (`forcar`) continua ignorando o cache e grava uma recomendação nova com o período. |
| PE9 | A "Variação no período" (card e quadro comparativo) mostra o `retornoPct` do resumo. |
| PE10 | O detalhe do ativo exibe as métricas do resumo e o histórico de recomendações tem a coluna "Período". |
| PE11 | Na análise múltipla, cada ativo recebe o resumo do próprio histórico, todos no mesmo período escolhido. |

## Casos-limite e erros

- **Série constante:** retorno, volatilidade, drawdown e distâncias iguais a
  `0.0`.
- **Série só subindo:** drawdown `0.0` e `distanciaMaximaPct` `0.0`.
- **Histórico curto demais:** continua valendo o erro atual de
  `IndicatorsService.calcular` (menos de 52 pregões); o resumo só é calculado
  depois dessa validação.
- **Fechamento faltando (NaN) em algum dia:** o dia é ignorado no resumo (o
  `YfinanceService` já remove linhas com NaN).
- **Período inválido:** a validação atual do controller continua valendo.

---

## Referências

- [`src/models/services/AnaliseService.py`](../../../src/models/services/AnaliseService.py)
- [`src/models/services/IndicatorsService.py`](../../../src/models/services/IndicatorsService.py)
- [`src/models/services/ClaudeService.py`](../../../src/models/services/ClaudeService.py)
- [`src/models/services/RecomendacoesService.py`](../../../src/models/services/RecomendacoesService.py)
- [`src/models/entities/RecomendacoesEntity.py`](../../../src/models/entities/RecomendacoesEntity.py)
- [`src/public/views/AnaliseView.py`](../../../src/public/views/AnaliseView.py)
