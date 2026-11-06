"""Spec: .agents/docs/specs/analise-ia.md (IA1-IA5, IA7, IA8).

IA6 (traduções de erro) continua coberto por teste_claude, teste_gemini e
teste_openrouter. Provedores simulados; SQLite temporário.
"""
import json
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
PASTA = tempfile.mkdtemp()
import dotenv
dotenv.load_dotenv = lambda *a, **k: False
os.environ["DATABASE_URL"] = f"sqlite:///{PASTA}/ia_json.db"
os.environ["ANTHROPIC_API_KEY"] = "chave-de-teste"
os.environ["GEMINI_API_KEY"] = "chave-de-teste"
os.environ["OPENROUTER_API_KEY"] = "chave-de-teste"
os.environ["IA_PROVEDOR"] = "claude"
for variavel in ("OPENROUTER_MODEL", "OPENROUTER_BASE_URL", "GEMINI_MODEL", "CLAUDE_MODEL", "SEED_IA"):
    os.environ.pop(variavel, None)

import httpx
import anthropic
import src.models.base as base

base.criarTabelas()

from tests.respostas_ia import respostaJson
from src.models.base import Session
from src.models.entities.RecomendacoesEntity import RecomendacoesEntity
from src.models.entities.StockEntity import StockEntity, IndicatorsEntity
from src.models.services import ClaudeService as moduloClaude
from src.models.services import GeminiService as moduloGemini
from src.models.services import OpenRouterService as moduloOpenRouter
from src.models.services.RecomendacoesService import RecomendacoesService
from src.models.services.ItensB3Service import ItensB3Service
from src.models.services.YfinanceService import YfinanceService
from src.models import Parametros

ok = []


def passo(nome):
    ok.append(nome)
    print("OK ", nome)


ESQUEMA = moduloClaude.ESQUEMA_RESPOSTA
stock = StockEntity(item="PETR4", nome="Petrobras", setor="Energia", segmento="Petroleo", descricao="Oil and gas")
ind = IndicatorsEntity(item="PETR4", data_referencia="2026-10-02", preco_atual=38.2, rsi=75.0, sinal_rsi="sobrecompra",
                       macd=0.12, macd_signal=0.10, macd_cruzamento="baixa", sma_short=37.0, sma_long=35.5,
                       tendencia_sma="alta", periodo="3mo",
                       resumo_periodo={"retornoPct": 8.4, "maxima": 41.2, "minima": 35.0, "distanciaMaximaPct": -3.1,
                                       "distanciaMinimaPct": 14.0, "volatilidadeAnualPct": 27.5,
                                       "drawdownMaximoPct": -9.8})
VALIDA = respostaJson("VENDA", "Petrobras explora petróleo.", "O RSI acima de 70 indica sobrecompra.",
                      ["Volatilidade do petróleo", "Interferência política"])

# Esquema: os quatro campos obrigatórios, sem campos extras
assert ESQUEMA["type"] == "object" and ESQUEMA.get("additionalProperties") is False
assert set(ESQUEMA["required"]) == {"recomendacao", "sobre_empresa", "justificativa", "riscos"}
assert ESQUEMA["properties"]["recomendacao"]["enum"] == ["COMPRA", "VENDA", "MANTER"]
assert ESQUEMA["properties"]["riscos"]["type"] == "array"

# --- provedores simulados ------------------------------------------------------------
corpoClaude = []


class FakeClaude:
    def __init__(self, api_key=None, **kw):
        pass

    class messages:
        resposta = VALIDA

        @staticmethod
        def create(**kw):
            corpoClaude.append(kw)
            return SimpleNamespace(content=[SimpleNamespace(type="text", text=cortes["claude"] or FakeClaude.messages.resposta)],
                                   stop_reason="max_tokens" if cortes["claude"] else "end_turn")


anthropic.Anthropic = FakeClaude

chamadasGemini = []


class FakeModels:
    def generate_content(self, model, contents, config):
        chamadasGemini.append({"contents": contents, "config": config})
        final = "MAX_TOKENS" if cortes["gemini"] else "STOP"
        return SimpleNamespace(text=cortes["gemini"] or VALIDA, prompt_feedback=SimpleNamespace(block_reason=None),
                               candidates=[SimpleNamespace(finish_reason=final)])


