# Primeiros passos

## Objetivo

Subir o InvestIA localmente com Docker e rodar os testes.

## Audiência

- **Devs** — setup do ambiente.
- **Assistentes/agentes IA** — comandos canônicos de execução e teste.

---

## Subir o sistema

1. Copie `.env.example` para `.env` e preencha `OPENROUTER_API_KEY`.
2. `docker compose up --build`
3. App: http://localhost:8501 · pgAdmin: http://localhost:5051
   (admin@admin.com / admin)

## Diagnóstico das integrações

```sh
docker compose exec app python -m src.scripts.Diagnostico
docker compose exec app python -m src.scripts.Diagnostico --completo
```

## Testes

```sh
docker compose exec app python -m tests.executar_todos
```

Cada bateria é um script com `assert`s rodado em subprocesso; banco SQLite
temporário, Yahoo, IA e brapi simulados (sem internet nem créditos).

Sem o container do app, os testes rodam em qualquer `python:3.11` com o
projeto montado e `pip install -r requirements.txt`.

## Atualizar a lista de ações

```sh
docker compose exec app python -m src.scripts.AtualizarCatalogoB3
docker compose exec app python -m src.scripts.SeedItensB3
```

---

## Referências

- [`docker-compose.yml`](../../../docker-compose.yml)
- [`tests/executar_todos.py`](../../../tests/executar_todos.py)
- [`src/scripts/Diagnostico.py`](../../../src/scripts/Diagnostico.py)
