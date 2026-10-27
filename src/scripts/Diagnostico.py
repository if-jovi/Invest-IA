import sys
import time
import anthropic
from sqlalchemy import text
from config.settings import ANTHROPIC_API_KEY
from src.models.base import engine, criarTabelas
from src.models.services.AnaliseService import AnaliseService
from src.models.services.ClaudeService import ClaudeService
from src.models.services.IndicatorsService import IndicatorsService
from src.models.services.YfinanceService import YfinanceService

ITEM_TESTE = "PETR4"

DICAS = {
    "banco": "Confira DB_HOST/DB_USER/DB_PASSWORD e se o container 'db' está saudável (docker compose ps).",
    "yahoo": (
        "Yahoo Finance inacessível ou bloqueando. Confira: (1) internet e DNS do container; "
        "(2) yfinance atualizado no requirements.txt (versões antigas levam erro 429); "
        "(3) rede, VPN ou firewall; (4) aguarde alguns minutos se for limite de requisições."
    ),
    "claude": "Confira ANTHROPIC_API_KEY no .env, o modelo em CLAUDE_MODEL e a internet do container.",
}


class Diagnostico:

    def __init__(self):
        self.yahoo = YfinanceService()
        self.claude = ClaudeService()
        self.falhas = []
        self.historico = None

    def etapa(self, nome: str, grupo: str, funcao) -> None:
        inicio = time.time()
        try:
            detalhe = funcao()
            print(f"[ OK  ] {nome} ({time.time() - inicio:.1f}s) {detalhe or ''}")
        except Exception as erro:
            print(f"[FALHA] {nome} ({time.time() - inicio:.1f}s) -> {type(erro).__name__}: {erro}")
            if grupo not in self.falhas:
                self.falhas.append(grupo)

    def testarBanco(self) -> str:
        with engine.connect() as conexao:
            conexao.execute(text("SELECT 1"))
        criarTabelas()
        return f"({engine.url.host}:{engine.url.port}/{engine.url.database})"

    def testarHistorico(self) -> str:
        self.historico = self.yahoo.buscarHistorico(ITEM_TESTE, "1y")
        return f"({len(self.historico)} candles, último em {self.historico.index[-1].date()})"

    def testarInfo(self) -> str:
        stock = self.yahoo.buscarInfo(ITEM_TESTE)
        if stock.nome == ITEM_TESTE:
            raise RuntimeError("o Yahoo não devolveu o nome da empresa (dados da empresa indisponíveis)")
        return f"({stock.nome} | {stock.setor})"

    def testarCotacao(self) -> str:
        preco = self.yahoo.buscarPrecoAtual(ITEM_TESTE)
        if preco is None:
            raise RuntimeError("cotação indisponível")
        return f"(R$ {preco:.2f})"

    def testarIndicadores(self) -> str:
        ind = IndicatorsService().calcular(ITEM_TESTE, self.historico)
        return f"(RSI {ind.rsi}, MACD de {ind.macd_cruzamento}, tendência de {ind.tendencia_sma})"

    def testarClaude(self) -> str:
        if not ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY não configurada no .env.")
        try:
            resposta = anthropic.Anthropic(
                api_key=ANTHROPIC_API_KEY, timeout=30.0, max_retries=1
            ).messages.create(
                model=self.claude.modelo(),
                max_tokens=20,
                messages=[{"role": "user", "content": "Responda apenas: ok"}],
            )
        except anthropic.APIError as erro:
            raise self.claude.traduzirErro(erro)
        return f"(modelo {self.claude.modelo()}, resposta: {self.claude.extrairTexto(resposta)[:30]!r})"

    def testarAnaliseCompleta(self) -> str:
        resultado = AnaliseService().analisar(ITEM_TESTE, "1y")
        return f"({resultado['recomendacao']['recomendacao']}, reaproveitada={resultado['doCache']})"

    def executar(self, completo: bool) -> int:
        print(f"Diagnóstico das integrações (ativo de teste: {ITEM_TESTE})\n")

        self.etapa("Banco de dados (conexão e tabelas)", "banco", self.testarBanco)
        self.etapa("Yahoo Finance - histórico de preços", "yahoo", self.testarHistorico)
        self.etapa("Yahoo Finance - dados da empresa", "yahoo", self.testarInfo)
        self.etapa("Yahoo Finance - cotação atual", "yahoo", self.testarCotacao)
        if self.historico is not None:
            self.etapa("Indicadores técnicos (RSI, MACD, médias)", "yahoo", self.testarIndicadores)
        self.etapa("Claude (chamada mínima à API)", "claude", self.testarClaude)
        if completo and not self.falhas:
            self.etapa("Análise completa (Yahoo, indicadores, Claude e banco)", "claude", self.testarAnaliseCompleta)

        print()
        if not self.falhas:
            print("Tudo certo: as integrações estão funcionando.")
            return 0
        for grupo in self.falhas:
            print(f"Dica ({grupo}): {DICAS[grupo]}")
        return 1


if __name__ == "__main__":
    sys.exit(Diagnostico().executar("--completo" in sys.argv))
