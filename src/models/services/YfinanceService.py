import logging
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional
import pandas as pd
import yfinance as yf
from src.models.Parametros import DEFAULT_PERIOD, DEFAULT_INTERVAL, DIAS_AQUECIMENTO, MESES_PERIODO, SIMBOLO_IBOVESPA
from src.models.entities.StockEntity import StockEntity

logger = logging.getLogger(__name__)

NAO_DISPONIVEL = "Não disponível"
COTACAO_VALIDADE_SEGUNDOS = 60
COTACAO_FALHA_SEGUNDOS = 30
INDICE_VALIDADE_SEGUNDOS = 3600
COLUNAS_ATIVO = ["Open", "High", "Low", "Close", "Volume"]
COLUNAS_INDICE = ["Close"]
FUSO_BRASILIA = ZoneInfo("America/Sao_Paulo")

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

    @staticmethod
    def inicioComAquecimento(periodo: str) -> str:
        """Hoje - período - DIAS_AQUECIMENTO (historico-aquecimento.md)."""
        inicio = (pd.Timestamp.today().normalize() - pd.DateOffset(months=MESES_PERIODO[periodo])
                  - pd.Timedelta(days=DIAS_AQUECIMENTO))
        return inicio.strftime("%Y-%m-%d")

    def buscarHistorico(
        self, item: str, periodo: str = DEFAULT_PERIOD, intervalo: str = DEFAULT_INTERVAL
    ) -> pd.DataFrame:
        """Histórico do período com os pregões de aquecimento antes dele (períodos de MESES_PERIODO)."""
        if periodo in MESES_PERIODO:
            return self.consultarHistorico(self.simbolo(item), intervalo, start=self.inicioComAquecimento(periodo))
        return self.consultarHistorico(self.simbolo(item), intervalo, period=periodo)

    def buscarHistoricoDesde(self, item: str, inicio, indice: bool = False) -> pd.DataFrame:
        """Histórico diário de `inicio` até hoje; com indice=True, `item` é o símbolo do índice (ex.: ^BVSP)."""
        simbolo = item if indice else self.simbolo(item)
        return self.consultarHistorico(simbolo, DEFAULT_INTERVAL, colunas=COLUNAS_INDICE if indice else COLUNAS_ATIVO,
                                       start=pd.Timestamp(inicio).strftime("%Y-%m-%d"))

    indices: dict = {}

    @classmethod
    def limparCacheIndice(cls) -> None:
        cls.indices.clear()

    def buscarHistoricoIndice(self, simbolo: str = SIMBOLO_IBOVESPA, periodo: str = DEFAULT_PERIOD) -> pd.DataFrame:
        """Histórico do índice no período (com aquecimento), com cache de 1 hora por período."""
        chave = (simbolo, periodo)
        agora = time.time()
        guardado = YfinanceService.indices.get(chave)
        if guardado is not None and agora - guardado[0] < INDICE_VALIDADE_SEGUNDOS:
            return guardado[1]
        if periodo in MESES_PERIODO:
            historico = self.consultarHistorico(simbolo, DEFAULT_INTERVAL, colunas=COLUNAS_INDICE,
                                                start=self.inicioComAquecimento(periodo))
        else:
            historico = self.consultarHistorico(simbolo, DEFAULT_INTERVAL, colunas=COLUNAS_INDICE, period=periodo)
        YfinanceService.indices[chave] = (agora, historico)
        return historico

    def consultarHistorico(self, simbolo: str, intervalo: str, colunas=None, **janela) -> pd.DataFrame:
        try:
            historico = yf.Ticker(simbolo).history(interval=intervalo, **janela)
        except Exception as erro:
            logger.warning("Falha ao buscar histórico de %s: %r", simbolo, erro)
            raise self.traduzirErro(erro, simbolo)

        if historico is None or historico.empty:
            raise ValueError(f"Nenhum dado encontrado para {simbolo}.")

        historico.index = pd.to_datetime(historico.index)
        historico = historico[colunas or COLUNAS_ATIVO].dropna()
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

    def baixarFechamentos(self, codigos: list) -> Optional[pd.DataFrame]:
        """Uma única chamada ao Yahoo para todos os ativos.

        Devolve uma tabela com uma coluna de fechamento por código
        (ex.: colunas PETR4, VALE3) ou None se o Yahoo falhar.
        """
        simbolos = [self.simbolo(c) for c in codigos]
        try:
            dados = yf.download(
                simbolos, period="5d", interval="1d", group_by="ticker",
                auto_adjust=False, progress=False,
            )
        except Exception as erro:
            logger.warning("Falha ao buscar cotações de %s: %r", simbolos, erro)
            return None

        fechamentos = pd.DataFrame(index=dados.index)
        for codigo, simbolo in zip(codigos, simbolos):
            if simbolo in dados.columns.get_level_values(0):
                fechamentos[codigo] = dados[simbolo]["Close"]
        return fechamentos

    def montarCotacao(self, fechamentos: pd.Series) -> Optional[dict]:
        """Último fechamento = preço atual; o anterior serve para a variação do dia."""
        valores = fechamentos.dropna()
        if valores.empty:
            return None

        preco = float(valores.iloc[-1])
        anterior = float(valores.iloc[-2]) if len(valores) > 1 else None
        variacaoDia = (preco / anterior - 1) * 100 if anterior else None
        return {
            "preco": preco,
            "fechamentoAnterior": anterior,
            "variacaoDia": variacaoDia,
            "atualizadoEm": datetime.now(FUSO_BRASILIA).replace(tzinfo=None),
            "desatualizada": False,
        }

    def lerCache(self, codigo: str, agora: float):
        """Devolve (encontrou, cotacao). Sucesso vale 60 s; falha vale 30 s."""
        guardado = YfinanceService.cotacoes.get(codigo)
        if guardado is None:
            return False, None

        validade = COTACAO_FALHA_SEGUNDOS if guardado["falhou"] else COTACAO_VALIDADE_SEGUNDOS
        if agora - guardado["instante"] >= validade:
            return False, None

        cotacao = guardado["cotacao"]
        if guardado["falhou"] and cotacao is not None:
            cotacao = {**cotacao, "desatualizada": True}
        return True, cotacao

    def guardarCache(self, codigo: str, agora: float, cotacao: Optional[dict], falhou: bool) -> None:
        YfinanceService.cotacoes[codigo] = {"instante": agora, "cotacao": cotacao, "falhou": falhou}

    def buscarCotacoes(self, itens: list, forcar: bool = False) -> dict:
        """Cotação de vários ativos de uma vez: {"PETR4": {...} ou None}."""
        codigos = []
        for item in itens:
            codigo = self.normalizarItem(item)
            if codigo and codigo not in codigos:
                codigos.append(codigo)

        agora = time.time()
        resultado = {}
        pendentes = []
        for codigo in codigos:
            encontrou, cotacao = (False, None) if forcar else self.lerCache(codigo, agora)
            if encontrou:
                resultado[codigo] = cotacao
            else:
                pendentes.append(codigo)

        if not pendentes:
            return resultado

        fechamentos = self.baixarFechamentos(pendentes)
        for codigo in pendentes:
            cotacao = None
            if fechamentos is not None and codigo in fechamentos:
                cotacao = self.montarCotacao(fechamentos[codigo])

            if cotacao is not None:
                self.guardarCache(codigo, agora, cotacao, falhou=False)
                resultado[codigo] = cotacao
                continue

            # Sem cotação nova: mantém a última conhecida, marcada como desatualizada.
            anterior = (YfinanceService.cotacoes.get(codigo) or {}).get("cotacao")
            if fechamentos is not None and anterior is None:
                self.guardarCache(codigo, agora, None, falhou=False)
                resultado[codigo] = None
            else:
                self.guardarCache(codigo, agora, anterior, falhou=True)
                resultado[codigo] = {**anterior, "desatualizada": True} if anterior else None
        return resultado

    def buscarPrecoAtual(self, item: str) -> Optional[float]:
        cotacao = self.buscarCotacoes([item]).get(self.normalizarItem(item))
        return cotacao["preco"] if cotacao is not None else None
