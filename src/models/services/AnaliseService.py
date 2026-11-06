import logging
from src.models.services.YfinanceService import YfinanceService
from src.models.services.IndicatorsService import IndicatorsService
from src.models.services.IaService import criarServicoIa
from src.models.services.ItensB3Service import ItensB3Service
from google.genai import errors, types
from src.models.services.RecomendacoesService import RecomendacoesService
from src.models.Parametros import SIMBOLO_IBOVESPA

logger = logging.getLogger(__name__)


class AnaliseService:

    def __init__(self):
        self.yfinanceService = YfinanceService()
        self.indicatorsService = IndicatorsService()
        self.claudeService = criarServicoIa()
        self.itensB3Service = ItensB3Service()
        self.recomendacoesService = RecomendacoesService()

    def analisar(self, item: str, periodo: str = "1y", forcar: bool = False) -> dict:
        ativo = self.itensB3Service.obterOuCadastrar(item)

        historico = self.yfinanceService.buscarHistorico(ativo["item"], periodo)
        indicadores = self.indicatorsService.calcular(ativo["item"], historico, periodo)
        indicadores.ibovespa = self.compararIbovespa(historico, periodo)

        recomendacao = None
        if not forcar:
            recomendacao = self.recomendacoesService.buscarPorItemDataEPeriodo(
                ativo["item"], indicadores.data_referencia, periodo
            )
        doCache = recomendacao is not None

        if recomendacao is None:
            stock = self.yfinanceService.buscarInfo(ativo["item"])
            entidade = self.claudeService.gerarRecomendacao(stock, indicadores)
            entidade.periodo = periodo
            recomendacao = self.recomendacoesService.salvar(entidade)

        return {
            "ativo": ativo,
            "indicadores": indicadores,
            "recomendacao": recomendacao,
            "doCache": doCache,
        }

    def compararIbovespa(self, historico, periodo: str):
        """Comparação com o Ibovespa; se o índice não puder ser obtido, a análise segue sem ela."""
        try:
            indice = self.yfinanceService.buscarHistoricoIndice(SIMBOLO_IBOVESPA, periodo)
            noPeriodo = self.indicatorsService.recortarPeriodo(historico, periodo)
            return self.indicatorsService.compararIndice(noPeriodo, indice)
        except Exception as erro:
            logger.warning("Ibovespa indisponível para a comparação: %r", erro)
            return None

    def buscarHistorico(self, item: str, limite: int = 20) -> list:
        return self.recomendacoesService.buscarHistorico(
            self.itensB3Service.normalizar(item), limite
        )
