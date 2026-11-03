# Spec — Catálogo de ativos da B3 e sugestões

## Objetivo

Deixar o banco pré-carregado com as principais ações da B3 e sugerir esses
ativos nas telas de Análise e Backtesting, para o usuário escolher em uma lista
em vez de digitar o código de memória.

## Audiência

- **Autor / devs** — critérios de aceite para implementar e testar.
- **Assistentes/agentes IA** — fonte de verdade do comportamento do catálogo.

---

## Contexto atual

- A tabela `itens_b3` (`item`, `nome`, `setor`, `ativo`) só ganha linhas quando
  alguém analisa ou compra um ativo: `ItensB3Service.obterOuCadastrar` valida o
  código no Yahoo e grava.
- `src/scripts/SeedItensB3.py` tem 10 códigos fixos, mas é manual e consulta o
  Yahoo para cada um (lento e sujeito ao erro 429).
- Análise e Backtesting usam um `text_input` livre.

## Escopo

**Entra:**

1. Catálogo estático no código (`CATALOGO_B3`: código, nome, setor) com as
   ações listadas em [Catálogo inicial](#catálogo-inicial).
2. Seed automático e offline na inicialização do app (junto de
   `criarTabelas()`), sem chamar o Yahoo.
3. Seletor de ativo nas telas **Análise de ativo** e **Backtesting**: lista
   do catálogo com busca, que também aceita digitar um código fora da lista
   (`st.selectbox(accept_new_options=True)`, disponível após a atualização do
   Streamlit — ver [`interface.md`](./interface.md)).
4. `SeedItensB3` sem argumentos passa a gravar o catálogo estático (offline);
   com argumentos mantém o comportamento atual (valida no Yahoo).

**Fica de fora:**

- Formulário de compra da Carteira (continua com campo de texto livre).
- Atualizar automaticamente a composição do Ibovespa ou buscar a lista na
  internet.
- Tela de administração do catálogo (ativar/desativar fica pelo banco/pgAdmin).
- FIIs, ETFs e BDRs.

## Comportamento

### Seed

- Na inicialização, para cada ativo de `CATALOGO_B3` **ausente** em
  `itens_b3`, insere `item`, `nome`, `setor` e `ativo = TRUE`.
- Ativo que **já existe** não é alterado (preserva o nome vindo do Yahoo e um
  `ativo = FALSE` definido manualmente).
- Nenhuma requisição de rede acontece no seed.

### Seletor (Análise e Backtesting)

- Opções: todos os ativos de `itens_b3` com `ativo = TRUE`, ordenados pelo
  código, com rótulo `CÓDIGO — Nome (Setor)`, ex.: `PETR4 — Petrobras
  (Energia)`. Inclui ativos que usuários cadastraram ao analisar códigos fora
  do catálogo.
- O usuário pode digitar para filtrar a lista ou informar um código que não
  está nela; nesse caso vale o fluxo atual (validação de formato, consulta ao
  Yahoo, cadastro no catálogo). Na próxima visita, esse ativo já aparece na
  lista.
- O valor enviado ao controller continua sendo o código (`PETR4`), sem
  alteração nas assinaturas de `AnaliseController.analisar` e
  `BacktestController.executar`.
- Os atalhos "Analisar"/"Backtesting" da Carteira continuam levando o ativo:
  ele vem selecionado no seletor (como opção da lista ou como valor digitado).

## Critérios de aceite

| ID   | Critério |
| ---- | -------- |
| CA1  | Com o banco vazio, após `criarTabelas()` + seed, `itens_b3` contém todos os códigos de `CATALOGO_B3` com nome, setor e `ativo = TRUE`. |
| CA2  | Rodar o seed duas vezes não duplica linhas nem levanta erro. |
| CA3  | Um ativo pré-existente com nome diferente ou `ativo = FALSE` mantém seus valores após o seed. |
| CA4  | O seed não chama o `YfinanceService` (funciona sem internet). |
| CA5  | `ItensB3Service` expõe a lista de ativos ativos ordenada por código; ativos com `ativo = FALSE` não aparecem. |
| CA6  | Na tela de Análise, escolher `PETR4` na lista e clicar em Analisar gera a análise de `PETR4`. |
| CA7  | Na tela de Análise, digitar no seletor um código válido fora do catálogo e analisar cadastra o ativo; ele passa a constar na lista. |
| CA8  | Na tela de Backtesting, o mesmo seletor funciona (lista e código digitado). |
| CA9  | O atalho "Analisar" da Carteira abre a Análise com o ativo da carteira selecionado. |
| CA10 | `python -m src.scripts.SeedItensB3` sem argumentos grava o catálogo sem acessar a internet; com argumentos mantém a validação pelo Yahoo. |
| CA11 | Todo código de `CATALOGO_B3` respeita o formato aceito por `ItensB3Service.validarFormato`. |

## Casos-limite e erros

- **Catálogo vazio no banco** (ex.: todos desativados): o seletor fica sem
  opções, mas continua aceitando código digitado.
- **Nada selecionado**: mantém a mensagem atual "Informe o código do ativo.".
- **Código digitado que já está na lista**: funciona normalmente (normalizado
  para maiúsculas, sem `.SA`).
- **Falha de banco no seed**: mesma tela de erro de conexão que já existe em
  `Main.py` (o app não sobe pela metade).
- **Ticker do catálogo que deixou de existir no Yahoo**: aparece na lista; ao
  analisar, mostra o erro atual "Nenhum dado encontrado para X.SA.". A lista
  é revisada manualmente.

## Catálogo inicial

Ações líquidas do Ibovespa, com setores no mesmo vocabulário que o
`YfinanceService.SETORES` já usa. TODO: revisar contra a carteira teórica
vigente do Ibovespa antes da apresentação. Ficaram de fora tickers que mudaram
de código recentemente (fusões e renomeações) para evitar códigos inválidos.

| Código | Nome | Setor |
| ------ | ---- | ----- |
| PETR3 | Petrobras ON | Energia |
| PETR4 | Petrobras PN | Energia |
| PRIO3 | PRIO | Energia |
| UGPA3 | Ultrapar | Energia |
| VBBR3 | Vibra Energia | Energia |
| CSAN3 | Cosan | Energia |
| VALE3 | Vale | Materiais Básicos |
| SUZB3 | Suzano | Materiais Básicos |
| GGBR4 | Gerdau | Materiais Básicos |
| CSNA3 | CSN | Materiais Básicos |
| USIM5 | Usiminas | Materiais Básicos |
| KLBN11 | Klabin | Materiais Básicos |
| ITUB4 | Itaú Unibanco | Serviços Financeiros |
| BBDC4 | Bradesco | Serviços Financeiros |
| BBAS3 | Banco do Brasil | Serviços Financeiros |
| SANB11 | Santander Brasil | Serviços Financeiros |
| BPAC11 | BTG Pactual | Serviços Financeiros |
| ITSA4 | Itaúsa | Serviços Financeiros |
| B3SA3 | B3 | Serviços Financeiros |
| BBSE3 | BB Seguridade | Serviços Financeiros |
| ABEV3 | Ambev | Consumo Não Cíclico |
| ASAI3 | Assaí | Consumo Não Cíclico |
| LREN3 | Lojas Renner | Consumo Cíclico |
| MGLU3 | Magazine Luiza | Consumo Cíclico |
| RENT3 | Localiza | Consumo Cíclico |
| CYRE3 | Cyrela | Consumo Cíclico |
| WEGE3 | WEG | Industrial |
| RAIL3 | Rumo | Industrial |
| EQTL3 | Equatorial | Utilidade Pública |
| CMIG4 | Cemig | Utilidade Pública |
| SBSP3 | Sabesp | Utilidade Pública |
| EGIE3 | Engie Brasil | Utilidade Pública |
| TAEE11 | Taesa | Utilidade Pública |
| ENGI11 | Energisa | Utilidade Pública |
| RADL3 | Raia Drogasil | Saúde |
| RDOR3 | Rede D'Or | Saúde |
| HAPV3 | Hapvida | Saúde |
| VIVT3 | Telefônica Brasil (Vivo) | Comunicação |
| TIMS3 | TIM | Comunicação |
| TOTS3 | Totvs | Tecnologia |
| MULT3 | Multiplan | Imobiliário |

## Testes previstos (Fase 2)

- `tests/teste_catalogo.py` (novo): CA1–CA5, CA10, CA11, com SQLite temporário
  no mesmo padrão de `teste_logica.py` e `YfinanceService` substituído por um
  dublê que falha se for chamado (CA4).
- `tests/teste_interface.py` (ajuste): o fluxo atual usa
  `text_input(key="analiseItem")` e `text_input(key="backtestItem")`; passa a
  usar o seletor. Cobre CA6–CA9.

---

## Referências

- Catálogo atual: [`src/models/entities/ItensB3Entity.py`](../../../src/models/entities/ItensB3Entity.py),
  [`src/models/services/ItensB3Service.py`](../../../src/models/services/ItensB3Service.py)
- Seed manual: [`src/scripts/SeedItensB3.py`](../../../src/scripts/SeedItensB3.py)
- Inicialização: [`src/public/Main.py`](../../../src/public/Main.py),
  [`src/models/base.py`](../../../src/models/base.py)
- Telas: [`src/public/views/AnaliseView.py`](../../../src/public/views/AnaliseView.py),
  [`src/public/views/BacktestView.py`](../../../src/public/views/BacktestView.py),
  [`src/public/views/Paginas.py`](../../../src/public/views/Paginas.py)
