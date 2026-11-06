# Arquitetura — visão geral

## Objetivo

Mapear as camadas do InvestIA e o fluxo de uma análise, para localizar onde
cada responsabilidade mora no código.

## Audiência

- **Devs** — saber onde implementar uma mudança.
- **Assistentes/agentes IA** — mapa camada → diretório.

---

## Camadas

| Camada     | Diretório | Responsabilidade |
| ---------- | --------- | ---------------- |
| View       | [`src/public/views/`](../../../src/public/views/), [`src/public/paginas/`](../../../src/public/paginas/) | Telas Streamlit; só chamam controllers. `paginas/` são os arquivos do menu (`st.navigation`); `Estilo.py` concentra paleta e CSS |
| Controller | [`src/controllers/`](../../../src/controllers/) | Validação de entrada, levanta `ValueError` com mensagem ao usuário |
| Service    | [`src/models/services/`](../../../src/models/services/) | Regra de negócio, banco, integrações (Yahoo, IA) |
| Entity     | [`src/models/entities/`](../../../src/models/entities/) | Tabelas SQLAlchemy e dataclasses de transporte |

As sessões do banco são abertas por service (`with Session()`), e os services
devolvem dicionários (DTOs) às views, nunca entidades ligadas à sessão.

## Fluxo de uma análise

```
AnaliseView → AnaliseController.analisarVarios(itens, periodo)   # até 5, 2 em paralelo
  → AnaliseService.analisar(item)              # para cada ativo:
  → ItensB3Service.obterOuCadastrar(item)      # valida e garante o ativo no catálogo
  → YfinanceService.buscarHistorico(item)      # histórico de preços (.SA)
  → IndicatorsService.calcular(...)            # RSI, MACD, SMA20/50
  → RecomendacoesService.buscarPorItemEData()  # reaproveita a recomendação do mesmo dia
  → criarServicoIa().gerarRecomendacao(...)    # OpenRouter (padrão), Gemini ou Claude
  → RecomendacoesService.salvar(...)
```

O provedor de IA é escolhido por `IA_PROVEDOR` no `.env`
([`IaService.py`](../../../src/models/services/IaService.py)). `OpenRouterService`
e `GeminiService` herdam de `ClaudeService` o prompt e a interpretação da resposta.

## Cotações da carteira

`CarteiraService.obterResumo` → `YfinanceService.buscarCotacoes(itens)`: uma
chamada `yf.download` para todos os ativos, cache de 60 s por ativo (30 s após
falha). A tela recarrega o resumo a cada 60 s via `st.fragment(run_every=60)`.

## Inicialização

`Main.py` chama `criarTabelas()` e `ItensB3Service.semearCatalogo()` uma vez por
processo (`st.cache_resource`). `criarTabelas()` aplica as migrações Alembic pendentes (`migracoes/`), sem perder dados; antes era o `create_all`, que não altera
as existentes; o seed insere só as ações do JSON que ainda não estão no banco.

---

## Referências

- Entrada: [`src/public/Main.py`](../../../src/public/Main.py)
- Banco: [`src/models/base.py`](../../../src/models/base.py)
- Análise: [`src/models/services/AnaliseService.py`](../../../src/models/services/AnaliseService.py)
