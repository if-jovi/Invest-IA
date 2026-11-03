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
| View       | [`src/public/views/`](../../../src/public/views/) | Telas Streamlit; só chamam controllers |
| Controller | [`src/controllers/`](../../../src/controllers/) | Validação de entrada, levanta `ValueError` com mensagem ao usuário |
| Service    | [`src/models/services/`](../../../src/models/services/) | Regra de negócio, banco, integrações (Yahoo, IA) |
| Entity     | [`src/models/entities/`](../../../src/models/entities/) | Tabelas SQLAlchemy e dataclasses de transporte |

As sessões do banco são abertas por service (`with Session()`), e os services
devolvem dicionários (DTOs) às views, nunca entidades ligadas à sessão.

## Fluxo de uma análise

```
AnaliseView → AnaliseController.analisar(item, periodo)
  → ItensB3Service.obterOuCadastrar(item)      # valida e garante o ativo no catálogo
  → YfinanceService.buscarHistorico(item)      # histórico de preços (.SA)
  → IndicatorsService.calcular(...)            # RSI, MACD, SMA20/50
  → RecomendacoesService.buscarPorItemEData()  # reaproveita a recomendação do mesmo dia
  → criarServicoIa().gerarRecomendacao(...)    # Gemini (padrão) ou Claude
  → RecomendacoesService.salvar(...)
```

O provedor de IA é escolhido por `IA_PROVEDOR` no `.env`
([`IaService.py`](../../../src/models/services/IaService.py)). `GeminiService`
herda de `ClaudeService` o prompt e a interpretação da resposta.

## Inicialização

`Main.py` chama `criarTabelas()` uma vez por processo (`st.cache_resource`).
`create_all` cria tabelas ausentes, mas não altera as existentes.

---

## Referências

- Entrada: [`src/public/Main.py`](../../../src/public/Main.py)
- Banco: [`src/models/base.py`](../../../src/models/base.py)
- Análise: [`src/models/services/AnaliseService.py`](../../../src/models/services/AnaliseService.py)
