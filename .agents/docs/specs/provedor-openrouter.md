# Spec — Provedor de IA OpenRouter (modelos NVIDIA gratuitos)

## Objetivo

Conectar o InvestIA ao [OpenRouter](https://openrouter.ai) para gerar as
recomendações com modelos NVIDIA Nemotron **gratuitos**, tornando-o o provedor
padrão do sistema.

## Audiência

- **Autor / devs** — critérios de aceite para implementar e testar.
- **Assistentes/agentes IA** — contrato da integração.

---

> **Status:** implementada em 04/11/2026 (`tests/teste_openrouter.py`).
> Revisada em 06/11/2026: `max_tokens` 8192 e raciocínio `low`.

## Contexto atual

- `criarServicoIa()` escolhe entre `GeminiService` (padrão) e `ClaudeService`
  por `IA_PROVEDOR`. Ambos usam o mesmo prompt em texto
  (`ClaudeService.montarPrompt`) e o mesmo recorte da resposta
  (`ClaudeService.interpretar`).
- O OpenRouter expõe uma API compatível com OpenAI em
  `https://openrouter.ai/api/v1/chat/completions`. Modelos gratuitos têm o
  sufixo `:free` e limites de uso (por minuto e por dia).
- Modelos NVIDIA gratuitos disponíveis em 04/11/2026 incluem
  `nvidia/nemotron-3.5-super-vl:free` e `nvidia/nemotron-3.5-lightning:free`.

## Escopo

**Entra:**

1. `OpenRouterService` (herda de `ClaudeService`: reaproveita prompt e
   interpretação), chamando o endpoint via `httpx` (sem dependência nova).
2. `IA_PROVEDOR` passa a aceitar `openrouter` e o **padrão** passa a ser
   `openrouter`. Gemini e Claude continuam como opções.
3. Variáveis no `.env`: `OPENROUTER_API_KEY`, `OPENROUTER_MODEL` (padrão
   `nvidia/nemotron-3.5-super-vl:free`).
4. **Somente modelos gratuitos**: modelo sem o sufixo `:free` é recusado antes
   de qualquer chamada.
5. Tradução dos erros da API para mensagens em português.
6. `testarConexao()` usado pelo `src/scripts/Diagnostico.py`.
7. `.env.example`, `docker-compose.yml` (se repassar variáveis) e `README.md`
   atualizados.

**Fica de fora:**

- Modelos pagos e controle de créditos.
- Lista de modelos de reserva (fallback automático entre modelos).
- Saída estruturada em JSON (continua o formato em texto; ver
  [`analise-ia.md`](./analise-ia.md), adiado).
- Streaming da resposta.

## Comportamento

### Requisição

- `POST {OPENROUTER_BASE_URL ou https://openrouter.ai/api/v1}/chat/completions`
- Cabeçalhos: `Authorization: Bearer <OPENROUTER_API_KEY>`,
  `X-Title: InvestIA`.
- Corpo: `model`, `messages = [{"role": "user", "content": <prompt>}]`,
  `temperature = 0.3`, `max_tokens = 8192` e `reasoning = {"effort": "low"}`.
  - **Revisão de 06/11/2026:** antes era `max_tokens = 4096`, sem `reasoning`.
    O modelo padrão "raciocina" antes de responder, e esse raciocínio consome o
    mesmo limite. Num teste real, 2.889 de 3.313 tokens foram de raciocínio, e
    uma resposta saiu cortada.
  - Esforço baixo reduz o raciocínio e o tempo de resposta. O limite maior dá
    folga (o modelo aceita até 131.072 tokens de saída, sem custo).
  - Ver também [`analise-ia.md`](./analise-ia.md) (IA9, resposta cortada).
- Timeout de 90 s; até 2 tentativas apenas para erro de rede/timeout
  (não repete 4xx).

### Resposta

- Texto = `choices[0].message.content`. Vazio ou ausente → erro "A IA não
  retornou texto para esta análise. Tente novamente."
- Corpo HTTP 200 contendo a chave `error` (o OpenRouter faz isso quando o
  provedor do modelo falha) → tratado como erro, usando `error.code` para a
  tradução.
- O texto segue para `interpretar()`, igual aos demais provedores; o modelo
  usado fica gravado como hoje.

### Erros traduzidos

| Situação | Mensagem |
| -------- | -------- |
| Chave não configurada | `ValueError`: "A chave OPENROUTER_API_KEY não está configurada no arquivo .env." |
| Modelo sem `:free` | `ValueError`: "Apenas modelos gratuitos do OpenRouter são permitidos (terminados em ':free'). Ajuste OPENROUTER_MODEL no arquivo .env." |
| 401 | "Chave da API do OpenRouter inválida. Confira OPENROUTER_API_KEY no arquivo .env." |
| 402 | "O OpenRouter recusou a solicitação por falta de créditos. Confira se o modelo configurado é gratuito." |
| 404 | "O modelo '<modelo>' não foi encontrado no OpenRouter. Ajuste OPENROUTER_MODEL no arquivo .env." |
| 429 | "Limite de uso do modelo gratuito atingido no OpenRouter. Aguarde cerca de um minuto e tente novamente." |
| ≥ 500 / 502 / 503 | "O OpenRouter ou o provedor do modelo está instável. Tente novamente em instantes." |
| Timeout | "A IA demorou demais para responder. Tente novamente." |
| Falha de rede | "Não foi possível conectar à API do OpenRouter. Verifique a internet do servidor." |
| Outros | "Falha ao consultar a IA: <mensagem>" |

Todas, exceto as duas primeiras, são `RuntimeError` (mesmo padrão do Gemini).

## Critérios de aceite

| ID | Critério |
| -- | -------- |
| OR1 | Sem `IA_PROVEDOR` definido, `criarServicoIa()` devolve `OpenRouterService`; `gemini` e `claude` continuam funcionando; valor inválido levanta o `ValueError` atual citando também `openrouter`. |
| OR2 | Sem `OPENROUTER_MODEL`, o modelo enviado é `nvidia/nemotron-3.5-super-vl:free`. |
| OR3 | A requisição vai para `/chat/completions` com `Authorization: Bearer`, o prompt de `montarPrompt` em `messages[0].content` e `temperature` 0.3, `max_tokens` 8192 e `reasoning` `{"effort": "low"}` (verificado em requisição simulada). |
| OR4 | Resposta válida vira `RecomendacoesEntity` com recomendação, sobre a empresa, justificativa e riscos, igual aos demais provedores. |
| OR5 | Modelo configurado sem `:free` levanta o `ValueError` da tabela e nenhuma requisição é feita. |
| OR6 | Chave ausente levanta o `ValueError` da tabela e nenhuma requisição é feita. |
| OR7 | Cada status/condição da tabela de erros (401, 402, 404, 429, 500, `error` em corpo 200, conteúdo vazio, timeout, falha de rede) gera a mensagem correspondente. |
| OR8 | Erro 4xx não é repetido; timeout é tentado no máximo 2 vezes. |
| OR9 | `testarConexao()` com resposta simulada devolve texto citando "OpenRouter" e o modelo. |
| OR10 | `.env.example` documenta `IA_PROVEDOR=openrouter`, `OPENROUTER_API_KEY` e `OPENROUTER_MODEL`. |

## Casos-limite e erros

- **Modelo com espaços ou maiúsculas no `.env`**: usa `strip()`; a checagem do
  sufixo `:free` diferencia maiúsculas (o id do OpenRouter é minúsculo).
- **Modelo gratuito que exige o prompt registrado para treino** (política de
  privacidade da conta): o OpenRouter devolve 404/400 com mensagem própria;
  cai em "Falha ao consultar a IA: <mensagem>" mostrando o texto do OpenRouter.
- **Limites do plano gratuito** afetam a análise de vários ativos; ver
  [`analise-multipla.md`](./analise-multipla.md). A conta do autor (verificada
  em 04/11/2026) está no plano gratuito sem créditos: o OpenRouter limita
  modelos `:free` a ~20 requisições/minuto e ~50/dia nessa situação. O cache de
  recomendação por ativo + data reduz o consumo.

## Testes previstos (Fase 2)

- `tests/teste_openrouter.py` (novo), no padrão de `teste_gemini.py`, com
  `httpx.MockTransport`: OR1–OR10. Entra na lista de
  `tests/executar_todos.py`.

---

## Referências

- [`src/models/services/IaService.py`](../../../src/models/services/IaService.py)
- [`src/models/services/ClaudeService.py`](../../../src/models/services/ClaudeService.py)
- [`src/models/services/GeminiService.py`](../../../src/models/services/GeminiService.py)
- [`src/scripts/Diagnostico.py`](../../../src/scripts/Diagnostico.py)
- [`.env.example`](../../../.env.example)
- API: <https://openrouter.ai/docs/api-reference/chat-completion>
