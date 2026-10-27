from src.models.services.CarteiraService import CarteiraService


class CarteiraController:

    def __init__(self):
        self.carteiraService = CarteiraService()

    def obterResumo(self, carteiraId: int) -> dict:
        return self.carteiraService.obterResumo(carteiraId)
