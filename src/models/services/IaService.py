import os
from src.models.services.ClaudeService import ClaudeService
from src.models.services.GeminiService import GeminiService
from google.genai import errors, types


def criarServicoIa():
    provedor = (os.getenv("IA_PROVEDOR") or "gemini").strip().lower()
    if provedor == "gemini":
        return GeminiService()
    if provedor == "claude":
        return ClaudeService()
    raise ValueError("IA_PROVEDOR inválido no arquivo .env. Use 'gemini' ou 'claude'.")
