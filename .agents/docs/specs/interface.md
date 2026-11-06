# Spec — Interface (identidade visual, login, dashboard e atualização do Streamlit)

## Objetivo

Dar ao InvestIA uma identidade visual própria com a paleta definida pelo autor,
uma tela de login caprichada e um dashboard da carteira claro para o investidor
iniciante, atualizando o Streamlit para uma versão que oferece navegação nativa,
autocomplete com valores digitados e fragmentos com atualização automática.

## Audiência

- **Autor / devs** — critérios de aceite para implementar e testar.
- **Assistentes/agentes IA** — fonte de verdade do comportamento das telas.

---

> **Status:** implementada em 04/11/2026 (`tests/teste_estilo.py` e
> `tests/teste_interface.py`). Ajuste para celular em 06/11/2026 (seção "Uso no celular").

## Contexto atual (evidência: screenshots de 03/11/2026)

- Streamlit 1.35 com tema padrão (vermelho) e botão "Deploy" visível.
- Tabelas com números no formato americano: `R$ 5070.00`, `407.00` (sem `%`).
- Tabela da carteira com 11 colunas cortada na lateral.
- Login ocupa a largura toda da tela, só título e abas.
- Navegação por `st.radio` na barra lateral.
- Recomendação exibida como uma caixa `st.success`/`st.error` simples.
- Gráficos com `template="plotly_white"` e cores fixas.

## Escopo

**Entra:**

1. Atualizar dependências: Streamlit 1.66.x, Plotly atual, NumPy 2.x e PyArrow
   compatíveis com Python 3.11 (imagem Docker); pandas fica na linha 2.x (a 3.x
   muda semântica de cópia e de strings).
2. Tema próprio com a **paleta do autor** em `.streamlit/config.toml` e uma
   folha de estilo única (`src/public/views/Estilo.py`) injetada uma vez.
3. Navegação nativa (`st.navigation`) com ícones; nome, email e botão **Sair**
   na barra lateral.
4. **Login** em tela dividida (painel de marca + formulário).
5. **Dashboard da carteira** com cards, tabela, gráfico de alocação e cotação
   atualizada ([`carteira.md`](./carteira.md)).
6. Formatação pt-BR em todos os números exibidos.
7. Análise: card de recomendação em destaque, explicação dos indicadores e
   quadro comparativo para vários ativos
   ([`analise-multipla.md`](./analise-multipla.md)).
8. Backtesting: cards de métricas comparando estratégia e buy and hold.
9. Gráficos com as cores da paleta.

**Fica de fora:**

- Trocar Streamlit por outro framework (decisão do autor em 04/11/2026).
- Manter o login ao recarregar a página (F5) — exige cookie/token.
- Recuperação de senha e login social.
- Modo escuro (a paleta foi definida para fundo claro).
- Internacionalização para outros idiomas.

## Comportamento

### Paleta e tema

| Papel | Cor | Uso |
| ----- | --- | --- |
| Primária (vinho) | `#651424` | barra lateral, painel do login, cabeçalho das páginas, títulos |
| Destaque (laranja) | `#FF5825` | botões primários, links, foco, item ativo do menu, realces |
| Base (branco) | `#FFFFFF` | fundo das páginas e dos cards, texto sobre vinho/laranja |

Derivadas permitidas (para legibilidade e estados), definidas como constantes
em `Estilo.py`: vinho escuro `#4A0E1A` (hover), laranja claro `#FFE6DD`
(fundos suaves e cabeçalho de tabelas), cinza de texto `#2B2B2B`, cinza de
borda `#ECE4E6`.
Cores semânticas de resultado/recomendação continuam: verde `#1E8E3E`
(COMPRA/positivo), vermelho `#C62828` (VENDA/negativo), âmbar `#B26A00`
(MANTER) — o vermelho não pode ser confundido com o vinho da marca.

- `config.toml`: `primaryColor = "#FF5825"`, `backgroundColor = "#FFFFFF"`,
  `secondaryBackgroundColor` laranja claro, `textColor` cinza de texto,
  barra lateral vinho com texto branco, `client.toolbarMode = "minimal"`
  (sem "Deploy").
