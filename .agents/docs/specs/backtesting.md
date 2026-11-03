# Spec — Backtesting (métricas)

## Objetivo

Corrigir o cálculo e o nome do índice de Sharpe do backtesting, para que a
métrica apresentada no TCC seja a definição usual e defensável na banca.

## Audiência

- **Autor / devs** — critérios de aceite.
- **Assistentes/agentes IA** — definição das métricas.

---

## Contexto atual

`BacktestService.calcularMetricas` calcula `sharpe = média / desvio` dos
retornos **por operação**. Isso não é o índice de Sharpe usual (que é
anualizado e calculado sobre retornos periódicos) e depende do número de
operações.

## Escopo

**Entra:** índice de Sharpe anualizado a partir dos retornos diários da
estratégia; rótulo explicando a convenção.

**Fica de fora:** custos de corretagem, taxa livre de risco (CDI), regras da
estratégia (cruzamento do MACD + RSI continua igual).

## Definição

- Retorno diário da estratégia: variação do fechamento nos dias em que está
  posicionada (do dia seguinte à entrada até o dia da saída); `0` fora de
  posição.
- Sharpe = `média(retornos diários) / desvio padrão(retornos diários) × √252`,
  com taxa livre de risco igual a zero.
- Exibido como "Índice de Sharpe (anualizado, sem taxa livre de risco)".

## Critérios de aceite

| ID | Critério |
| -- | -------- |
| BT1 | Para uma série sintética conhecida, o Sharpe calculado bate com o valor de referência calculado à mão no teste (tolerância 0,01). |
| BT2 | Sem operações ou com desvio zero, o Sharpe é `0.0`. |
| BT3 | As demais métricas (taxa de acerto, retorno acumulado, buy and hold, drawdown) não mudam de valor para os mesmos dados. |
| BT4 | A tela mostra o rótulo com a convenção do cálculo. |

---

## Referências

- [`src/models/services/BacktestService.py`](../../../src/models/services/BacktestService.py)
- [`src/public/views/BacktestView.py`](../../../src/public/views/BacktestView.py)
