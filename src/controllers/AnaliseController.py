from src.models.services.AnaliseService import AnaliseService

PERIODOS = ("3mo", "6mo", "1y", "2y")


class AnaliseController:

    def __init__(self):
        self.analiseService = AnaliseService()

    def analisar(self, item: str, periodo: str = "1y", forcar: bool = False) -> dict:
        if not (item or "").strip():
            raise ValueError("Informe o código do ativo.")
        if periodo not in PERIODOS:
            raise ValueError("Período inválido.")
        return self.analiseService.analisar(item, periodo, forcar)

    def buscarHistorico(self, item: str, limite: int = 20) -> list:
        return self.analiseService.buscarHistorico(item, limite)