- Contraste mínimo 4,5:1 para texto (WCAG AA). Medido: branco sobre vinho
  12,5:1 ✓; cinza de texto sobre branco 14,2:1 ✓; **branco sobre laranja
  3,2:1 ✗** — por isso texto sobre laranja (botões, badges) usa o vinho escuro
  `#4A0E1A` (4,9:1), e laranja sobre branco só aparece em bordas, ícones,
  sublinhados e números grandes (≥ 24 px), nunca em texto corrido.
- Fonte: Inter (Google Fonts) com fallback `sans-serif`.

### Login

- Duas colunas no desktop: à esquerda painel vinho com o logo "InvestIA",
  a frase "Recomendações de ações da B3 explicadas em linguagem simples" e três
  destaques curtos com ícone (análise por IA, carteira com cotação, backtesting);
  à direita card branco com as abas **Entrar** / **Criar conta**.
- Em telas estreitas (≤ 640 px) o painel vira um cabeçalho compacto acima do
  formulário.
- Botões primários laranja com texto vinho escuro. Validações e mensagens de
  erro atuais mantidas.

### Navegação

- Barra lateral vinho: logo, menu com três páginas — **Minha carteira**,
  **Análise de ativo**, **Backtesting** — com ícones, nome e email do usuário e
  botão **Sair** no rodapé. Página inicial após o login: Carteira.
- Atalhos da Carteira ("Analisar", "Backtesting") abrem a página com o ativo
  selecionado.

### Dashboard da carteira

- Cabeçalho vinho "Olá, <primeiro nome>" + texto de atualização das cotações e
  botão **Atualizar cotações**.
- Cards (branco, borda suave, ícone/realce laranja): valor investido, valor
  atual, resultado (R$ e %), variação do dia, quantidade de ativos. Resultado
  e variação em verde quando positivos e vermelho quando negativos.
- Tabela: colunas essenciais visíveis sem rolagem horizontal da **página** em
  1440 px (código, empresa, quantidade, preço médio, cotação, variação do dia,
  resultado, recomendação). Demais colunas podem ter rolagem interna.
- Gráfico de alocação por setor (rosca) com tons da paleta, usando o valor
  atual (ou o investido quando faltar cotação).
- Gerenciar posições (compra com autocomplete, venda, correção, remoção) em
  abas abaixo.
- Carteira vazia: estado vazio ilustrado orientando a registrar a primeira
  compra, sem gráfico.

### Formatação pt-BR

| Tipo | Exemplo |
| ---- | ------- |
| Moeda | `R$ 5.070,00`, `-R$ 12,50` |
| Percentual | `407,00%`, `-3,25%` (com sinal `+` em variações) |
| Quantidade inteira | `100` |
| Data | `03/11/2026` |
| Data e hora | `03/11/2026 14:05` |

Vale para cards, tabelas e textos. Valor ausente aparece como `-`.

### Análise

- Card da recomendação: badge **COMPRA** (verde), **VENDA** (vermelho) ou
  **MANTER** (âmbar), com preço de referência e data dos dados.
- Seções na ordem: **Sobre a empresa**, **Por que esta recomendação?**,
  **Riscos** (lista).
- Cards dos indicadores (RSI, MACD, média curta, média longa), cada um com uma
  frase curta do que o valor significa.
- Aviso fixo: recomendação é apoio à decisão, não garantia de retorno.

### Backtesting

- Cards: retorno da estratégia, retorno do buy and hold, taxa de acerto,
  número de operações, drawdown máximo e índice de Sharpe (cálculo atual; a
  correção está em [`backtesting.md`](./backtesting.md), adiada).
- Tabela de operações com datas e valores formatados em pt-BR.

### Gráficos

- Sem `template` fixo do Plotly; cores da série principal vinho, destaques
  laranja, fundo transparente.
- RSI com as faixas de sobrecompra (>70) e sobrevenda (<30) destacadas.

## Uso no celular (ajuste de 06/11/2026)

Para a banca, em que o júri acessa pelo celular via ngrok. Conferido com
prints numa tela de 390×844 (iPhone) e de 1366 px (notebook).

