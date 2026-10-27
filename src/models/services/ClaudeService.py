import logging
import os
import re
from typing import Optional
import anthropic
from config.settings import ANTHROPIC_API_KEY, CLAUDE_MODEL
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

Regras:
- Use apenas os dados acima. Não invente notícias, balanços ou números que não foram fornecidos.
- A recomendação é apoio à decisão e nunca uma garantia de retorno.
- Explique cada indicador em linguagem simples e mostre como ele sustenta a recomendação.

Responda EXATAMENTE neste formato, sem usar markdown nos títulos:

RECOMENDAÇÃO: [COMPRA ou VENDA ou MANTER]

SOBRE A EMPRESA:
[2 a 3 frases explicando o que a empresa faz e em qual setor atua]

JUSTIFICATIVA:
[3 a 5 parágrafos curtos em português acessível]

RISCOS:
[lista com hífens dos principais riscos]
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
        tipo = self.identificarTipo(texto)
        if tipo is None:
            raise RuntimeError(
                "A IA respondeu fora do formato esperado (COMPRA, VENDA ou MANTER). Tente novamente."
            )

        justificativa = self.extrairSecao(texto, "JUSTIFICATIVA") or texto.strip()
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
            recomendacao=tipo,
            justificativa=justificativa,
            riscos=self.extrairSecao(texto, "RISCOS"),
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
            )
        except anthropic.APIError as erro:
            logger.warning("Falha na chamada à API da Anthropic: %r", erro)
            raise self.traduzirErro(erro)

        return self.interpretar(self.extrairTexto(resposta), ind)
