# Spec — Backtesting (métricas, custos e posição aberta)

## Objetivo

Deixar o backtesting defensável na banca:

- **Sharpe na definição usual** (anualizado);
- **custos de operação da B3** descontados, para o resultado não sair otimista
  demais;
- **posição aberta no último dia** considerada, em vez de ignorada.

## Audiência

- **Autor / devs** — critérios de aceite.
- **Assistentes/agentes IA** — definição das métricas.

---

> **Status:** implementada em 06/11/2026 (`tests/teste_backtesting.py`; BT4
> em `tests/teste_interface.py`).

## Contexto atual

- **Sharpe:** `BacktestService.calcularMetricas` calcula `sharpe = média / desvio`
  dos retornos **por operação**. Isso não é o índice de Sharpe usual, que é
  anualizado e calculado sobre retornos periódicos, e depende do número de
  operações.
- **Custos:** as operações não descontam custo nenhum.
- **Posição aberta:** se a estratégia ainda está comprada no último dia, essa
  operação é descartada, escondendo ganho ou perda.

## Escopo

**Entra:**

1. Índice de Sharpe anualizado a partir dos retornos diários da estratégia,
   com rótulo explicando a convenção.
2. **Custo por operação** `CUSTO_OPERACAO_PCT` (padrão **0,03%** do valor, em
   cada compra e em cada venda; emolumentos + liquidação da B3, corretagem
   zero). Vale também para o Buy and Hold (uma compra e uma venda), para a
   comparação ser justa.
3. **Posição aberta no fim:** encerrada pelo fechamento do último pregão,
   marcada como "em aberto" e incluída nas métricas.
4. A simulação usa só os pregões do período escolhido; os indicadores vêm com
   o aquecimento definido em
   [`historico-aquecimento.md`](./historico-aquecimento.md).

**Fica de fora:**

- Taxa livre de risco (CDI).
- Imposto de renda.
- Mudanças nas regras da estratégia: o cruzamento do MACD + RSI continua igual.
- Comparação com o Ibovespa (ver [`comparacao-ibovespa.md`](./comparacao-ibovespa.md)).

## Definições

- **Resultado líquido de uma operação:**
  `(preço_saída × (1 − c)) / (preço_entrada × (1 + c)) − 1`, com
  `c = CUSTO_OPERACAO_PCT / 100`.
- **Buy and Hold:** mesma fórmula, do primeiro ao último fechamento do
  período.
- **Retorno diário da estratégia:** um valor por pregão do período, a partir
  do 2º. Para cada pregão `t`:
  - **dia da entrada** (a compra é no fechamento): `1/(1+c) − 1`;
  - **dias seguintes, até a saída:** `fechamento_t / fechamento_{t−1} − 1`;
  - **dia da saída:** `(fechamento_t / fechamento_{t−1}) × (1 − c) − 1`;
  - **entrada e saída no mesmo dia:** `(1 − c)/(1 + c) − 1`;
  - **fora de posição:** `0`.

  Assim, o produto de `(1 + retorno diário)` ao longo de uma operação é igual
  ao seu resultado líquido.
- **Sharpe:**
  `média(retornos diários) / desvio padrão amostral(retornos diários) × √252`,
  com taxa livre de risco igual a zero. Exibido como "Índice de Sharpe
  (anualizado)", com a ajuda "sem taxa livre de risco".
- **Operação em aberto:** saída = fechamento do último pregão, com
  `emAberto: true`. Na tabela, a saída aparece como "Em aberto". Ela entra em
  todas as métricas.

## Critérios de aceite

| ID | Critério |
| -- | -------- |
| BT1 | Para uma série sintética conhecida, o Sharpe calculado bate com o valor de referência calculado à mão no teste (tolerância 0,01). |
| BT2 | Sem operações ou com desvio zero, o Sharpe é `0.0`. |
| BT3 | Com `CUSTO_OPERACAO_PCT = 0` e sem posição aberta no fim, taxa de acerto, retorno acumulado, Buy and Hold e drawdown são iguais aos do cálculo anterior para os mesmos dados. |
| BT4 | A tela mostra o rótulo "Índice de Sharpe (anualizado)" e a informação de que os custos estão incluídos (com o percentual usado). |
| BT5 | Com custo de 0,03%, uma operação de R$ 10,00 → R$ 11,00 tem resultado líquido de `(11 × 0,9997) / (10 × 1,0003) − 1` (tolerância 0,01 p.p.); o Buy and Hold também desconta as duas pontas. |
| BT6 | Se a estratégia termina comprada, a última operação sai pelo fechamento do último pregão, com `emAberto: true`, entra na contagem e nas métricas e aparece como "Em aberto" na tabela. |
| BT7 | A simulação começa no primeiro pregão do período: nenhuma operação tem entrada antes do início do período, mesmo com os pregões de aquecimento. |

## Casos-limite e erros

- **Compra no último pregão:** a operação em aberto tem entrada e saída no
  mesmo dia e resultado igual a só os custos (negativo).
- **Nenhum sinal de compra no período:** zero operações; o Sharpe é `0.0`; o
  Buy and Hold continua calculado.
- **`CUSTO_OPERACAO_PCT` negativo ou ≥ 100:** erro de configuração na
  inicialização do service (`ValueError`).

---

## Referências

- [`src/models/services/BacktestService.py`](../../../src/models/services/BacktestService.py)
- [`src/public/views/BacktestView.py`](../../../src/public/views/BacktestView.py)
- [`src/models/Parametros.py`](../../../src/models/Parametros.py)