class FakeClienteGemini:
    models = FakeModels()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


moduloGemini.GeminiService.cliente = lambda self: FakeClienteGemini()
corposOpenRouter = []


cortes = {"openrouter": None, "gemini": None, "claude": None}


def handler(request):
    corposOpenRouter.append(json.loads(request.content))
    escolha = {"index": 0, "message": {"role": "assistant", "content": cortes["openrouter"] or VALIDA},
               "finish_reason": "length" if cortes["openrouter"] else "stop"}
    return httpx.Response(200, json={"id": "gen-1", "model": moduloOpenRouter.MODELO_PADRAO, "choices": [escolha]})


moduloOpenRouter.OpenRouterService.cliente = lambda self: httpx.Client(transport=httpx.MockTransport(handler))

# IA1 + IA7 — esquema e seed na requisição de cada provedor
assert Parametros.SEED_IA == 42
recOR = moduloOpenRouter.OpenRouterService().gerarRecomendacao(stock, ind)
corpo = corposOpenRouter[-1]
assert corpo["response_format"] == {"type": "json_schema",
                                    "json_schema": {"name": "recomendacao", "strict": True, "schema": ESQUEMA}}, corpo
assert corpo["seed"] == 42 and corpo["temperature"] == 0.3

recGemini = moduloGemini.GeminiService().gerarRecomendacao(stock, ind)
config = chamadasGemini[-1]["config"]
assert config.response_mime_type == "application/json" and config.response_json_schema == ESQUEMA, config
assert config.seed == 42 and config.temperature == 0.3

recClaude = moduloClaude.ClaudeService().gerarRecomendacao(stock, ind)
corpo = corpoClaude[-1]
assert corpo["output_config"] == {"format": {"type": "json_schema", "schema": ESQUEMA}}, corpo.keys()
assert "seed" not in corpo
passo("IA1/IA7 OpenRouter (response_format + seed), Gemini (json schema + seed) e Claude (output_config, sem seed)")

# IA2 + IA4 — resposta válida vira entidade
for rec in (recOR, recGemini, recClaude):
    assert rec.recomendacao == "VENDA" and rec.sobre_empresa == "Petrobras explora petróleo."
    assert rec.justificativa == "O RSI acima de 70 indica sobrecompra."
    assert rec.riscos == "- Volatilidade do petróleo\n- Interferência política", rec.riscos
    assert rec.resposta_completa == VALIDA
    assert rec.item == "PETR4" and rec.data_referencia == "2026-10-02" and float(rec.rsi) == 75.0
passo("IA2/IA4 JSON válido vira RecomendacoesEntity (sobre_empresa, justificativa, riscos em linhas) e resposta_completa = JSON")

# IA3 — respostas fora do contrato são recusadas e nada é gravado
base_ = json.loads(VALIDA)
invalidas = {
    "texto livre": "RECOMENDAÇÃO: COMPRA\n\nJUSTIFICATIVA:\nsobe",
    "JSON em bloco de código": "```json\n" + VALIDA + "\n```",
    "campo faltando": json.dumps({k: v for k, v in base_.items() if k != "justificativa"}),
    "recomendação fora dos três valores": json.dumps(dict(base_, recomendacao="COMPRAR")),
    "riscos vazio": json.dumps(dict(base_, riscos=[])),
    "risco em branco": json.dumps(dict(base_, riscos=["Volatilidade", "  "])),
    "riscos demais": json.dumps(dict(base_, riscos=[f"r{i}" for i in range(9)])),
    "justificativa vazia": json.dumps(dict(base_, justificativa="   ")),
    "sobre_empresa vazio": json.dumps(dict(base_, sobre_empresa="")),
}
servico = moduloClaude.ClaudeService()
for nome, texto in invalidas.items():
    try:
        servico.interpretar(texto, ind)
    except RuntimeError as erro:
        assert str(erro).startswith("A IA respondeu fora do formato esperado"), (nome, erro)
    else:
        raise AssertionError(f"{nome}: deveria ser recusado")

