import os
from src.models.services.ClaudeService import ClaudeService
from src.models.services.GeminiService import GeminiService
from src.models.services.OpenRouterService import OpenRouterService

PROVEDORES = {
    "openrouter": OpenRouterService,
    "gemini": GeminiService,
    "claude": ClaudeService,
}


def criarServicoIa():
    provedor = (os.getenv("IA_PROVEDOR") or "openrouter").strip().lower()
    if provedor not in PROVEDORES:
        raise ValueError(
            "IA_PROVEDOR inválido no arquivo .env. Use 'openrouter', 'gemini' ou 'claude'."
        )
    return PROVEDORES[provedor]()
