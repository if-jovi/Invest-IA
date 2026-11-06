import logging
import os
import httpx
from google import genai
from google.genai import errors, types
from src.models.entities.RecomendacoesEntity import RecomendacoesEntity
from src.models.entities.StockEntity import StockEntity, IndicatorsEntity
from src.models.Parametros import SEED_IA
from src.models.services.ClaudeService import ClaudeService, ESQUEMA_RESPOSTA, MENSAGEM_CORTADA

logger = logging.getLogger(__name__)

MODELO_PADRAO = "gemini-3.8-flash"
TIMEOUT_MS = 60000
TENTATIVAS = 3
MAXIMO_TOKENS = 8192


class GeminiService(ClaudeService):

    def chave(self) -> str:
        return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""

    def modelo(self) -> str:
        return os.getenv("GEMINI_MODEL") or MODELO_PADRAO

    def cliente(self) -> genai.Client:
        opcoes = types.HttpOptions(
            base_url=os.getenv("GEMINI_BASE_URL") or None,
            timeout=TIMEOUT_MS,
            retry_options=types.HttpRetryOptions(attempts=TENTATIVAS),
        )
        return genai.Client(api_key=self.chave(), http_options=opcoes)

    def traduzirErro(self, erro: Exception) -> Exception:
        if isinstance(erro, errors.APIError):
            codigo = getattr(erro, "code", None)
            mensagem = (getattr(erro, "message", "") or "").lower()

            if codigo in (400, 401) and "api key" in mensagem:
                return RuntimeError(
                    "Chave da API do Gemini inválida. Confira GEMINI_API_KEY no arquivo .env."
                )
            if codigo == 400 and "location" in mensagem:
                return RuntimeError(
                    "A API do Gemini não está disponível na sua região para esta chave."
                )
            if codigo == 403 and ("billing" in mensagem or "free tier" in mensagem):
                return RuntimeError(
                    "O projeto desta chave do Gemini não tem acesso ao plano gratuito. "
                    "Ative o faturamento em https://aistudio.google.com/billing "
                    "ou use uma chave de outro projeto."
                )
            if codigo == 403:
                return RuntimeError(
                    "A chave do Gemini não tem permissão ou foi bloqueada. Gere uma nova no Google AI Studio."
                )
            if codigo == 404:
                return RuntimeError(
                    f"O modelo '{self.modelo()}' não foi encontrado. Ajuste GEMINI_MODEL no arquivo .env."
                )
            if codigo == 429:
                return RuntimeError(
                    "Limite de uso do Gemini atingido (plano gratuito). Aguarde cerca de um minuto e tente novamente."
                )
            if codigo is not None and codigo >= 500:
                return RuntimeError(
                    "O Gemini está com instabilidade ou sobrecarregado. Tente novamente em instantes."
                )
            return RuntimeError(
                f"Falha ao consultar a IA: {getattr(erro, 'message', erro)}"
            )

        if isinstance(erro, httpx.TimeoutException):
            return RuntimeError("A IA demorou demais para responder. Tente novamente.")
        if isinstance(erro, httpx.TransportError):
            return RuntimeError(
                "Não foi possível conectar à API do Gemini. Verifique a internet do servidor."
            )
        return RuntimeError(f"Falha ao consultar a IA: {erro}")

    def extrairTexto(self, resposta) -> str:
        retorno = getattr(resposta, "prompt_feedback", None)
        if retorno is not None and getattr(retorno, "block_reason", None):
            raise RuntimeError("A IA bloqueou esta solicitação. Tente novamente.")

        candidatos = getattr(resposta, "candidates", None) or []
        if candidatos and "MAX_TOKENS" in str(getattr(candidatos[0], "finish_reason", "")):
            raise RuntimeError(MENSAGEM_CORTADA)
        texto = (resposta.text or "").strip()
        if not texto:
            raise RuntimeError(
                "A IA não retornou texto para esta análise. Tente novamente."
            )
        return texto

    def gerar(self, prompt: str, maximoTokens: int = MAXIMO_TOKENS, estruturado: bool = False):
        extras = (
            {"response_mime_type": "application/json", "response_json_schema": ESQUEMA_RESPOSTA}
            if estruturado else {}
        )
        try:
            with self.cliente() as cliente:
                return cliente.models.generate_content(
                    model=self.modelo(),
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        max_output_tokens=maximoTokens, temperature=0.3, seed=SEED_IA, **extras
                    ),
                )
        except Exception as erro:
            logger.warning("Falha na chamada à API do Gemini: %r", erro)
            raise self.traduzirErro(erro)

    def gerarRecomendacao(
        self, stock: StockEntity, ind: IndicatorsEntity
    ) -> RecomendacoesEntity:
        if not self.chave():
            raise ValueError(
                "A chave GEMINI_API_KEY não está configurada no arquivo .env."
            )
        resposta = self.gerar(self.montarPrompt(stock, ind), estruturado=True)
        return self.interpretar(self.extrairTexto(resposta), ind)

    def testarConexao(self) -> str:
        if not self.chave():
            raise ValueError("GEMINI_API_KEY não configurada no .env.")
        resposta = self.gerar("Responda apenas: ok", maximoTokens=256)
        return f"(Gemini, modelo {self.modelo()}, resposta: {self.extrairTexto(resposta)[:30]!r})"
