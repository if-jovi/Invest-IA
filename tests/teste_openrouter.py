"""Spec: .agents/docs/specs/provedor-openrouter.md (OR1-OR10).

Usa httpx.MockTransport: nenhuma chamada real ao OpenRouter.
"""
import json
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
import dotenv
dotenv.load_dotenv = lambda *a, **k: False
for variavel in ("IA_PROVEDOR", "OPENROUTER_MODEL", "OPENROUTER_BASE_URL"):
    os.environ.pop(variavel, None)
os.environ["OPENROUTER_API_KEY"] = "chave-de-teste"

import httpx
from src.models.entities.StockEntity import StockEntity, IndicatorsEntity
from src.models.services import OpenRouterService as modulo
from src.models.services.GeminiService import GeminiService
from src.models.services.ClaudeService import ClaudeService
from src.models.services.IaService import criarServicoIa

TEXTO = """RECOMENDAÇÃO: VENDA

SOBRE A EMPRESA:
Empresa de energia que explora petróleo.

JUSTIFICATIVA:
O RSI acima de 70 indica sobrecompra.

RISCOS:
- Volatilidade
"""

requisicoes = []
comportamento = {"resposta": None}


def respostaOk(texto):
    return httpx.Response(200, json={
        "id": "gen-1", "model": modulo.MODELO_PADRAO,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": texto}}],
    })


def handler(request: httpx.Request) -> httpx.Response:
    requisicoes.append(request)
    acao = comportamento["resposta"]
    if isinstance(acao, Exception):
        raise acao
    if callable(acao):
        return acao(request)
    return acao


modulo.OpenRouterService.cliente = lambda self: httpx.Client(transport=httpx.MockTransport(handler))

stock = StockEntity(item="PETR4", nome="Petrobras", setor="Energia", segmento="Petroleo", descricao="Oil and gas")
ind = IndicatorsEntity(item="PETR4", data_referencia="2026-10-02", preco_atual=38.2, rsi=75.0, sinal_rsi="sobrecompra",
                       macd=0.12, macd_signal=0.10, macd_cruzamento="baixa", sma_short=37.0, sma_long=35.5,
                       tendencia_sma="alta")
svc = modulo.OpenRouterService()


def esperarErro(resposta, trecho, tipo=RuntimeError):
    comportamento["resposta"] = resposta
    try:
        svc.gerarRecomendacao(stock, ind)
    except tipo as e:
        assert trecho in str(e), f"esperava '{trecho}' em '{e}'"
    else:
        raise AssertionError(f"esperava {tipo.__name__} com '{trecho}'")


# OR1 — provedor padrão e alternativas
assert isinstance(criarServicoIa(), modulo.OpenRouterService)
os.environ["IA_PROVEDOR"] = "gemini"
assert isinstance(criarServicoIa(), GeminiService)
os.environ["IA_PROVEDOR"] = "claude"
servico = criarServicoIa()
assert type(servico) is ClaudeService
os.environ["IA_PROVEDOR"] = " OpenRouter "
assert isinstance(criarServicoIa(), modulo.OpenRouterService)
os.environ["IA_PROVEDOR"] = "xpto"
try:
    criarServicoIa()
    raise AssertionError("IA_PROVEDOR inválido deveria falhar")
except ValueError as e:
    assert "openrouter" in str(e) and "gemini" in str(e) and "claude" in str(e), e
os.environ.pop("IA_PROVEDOR")
print("OK  OR1 IA_PROVEDOR ausente -> OpenRouter; gemini/claude continuam; inválido cita as 3 opções")

# OR2, OR3, OR4 — requisição e conversão da resposta
comportamento["resposta"] = respostaOk(TEXTO)
rec = svc.gerarRecomendacao(stock, ind)
assert modulo.MODELO_PADRAO == "nvidia/nemotron-3.5-super-vl:free"
req = requisicoes[-1]
corpo = json.loads(req.content)
assert corpo["model"] == "nvidia/nemotron-3.5-super-vl:free", corpo["model"]
print("OK  OR2 modelo padrão nvidia/nemotron-3.5-super-vl:free")
assert req.method == "POST" and str(req.url) == "https://openrouter.ai/api/v1/chat/completions", req.url
assert req.headers["Authorization"] == "Bearer chave-de-teste"
assert req.headers.get("X-Title") == "InvestIA"
assert corpo["messages"] == [{"role": "user", "content": svc.montarPrompt(stock, ind)}]
assert corpo["temperature"] == 0.3 and corpo["max_tokens"] == 4096
print("OK  OR3 POST /chat/completions com Bearer, X-Title, prompt e temperature 0.3")
assert rec.recomendacao == "VENDA" and rec.item == "PETR4"
assert rec.justificativa.startswith("O RSI") and rec.riscos == "- Volatilidade"
assert "explora petróleo" in rec.resposta_completa
print("OK  OR4 resposta convertida em RecomendacoesEntity")

