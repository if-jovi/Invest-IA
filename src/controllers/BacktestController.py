from src.models.services.BacktestService import BacktestService
from src.controllers.AnaliseController import PERIODOS


class BacktestController:

    def __init__(self):
        self.backtestService = BacktestService()

    def executar(self, item: str, periodo: str, usuarioId: int) -> dict:
        if not (item or "").strip():
            raise ValueError("Informe o código do ativo.")
        if periodo not in PERIODOS:
            raise ValueError("Período inválido.")
        return self.backtestService.executar(item, periodo, usuarioId)
