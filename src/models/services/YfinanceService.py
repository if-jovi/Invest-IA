import logging
import time
from typing import Optional
import pandas as pd
import yfinance as yf
from src.models.Parametros import DEFAULT_PERIOD, DEFAULT_INTERVAL
from src.models.entities.StockEntity import StockEntity

logger = logging.getLogger(__name__)

NAO_DISPONIVEL = "Não disponível"
COTACAO_VALIDADE_SEGUNDOS = 300
COTACAO_FALHA_SEGUNDOS = 60

SETORES = {
    "Energy": "Energia",
    "Financial Services": "Serviços Financeiros",
    "Basic Materials": "Materiais Básicos",
    "Consumer Cyclical": "Consumo Cíclico",
    "Consumer Defensive": "Consumo Não Cíclico",
    "Healthcare": "Saúde",
    "Industrials": "Industrial",
    "Real Estate": "Imobiliário",
    "Technology": "Tecnologia",
    "Utilities": "Utilidade Pública",
    "Communication Services": "Comunicação",
}

NOMES_ATIVO_AUSENTE = {"YFTickerMissingError", "YFPricesMissingError", "YFTzMissingError"}


def configurarYfinance() -> None:
    try:
        yf.config.debug.hide_exceptions = False
    except AttributeError:
        pass


class YfinanceService:
    cotacoes: dict = {}

    def __init__(self):
        configurarYfinance()

    def normalizarItem(self, item: str) -> str:
        valor = (item or "").strip().upper()
        return valor[:-3] if valor.endswith(".SA") else valor

    def simbolo(self, item: str) -> str:
        return self.normalizarItem(item) + ".SA"

    def traduzirSetor(self, setor: Optional[str]) -> str:
        if not setor:
            return NAO_DISPONIVEL
        return SETORES.get(setor, setor)

    def traduzirErro(self, erro: Exception, simbolo: str) -> Exception:
        nomes = {classe.__name__ for classe in type(erro).__mro__}

        if "YFRateLimitError" in nomes:
            return RuntimeError(
                "O Yahoo Finance limitou as requisições deste servidor (erro 429). "
                "Aguarde alguns minutos e tente novamente."
            )
        if nomes & NOMES_ATIVO_AUSENTE:
            return ValueError(f"Nenhum dado encontrado para {simbolo}.")
        return RuntimeError(
            f"Não foi possível consultar o Yahoo Finance ({type(erro).__name__}). "
            "Verifique a conexão do servidor com a internet."
        )

    def buscarHistorico(
        self, item: str, periodo: str = DEFAULT_PERIOD, intervalo: str = DEFAULT_INTERVAL
    ) -> pd.DataFrame:
        simbolo = self.simbolo(item)
        try:
            historico = yf.Ticker(simbolo).history(period=periodo, interval=intervalo)
        except Exception as erro:
            logger.warning("Falha ao buscar histórico de %s: %r", simbolo, erro)
            raise self.traduzirErro(erro, simbolo)

        if historico is None or historico.empty:
            raise ValueError(f"Nenhum dado encontrado para {simbolo}.")

        historico.index = pd.to_datetime(historico.index)
        historico = historico[["Open", "High", "Low", "Close", "Volume"]].dropna()
        if historico.empty:
            raise ValueError(f"Nenhum dado válido encontrado para {simbolo}.")
        return historico

    def buscarInfo(self, item: str) -> StockEntity:
        item = self.normalizarItem(item)
        try:
            info = yf.Ticker(self.simbolo(item)).info or {}
        except Exception as erro:
            logger.warning("Falha ao buscar informações de %s: %r", item, erro)
            info = {}

        return StockEntity(
            item=item,
            nome=info.get("longName") or info.get("shortName") or item,
            setor=self.traduzirSetor(info.get("sector")),
            segmento=info.get("industry") or NAO_DISPONIVEL,
            descricao=info.get("longBusinessSummary") or NAO_DISPONIVEL,
            preco_atual=info.get("currentPrice") or info.get("regularMarketPrice"),
            moeda=info.get("currency") or "BRL",
            pais=info.get("country") or "Brasil",
            site=info.get("website") or "",
        )

    def buscarInfoAtivo(self, item: str) -> dict:
        item = self.normalizarItem(item)
        try:
            self.buscarHistorico(item, periodo="1mo")
        except ValueError:
            raise ValueError(f"O ativo {item} não foi encontrado na B3.")

        stock = self.buscarInfo(item)
        return {"item": item, "nome": stock.nome, "setor": stock.setor}

    def buscarPrecoAtual(self, item: str) -> Optional[float]:
        chave = self.normalizarItem(item)
        agora = time.time()
        guardado = YfinanceService.cotacoes.get(chave)
        if guardado is not None:
            instante, preco, falhou = guardado
            validade = COTACAO_FALHA_SEGUNDOS if falhou else COTACAO_VALIDADE_SEGUNDOS
            if agora - instante < validade:
                return preco

        try:
            fechamentos = yf.Ticker(self.simbolo(chave)).history(period="5d")["Close"].dropna()
            preco = float(fechamentos.iloc[-1])
        except Exception as erro:
            logger.warning("Falha ao buscar cotação de %s: %r", chave, erro)
            anterior = guardado[1] if guardado is not None else None
            YfinanceService.cotacoes[chave] = (agora, anterior, True)
            return anterior

        YfinanceService.cotacoes[chave] = (agora, preco, False)
        return preco