os.environ["OPENROUTER_MODEL"] = "  nvidia/nemotron-3.5-lightning:free "
svc.gerarRecomendacao(stock, ind)
assert json.loads(requisicoes[-1].content)["model"] == "nvidia/nemotron-3.5-lightning:free"
print("OK  OPENROUTER_MODEL do .env (com espaços) substitui o padrão")

# OR5 — modelo pago é recusado sem requisição
antes = len(requisicoes)
os.environ["OPENROUTER_MODEL"] = "nvidia/nemotron-3-super-120b-a12b"
esperarErro(respostaOk(TEXTO), "Apenas modelos gratuitos", ValueError)
os.environ["OPENROUTER_MODEL"] = "nvidia/nemotron-3.5-super-vl:FREE"
esperarErro(respostaOk(TEXTO), "OPENROUTER_MODEL", ValueError)
assert len(requisicoes) == antes
os.environ.pop("OPENROUTER_MODEL")
print("OK  OR5 modelo sem ':free' -> ValueError e nenhuma requisição")

# OR6 — sem chave
os.environ["OPENROUTER_API_KEY"] = ""
esperarErro(respostaOk(TEXTO), "OPENROUTER_API_KEY não está configurada", ValueError)
assert len(requisicoes) == antes
os.environ["OPENROUTER_API_KEY"] = "chave-de-teste"
print("OK  OR6 sem OPENROUTER_API_KEY -> ValueError e nenhuma requisição")


# OR7 — erros traduzidos
def erroHttp(status, mensagem="erro"):
    return httpx.Response(status, json={"error": {"code": status, "message": mensagem}})


esperarErro(erroHttp(401, "No auth credentials found"), "Chave da API do OpenRouter inválida")
esperarErro(erroHttp(402, "Insufficient credits"), "falta de créditos")
esperarErro(erroHttp(404, "No endpoints found"), "não foi encontrado no OpenRouter")
esperarErro(erroHttp(429, "Rate limit exceeded: free-models-per-day"), "Limite de uso do modelo gratuito")
esperarErro(erroHttp(500, "Internal"), "instável")
esperarErro(erroHttp(503, "Provider unavailable"), "instável")
esperarErro(httpx.Response(200, json={"error": {"code": 502, "message": "Provider returned error"}}), "instável")
esperarErro(httpx.Response(200, json={"error": {"code": 429, "message": "rate limited upstream"}}),
            "Limite de uso do modelo gratuito")
esperarErro(respostaOk(""), "não retornou texto")
esperarErro(httpx.Response(200, json={"choices": [{"message": {"role": "assistant", "content": None}}]}),
            "não retornou texto")
esperarErro(httpx.Response(400, json={"error": {"code": 400, "message": "Mensagem própria do OpenRouter"}}),
            "Falha ao consultar a IA: Mensagem própria do OpenRouter")
esperarErro(httpx.ReadTimeout("timeout"), "demorou demais")
esperarErro(httpx.ConnectError("sem rede"), "Não foi possível conectar à API do OpenRouter")
esperarErro(respostaOk("Não sei responder."), "fora do formato")
print("OK  OR7 401/402/404/429/5xx, erro em corpo 200, vazio, timeout, rede e formato traduzidos")

# OR8 — repetição
antes = len(requisicoes)
esperarErro(erroHttp(429, "limite"), "Limite de uso")
assert len(requisicoes) - antes == 1, "4xx não deve ser repetido"
antes = len(requisicoes)
esperarErro(httpx.ReadTimeout("timeout"), "demorou demais")
assert len(requisicoes) - antes == 2, f"timeout: esperadas 2 tentativas, houve {len(requisicoes) - antes}"
tentativas = {"n": 0}


def falhaDepoisOk(request):
    tentativas["n"] += 1
    if tentativas["n"] == 1:
        raise httpx.ConnectError("oscilação")
    return respostaOk(TEXTO)


comportamento["resposta"] = falhaDepoisOk
assert svc.gerarRecomendacao(stock, ind).recomendacao == "VENDA"
print("OK  OR8 4xx sem repetição; timeout/rede com no máximo 2 tentativas")

# OR9 — teste de conexão
comportamento["resposta"] = respostaOk("ok")
texto = svc.testarConexao()
assert "OpenRouter" in texto and modulo.MODELO_PADRAO in texto, texto
print("OK  OR9 testarConexao cita OpenRouter e o modelo")

# OR10 — .env.example documentado
exemplo = (RAIZ / ".env.example").read_text(encoding="utf-8")
assert "IA_PROVEDOR=openrouter" in exemplo
assert "OPENROUTER_API_KEY=" in exemplo and "OPENROUTER_MODEL=" in exemplo
print("OK  OR10 .env.example documenta o OpenRouter")

print("\nOpenRouter validado sem acessar a internet")
