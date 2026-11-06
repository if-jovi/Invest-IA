# Spec — Análise com IA (resposta estruturada)

## Objetivo

Tornar a interpretação da resposta da IA confiável: em vez de ler texto livre
com expressões regulares, o sistema pede à IA uma resposta em JSON com campos
definidos e valida esse JSON antes de gravar.

## Audiência

- **Autor / devs** — critérios de aceite para implementar e testar.
- **Assistentes/agentes IA** — contrato da resposta da LLM.

---

> **Status:** implementada em 06/11/2026 (IA1–IA5 e IA7–IA9 em
> `tests/teste_analise_ia_json.py`; IA6 nos testes de cada provedor).
> Validação com Pydantic (`ClaudeService.RespostaIa`) e esquema em
> `ClaudeService.ESQUEMA_RESPOSTA`.

> **Revisão de 06/11/2026:** inclui o OpenRouter (provedor padrão, criado
> depois desta spec) e o `seed` fixo para respostas mais consistentes. A
> coluna `sobre_empresa` já existe (migração 0003).

## Contexto atual

- O prompt pede o formato `RECOMENDAÇÃO: / SOBRE A EMPRESA: / JUSTIFICATIVA: /
  RISCOS:` e `ClaudeService.extrairSecao` recorta o texto com regex.
- Variações de formatação (markdown, títulos diferentes) podem quebrar o recorte;
  a seção "Sobre a empresa" nem é gravada em coluna própria (é recalculada a
  partir de `resposta_completa`).

## Escopo

**Entra:**

1. Contrato JSON da resposta, pedido com o recurso de saída estruturada de cada
   provedor:
   - **OpenRouter:** `response_format` do tipo `json_schema` com `strict: true`;
   - **Gemini:** `response_mime_type="application/json"` + `response_json_schema`;
   - **Claude:** `output_config` com formato `json_schema`.

   O prompt também descreve o JSON esperado, para que o formato saia certo
   mesmo em modelos que não aceitam saída estruturada.
5. **Consistência:** `temperature` 0.3 (como hoje) e `seed` fixo (`SEED_IA`,
   padrão 42) onde o provedor aceita (OpenRouter e Gemini). Mesmos dados →
   resposta o mais estável possível.
2. Validação do JSON com um modelo (Pydantic) antes de criar a entidade.
3. Coluna `sobre_empresa` em `recomendacoes` (via migração; ver
   [`persistencia.md`](./persistencia.md)).
4. Riscos gravados como lista de itens (texto com um risco por linha).

**Fica de fora:**

- Mudar os indicadores enviados ou a regra de cache por ativo + data.
- Streaming da resposta.

## Contrato da resposta

```json
{
  "recomendacao": "COMPRA | VENDA | MANTER",
  "sobre_empresa": "2 a 3 frases sobre o que a empresa faz e o setor",
  "justificativa": "3 a 5 parágrafos curtos em português acessível",
  "riscos": ["risco 1", "risco 2"]
}
```

Regras: `recomendacao` só aceita os três valores; textos não vazios; `riscos`
com 1 a 8 itens não vazios.

## Critérios de aceite

| ID | Critério |
| -- | -------- |
| IA1 | OpenRouter, Gemini e Claude recebem o esquema JSON na chamada, cada um no seu formato (verificado na requisição simulada). |
| IA2 | Resposta válida vira `RecomendacoesEntity` com `recomendacao`, `sobre_empresa`, `justificativa` e `riscos` preenchidos. |
| IA3 | JSON inválido, campo faltando, `recomendacao` fora dos três valores ou `riscos` vazio → `RuntimeError` "A IA respondeu fora do formato esperado..." e nada é gravado. |
| IA4 | `resposta_completa` guarda o JSON recebido. |
| IA5 | Recomendações antigas (gravadas em texto, sem `sobre_empresa`) continuam exibidas: o DTO usa a coluna quando existe e cai no recorte do texto antigo quando ela está vazia. |
| IA6 | As traduções de erro atuais (chave, permissão, faturamento, modelo, limite, timeout, rede) continuam valendo. |
| IA7 | OpenRouter e Gemini enviam `seed` = `SEED_IA` (42 por padrão); Claude não envia `seed`. |
| IA9 | Resposta cortada pelo limite de tamanho → `RuntimeError` "A resposta da IA veio incompleta. Tente novamente." e nada é gravado. Vale para os três provedores: OpenRouter com `finish_reason = "length"`, Gemini com `finish_reason = MAX_TOKENS` e Claude com `stop_reason = "max_tokens"`. |
| IA8 | O prompt continua contendo os indicadores e o resumo do período ([`analise-periodo.md`](./analise-periodo.md)) e passa a descrever os quatro campos do JSON. |

## Casos-limite e erros

- **IA devolve texto com JSON dentro de bloco de código**: tratado como
  inválido se o SDK não entregar JSON puro (IA3); não tentar "consertar" texto.
- **Resposta bloqueada / vazia**: mensagens atuais.
- **Resposta cortada pelo limite de tamanho** (IA9). Achado em teste real em
  06/11/2026: o modelo padrão gasta parte do limite "raciocinando" e o JSON
  saiu pela metade. O sistema mostra uma mensagem própria em vez de "fora do
  formato". Antes do JSON, o recorte por texto aceitava a justificativa pela
  metade sem avisar.
- **Modelo do OpenRouter sem saída estruturada** (ex.: `nemotron-3.5-lightning:free`):
  a requisição é a mesma; se o texto devolvido não for o JSON válido, vale IA3.
  O modelo padrão (`nemotron-3.5-super-vl:free`) aceita saída estruturada.

---

## Referências

- [`src/models/services/ClaudeService.py`](../../../src/models/services/ClaudeService.py)
- [`src/models/services/GeminiService.py`](../../../src/models/services/GeminiService.py)
- [`src/models/services/OpenRouterService.py`](../../../src/models/services/OpenRouterService.py)
- [`src/models/services/RecomendacoesService.py`](../../../src/models/services/RecomendacoesService.py)
- [`src/models/entities/RecomendacoesEntity.py`](../../../src/models/entities/RecomendacoesEntity.py)
