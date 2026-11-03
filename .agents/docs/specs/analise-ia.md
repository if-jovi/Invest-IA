# Spec — Análise com IA (resposta estruturada)

## Objetivo

Tornar a interpretação da resposta da IA confiável: em vez de ler texto livre
com expressões regulares, o sistema pede à IA uma resposta em JSON com campos
definidos e valida esse JSON antes de gravar.

## Audiência

- **Autor / devs** — critérios de aceite para implementar e testar.
- **Assistentes/agentes IA** — contrato da resposta da LLM.

---

## Contexto atual

- O prompt pede o formato `RECOMENDAÇÃO: / SOBRE A EMPRESA: / JUSTIFICATIVA: /
  RISCOS:` e `ClaudeService.extrairSecao` recorta o texto com regex.
- Variações de formatação (markdown, títulos diferentes) podem quebrar o recorte;
  a seção "Sobre a empresa" nem é gravada em coluna própria (é recalculada a
  partir de `resposta_completa`).

## Escopo

**Entra:**

1. Contrato JSON da resposta, pedido com o recurso de saída estruturada de cada
   SDK (Gemini: `response_json_schema`; Claude: saída estruturada do SDK).
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
| IA1 | Gemini e Claude recebem o esquema JSON na chamada (verificado na requisição simulada). |
| IA2 | Resposta válida vira `RecomendacoesEntity` com `recomendacao`, `sobre_empresa`, `justificativa` e `riscos` preenchidos. |
| IA3 | JSON inválido, campo faltando, `recomendacao` fora dos três valores ou `riscos` vazio → `RuntimeError` "A IA respondeu fora do formato esperado..." e nada é gravado. |
| IA4 | `resposta_completa` guarda o JSON recebido. |
| IA5 | Recomendações antigas (gravadas em texto, sem `sobre_empresa`) continuam exibidas: o DTO usa a coluna quando existe e cai no recorte do texto antigo quando ela está vazia. |
| IA6 | As traduções de erro atuais (chave, permissão, faturamento, modelo, limite, timeout, rede) continuam valendo. |

## Casos-limite e erros

- **IA devolve texto com JSON dentro de bloco de código**: tratado como
  inválido se o SDK não entregar JSON puro (IA3); não tentar "consertar" texto.
- **Resposta bloqueada / vazia**: mensagens atuais.

---

## Referências

- [`src/models/services/ClaudeService.py`](../../../src/models/services/ClaudeService.py)
- [`src/models/services/GeminiService.py`](../../../src/models/services/GeminiService.py)
- [`src/models/services/RecomendacoesService.py`](../../../src/models/services/RecomendacoesService.py)
- [`src/models/entities/RecomendacoesEntity.py`](../../../src/models/entities/RecomendacoesEntity.py)
