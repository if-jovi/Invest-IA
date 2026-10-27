from src.models.services.YfinanceService import YfinanceService
from src.models.services.IndicatorsService import IndicatorsService
from src.models.services.ClaudeService import ClaudeService
from src.models.services.ItensB3Service import ItensB3Service
from src.models.services.RecomendacoesService import RecomendacoesService


class AnaliseService:

    def __init__(self):
        self.yfinanceService = YfinanceService()
        self.indicatorsService = IndicatorsService()
        self.claudeService = ClaudeService()
        self.itensB3Service = ItensB3Service()
        self.recomendacoesService = RecomendacoesService()

    def analisar(self, item: str, periodo: str = "1y", forcar: bool = False) -> dict:
        ativo = self.itensB3Service.obterOuCadastrar(item)

        historico = self.yfinanceService.buscarHistorico(ativo["item"], periodo)
        indicadores = self.indicatorsService.calcular(ativo["item"], historico)

        recomendacao = None
        if not forcar:
            recomendacao = self.recomendacoesService.buscarPorItemEData(
                ativo["item"], indicadores.data_referencia
            )
        doCache = recomendacao is not None

        if recomendacao is None:
            stock = self.yfinanceService.buscarInfo(ativo["item"])
            entidade = self.claudeService.gerarRecomendacao(stock, indicadores)
            recomendacao = self.recomendacoesService.salvar(entidade)

        return {
            "ativo": ativo,
            "indicadores": indicadores,
            "recomendacao": recomendacao,
            "doCache": doCache,
        }

    def buscarHistorico(self, item: str, limite: int = 20) -> list:
        return self.recomendacoesService.buscarHistorico(self.itensB3Service.normalizar(item), limite)
