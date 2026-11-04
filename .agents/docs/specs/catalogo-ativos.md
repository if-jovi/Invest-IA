# Spec — Catálogo de ativos da B3 e autocomplete

## Objetivo

Deixar o sistema com a lista completa de ações negociadas na B3 e usá-la como
autocomplete nos campos de ativo (Análise, Backtesting e compra na Carteira),
para o usuário buscar por código ou nome em vez de digitar o ticker de memória.

## Audiência

- **Autor / devs** — critérios de aceite para implementar e testar.
- **Assistentes/agentes IA** — fonte de verdade do comportamento do catálogo.

---

## Contexto atual

- A tabela `itens_b3` (`item`, `nome`, `setor`, `ativo`) só ganha linhas quando
  alguém analisa ou compra um ativo: `ItensB3Service.obterOuCadastrar` valida o
  código no Yahoo e grava.
- `src/scripts/SeedItensB3.py` tem 10 códigos fixos, é manual e consulta o Yahoo
  para cada um (lento e sujeito ao erro 429).
- Análise, Backtesting e o formulário de compra usam `text_input` livre.
- Não foi encontrado repositório no GitHub mantido com a lista completa; a
  fonte escolhida é a API pública da [brapi.dev](https://brapi.dev)
  (`GET /api/quote/list`, gratuita e sem token), que devolve ~780 registros
  `type = "stock"` com nome e setor; descartados os códigos do mercado
  fracionário (`PETR4F`), restam **~377 ações** (inclui units como `KLBN11`).
  Verificado em 04/11/2026.

## Escopo

**Entra:**

1. Arquivo versionado `src/data/ativos_b3.json` com as ações da B3
   (`item`, `nome`, `setor`), gerado a partir da brapi.
2. Script `python -m src.scripts.AtualizarCatalogoB3` que baixa a lista da
   brapi, filtra `type == "stock"`, traduz o setor e regrava o JSON (uso manual,
   quando o autor quiser atualizar o catálogo).
3. Seed automático e **offline** na inicialização do app (junto de
   `criarTabelas()`), lendo o JSON — nenhuma chamada de rede.
4. Autocomplete (seletor com busca) nos campos de ativo:
   - **Análise**: seleção de vários ativos (ver
     [`analise-multipla.md`](./analise-multipla.md));
   - **Backtesting**: seleção de um ativo;
   - **Carteira › Registrar compra**: seleção de um ativo.
   Todos aceitam digitar um código fora da lista (`accept_new_options=True`,
   Streamlit ≥ 1.66 — ver [`interface.md`](./interface.md)).
5. `SeedItensB3` sem argumentos passa a gravar o catálogo do JSON (offline);
   com argumentos mantém o comportamento atual (valida no Yahoo).

**Fica de fora:**

- FIIs, ETFs e BDRs (decisão do autor: só ações).
- Consultar a brapi em tempo de execução do app (só o script de atualização a
  acessa).
- Atualização automática/agendada do JSON.
- Tela de administração do catálogo (ativar/desativar fica pelo banco/pgAdmin).

## Comportamento

### Formato do JSON

```json
[
  {"item": "PETR4", "nome": "PETROBRAS PN", "setor": "Energia"},
  {"item": "VALE3", "nome": "VALE ON", "setor": "Materiais Básicos"}
]
```

- Ordenado por `item`, sem códigos repetidos.
- `item` sem o sufixo `.SA` e válido para `ItensB3Service.validarFormato`;
  ativos da brapi com código fora desse formato são descartados pelo script.
- `nome` como vem da brapi (sem reescrita de caixa).
- `setor` traduzido para pt-BR pela tabela `SETORES_BRAPI` do script; setor
  ausente ou não mapeado vira `"Não disponível"`.

### Script de atualização

- Sucesso: grava o JSON e imprime quantos ativos foram gravados.
- Falha de rede, HTTP ≠ 200 ou resposta sem a chave `stocks`: termina com
  código de saída ≠ 0, mensagem clara, e **não** sobrescreve o JSON existente.
- Resposta com menos de 300 ações (sinal de resposta truncada): mesmo
  tratamento de falha.

### Seed

- Na inicialização, para cada ativo do JSON **ausente** em `itens_b3`, insere
  `item`, `nome`, `setor` e `ativo = TRUE`, em uma única transação.
- Ativo que **já existe** não é alterado (preserva nome vindo do Yahoo e um
  `ativo = FALSE` definido manualmente).
- JSON ausente ou inválido: o app sobe normalmente sem seed e registra aviso
  no log (o catálogo só fica menor; não é erro fatal).

### Seletor (autocomplete)

- Opções: ativos de `itens_b3` com `ativo = TRUE`, ordenados pelo código, com
  rótulo `CÓDIGO — Nome`, ex.: `PETR4 — PETROBRAS PN`. A busca do componente
  filtra tanto pelo código quanto pelo nome. Inclui ativos que usuários
  cadastraram ao analisar códigos fora do catálogo.
- A lista é carregada uma vez e reaproveitada (`st.cache_data`, validade de
  10 min) para não consultar o banco a cada interação.
- Código digitado fora da lista: vale o fluxo atual (normalização, validação de
  formato, consulta ao Yahoo, cadastro no catálogo).
- O valor enviado ao controller continua sendo o código (`PETR4`); as
  assinaturas de `BacktestController.executar` e
  `ItensCarteiraController.adicionarCompra` não mudam.
- Os atalhos "Analisar"/"Backtesting" da Carteira abrem a página com o ativo
  já selecionado.

## Critérios de aceite

| ID   | Critério |
| ---- | -------- |
| CA1  | Com o banco vazio, após `criarTabelas()` + seed, `itens_b3` contém todos os códigos do JSON com nome, setor e `ativo = TRUE`. |
| CA2  | Rodar o seed duas vezes não duplica linhas nem levanta erro. |
| CA3  | Um ativo pré-existente com nome diferente ou `ativo = FALSE` mantém seus valores após o seed. |
| CA4  | O seed não chama o `YfinanceService` nem faz requisição HTTP. |
| CA5  | `ItensB3Service.listarAtivos()` devolve os ativos com `ativo = TRUE` ordenados por código; ativos com `ativo = FALSE` não aparecem. |
| CA6  | O JSON versionado tem ≥ 300 ações, sem códigos repetidos, ordenado, e todo `item` passa em `validarFormato`; contém `PETR4`, `VALE3`, `ITUB4` e `KLBN11`. |
| CA7  | O script, com a brapi simulada devolvendo ações, fundos e BDRs, grava só `type == "stock"`, com setor traduzido e códigos inválidos descartados. |
| CA8  | O script, com a brapi simulada falhando (erro de rede, HTTP 500, payload sem `stocks` ou < 300 ações), sai com código ≠ 0 e o JSON anterior fica intacto. |
| CA9  | JSON ausente ou corrompido: a inicialização do app não falha. |
| CA10 | Na Análise, Backtesting e Registrar compra, o campo de ativo é um seletor com as opções do catálogo no formato `CÓDIGO — Nome`. |
| CA11 | Nos três seletores, digitar um código válido fora do catálogo funciona e cadastra o ativo; ele passa a constar na lista. |
| CA12 | O atalho "Analisar" da Carteira abre a Análise com o ativo selecionado; o atalho "Backtesting" idem. |
| CA13 | `python -m src.scripts.SeedItensB3` sem argumentos grava o catálogo do JSON sem acessar a internet; com argumentos mantém a validação pelo Yahoo. |

## Casos-limite e erros

- **Catálogo vazio no banco** (ex.: todos desativados): o seletor fica sem
  opções, mas continua aceitando código digitado.
- **Nada selecionado**: mensagem atual "Informe o código do ativo." (Backtesting
  e compra).
- **Código digitado em minúsculas ou com `.SA`**: normalizado (`petr4.sa` →
  `PETR4`); se já existe na lista, usa o ativo existente.
- **Ticker do catálogo que deixou de existir no Yahoo**: aparece na lista; ao
  usar, mostra o erro atual "Nenhum dado encontrado para X.SA.".
- **Falha de banco no seed**: mesma tela de erro de conexão que já existe em
  `Main.py`.

## Testes previstos (Fase 2)

- `tests/teste_catalogo.py` (novo): CA1–CA9, CA13, com SQLite temporário no
  padrão de `teste_logica.py`, `YfinanceService` substituído por dublê que
  falha se chamado (CA4) e brapi simulada via `httpx.MockTransport` (CA7, CA8).
- `tests/teste_interface.py` (ajuste): CA10–CA12 com `AppTest`.

---

## Referências

- Catálogo: [`src/models/entities/ItensB3Entity.py`](../../../src/models/entities/ItensB3Entity.py),
  [`src/models/services/ItensB3Service.py`](../../../src/models/services/ItensB3Service.py)
- Seed manual: [`src/scripts/SeedItensB3.py`](../../../src/scripts/SeedItensB3.py)
- Inicialização: [`src/public/Main.py`](../../../src/public/Main.py),
  [`src/models/base.py`](../../../src/models/base.py)
- Telas: [`src/public/views/AnaliseView.py`](../../../src/public/views/AnaliseView.py),
  [`src/public/views/BacktestView.py`](../../../src/public/views/BacktestView.py),
  [`src/public/views/CarteiraDashboard.py`](../../../src/public/views/CarteiraDashboard.py)
- Fonte dos dados: <https://brapi.dev/api/quote/list>
