# Spec — Comparação com o Ibovespa

## Objetivo

Dar referência aos números. "A ação subiu 12%" só é bom se o mercado subiu
menos. O sistema passa a comparar o retorno do ativo com o do **Ibovespa**
(`^BVSP`) no mesmo período, na análise (prompt e tela) e no backtesting.

## Audiência

- **Autor / devs** — critérios de aceite.
- **Assistentes/agentes IA** — como a comparação é calculada e enviada à IA.

---

> **Status:** implementada em 06/11/2026 (`tests/teste_ibovespa.py`; IB4 em
> `tests/teste_interface.py`).

## Escopo

**Entra:**

1. `YfinanceService.buscarHistoricoIndice(simbolo, periodo)`: histórico do
   índice (sem o sufixo `.SA`), com cache em memória de 1 hora por período.
2. **Comparação na análise** (`ind.ibovespa`), separada do `resumo_periodo`:
   - `retornoPct`: retorno do Ibovespa entre o primeiro e o último pregão do
     período do ativo;
   - `diferencaPct`: retorno do ativo − retorno do Ibovespa, em pontos
     percentuais.
3. **Prompt:** linha nova na seção do período, por exemplo
   `- Ibovespa no mesmo período: +5,10% (a ação ficou 3,30 p.p. acima do
   índice)`, e a regra "compare o desempenho da ação com o do Ibovespa".
4. **Tela de análise:** card "Ibovespa no período" no bloco do período, com a
   diferença na legenda.
5. **Backtesting:** card "Ibovespa no período", ao lado do Buy and Hold, com o
   mesmo cálculo (sem custos, por ser referência de mercado).

**Fica de fora:** outros índices (IFIX, SMLL, setoriais); mudar a recomendação
por regra fixa.

## Definições

- **Datas de comparação:** o primeiro fechamento do Ibovespa com data ≥ o
  primeiro pregão do período do ativo, e o último com data ≤ o último pregão
  do ativo.
- **Arredondamento:** valores em %, com 2 casas.

## Critérios de aceite

| ID | Critério |
| -- | -------- |
| IB1 | Para séries conhecidas de ativo e índice, `retornoPct` e `diferencaPct` batem com o cálculo à mão (tolerância 0,01). |
| IB2 | O Ibovespa é alinhado às datas do período do ativo: pregões do índice fora desse intervalo não entram. |
| IB3 | O prompt contém a linha do Ibovespa, com sinal e "acima/abaixo do índice", e a regra de comparação, nos três provedores. |
| IB4 | A tela de análise mostra o card "Ibovespa no período"; o backtesting mostra o card "Ibovespa no período". |
| IB5 | Se o Ibovespa não puder ser obtido, a análise e o backtesting funcionam normalmente: `ind.ibovespa` é `None`, o prompt omite a linha e os cards mostram "-". |
| IB6 | Analisar 5 ativos no mesmo período busca o Ibovespa uma única vez (cache). |

---

## Referências

- [`src/models/services/YfinanceService.py`](../../../src/models/services/YfinanceService.py)
- [`src/models/services/AnaliseService.py`](../../../src/models/services/AnaliseService.py)
- [`src/models/services/BacktestService.py`](../../../src/models/services/BacktestService.py)
- [`src/models/services/ClaudeService.py`](../../../src/models/services/ClaudeService.py)
