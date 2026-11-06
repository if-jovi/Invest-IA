import os
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import dotenv
dotenv.load_dotenv = lambda *a, **k: False
os.environ["GEMINI_API_KEY"] = "chave-de-teste"
os.environ.pop("GEMINI_MODEL", None)

import httpx
from google.genai import errors
from src.models.entities.StockEntity import StockEntity, IndicatorsEntity
from src.models.services import GeminiService as modulo
from src.models.services.IaService import criarServicoIa

from tests.respostas_ia import respostaJson
TEXTO = respostaJson("VENDA", "Empresa de energia que explora petróleo.", "O RSI acima de 70 indica sobrecompra.", ["Volatilidade"])

chamadas = []
comportamento = {"resposta": None, "erro": None}


class FakeModels:
    def generate_content(self, model, contents, config):
        chamadas.append({"model": model, "contents": contents, "config": config})
        if comportamento["erro"] is not None:
            raise comportamento["erro"]
        return comportamento["resposta"]


class FakeCliente:
    models = FakeModels()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


modulo.GeminiService.cliente = lambda self: FakeCliente()


def resposta(texto, bloqueio=None):
    return SimpleNamespace(text=texto, prompt_feedback=SimpleNamespace(block_reason=bloqueio))


def erroApi(codigo, mensagem):
    return errors.APIError(codigo, {"error": {"code": codigo, "message": mensagem, "status": "X"}})


def esperarErro(erro, trecho):
    comportamento["erro"] = erro
    try:
        svc.gerarRecomendacao(stock, ind)
    except RuntimeError as e:
        assert trecho in str(e), f"esperava '{trecho}' em '{e}'"
    else:
        raise AssertionError(f"esperava RuntimeError com '{trecho}'")
    finally:
        comportamento["erro"] = None


stock = StockEntity(item="PETR4", nome="Petrobras", setor="Energia", segmento="Petroleo", descricao="Oil and gas")
ind = IndicatorsEntity(item="PETR4", data_referencia="2026-10-02", preco_atual=38.2, rsi=75.0, sinal_rsi="sobrecompra",
                       macd=0.12, macd_signal=0.10, macd_cruzamento="baixa", sma_short=37.0, sma_long=35.5, tendencia_sma="alta")
svc = modulo.GeminiService()

os.environ["IA_PROVEDOR"] = "gemini"
assert isinstance(criarServicoIa(), modulo.GeminiService)
print("OK  IA_PROVEDOR=gemini -> GeminiService (o padrão agora é o OpenRouter)")

comportamento["resposta"] = resposta(TEXTO)
rec = svc.gerarRecomendacao(stock, ind)
assert chamadas[-1]["model"] == modulo.MODELO_PADRAO
assert "PETR4" in chamadas[-1]["contents"] and "sobrecompra" in chamadas[-1]["contents"]
assert rec.recomendacao == "VENDA" and rec.item == "PETR4" and rec.riscos == "- Volatilidade"
assert rec.justificativa.startswith("O RSI")
print("OK  resposta convertida em RecomendacoesEntity (VENDA, justificativa, riscos) com o modelo padrão")

os.environ["GEMINI_MODEL"] = "modelo-x"
svc.gerarRecomendacao(stock, ind)
assert chamadas[-1]["model"] == "modelo-x"
os.environ.pop("GEMINI_MODEL")
print("OK  GEMINI_MODEL do .env substitui o modelo padrão")

comportamento["resposta"] = resposta("Não sei responder.")
try:
    svc.gerarRecomendacao(stock, ind)
    raise AssertionError("resposta fora do formato deveria falhar")
except RuntimeError as e:
    assert "fora do formato" in str(e)
print("OK  resposta fora do formato -> erro, nada é gravado")

comportamento["resposta"] = resposta("", bloqueio="SAFETY")
try:
    svc.gerarRecomendacao(stock, ind)
    raise AssertionError("prompt bloqueado deveria falhar")
except RuntimeError as e:
    assert "bloqueou" in str(e)
comportamento["resposta"] = resposta("")
try:
    svc.gerarRecomendacao(stock, ind)
    raise AssertionError("resposta vazia deveria falhar")
except RuntimeError as e:
    assert "não retornou texto" in str(e)
print("OK  prompt bloqueado e resposta vazia -> mensagens claras")

esperarErro(erroApi(400, "API key not valid. Please pass a valid API key."), "Chave da API do Gemini inválida")
esperarErro(erroApi(403, "Permission denied"), "não tem permissão")
esperarErro(erroApi(403, "The Gemini API free tier is not available for this project. Please set up billing."),
            "não tem acesso ao plano gratuito")
esperarErro(erroApi(404, "model not found"), "não foi encontrado")
esperarErro(erroApi(429, "Resource exhausted"), "Limite de uso do Gemini")
esperarErro(erroApi(503, "overloaded"), "instabilidade")
esperarErro(httpx.ReadTimeout("timeout"), "demorou demais")
esperarErro(httpx.ConnectError("sem rede"), "Não foi possível conectar")
print("OK  erros 400/403/404/429/503, timeout e rede fora traduzidos para o usuário")

os.environ["GEMINI_API_KEY"] = ""
try:
    svc.gerarRecomendacao(stock, ind)
    raise AssertionError("sem chave deveria falhar")
except ValueError as e:
    assert "GEMINI_API_KEY" in str(e)
print("OK  sem GEMINI_API_KEY -> ValueError antes de chamar a API")

print("\nGemini validado sem acessar a internet")