- **Menu lateral:** começa no estado `auto`. Fica aberto no computador e
  fechado no celular, onde antes cobria a tela inteira após o login.
- **Métricas (até 640 px):** 2 por linha, com rótulos que quebram linha em
  vez de serem cortados com "…".
- **Comportamento no período:** no computador, aparece em duas linhas (3 + 2),
  porque 5 cards lado a lado cortavam os valores.
- **Gráficos:** a legenda fica abaixo do gráfico. Até 640 px, a barra de
  ferramentas do Plotly fica oculta, porque no toque ela ficava sempre
  visível por cima dos títulos.
- **Tabelas largas** (carteira, operações do backtesting): rolam na
  horizontal dentro da própria tabela; a página não rola para o lado.
- **Pendência conhecida:** a regra de estilo dos rótulos das métricas
  (`div[data-testid="stMetricLabel"] p`, vinho e maiúsculas) nunca é
  aplicada, porque o elemento é um `<label>`. Os rótulos aparecem no estilo
  padrão.

## Critérios de aceite

| ID | Critério |
| -- | -------- |
| UI1 | `requirements.txt` fixa Streamlit 1.66.x e a suíte inteira passa com as novas versões. |
| UI2 | `.streamlit/config.toml` define `primaryColor = "#FF5825"`, fundo `#FFFFFF` e `client.toolbarMode` que oculta o "Deploy". |
| UI3 | `Estilo.py` expõe as constantes `VINHO = "#651424"`, `LARANJA = "#FF5825"`, `BRANCO = "#FFFFFF"` e nenhuma outra view usa cor hexadecimal fora dessas constantes e das derivadas/semânticas listadas. |
| UI4 | O app usa `st.navigation` com as três páginas e ícones; após o login abre a Carteira. |
| UI5 | `Formatacao` formata moeda, percentual, quantidade, data e data-hora conforme a tabela acima, inclusive negativos e `None`. |
| UI6 | Nenhuma tabela exibe número no formato americano (verificado pelos valores renderizados no AppTest). |
| UI7 | O login mostra o painel de marca e o formulário lado a lado, mantém as abas Entrar / Criar conta e suas validações atuais. |
| UI8 | A Carteira mostra os cards (incl. variação do dia), a tabela e o gráfico de alocação quando há ativos, e o estado vazio sem gráfico quando não há. |
| UI9 | A Análise mostra o card com a recomendação, as três seções e os quatro cards de indicadores. |
| UI10 | O Backtesting mostra os cards de métricas da estratégia e do buy and hold. |
| UI11 | `charts.py` não fixa `template` do Plotly e usa as constantes da paleta. |
| UI12 | Em 390 px de largura nenhuma página tem rolagem horizontal, e em 1440 px o login e a carteira seguem o layout descrito (verificação manual com screenshot). |

## Casos-limite e erros

- **Cotação indisponível**: cards de valor atual, resultado e variação mostram
  `-` e a legenda informa quantos ativos ficaram sem cotação.
- **Falha da IA**: mensagem de erro traduzida e nenhum card de recomendação.
- **Backtesting sem operações**: cards com zeros e a mensagem "Nenhuma operação
  simulada no período selecionado."
- **Usuário com tema escuro no sistema operacional**: o app força o tema claro
  (`base = "light"`), já que não há variante escura.

## Testes (Fase 2)

- `tests/teste_estilo.py` (novo): UI1, UI2, UI3, UI5, UI11 (verificações
  estáticas de dependências, `config.toml`, paleta, formatação e gráficos).
- `tests/teste_interface.py` (reescrito, `AppTest`): UI4, UI6–UI10.
- UI12: verificação manual com screenshot em 390 px e 1440 px.

---

## Referências

- Telas: [`src/public/views/`](../../../src/public/views/)
- Entrada e navegação: [`src/public/Main.py`](../../../src/public/Main.py)
- Formatação: [`src/public/views/Formatacao.py`](../../../src/public/views/Formatacao.py)
- Gráficos: [`src/public/views/charts.py`](../../../src/public/views/charts.py)
- Dependências: [`requirements.txt`](../../../requirements.txt)
