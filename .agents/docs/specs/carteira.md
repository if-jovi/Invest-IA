# Spec — Carteira com cotação atualizada

## Objetivo

Garantir que, sempre que o usuário abrir a carteira, veja a cotação mais
recente disponível de cada ativo (com variação do dia e horário da
atualização), e que ela continue se atualizando enquanto a página estiver
aberta.

## Audiência

- **Autor / devs** — critérios de aceite para implementar e testar.
- **Assistentes/agentes IA** — regras de cotação e cálculo da carteira.

---

## Contexto atual

- `CarteiraService.enriquecer` chama `YfinanceService.buscarPrecoAtual` por
  ativo, em threads; cada chamada faz `yf.Ticker(...).history(period="5d")`
  e usa o último fechamento.
- Cache em memória por processo: 300 s para sucesso, 60 s para falha (devolve
  o último valor conhecido).
- A cotação só é recalculada quando a página é recarregada; não há variação do
  dia nem horário da atualização.

### Como funciona a cotação via yfinance (fato relevante para a banca)

O `yfinance` lê os dados públicos do Yahoo Finance, que para a B3 têm **atraso
de cerca de 15 minutos** — não é cotação em tempo real de corretora. Durante o
pregão, a barra diária do dia corrente traz no `Close` o último preço
negociado (com o atraso); fora do pregão, o fechamento do último dia útil. O
Yahoo limita requisições por IP (erro 429), por isso o sistema agrupa ativos em
uma única chamada e usa cache curto.

## Escopo

**Entra:**

1. `YfinanceService.buscarCotacoes(itens) -> dict` com **uma única chamada**
   `yf.download` para todos os ativos da carteira (`period="5d"`,
   `interval="1d"`), devolvendo por ativo: `preco`, `fechamentoAnterior`,
   `variacaoDia` (%) e `atualizadoEm`.
2. Cache por ativo de **60 s** (sucesso) e 30 s (falha, devolvendo o último
   valor conhecido marcado como desatualizado).
3. Na tela da Carteira, cards e tabela dentro de um `st.fragment` com
   `run_every=60s`: as cotações se atualizam sozinhas com a página aberta.
4. Botão **Atualizar cotações** que ignora o cache.
5. Texto "Cotações do Yahoo Finance com atraso de até 15 min · atualizado às
   HH:MM".
6. Coluna **Variação do dia** (%) na tabela e card **Variação do dia** da
   carteira: valor em % (fórmula abaixo) e, como delta, o ganho/perda do dia em
   R$ (verde/vermelho).

**Fica de fora:**

- Cotação em tempo real (exigiria fonte paga/streaming).
- Histórico de valor da carteira no tempo.
- Proventos (dividendos/JCP) no resultado.
- Atualização com a aba do navegador fechada.

## Comportamento

### Cálculo por ativo

- `preco` = último `Close` válido; `fechamentoAnterior` = `Close` anterior.
- `variacaoDia` = `(preco / fechamentoAnterior − 1) × 100`; `None` se só houver
  uma barra.
- `atualizadoEm` = instante da consulta bem-sucedida.
- Ativo ausente na resposta ou só com `NaN` → sem cotação (`None`); se havia
  valor anterior em cache, é tratado como falha daquele ativo (último valor
  marcado como desatualizado, nova tentativa após 30 s).
- As regras de valor atual, resultado e `semCotacao` de
  `CarteiraService.obterResumo` não mudam.

### Variação do dia da carteira

- `Σ(quantidade × (preco − fechamentoAnterior)) / Σ(quantidade ×
  fechamentoAnterior) × 100`, considerando só ativos com as duas informações.
- Sem nenhum ativo com variação → `-`.

### Tela

- Abrir a Carteira sempre chama `obterResumo` (cotação no máximo 60 s mais
  velha que a do Yahoo).
- O fragmento se reexecuta a cada 60 s sem recarregar formulários nem perder o
  que está sendo digitado nas abas de gerenciamento (que ficam fora do
  fragmento).
- "Atualizar cotações" limpa o cache dos ativos da carteira e recarrega.
- Cotação desatualizada (falha com valor anterior): legenda "N ativo(s) com
  cotação desatualizada".

## Critérios de aceite

| ID | Critério |
| -- | -------- |
| CT1 | `buscarCotacoes(["PETR4", "VALE3", "ITUB4"])` faz **uma** chamada a `yf.download` com os três símbolos `.SA`. |
| CT2 | Para barras simuladas conhecidas, `preco`, `fechamentoAnterior` e `variacaoDia` batem com o valor calculado à mão (tolerância 0,01). |
| CT3 | Ativo ausente ou só com `NaN` volta sem cotação, sem derrubar os outros. |
| CT4 | Segunda chamada em menos de 60 s não chama o Yahoo; após 60 s chama de novo. |
| CT5 | Falha do Yahoo devolve o último valor conhecido marcado como desatualizado; sem valor anterior, `None`. Nova tentativa só após 30 s. |
| CT6 | `forcar=True` ignora o cache. |
| CT7 | `obterResumo` inclui `variacaoDia` por ativo e a variação do dia da carteira conforme a fórmula. |
| CT8 | A tela mostra a coluna "Variação do dia", o card de variação do dia, o texto com o horário de atualização e o botão "Atualizar cotações". |
| CT9 | Os cards e a tabela estão em um fragmento com `run_every` de 60 s; os formulários de gerenciamento não. |
| CT10 | Valores existentes (valor investido, valor atual, resultado, `semCotacao`) continuam iguais para os mesmos dados. |

## Casos-limite e erros

- **Carteira vazia**: não chama o Yahoo; mensagem atual.
- **Erro 429 do Yahoo**: usa valores em cache/desatualizados e mostra a legenda.
- **Fim de semana/feriado**: `preco` = último fechamento; variação em relação
  ao pregão anterior a ele.
- **Ativo com uma única barra no período** (recém-listado): variação `-`.

## Testes previstos (Fase 2)

- `tests/teste_yfinance.py` (ajuste): CT1–CT6 com `yf.download` substituído
  por dublê (o simulador HTTP do projeto não intercepta o `yf.download`, que
  acessaria a internet). `buscarCotacoes` substitui `buscarPrecoAtual` na
  carteira.
- `tests/teste_logica.py` (ajuste): CT7, CT10.
- `tests/teste_interface.py` (ajuste): CT8; `tests/teste_estilo.py`: CT9.

---

## Referências

- [`src/models/services/YfinanceService.py`](../../../src/models/services/YfinanceService.py)
- [`src/models/services/CarteiraService.py`](../../../src/models/services/CarteiraService.py)
- [`src/public/views/CarteiraDashboard.py`](../../../src/public/views/CarteiraDashboard.py)
