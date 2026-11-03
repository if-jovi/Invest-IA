# Spec — Persistência (migrações e consultas)

## Objetivo

Permitir evoluir o banco sem apagar dados, corrigir o tipo da data de
referência das recomendações e eliminar consultas repetidas na carteira.

## Audiência

- **Autor / devs** — critérios de aceite.
- **Assistentes/agentes IA** — regras de evolução do schema.

---

## Contexto atual

- `criarTabelas()` usa `Base.metadata.create_all`, que não altera tabelas
  existentes: qualquer mudança de coluna exige `DROP TABLE` (dados perdidos).
  `alembic` está no `requirements.txt` mas não é usado.
- `recomendacoes.data_referencia` é `VARCHAR(10)` guardando `AAAA-MM-DD`.
- `RecomendacoesService.buscarUltimasPorItens` faz uma consulta por ativo (N+1).

## Escopo

**Entra:**

1. Alembic configurado; migração inicial = schema atual; migrações seguintes
   para `data_referencia` → `DATE` e para a coluna `sobre_empresa`
   ([`analise-ia.md`](./analise-ia.md)).
2. O app aplica as migrações pendentes na inicialização (substitui o
   `create_all`).
3. Banco já existente criado pelo `create_all` (sem tabela `alembic_version`)
   é reconhecido e marcado na revisão inicial antes de aplicar as seguintes,
   sem perder dados.
4. `buscarUltimasPorItens` em uma única consulta.

**Fica de fora:** trocar o banco, réplicas, backup.

## Critérios de aceite

| ID | Critério |
| -- | -------- |
| DB1 | Banco vazio: a inicialização cria todas as tabelas e a `alembic_version` fica na última revisão. |
| DB2 | Banco criado pelo schema atual com dados: a inicialização migra para a última revisão e as linhas existentes continuam lá, com `data_referencia` convertida para data. |
| DB3 | Rodar a inicialização duas vezes não falha nem duplica nada. |
| DB4 | `buscarUltimasPorItens` com N ativos executa uma única consulta SQL (contada no teste) e retorna a recomendação mais recente de cada um. |
| DB5 | O cache de recomendação por ativo + data continua funcionando com a data como `DATE`. |
| DB6 | As migrações rodam em PostgreSQL (app) e SQLite (testes). |

## Casos-limite e erros

- **`data_referencia` com valor fora do formato** no banco antigo: a migração
  falha com mensagem clara em vez de gravar data errada.
- **Falha de migração na inicialização**: tela de erro de conexão/banco atual;
  o app não sobe pela metade.

---

## Referências

- [`src/models/base.py`](../../../src/models/base.py)
- [`src/models/services/RecomendacoesService.py`](../../../src/models/services/RecomendacoesService.py)
- [`schema.sql`](../../../schema.sql)
