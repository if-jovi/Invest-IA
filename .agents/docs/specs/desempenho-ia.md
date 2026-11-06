# Spec — Desempenho da IA (taxa de acerto das recomendações)

## Objetivo

Medir se as recomendações da IA acertam, que é a pergunta central do TCC. O
backtesting atual avalia uma regra fixa de MACD + RSI, **não a IA**.

Para cada recomendação, o sistema confere o preço `H` pregões depois e
calcula a taxa de acerto. Há duas fontes:

1. **Avaliação histórica:** um script "volta no tempo", pede à IA uma
   recomendação para datas passadas (usando só os dados até cada data) e
   confere o que aconteceu depois. Isso gera números antes da banca.
2. **Uso no app:** as recomendações já gravadas em `recomendacoes`, conferidas
   quando o horizonte se completa.

## Audiência

- **Autor / banca** — o que é medido e como interpretar.
- **Devs / agentes IA** — critérios de aceite.

---

> **Status:** implementada em 06/11/2026 (`tests/teste_desempenho_ia.py`;
> DI7 em `tests/teste_persistencia.py`; DI8 em `tests/teste_interface.py`).
> Script: `python -m src.scripts.AvaliarIA`; tela: "Desempenho da IA".

## Definições

- **Horizonte `H`:** `HORIZONTE_AVALIACAO` = **20 pregões** (≈ 1 mês).
- **Retorno futuro:** `fechamento no pregão data+H / preço da recomendação − 1`.
- **Acerto:**

  | Recomendação | Acerta quando |
  | ------------ | ------------- |
  | COMPRA | retorno futuro > 0 |
  | VENDA | retorno futuro < 0 |
  | MANTER | \|retorno futuro\| ≤ `FAIXA_MANTER_PCT` (**3%**) |
- **Acerto contra o Ibovespa** (COMPRA e VENDA): COMPRA acerta se o ativo
  rendeu **mais** que o Ibovespa no mesmo intervalo; VENDA, se rendeu
  **menos**.
- **Taxa base:** % dos casos avaliados em que o preço subiu em `H` pregões,
  ou seja, a taxa de acerto de quem "compra sempre". A COMPRA da IA só agrega
  valor se acertar mais que isso.
- **Pendente:** recomendação cuja data + `H` pregões ainda não chegou. Não
  entra nas taxas.
- **Intervalo de confiança (95%):** intervalo de Wilson para cada taxa de
  acerto (`z = 1,96`). Exibido como "60,0% (53,1% a 66,5%)".
- **Teste contra a taxa base:** teste binomial unilateral para a COMPRA. É a
  probabilidade de acertar pelo menos `k` de `n` COMPRAs se a chance de acerto
  fosse igual à taxa base (p-valor). Calculado exatamente pela soma da
  binomial; abaixo de 5%, a tela diz que o acerto é "acima do acaso".
- **Retorno médio:** média do retorno futuro depois de cada tipo de
  recomendação, comparada à média de todos os casos avaliados.

## Escopo

**Entra:**

1. **Tabela `avaliacoes_ia`** (migração 0005), uma linha por recomendação
   histórica, com:
   - item, data de referência, período, recomendação e preço;
   - provedor e modelo;
   - resposta completa;
   - data de geração.

   É única por (item, data, período, modelo).
2. **Script `python -m src.scripts.AvaliarIA`:**
   - **ativos:** padrão PETR4, VALE3, ITUB4, BBDC4, BBAS3, ABEV3, WEGE3,
     B3SA3, RENT3, SUZB3 (`--ativos` para trocar);
   - **datas:** são candidatos os pregões com data ≥ `último pregão − meses`
     (`--meses`, padrão 12), menos os últimos `H`. Desses, entram o 1º, o
     11º, o 21º… (um a cada `--intervalo`, padrão 10);
   - **período da análise:** `1y` (`--periodo`).
   - **Para cada (ativo, data):** usa o histórico **até a data, inclusive**,
     com aquecimento; calcula indicadores, resumo e Ibovespa; chama a IA com
     o mesmo prompt do app; grava em `avaliacoes_ia`.
   - **Retomável:** pula o que já existe.
   - **Limite de chamadas:** `--limite` (padrão 40 chamadas por execução) e
     pausa entre chamadas (`--pausa`, padrão 4 s), para respeitar o plano
     gratuito.
   - **Limite de uso atingido:** para, guarda o que já fez e informa como
     continuar.
   - **Saída:** um resumo do que foi feito (geradas, puladas, falhas).