import numpy as np
import pandas as pd


def historicoFake(self, item, periodo="1y", intervalo="1d"):
    n = 400
    datas = pd.bdate_range(end="2026-10-02", periods=n)
    preco = 30 + 4 * np.sin(np.arange(n) / 9)
    return pd.DataFrame({"Open": preco, "High": preco, "Low": preco, "Close": preco, "Volume": 1000}, index=datas)


YfinanceService.buscarHistorico = historicoFake
YfinanceService.buscarInfo = lambda self, item: stock
YfinanceService.buscarInfoAtivo = lambda self, item: {"item": "PETR4", "nome": "Petrobras", "setor": "Energia"}
YfinanceService.buscarHistoricoIndice = lambda self, simbolo="^BVSP", periodo="1y": None
from src.models.services.AnaliseService import AnaliseService
FakeClaude.messages.resposta = invalidas["campo faltando"]
try:
    AnaliseService().analisar("PETR4", "1y")
except RuntimeError:
    pass
else:
    raise AssertionError("análise com resposta inválida deveria falhar")
with Session() as s:
    assert s.query(RecomendacoesEntity).count() == 0
FakeClaude.messages.resposta = VALIDA
passo(f"IA3 {len(invalidas)} formatos inválidos recusados com a mensagem padrão; nada é gravado")

# IA9 — resposta cortada pelo limite de tamanho
cortada = VALIDA[: len(VALIDA) // 2]
for provedor, servicoProvedor in (("openrouter", moduloOpenRouter.OpenRouterService()),
                                  ("gemini", moduloGemini.GeminiService()), ("claude", moduloClaude.ClaudeService())):
    cortes[provedor] = cortada
    try:
        servicoProvedor.gerarRecomendacao(stock, ind)
    except RuntimeError as erro:
        assert str(erro) == "A resposta da IA veio incompleta. Tente novamente.", (provedor, erro)
    else:
        raise AssertionError(f"{provedor}: resposta cortada deveria ser recusada")
    cortes[provedor] = None
with Session() as s:
    assert s.query(RecomendacoesEntity).count() == 0
passo("IA9 resposta cortada (length / MAX_TOKENS / max_tokens) vira 'A resposta da IA veio incompleta' nos três provedores")

# IA5 — recomendações antigas (texto) continuam exibidas
ItensB3Service().obterOuCadastrar("PETR4")
antigo = "RECOMENDAÇÃO: MANTER\n\nSOBRE A EMPRESA:\nTexto antigo da empresa.\n\nJUSTIFICATIVA:\nJ\n\nRISCOS:\n- R"
with Session() as s:
    s.add(RecomendacoesEntity(item="PETR4", data_referencia="2026-09-01", periodo="1y", recomendacao="MANTER",
                              justificativa="J", riscos="- R", resposta_completa=antigo))
    s.commit()
novo = RecomendacoesService().salvar(servico.interpretar(VALIDA, ind))
assert novo["sobreEmpresa"] == "Petrobras explora petróleo."
historico = {h["dataReferencia"]: h for h in RecomendacoesService().buscarHistorico("PETR4")}
assert historico["2026-09-01"]["sobreEmpresa"] == "Texto antigo da empresa.", historico["2026-09-01"]
passo("IA5 DTO usa a coluna sobre_empresa e cai no recorte do texto antigo quando ela está vazia")

# IA8 — prompt mantém indicadores e período e descreve o JSON
prompt = servico.montarPrompt(stock, ind)
for trecho in ("RSI (14 períodos): 75.0", "horizonte: 3 meses", "Retorno no período: +8,40%",
               '"recomendacao"', '"sobre_empresa"', '"justificativa"', '"riscos"', "COMPRA", "VENDA", "MANTER"):
    assert trecho in prompt, f"'{trecho}' ausente do prompt"
assert "RECOMENDAÇÃO:" not in prompt, "o formato antigo em texto não deve mais ser pedido"
passo("IA8 prompt com indicadores, resumo do período e a descrição dos quatro campos do JSON")

print(f"\n{len(ok)} critérios da resposta estruturada passaram")
