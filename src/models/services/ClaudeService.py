import logging
import os
import re
from typing import List, Literal, Optional
import anthropic
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from src.models.Parametros import ANTHROPIC_API_KEY, CLAUDE_MODEL, ROTULOS_PERIODO
from src.models.entities.RecomendacoesEntity import RecomendacoesEntity, TipoRecomendacao
from src.models.entities.StockEntity import StockEntity, IndicatorsEntity

logger = logging.getLogger(__name__)

TIMEOUT_SEGUNDOS = 60.0
TENTATIVAS = 2

TITULOS = {
    "RECOMENDACAO": r"RECOMENDA[ÇC][ÃA]O",
    "SOBRE_EMPRESA": r"SOBRE\s+A\s+EMPRESA",
    "JUSTIFICATIVA": r"JUSTIFICATIVA",
    "RISCOS": r"RISCOS",
}
ALTERNATIVA_TITULOS = "|".join(TITULOS.values())
MENSAGEM_FORMATO = "A IA respondeu fora do formato esperado (COMPRA, VENDA ou MANTER). Tente novamente."
MENSAGEM_CORTADA = "A resposta da IA veio incompleta. Tente novamente."
MAXIMO_RISCOS = 8

# Contrato da resposta (spec analise-ia.md). Enviado como saída estruturada a cada provedor.
ESQUEMA_RESPOSTA = {
    "type": "object",
    "properties": {
        "recomendacao": {"type": "string", "enum": ["COMPRA", "VENDA", "MANTER"]},
        "sobre_empresa": {"type": "string"},
        "justificativa": {"type": "string"},
        "riscos": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["recomendacao", "sobre_empresa", "justificativa", "riscos"],
    "additionalProperties": False,
}


class RespostaIa(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recomendacao: Literal["COMPRA", "VENDA", "MANTER"]
    sobre_empresa: str
    justificativa: str
    riscos: List[str] = Field(min_length=1, max_length=MAXIMO_RISCOS)

    @field_validator("sobre_empresa", "justificativa")
    @classmethod
    def textoPreenchido(cls, valor: str) -> str:
        if not valor.strip():
            raise ValueError("texto vazio")
        return valor.strip()

    @field_validator("riscos")
    @classmethod
    def riscosPreenchidos(cls, valores: List[str]) -> List[str]:
        if any(not v.strip() for v in valores):
            raise ValueError("risco vazio")
        return [v.strip() for v in valores]


def numeroBr(valor: float) -> str:
    texto = f"{abs(valor):,.2f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def pctComSinal(valor: float) -> str:
    sinal = "+" if valor > 0 else "-" if valor < 0 else ""
    return f"{sinal}{numeroBr(valor)}%"


def secaoPeriodo(ind: IndicatorsEntity) -> str:
    resumo = ind.resumo_periodo
    if not resumo:
        return ""
    rotulo = ROTULOS_PERIODO.get(ind.periodo, ind.periodo or "período escolhido")
    return f"""
## Comportamento no período analisado (horizonte: {rotulo})
- Retorno no período: {pctComSinal(resumo["retornoPct"])}
- Máxima: R$ {numeroBr(resumo["maxima"])} (preço atual {numeroBr(resumo["distanciaMaximaPct"])}% abaixo) | Mínima: R$ {numeroBr(resumo["minima"])} (preço atual {numeroBr(resumo["distanciaMinimaPct"])}% acima)
- Volatilidade anualizada: {numeroBr(resumo["volatilidadeAnualPct"])}%
- Maior queda (drawdown máximo): {pctComSinal(resumo["drawdownMaximoPct"])}
{linhaIbovespa(ind)}"""


def linhaIbovespa(ind: IndicatorsEntity) -> str:
    ibovespa = getattr(ind, "ibovespa", None)
    if not ibovespa:
        return ""
    lado = "abaixo" if ibovespa["diferencaPct"] < 0 else "acima"
    return (f"- Ibovespa no mesmo período: {pctComSinal(ibovespa['retornoPct'])} "
            f"(a ação ficou {numeroBr(ibovespa['diferencaPct'])} p.p. {lado} do índice)\n")


def regraPeriodo(ind: IndicatorsEntity) -> str:
    if not ind.resumo_periodo:
        return ""
    regras = "- Considere o horizonte informado: a recomendação vale para quem acompanha o ativo nessa janela de tempo.\n"
    if getattr(ind, "ibovespa", None):
        regras += "- Compare o desempenho da ação com o do Ibovespa no mesmo período.\n"
    return regras


class ClaudeService:

    def montarPrompt(self, stock: StockEntity, ind: IndicatorsEntity) -> str:
        return f"""Você é um analista financeiro especializado em análise técnica de ações da B3 e explica tudo para investidores iniciantes, em português simples e sem jargão desnecessário.

Com base nos dados abaixo, gere uma recomendação de COMPRA, VENDA ou MANTER.

## Empresa
- Código: {stock.item}
- Nome: {stock.nome}
- Setor: {stock.setor}
- Segmento: {stock.segmento}
- Descrição (fonte em inglês, resuma em português): {stock.descricao[:600]}

## Indicadores técnicos (referência: {ind.data_referencia})
- Preço: R$ {ind.preco_atual}
- RSI (14 períodos): {ind.rsi} ({ind.sinal_rsi})
- MACD: {ind.macd} | Linha de sinal: {ind.macd_signal} | Cruzamento: {ind.macd_cruzamento}
- Média móvel de 20 períodos: R$ {ind.sma_short} | Média móvel de 50 períodos: R$ {ind.sma_long} | Tendência: {ind.tendencia_sma}
{secaoPeriodo(ind)}
Regras:
- Use apenas os dados acima. Não invente notícias, balanços ou números que não foram fornecidos.
- A recomendação é apoio à decisão e nunca uma garantia de retorno.
- Explique cada indicador em linguagem simples e mostre como ele sustenta a recomendação.
{regraPeriodo(ind)}
Responda APENAS com um objeto JSON (sem markdown e sem texto antes ou depois), com exatamente estes campos:
{{
  "recomendacao": "COMPRA" ou "VENDA" ou "MANTER",
  "sobre_empresa": "2 a 3 frases explicando o que a empresa faz e em qual setor atua",
  "justificativa": "3 a 5 parágrafos curtos em português acessível, separados por uma linha em branco",
  "riscos": ["de 1 a {MAXIMO_RISCOS} riscos principais, um por item"]
}}
"""

    @staticmethod
    def extrairSecao(texto: str, chave: str) -> str:
        padrao = (
            r"(?:^|\n)[ \t]*[*#_]*[ \t]*" + TITULOS[chave] + r"[ \t]*[*#_]*[ \t]*:[ \t]*[*#_]*[ \t]*"
            r"(.*?)"
            r"(?=\n[ \t]*[*#_]*[ \t]*(?:" + ALTERNATIVA_TITULOS + r")[ \t]*[*#_]*[ \t]*:|\Z)"
        )
        resultado = re.search(padrao, texto or "", re.IGNORECASE | re.DOTALL)
        return resultado.group(1).strip() if resultado else ""

    def identificarTipo(self, texto: str) -> Optional[str]:
        trecho = self.extrairSecao(texto, "RECOMENDACAO").upper()
        posicoes = {
            tipo.value: trecho.find(tipo.value) for tipo in TipoRecomendacao if tipo.value in trecho
        }
        if not posicoes:
            return None
        return min(posicoes, key=posicoes.get)

    def interpretar(self, texto: str, ind: IndicatorsEntity) -> RecomendacoesEntity:
        try:
            resposta = RespostaIa.model_validate_json((texto or "").strip())
        except ValidationError as erro:
            logger.warning("Resposta da IA fora do contrato JSON: %s", erro.errors(include_url=False)[:3])
            raise RuntimeError(MENSAGEM_FORMATO)

        return RecomendacoesEntity(
            item=ind.item,
            data_referencia=ind.data_referencia,
            preco_atual=ind.preco_atual,
            rsi=ind.rsi,
            sinal_rsi=ind.sinal_rsi,
            macd=ind.macd,
            macd_signal=ind.macd_signal,
            macd_cruzamento=ind.macd_cruzamento,
            sma20=ind.sma_short,
            sma50=ind.sma_long,
            tendencia_sma=ind.tendencia_sma,
            recomendacao=resposta.recomendacao,
            sobre_empresa=resposta.sobre_empresa,
            justificativa=resposta.justificativa,
            riscos="\n".join(f"- {risco}" for risco in resposta.riscos),
            resposta_completa=texto,
        )

    def modelo(self) -> str:
        return os.getenv("CLAUDE_MODEL") or CLAUDE_MODEL

    def traduzirErro(self, erro: anthropic.APIError) -> Exception:
        if isinstance(erro, anthropic.AuthenticationError):
            return RuntimeError("Chave da API da Anthropic inválida. Confira ANTHROPIC_API_KEY no arquivo .env.")
        if isinstance(erro, anthropic.PermissionDeniedError):
            return RuntimeError("A chave da API não tem permissão para usar este modelo.")
        if isinstance(erro, anthropic.NotFoundError):
            return RuntimeError(
                f"O modelo '{self.modelo()}' não foi encontrado. Ajuste CLAUDE_MODEL no arquivo .env."
            )
        if isinstance(erro, anthropic.RateLimitError):
            return RuntimeError("Limite de requisições da API da Anthropic atingido. Tente novamente em instantes.")
        if isinstance(erro, anthropic.APITimeoutError):
            return RuntimeError("A IA demorou demais para responder. Tente novamente.")
        if isinstance(erro, anthropic.APIConnectionError):
            return RuntimeError("Não foi possível conectar à API da Anthropic. Verifique a internet do servidor.")
        if isinstance(erro, anthropic.InternalServerError):
            return RuntimeError("A API da Anthropic está com instabilidade no momento. Tente novamente.")
        return RuntimeError(f"Falha ao consultar a IA: {erro}")

    def extrairTexto(self, resposta) -> str:
        if getattr(resposta, "stop_reason", None) == "refusal":
            raise RuntimeError("A IA não pôde responder a esta solicitação.")
        if getattr(resposta, "stop_reason", None) == "max_tokens":
            raise RuntimeError(MENSAGEM_CORTADA)
        texto = "".join(
            bloco.text for bloco in (resposta.content or []) if getattr(bloco, "type", "text") == "text"
        ).strip()
        if not texto:
            raise RuntimeError("A IA não retornou texto para esta análise. Tente novamente.")
        return texto

    def gerarRecomendacao(self, stock: StockEntity, ind: IndicatorsEntity) -> RecomendacoesEntity:
        if not ANTHROPIC_API_KEY:
            raise ValueError("A chave ANTHROPIC_API_KEY não está configurada no arquivo .env.")

        try:
            cliente = anthropic.Anthropic(
                api_key=ANTHROPIC_API_KEY, timeout=TIMEOUT_SEGUNDOS, max_retries=TENTATIVAS
            )
            resposta = cliente.messages.create(
                model=self.modelo(),
                max_tokens=1500,
                messages=[{"role": "user", "content": self.montarPrompt(stock, ind)}],
                output_config={"format": {"type": "json_schema", "schema": ESQUEMA_RESPOSTA}},
            )
        except anthropic.APIError as erro:
            logger.warning("Falha na chamada à API da Anthropic: %r", erro)
            raise self.traduzirErro(erro)

        return self.interpretar(self.extrairTexto(resposta), ind)
