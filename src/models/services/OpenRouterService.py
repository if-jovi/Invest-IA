import logging
import os
import httpx
from src.models.entities.RecomendacoesEntity import RecomendacoesEntity
from src.models.entities.StockEntity import StockEntity, IndicatorsEntity
from src.models.Parametros import SEED_IA
from src.models.services.ClaudeService import ClaudeService, ESQUEMA_RESPOSTA, MENSAGEM_CORTADA

logger = logging.getLogger(__name__)

URL_PADRAO = "https://openrouter.ai/api/v1"
MODELO_PADRAO = "nvidia/nemotron-3.5-super-vl:free"
SUFIXO_GRATUITO = ":free"
TIMEOUT_SEGUNDOS = 90.0
TENTATIVAS = 2
MAXIMO_TOKENS = 8192


class ErroOpenRouter(Exception):

    def __init__(self, codigo, mensagem: str):
        super().__init__(mensagem)
        self.codigo = codigo
        self.mensagem = mensagem


class OpenRouterService(ClaudeService):

    def chave(self) -> str:
        return (os.getenv("OPENROUTER_API_KEY") or "").strip()

    def modelo(self) -> str:
        return (os.getenv("OPENROUTER_MODEL") or "").strip() or MODELO_PADRAO

    def urlBase(self) -> str:
        return ((os.getenv("OPENROUTER_BASE_URL") or "").strip() or URL_PADRAO).rstrip("/")

    def cliente(self) -> httpx.Client:
        return httpx.Client(timeout=TIMEOUT_SEGUNDOS)

    def validarConfiguracao(self) -> None:
        if not self.chave():
            raise ValueError("A chave OPENROUTER_API_KEY não está configurada no arquivo .env.")
        if not self.modelo().endswith(SUFIXO_GRATUITO):
            raise ValueError(
                "Apenas modelos gratuitos do OpenRouter são permitidos (terminados em ':free'). "
                "Ajuste OPENROUTER_MODEL no arquivo .env."
            )

    def traduzirErro(self, erro: Exception) -> Exception:
        if isinstance(erro, ErroOpenRouter):
            codigo = erro.codigo
            if codigo == 401:
                return RuntimeError(
                    "Chave da API do OpenRouter inválida. Confira OPENROUTER_API_KEY no arquivo .env."
                )
            if codigo == 402:
                return RuntimeError(
                    "O OpenRouter recusou a solicitação por falta de créditos. "
                    "Confira se o modelo configurado é gratuito."
                )
            if codigo == 404:
                return RuntimeError(
                    f"O modelo '{self.modelo()}' não foi encontrado no OpenRouter. "
                    "Ajuste OPENROUTER_MODEL no arquivo .env."
                )
            if codigo == 429:
                return RuntimeError(
                    "Limite de uso do modelo gratuito atingido no OpenRouter. "
                    "Aguarde cerca de um minuto e tente novamente."
                )
            if isinstance(codigo, int) and codigo >= 500:
                return RuntimeError(
                    "O OpenRouter ou o provedor do modelo está instável. Tente novamente em instantes."
                )
            return RuntimeError(f"Falha ao consultar a IA: {erro.mensagem}")

        if isinstance(erro, httpx.TimeoutException):
            return RuntimeError("A IA demorou demais para responder. Tente novamente.")
        if isinstance(erro, httpx.TransportError):
            return RuntimeError(
                "Não foi possível conectar à API do OpenRouter. Verifique a internet do servidor."
            )
        return RuntimeError(f"Falha ao consultar a IA: {erro}")

    def lerResposta(self, resposta: httpx.Response) -> dict:
        """Devolve o JSON da resposta ou levanta ErroOpenRouter.

        O OpenRouter pode avisar erro de dois jeitos: pelo status HTTP (4xx/5xx)
        ou com status 200 e uma chave "error" no corpo.
        """
        try:
            corpo = resposta.json()
        except ValueError:
            corpo = {}

        erro = corpo.get("error") if isinstance(corpo, dict) else None
        if resposta.status_code < 400 and not erro:
            return corpo

        erro = erro if isinstance(erro, dict) else {}
        codigo = resposta.status_code
        if codigo < 400 and str(erro.get("code", "")).isdigit():
            codigo = int(erro["code"])
        mensagem = erro.get("message") or resposta.text or f"HTTP {resposta.status_code}"
        raise ErroOpenRouter(codigo, mensagem)

    def enviar(self, prompt: str, maximoTokens: int = MAXIMO_TOKENS, estruturado: bool = False) -> dict:
        corpo = {
            "model": self.modelo(),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": maximoTokens,
            "seed": SEED_IA,
            # o modelo "raciocina" antes de responder e isso consome max_tokens (provedor-openrouter.md)
            "reasoning": {"effort": "low"},
        }
        if estruturado:
            corpo["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "recomendacao", "strict": True, "schema": ESQUEMA_RESPOSTA},
            }
        cabecalhos = {"Authorization": f"Bearer {self.chave()}", "X-Title": "InvestIA"}

        # Só falhas de rede/timeout são repetidas; erro da API (4xx/5xx) volta na hora.
        for tentativa in range(1, TENTATIVAS + 1):
            try:
                with self.cliente() as cliente:
                    resposta = cliente.post(
                        f"{self.urlBase()}/chat/completions", json=corpo, headers=cabecalhos
                    )
                return self.lerResposta(resposta)
            except httpx.TransportError as erro:
                logger.warning("Falha de rede no OpenRouter (tentativa %s): %r", tentativa, erro)
                if tentativa == TENTATIVAS:
                    raise self.traduzirErro(erro)
            except ErroOpenRouter as erro:
                logger.warning("OpenRouter respondeu erro %s: %s", erro.codigo, erro.mensagem)
                raise self.traduzirErro(erro)

    def extrairTexto(self, corpo: dict) -> str:
        escolhas = corpo.get("choices") or [{}]
        if (escolhas[0] or {}).get("finish_reason") == "length":
            raise RuntimeError(MENSAGEM_CORTADA)
        mensagem = (escolhas[0] or {}).get("message") or {}
        texto = (mensagem.get("content") or "").strip()
        if not texto:
            raise RuntimeError("A IA não retornou texto para esta análise. Tente novamente.")
        return texto

    def gerarRecomendacao(self, stock: StockEntity, ind: IndicatorsEntity) -> RecomendacoesEntity:
        self.validarConfiguracao()
        corpo = self.enviar(self.montarPrompt(stock, ind), estruturado=True)
        return self.interpretar(self.extrairTexto(corpo), ind)

    def testarConexao(self) -> str:
        self.validarConfiguracao()
        corpo = self.enviar("Responda apenas: ok", maximoTokens=256)
        return f"(OpenRouter, modelo {self.modelo()}, resposta: {self.extrairTexto(corpo)[:30]!r})"
