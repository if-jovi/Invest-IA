import subprocess
import sys
from pathlib import Path

PASTA = Path(__file__).resolve().parent
SUITES = [
    ("Regras de negócio e banco de dados", "teste_logica.py"),
    ("Integração com o yfinance", "teste_yfinance.py"),
    ("Integração com a API da Claude", "teste_claude.py"),
    ("Interface Streamlit de ponta a ponta", "teste_interface.py"),
]


def executar() -> int:
    resultados = []
    for nome, arquivo in SUITES:
        processo = subprocess.run(
            [sys.executable, "-u", str(PASTA / arquivo)], capture_output=True, text=True, cwd=PASTA.parent
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
