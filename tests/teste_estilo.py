"""Specs: .agents/docs/specs/interface.md (UI1, UI2, UI3, UI5, UI11) e
.agents/docs/specs/carteira.md (CT9) — verificações estáticas de
dependências, tema, paleta, formatação e estrutura das telas.
"""
import ast
import re
import sys
import tomllib
from datetime import date, datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

ok = []


def passo(nome):
    ok.append(nome)
    print("OK ", nome)


# UI1 — dependências
requisitos = (RAIZ / "requirements.txt").read_text(encoding="utf-8")
assert re.search(r"^streamlit==1\.66\.\d+\s*$", requisitos, re.M), "Streamlit 1.66.x não fixado"
pandas = re.search(r"^pandas(.*)$", requisitos, re.M).group(1)
assert "<3" in pandas or re.match(r"==2\.", pandas), f"pandas deve ficar na linha 2.x: {pandas}"
assert re.search(r"^numpy[=<>~!]=?2\.", requisitos, re.M) or re.search(r"^numpy>=2", requisitos, re.M), \
    "NumPy 2.x"
import streamlit
assert streamlit.__version__.startswith("1.66."), streamlit.__version__
passo("UI1 requirements fixa Streamlit 1.66.x, pandas 2.x e NumPy 2.x (e é a versão instalada)")

# UI2 — tema
config = tomllib.loads((RAIZ / ".streamlit" / "config.toml").read_text(encoding="utf-8"))
tema = config["theme"]
assert tema["primaryColor"].upper() == "#FF5825"
assert tema["backgroundColor"].upper() == "#FFFFFF"
assert tema.get("base") == "light"
assert tema["sidebar"]["backgroundColor"].upper() == "#651424"
assert config["client"]["toolbarMode"] in ("minimal", "viewer")
passo("UI2 config.toml: primária #FF5825, fundo branco, tema claro, sidebar vinho, sem 'Deploy'")

# UI3 — paleta centralizada
from src.public.views import Estilo

assert (Estilo.VINHO, Estilo.LARANJA, Estilo.BRANCO) == ("#651424", "#FF5825", "#FFFFFF")
PERMITIDAS = {"#651424", "#FF5825", "#FFFFFF", "#4A0E1A", "#FFE6DD", "#2B2B2B", "#ECE4E6",
              "#1E8E3E", "#C62828", "#B26A00"}
definidas = {v.upper() for k, v in vars(Estilo).items() if k.isupper() and isinstance(v, str)
             and re.fullmatch(r"#[0-9A-Fa-f]{6}", v)}
assert definidas <= PERMITIDAS, definidas - PERMITIDAS
assert Estilo.TEXTO_SOBRE_LARANJA.upper() == "#4A0E1A"
HEX = re.compile(r"#[0-9A-Fa-f]{6}\b|#[0-9A-Fa-f]{3}\b")
for arquivo in (RAIZ / "src" / "public").rglob("*.py"):
    if arquivo.name == "Estilo.py":
        continue
    achados = set(HEX.findall(arquivo.read_text(encoding="utf-8")))
    assert not achados, f"{arquivo.relative_to(RAIZ)} usa cor fixa fora de Estilo.py: {achados}"
passo("UI3 paleta em Estilo.py; nenhuma outra view usa hexadecimal próprio")

# UI5 — formatação pt-BR
from src.public.views import Formatacao as f

casos = [
    (f.moeda(5070), "R$ 5.070,00"), (f.moeda(-12.5), "-R$ 12,50"), (f.moeda(1234567.891), "R$ 1.234.567,89"),
    (f.moeda(0), "R$ 0,00"), (f.moeda(None), "-"),
    (f.percentual(407), "407,00%"), (f.percentual(-3.25), "-3,25%"), (f.percentual(1234.5), "1.234,50%"),
    (f.percentual(None), "-"),
    (f.variacao(3.25), "+3,25%"), (f.variacao(-3.25), "-3,25%"), (f.variacao(0), "0,00%"), (f.variacao(None), "-"),
    (f.quantidade(100.0), "100"), (f.quantidade(1500), "1.500"), (f.quantidade(None), "-"),
    (f.dataBr("2026-11-03"), "03/11/2026"), (f.dataBr(date(2026, 11, 3)), "03/11/2026"), (f.dataBr(None), "-"),
    (f.dataHora(datetime(2026, 11, 3, 14, 5)), "03/11/2026 14:05"), (f.dataHora(None), "-"),
    (f.hora(datetime(2026, 11, 3, 14, 5)), "14:05"), (f.hora(None), "-"),
]
for obtido, esperado in casos:
    assert obtido == esperado, f"esperado {esperado!r}, obtido {obtido!r}"
passo(f"UI5 Formatacao: {len(casos)} casos (moeda, percentual, variação, quantidade, datas, None)")

# UI11 — gráficos
graficos = (RAIZ / "src" / "public" / "views" / "charts.py").read_text(encoding="utf-8")
assert not re.search(r"\btemplate\s*=", graficos), "charts.py não deve fixar template do Plotly"
assert "Estilo" in graficos, "charts.py deve usar as constantes de Estilo"
nomeadas = re.findall(r"""color\s*=\s*["'](?!rgba)([a-z]+)["']""", graficos)
assert not nomeadas, f"cores nomeadas fixas em charts.py: {nomeadas}"
passo("UI11 charts.py sem template fixo e com cores da paleta")

# CT9 — fragmento com atualização automática na carteira
caminho = RAIZ / "src" / "public" / "views" / "CarteiraDashboard.py"
arvore = ast.parse(caminho.read_text(encoding="utf-8"))
from src.public.views import CarteiraDashboard

assert CarteiraDashboard.INTERVALO_ATUALIZACAO == 60
fragmentos = []
for no in ast.walk(arvore):
    if isinstance(no, ast.FunctionDef):
        for dec in no.decorator_list:
            if isinstance(dec, ast.Call) and ast.unparse(dec.func) == "st.fragment":
                if any(k.arg == "run_every" for k in dec.keywords):
                    fragmentos.append(no)
assert len(fragmentos) == 1, f"esperado 1 fragmento com run_every, achados {len(fragmentos)}"
corpo = ast.unparse(fragmentos[0])
assert "obterResumo" in corpo, "o fragmento deve recarregar o resumo (cotações)"
assert "st.form(" not in corpo and "renderGerenciamento" not in corpo, \
    "formulários de gerenciamento devem ficar fora do fragmento"
passo("CT9 cards e tabela em st.fragment(run_every=60s); formulários fora do fragmento")

print(f"\n{len(ok)} verificações de estilo passaram")
