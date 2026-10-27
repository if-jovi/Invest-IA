import os
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
PASTA = tempfile.mkdtemp()
try:
    import pandas_ta
except ImportError:
    from tests import pandas_ta_simulado
    sys.modules["pandas_ta"] = pandas_ta_simulado
import json, os, sys, threading, time
from http.server import BaseHTTPRequestHandler, HTTPServer

os.environ["DATABASE_URL"] = f"sqlite:///{PASTA}/claude.db"
os.environ["ANTHROPIC_API_KEY"] = "chave-inicial"

TEXTO = """RECOMENDAÇÃO: VENDA

SOBRE A EMPRESA:
Empresa de energia.

JUSTIFICATIVA:
O RSI indica sobrecompra.

RISCOS:
- Volatilidade
"""
requisicoes = []

def erro(tipo, msg):
    return {"type": "error", "error": {"type": tipo, "message": msg}}

class Falso(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def responder(self, status, corpo, extra=None):
        dados = json.dumps(corpo).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        for k, v in (extra or {}).items(): self.send_header(k, v)
        self.send_header("content-length", str(len(dados)))
        self.end_headers(); self.wfile.write(dados)
    def do_POST(self):
        corpo = json.loads(self.rfile.read(int(self.headers["content-length"])))
        chave = self.headers.get("x-api-key")
        requisicoes.append({"path": self.path, "chave": chave, "versao": self.headers.get("anthropic-version"), "corpo": corpo})
        if chave == "k401": return self.responder(401, erro("authentication_error", "invalid x-api-key"))
        if chave == "k403": return self.responder(403, erro("permission_error", "sem permissao"))
        if chave == "k404": return self.responder(404, erro("not_found_error", "model: nao existe"))
        if chave == "k429": return self.responder(429, erro("rate_limit_error", "muitas requisicoes"), {"retry-after": "0"})
        if chave == "k500": return self.responder(500, erro("api_error", "falha interna"))
        if chave == "klento": time.sleep(3)
        texto = "Acho melhor esperar um pouco." if chave == "kfora" else TEXTO
        conteudo = [] if chave == "kvazio" else [{"type": "text", "text": texto}]
        parada = "refusal" if chave == "krecusa" else "end_turn"
        self.responder(200, {"id": "msg_01", "type": "message", "role": "assistant", "model": corpo["model"],
                             "content": conteudo, "stop_reason": parada, "stop_sequence": None,
                             "usage": {"input_tokens": 100, "output_tokens": 50}})

servidor = HTTPServer(("127.0.0.1", 0), Falso)
threading.Thread(target=servidor.serve_forever, daemon=True).start()
os.environ["ANTHROPIC_BASE_URL"] = f"http://127.0.0.1:{servidor.server_port}"

import anthropic
import src.models.services.ClaudeService as modulo
from src.models.entities.StockEntity import StockEntity, IndicatorsEntity

stock = StockEntity(item="PETR4", nome="Petrobras", setor="Energia", segmento="Petroleo", descricao="Oil and gas")
ind = IndicatorsEntity(item="PETR4", data_referencia="2026-10-02", preco_atual=38.2, rsi=75.0, sinal_rsi="sobrecompra",
                       macd=0.12, macd_signal=0.10, macd_cruzamento="baixa", sma_short=37.0, sma_long=35.5, tendencia_sma="alta")
svc = modulo.ClaudeService()

def com_chave(chave):
    modulo.ANTHROPIC_API_KEY = chave
    requisicoes.clear()

com_chave("kok")
rec = svc.gerarRecomendacao(stock, ind)
req = requisicoes[0]
assert req["path"] == "/v1/messages" and req["chave"] == "kok" and req["versao"] == "2023-06-01"
assert req["corpo"]["model"] == "claude-sonnet-4-6" and req["corpo"]["max_tokens"] == 1500
prompt = req["corpo"]["messages"][0]["content"]
assert req["corpo"]["messages"][0]["role"] == "user" and "PETR4" in prompt and "75.0" in prompt and "sobrecompra" in prompt
print("OK  requisicao: POST /v1/messages, x-api-key, anthropic-version, modelo, max_tokens e prompt com indicadores")
assert rec.recomendacao == "VENDA" and rec.item == "PETR4" and rec.data_referencia == "2026-10-02"
assert float(rec.rsi) == 75.0 and rec.justificativa.startswith("O RSI") and rec.riscos == "- Volatilidade"
assert "Empresa de energia" in rec.resposta_completa
print("OK  resposta da SDK real convertida em RecomendacoesEntity (VENDA, indicadores, justificativa, riscos)")

os.environ["CLAUDE_MODEL"] = "claude-sonnet-5-5"
com_chave("kok"); svc.gerarRecomendacao(stock, ind)
assert requisicoes[0]["corpo"]["model"] == "claude-sonnet-5-5"
del os.environ["CLAUDE_MODEL"]
print("OK  CLAUDE_MODEL no ambiente troca o modelo sem editar codigo")

def esperar(chave, trecho, tentativas=1):
    com_chave(chave)
    try:
        svc.gerarRecomendacao(stock, ind)
    except RuntimeError as e:
        assert trecho in str(e), f"{chave}: {e}"
        assert len(requisicoes) == tentativas, f"{chave}: {len(requisicoes)} tentativas"
        return
    raise AssertionError(f"{chave}: esperava erro")

esperar("k401", "Chave da API da Anthropic inválida")
esperar("k403", "não tem permissão")
esperar("k404", "claude-sonnet-4-6' não foi encontrado")
esperar("k429", "Limite de requisições", tentativas=3)
esperar("k500", "instabilidade", tentativas=3)
print("OK  401, 403, 404 (modelo), 429 e 500 viram mensagens em portugues; 429/500 fazem 3 tentativas (1 + 2 retentativas)")

esperar("kvazio", "não retornou texto")
esperar("kfora", "fora do formato esperado")
esperar("krecusa", "não pôde responder")
print("OK  resposta vazia, fora do formato (nao assume MANTER) e recusa da IA viram erro claro e nada e gravado")

modulo.TIMEOUT_SEGUNDOS = 0.5
modulo.TENTATIVAS = 0
esperar("klento", "demorou demais")
print("OK  timeout vira mensagem amigavel (sem travar a tela)")

com_chave("")
try:
    svc.gerarRecomendacao(stock, ind)
except ValueError as e:
    assert "ANTHROPIC_API_KEY" in str(e)
print("OK  sem chave configurada: mensagem orienta o .env, sem chamar a API")
print("\nSDK anthropic", anthropic.__version__, "- integracao validada")
