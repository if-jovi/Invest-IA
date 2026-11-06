# Spec — Análise de vários ativos ao mesmo tempo

## Objetivo

Permitir que o usuário selecione vários ativos e receba, em uma única ação, a
recomendação de cada um, com um quadro comparativo e o detalhe por ativo.

## Audiência

- **Autor / devs** — critérios de aceite para implementar e testar.
- **Assistentes/agentes IA** — fonte de verdade do fluxo de análise.

---

> **Status:** implementada em 04/11/2026 (`tests/teste_analise_multipla.py`).

## Contexto atual

- A tela de Análise tem um `text_input` para um código;
  `AnaliseController.analisar(item, periodo, forcar)` devolve o resultado de
  um ativo, que fica em `st.session_state["analiseResultado"]`.
- O provedor padrão passa a ser um modelo gratuito do OpenRouter, com limite de
  requisições por minuto ([`provedor-openrouter.md`](./provedor-openrouter.md)).

## Escopo

**Entra:**

1. Campo de ativos com seleção múltipla e autocomplete do catálogo
   ([`catalogo-ativos.md`](./catalogo-ativos.md)), aceitando código digitado.
2. Limite de **5 ativos** por análise (`LIMITE_ATIVOS_ANALISE = 5`).
3. `AnaliseController.analisarVarios(itens, periodo, forcar)`; o
   `analisar(item, ...)` atual continua existindo.
4. Execução com no máximo **2 ativos em paralelo**, para respeitar o limite do
   modelo gratuito; falha em um ativo não interrompe os outros.
5. Tela de resultado: quadro comparativo + uma aba por ativo com o detalhe
   atual (recomendação, indicadores, gráfico, histórico, registrar compra).
6. Progresso visível durante a execução ("Analisando 2 de 4...").

**Fica de fora:**

- Análise de vários ativos no Backtesting (continua um ativo).
- Botão "analisar a carteira inteira".
- Fila/agendamento de análises em segundo plano.
- Comparação gráfica sobreposta dos preços.

## Comportamento

### Entrada

- Os códigos são normalizados (maiúsculas, sem `.SA`) e repetidos são
  removidos, mantendo a ordem da primeira ocorrência.
- Lista vazia → `ValueError` "Informe ao menos um ativo."
- Mais de 5 ativos (após remover repetidos) → `ValueError` "Selecione no
  máximo 5 ativos por análise." (o seletor também usa `max_selections=5`).
- Período e "Gerar nova análise" valem para todos os ativos da execução.

### Retorno de `analisarVarios`

```python
{
    "resultados": [<dict de analisar()>, ...],      # na ordem de entrada
    "erros": [{"item": "XPTO3", "mensagem": "..."}],  # na ordem de entrada
}
```

- Cada ativo usa o mesmo fluxo de `analisar()` (catálogo, histórico,
  indicadores, cache por ativo + data, IA, gravação).
- `ValueError`/`RuntimeError` de um ativo vira item em `erros` com a mensagem
  já traduzida; outras exceções viram "Não foi possível concluir a análise:
  <erro>".

### Tela

- **Um resultado**: mesmo layout detalhado de hoje (sem quadro comparativo).
- **Dois ou mais**: quadro comparativo com uma linha por ativo — código,
  empresa, preço, variação do período (%), RSI, tendência e recomendação
  (badge colorido: COMPRA verde, VENDA vermelho, MANTER âmbar) — seguido de
  abas `PETR4`, `VALE3`, ... com o detalhe de cada um.
- **Erros**: um aviso por ativo com falha ("XPTO3: Nenhum dado encontrado para
  XPTO3.SA."), exibido acima do resultado; os ativos que deram certo aparecem
  normalmente.
- Todos falharam: só os avisos, sem quadro.
- O resultado fica em `st.session_state["analiseResultado"]` (agora no formato
  de `analisarVarios`) e sobrevive à troca de página.

## Critérios de aceite

| ID | Critério |
| -- | -------- |
| AM1 | `analisarVarios(["PETR4", "VALE3"], ...)` devolve dois resultados na ordem de entrada e `erros` vazio. |
| AM2 | `["petr4", "PETR4.SA", "PETR4"]` resulta em uma única análise de `PETR4`. |
| AM3 | Lista vazia → `ValueError` "Informe ao menos um ativo."; 6 ativos distintos → `ValueError` "Selecione no máximo 5 ativos por análise."; período inválido → erro atual. |
| AM4 | Com um ativo inválido entre dois válidos, os dois válidos aparecem em `resultados` e o inválido em `erros` com a mensagem traduzida. |
| AM5 | Nunca há mais de 2 análises executando ao mesmo tempo (verificado com dublê que mede a concorrência). |
| AM6 | O cache por ativo + data continua valendo por ativo: segunda execução no mesmo dia não chama a IA, salvo com "Gerar nova análise". |
| AM7 | Na tela, o seletor de ativos aceita múltiplos itens do catálogo e código digitado, limitado a 5. |
| AM8 | Com 2+ ativos, a tela mostra o quadro comparativo e uma aba por ativo; com 1 ativo, mostra o detalhe direto. |
| AM9 | Ativos com falha aparecem como aviso individual sem esconder os bem-sucedidos. |
| AM10 | O atalho "Analisar" da Carteira abre a Análise com aquele ativo pré-selecionado. |

## Casos-limite e erros

- **Limite do modelo gratuito (429) no meio da execução**: o ativo afetado vai
  para `erros` com a mensagem de limite; os já concluídos são mantidos.
- **Mesmo ativo com cache e outro sem**: só o sem cache chama a IA.
- **Usuário troca de página durante a análise**: comportamento padrão do
  Streamlit (a execução é interrompida; nada parcial é exibido).

## Testes previstos (Fase 2)

- `tests/teste_analise_multipla.py` (novo): AM1–AM6 com serviços simulados.
- `tests/teste_interface.py` (ajuste): AM7–AM10 com `AppTest`.

---

## Referências

- [`src/controllers/AnaliseController.py`](../../../src/controllers/AnaliseController.py)
- [`src/models/services/AnaliseService.py`](../../../src/models/services/AnaliseService.py)
- [`src/public/views/AnaliseView.py`](../../../src/public/views/AnaliseView.py)
