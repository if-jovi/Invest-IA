# Spec — Histórico com aquecimento dos indicadores

## Objetivo

Os indicadores (SMA50, MACD, RSI) precisam de dezenas de pregões anteriores
para existir e se estabilizar. Hoje esses pregões saem **de dentro** do período
escolhido, então com 3 meses quase nada sobra. Esta spec busca pregões extras
**antes** do período, só para o cálculo.

## Audiência

- **Autor / devs** — critérios de aceite.
- **Assistentes/agentes IA** — o que é "período" e o que é "aquecimento".

---

> **Status:** implementada em 06/11/2026 (`tests/teste_aquecimento.py`).
> Teste real com PETR4 em 3 meses: 64 pregões no período, contra ~12 antes.

## Contexto atual

- `YfinanceService.buscarHistorico(item, periodo)` busca exatamente o
  período.
- `IndicatorsService.calcular` faz `dropna()`, descartando os ~50 primeiros
  pregões do período. Com 3 meses (~62 pregões), sobram ~12.
- **Na análise:** o gráfico cobre só esses ~12 dias.
- **No backtesting:** simula sobre eles e quase nunca gera operação.
- **Precisão:** as médias exponenciais (MACD, RSI) começam "frias", sem
  histórico anterior, e ficam menos precisas.

## Definições

- **Período:** do primeiro pregão com data ≥ `último pregão − N meses` até o
  último pregão, com `N` = 3, 6, 12 ou 24 para `3mo`, `6mo`, `1y` e `2y`
  (`MESES_PERIODO` em `Parametros`).
- **Aquecimento:** os pregões anteriores ao período, buscados a partir de
  `início do período − DIAS_AQUECIMENTO` dias corridos (padrão **150**, ≈ 100
  pregões).

## Escopo

**Entra:**

1. `YfinanceService.buscarHistorico(item, periodo)` devolve o período **mais**
   o aquecimento (via `history(start=...)`).
2. `IndicatorsService.calcular(item, historico, periodo)` calcula os
   indicadores sobre tudo e devolve só o período:
   - `ind.historico` (gráfico): os pregões do período;
   - `ind.resumo_periodo` e a "Variação no período": só os pregões do período,
     sem o aquecimento;
   - os indicadores do último dia: calculados com o aquecimento.
3. O backtesting simula sobre os pregões do período, usando os indicadores
   calculados com o aquecimento (o cruzamento no 1º dia do período compara com
   o último dia do aquecimento).
4. **Ajuste em [`analise-periodo.md`](./analise-periodo.md):** o resumo passa a
   excluir explicitamente o aquecimento. Os testes PE2, PE9 e PE11 são
   ajustados a essa definição.

**Fica de fora:** intervalos diferentes de diário; períodos novos.

## Critérios de aceite

| ID | Critério |
| -- | -------- |
| AQ1 | `buscarHistorico(item, "3mo")` pede ao Yahoo a partir de `hoje − 3 meses − 150 dias` (verificado na chamada simulada). |
| AQ2 | Com aquecimento suficiente, `ind.historico` começa no primeiro pregão do período e não tem valores faltando: para 3 meses, ≈ 62 pregões, e não ≈ 12. |
| AQ3 | O resumo do período ignora o aquecimento: numa série cuja máxima está no aquecimento, essa máxima **não** entra no resumo. |
| AQ4 | Os indicadores do último dia usam o aquecimento: o RSI calculado com o aquecimento difere do RSI calculado só com o período (série de teste) e bate com o cálculo sobre a série inteira. |
| AQ5 | O backtesting de 3 meses simula sobre os ≈ 62 pregões do período (BT7 em [`backtesting.md`](./backtesting.md)). |

## Casos-limite e erros

- **Ativo listado há pouco tempo** (sem aquecimento completo): usa o que
  existir. Pregões do período sem indicadores são descartados, como hoje.
  Continua valendo o erro de histórico insuficiente (menos de 52 pregões no
  total).
- **Período sem pregões depois do corte:** erro de histórico insuficiente
  (mensagem atual).

---

## Referências

- [`src/models/services/YfinanceService.py`](../../../src/models/services/YfinanceService.py)
- [`src/models/services/IndicatorsService.py`](../../../src/models/services/IndicatorsService.py)
- [`src/models/services/BacktestService.py`](../../../src/models/services/BacktestService.py)