3. **`DesempenhoIaService.avaliar(fonte)`** (`fonte` = `historico` ou `app`):
   - busca os preços futuros (e os do Ibovespa) e calcula, para cada
     recomendação, o retorno futuro, o acerto e o acerto contra o Ibovespa;
   - agrega: total avaliado, pendentes, acerto geral e por tipo, acerto contra
     o Ibovespa e taxa base.
4. **Tela "Desempenho da IA"** (novo item no menu):
   - escolha da fonte;
   - cards: avaliadas, acerto geral, acerto de COMPRA × taxa base (com
     intervalo de confiança e p-valor), acerto contra o Ibovespa, retorno
     médio depois de COMPRA × retorno médio geral;
   - tabela por tipo de recomendação e a lista das recomendações avaliadas;
   - quadro "Como ler estes números", com as definições e as limitações.

**Fica de fora:** mudar a recomendação com base no desempenho; avaliar vários
horizontes ao mesmo tempo; outros testes estatísticos além dos definidos acima.

## Limitações (exibidas na tela)

- **Amostra pequena:** algumas centenas de casos, no máximo, dão uma
  indicação, não uma prova.
- **Conhecimento do modelo:** a IA foi treinada com dados que podem incluir o
  período avaliado. O prompt só leva números e o nome da empresa, o que reduz
  esse viés, mas não o elimina.
- **Descrição da empresa atual:** a descrição vem do Yahoo de hoje, mesmo nas
  datas passadas.
- **Viés de sobrevivência:** os ativos avaliados são grandes e negociados
  **hoje**. Empresas que caíram muito ou saíram da bolsa no período não
  entram, o que tende a favorecer os resultados.
- **Casos não independentes:** datas próximas do mesmo ativo se parecem, então
  o intervalo de confiança tende a ser otimista (mais estreito que o real).

## Critérios de aceite

| ID | Critério |
| -- | -------- |
| DI1 | Com preços conhecidos, retorno futuro, acerto (COMPRA, VENDA e MANTER, incluindo os limites exatos de 0% e ±3%) e acerto contra o Ibovespa batem com o cálculo à mão. |
| DI2 | A taxa base, o acerto geral e o acerto por tipo batem com o cálculo à mão; recomendações pendentes não entram nas taxas e são contadas à parte. |
| DI3 | O script usa só dados até a data avaliada: o histórico entregue ao cálculo termina na data (nenhum pregão posterior), e as datas respeitam `--intervalo`, `--meses` e a exclusão dos últimos `H` pregões. |
| DI4 | O script é retomável: rodar de novo não chama a IA para (item, data, período, modelo) já gravados. |
| DI5 | O script respeita `--limite` (número de chamadas) e, em erro de limite da IA, para sem perder o que já gravou e informa como continuar. |
| DI6 | A fonte `app` avalia as recomendações de `recomendacoes`; a fonte `historico`, as de `avaliacoes_ia`. |
| DI7 | A migração 0005 cria `avaliacoes_ia` em banco novo e em banco existente, sem perder dados (SQLite e PostgreSQL). |
| DI9 | Para contagens conhecidas, o intervalo de Wilson e o p-valor do teste binomial batem com valores de referência calculados à mão (tolerância 0,001); com `n = 0`, o intervalo e o p-valor são `None` e a tela mostra "-". |
| DI10 | O retorno médio por tipo e o retorno médio geral batem com o cálculo à mão. |
| DI8 | A tela "Desempenho da IA" aparece no menu e mostra os cards, a tabela por tipo e o quadro de limitações; sem dados avaliados, mostra como gerar a avaliação histórica. |

---

## Referências

- [`src/models/services/RecomendacoesService.py`](../../../src/models/services/RecomendacoesService.py)
- [`src/models/services/AnaliseService.py`](../../../src/models/services/AnaliseService.py)
- [`src/public/views/Paginas.py`](../../../src/public/views/Paginas.py)
