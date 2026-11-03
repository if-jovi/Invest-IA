# Spec — Interface (visual, usabilidade e atualização do Streamlit)

## Objetivo

Deixar a interface do InvestIA com identidade própria, legível para o investidor
iniciante e coerente com o português do Brasil, atualizando o Streamlit para uma
versão atual que oferece navegação nativa e componentes mais ricos.

## Audiência

- **Autor / devs** — critérios de aceite para implementar e testar.
- **Assistentes/agentes IA** — fonte de verdade do comportamento das telas.

---

## Contexto atual (evidência: screenshots de 03/11/2026)

- Streamlit 1.35 com tema padrão (vermelho) e botão "Deploy" visível.
- Tabelas com números no formato americano: `R$ 5070.00`, `407.00` (sem `%`).
- Tabela da carteira com 11 colunas cortada na lateral.
- Login ocupa a largura toda da tela.
- Navegação por `st.radio` na barra lateral.
- Recomendação exibida como uma caixa `st.success`/`st.error` simples.
- Gráficos com `template="plotly_white"` e cores fixas.

## Escopo

**Entra:**

1. Atualizar dependências: Streamlit 1.66, NumPy 2, PyArrow e Plotly atuais;
   pandas fica na linha 2.x (a 3.x muda semântica de cópia e de strings).
2. Tema próprio em `.streamlit/config.toml` (cores, fonte, barra de ferramentas
   sem "Deploy"), com variante clara e escura.
3. Navegação nativa (`st.navigation`) com ícones; nome e email do usuário e o
   botão **Sair** na barra lateral.
4. Tela de login centralizada, com uma frase sobre o sistema.
5. Formatação pt-BR em todos os números exibidos.
6. Carteira: cards de resumo, tabela com resultado colorido e gráfico de
   alocação por setor.
7. Análise: card da recomendação em destaque e explicação dos indicadores.
8. Backtesting: cards de métricas comparando estratégia e buy and hold.
9. Gráficos seguindo o tema ativo.

**Fica de fora:**

- Trocar Streamlit por outro framework (Vue, React).
- Manter o login ao recarregar a página (F5) — exige cookie/token; fica para depois.
- Internacionalização para outros idiomas.

## Comportamento

### Tema e navegação

- Cor primária própria (não o vermelho padrão do Streamlit). O menu "Deploy"
  não aparece.
- Menu com três páginas: **Minha carteira**, **Análise de ativo**,
  **Backtesting**, cada uma com ícone. A página inicial após o login é a
  Carteira.
- Os atalhos da Carteira ("Analisar", "Backtesting") abrem a página
  correspondente com o ativo escolhido (ver
  [`catalogo-ativos.md`](./catalogo-ativos.md), CA9).

### Formatação pt-BR

| Tipo | Exemplo |
| ---- | ------- |
| Moeda | `R$ 5.070,00`, `-R$ 12,50` |
| Percentual | `407,00%`, `-3,25%` (com sinal `+` em variações) |
| Quantidade inteira | `100` |
| Data | `03/11/2026` |
| Data e hora | `03/11/2026 14:05` |

Vale para cards, tabelas e textos. Valor ausente aparece como `-`.

### Carteira

- Cards: valor investido, valor atual, resultado (R$ e %) e quantidade de
  ativos; o resultado aparece em verde quando positivo e vermelho quando
  negativo.
- Tabela: colunas essenciais visíveis sem rolagem horizontal da **página** em
  1440 px (código, empresa, quantidade, preço médio, cotação, resultado,
  recomendação). Demais colunas podem ficar na tabela com rolagem interna.
- Gráfico de alocação por setor (rosca), usando o valor atual (ou o investido,
  quando faltar cotação).
- Carteira vazia: mensagem orientando a registrar a primeira compra, sem gráfico.

### Análise

- Card da recomendação: rótulo **COMPRA** (verde), **VENDA** (vermelho) ou
  **MANTER** (âmbar), com o preço de referência e a data dos dados.
- Seções na ordem: **Sobre a empresa**, **Por que esta recomendação?**,
  **Riscos** (lista).
- Cards dos indicadores (RSI, MACD, média curta, média longa), cada um com uma
  frase curta do que o valor significa.
- Aviso fixo: recomendação é apoio à decisão, não garantia de retorno.

### Backtesting

- Cards: retorno da estratégia, retorno do buy and hold, taxa de acerto,
  número de operações, drawdown máximo e índice de Sharpe (ver
  [`backtesting.md`](./backtesting.md)).
- Tabela de operações com datas e valores formatados em pt-BR.

### Gráficos

- Sem `template` fixo: seguem o tema claro/escuro ativo.
- RSI com as faixas de sobrecompra (>70) e sobrevenda (<30) destacadas.

## Critérios de aceite

| ID | Critério |
| -- | -------- |
| UI1 | `requirements.txt` fixa Streamlit 1.66.x e a suíte inteira passa com as novas versões. |
| UI2 | `.streamlit/config.toml` define cor primária diferente de `#FF4B4B` e `client.toolbarMode` que oculta o "Deploy". |
| UI3 | O app usa `st.navigation` com as três páginas e ícones; após o login abre a Carteira. |
| UI4 | `Formatacao` formata moeda, percentual, quantidade, data e data-hora conforme a tabela acima, inclusive negativos e `None`. |
| UI5 | Nenhuma tabela exibe número no formato americano (verificado pelos valores renderizados no AppTest). |
| UI6 | A tela de login fica centralizada (coluna central) e mantém as abas Entrar / Criar conta e suas validações atuais. |
| UI7 | A Carteira mostra o gráfico de alocação por setor quando há ativos e não o mostra quando está vazia. |
| UI8 | A Análise mostra o card com a recomendação, as três seções e os quatro cards de indicadores. |
| UI9 | O Backtesting mostra os cards de métricas da estratégia e do buy and hold. |
| UI10 | `charts.py` não fixa `template` do Plotly. |
| UI11 | Em 390 px de largura a página não tem rolagem horizontal (verificação manual com screenshot). |

## Casos-limite e erros

- **Cotação indisponível**: card de valor atual e resultado mostram `-` e a
  legenda informa quantos ativos ficaram sem cotação (comportamento atual).
- **Falha da IA**: mensagem de erro traduzida (comportamento atual) e nenhum card
  de recomendação.
- **Backtesting sem operações**: cards com zeros e a mensagem "Nenhuma operação
  simulada no período selecionado."

---

## Referências

- Telas: [`src/public/views/`](../../../src/public/views/)
- Entrada e navegação: [`src/public/Main.py`](../../../src/public/Main.py)
- Formatação: [`src/public/views/Formatacao.py`](../../../src/public/views/Formatacao.py)
- Gráficos: [`src/public/views/charts.py`](../../../src/public/views/charts.py)
- Dependências: [`requirements.txt`](../../../requirements.txt)
