import subprocess
import sys
from pathlib import Path

PASTA = Path(__file__).resolve().parent
SUITES = [
    ("Regras de negócio e banco de dados", "teste_logica.py"),
    ("Migrações e consultas do banco", "teste_persistencia.py"),
    ("Integração com o yfinance", "teste_yfinance.py"),
    ("Integração com a API da Claude", "teste_claude.py"),
    ("Integração com a API do Gemini", "teste_gemini.py"),
    ("Integração com o OpenRouter", "teste_openrouter.py"),
    ("Catálogo de ativos da B3", "teste_catalogo.py"),
    ("Análise de vários ativos", "teste_analise_multipla.py"),
    ("Análise considerando o período", "teste_analise_periodo.py"),
    ("Resposta da IA em JSON", "teste_analise_ia_json.py"),
    ("Aquecimento dos indicadores", "teste_aquecimento.py"),
    ("Comparação com o Ibovespa", "teste_ibovespa.py"),
    ("Backtesting: Sharpe, custos e posição aberta", "teste_backtesting.py"),
    ("Desempenho da IA", "teste_desempenho_ia.py"),
    ("Tema, paleta e formatação", "teste_estilo.py"),
    ("Interface Streamlit de ponta a ponta", "teste_interface.py"),
]


def executar() -> int:
    resultados = []
    for nome, arquivo in SUITES:
        processo = subprocess.run(
            [sys.executable, "-u", str(PASTA / arquivo)],
            capture_output=True,
            text=True,
            cwd=PASTA.parent,
        )
        passou = processo.returncode == 0
        resultados.append((nome, passou))
        print(f"[{'PASSOU' if passou else 'FALHOU'}] {nome}")
        if not passou:
            print((processo.stdout + processo.stderr)[-1500:])

    falhas = [nome for nome, passou in resultados if not passou]
    print(f"\n{len(resultados) - len(falhas)}/{len(resultados)} baterias passaram")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(executar())
