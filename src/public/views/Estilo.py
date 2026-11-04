"""Identidade visual do InvestIA.

Paleta e regras de contraste: .agents/docs/specs/interface.md.
Nenhuma outra view deve declarar cor em hexadecimal: use as constantes daqui.
"""
from html import escape
import streamlit as st

VINHO = "#651424"
LARANJA = "#FF5825"
BRANCO = "#FFFFFF"

VINHO_ESCURO = "#4A0E1A"
LARANJA_CLARO = "#FFE6DD"
CINZA_TEXTO = "#2B2B2B"
CINZA_BORDA = "#ECE4E6"

VERDE = "#1E8E3E"
VERMELHO = "#C62828"
AMBAR = "#B26A00"

TEXTO_SOBRE_LARANJA = VINHO_ESCURO

SEQUENCIA_GRAFICO = [
    VINHO, LARANJA, VINHO_ESCURO, AMBAR,
    "rgba(101, 20, 36, 0.65)", "rgba(255, 88, 37, 0.6)",
    "rgba(101, 20, 36, 0.4)", "rgba(255, 88, 37, 0.35)",
    "rgba(178, 106, 0, 0.55)", CINZA_TEXTO,
]

CORES_RECOMENDACAO = {"COMPRA": VERDE, "VENDA": VERMELHO, "MANTER": AMBAR}

CSS = f"""
<style>
:root {{
  --ia-vinho: {VINHO};
  --ia-vinho-escuro: {VINHO_ESCURO};
  --ia-laranja: {LARANJA};
  --ia-laranja-claro: {LARANJA_CLARO};
  --ia-branco: {BRANCO};
  --ia-texto: {CINZA_TEXTO};
  --ia-borda: {CINZA_BORDA};
  --ia-verde: {VERDE};
  --ia-vermelho: {VERMELHO};
  --ia-ambar: {AMBAR};
}}

.block-container {{ padding-top: 2rem; padding-bottom: 3rem; max-width: 1280px; }}
h1, h2, h3 {{ color: var(--ia-vinho); letter-spacing: -0.02em; }}

/* Botões primários: laranja com texto vinho escuro (contraste 4,9:1) */
button[data-testid^="stBaseButton-primary"] {{
  color: var(--ia-vinho-escuro) !important;
  font-weight: 700 !important;
  border: none !important;
  box-shadow: 0 6px 16px -8px rgba(255, 88, 37, 0.9);
}}
button[data-testid^="stBaseButton-primary"] p {{ color: var(--ia-vinho-escuro) !important; font-weight: 700; }}
button[data-testid^="stBaseButton-primary"]:hover {{ filter: brightness(1.05); }}

/* Cards de métricas */
div[data-testid="stMetric"] {{
  background: var(--ia-branco);
  border: 1px solid var(--ia-borda);
  border-left: 4px solid var(--ia-laranja);
  border-radius: 14px;
  padding: 14px 18px;
  box-shadow: 0 4px 18px -12px rgba(101, 20, 36, 0.45);
}}
div[data-testid="stMetricLabel"] p {{
  color: var(--ia-vinho); font-weight: 600; font-size: 0.82rem;
  text-transform: uppercase; letter-spacing: 0.04em;
}}
div[data-testid="stMetricValue"] {{ color: var(--ia-texto); font-weight: 800; }}

/* Abas */
button[data-baseweb="tab"] p {{ font-weight: 600; }}
button[data-baseweb="tab"][aria-selected="true"] p {{ color: var(--ia-vinho); }}

/* Barra lateral */
section[data-testid="stSidebar"] a[data-testid="stSidebarNavLink"][aria-current="page"] {{
  background: var(--ia-vinho-escuro);
  border-left: 3px solid var(--ia-laranja);
}}
section[data-testid="stSidebar"] .stButton button {{
  background: transparent; color: var(--ia-branco);
  border: 1px solid rgba(255, 255, 255, 0.35);
}}

/* Componentes do InvestIA */
.ia-marca {{ display: flex; align-items: center; gap: 10px; font-weight: 800; font-size: 1.35rem; }}
.ia-marca-icone {{
  width: 36px; height: 36px; border-radius: 10px; background: var(--ia-laranja);
  color: var(--ia-vinho-escuro); display: grid; place-items: center; font-weight: 900;
}}
.ia-usuario {{ line-height: 1.3; padding: 4px 0 8px; }}
.ia-usuario strong {{ display: block; font-size: 1rem; }}
.ia-usuario span {{ opacity: 0.8; font-size: 0.85rem; }}

.ia-painel-login {{
  background: radial-gradient(circle at 85% 10%, rgba(255, 88, 37, 0.35), transparent 45%),
              linear-gradient(160deg, var(--ia-vinho) 0%, var(--ia-vinho-escuro) 100%);
  color: var(--ia-branco); border-radius: 24px; padding: 48px 40px; min-height: 560px;
  display: flex; flex-direction: column; justify-content: space-between;
}}
.ia-painel-login h1 {{ color: var(--ia-branco); font-size: 2.6rem; line-height: 1.1; margin: 28px 0 12px; }}
.ia-painel-login p {{ color: var(--ia-branco); opacity: 0.92; font-size: 1.05rem; }}
.ia-painel-login .ia-destaque {{ color: var(--ia-laranja); }}
.ia-recursos {{ list-style: none; padding: 0; margin: 24px 0 0; }}
.ia-recursos li {{
  display: flex; gap: 12px; align-items: flex-start; margin-bottom: 14px;
  background: rgba(255, 255, 255, 0.07); border-radius: 12px; padding: 12px 14px;
}}
.ia-recursos .ia-ponto {{
  flex: 0 0 28px; height: 28px; border-radius: 8px; background: var(--ia-laranja);
  color: var(--ia-vinho-escuro); display: grid; place-items: center; font-weight: 800;
}}
.ia-rodape-login {{ font-size: 0.8rem; opacity: 0.75; }}
.ia-form-titulo h2 {{ margin-bottom: 0; }}
.ia-form-titulo p {{ color: var(--ia-texto); opacity: 0.75; }}

.ia-cabecalho {{
  background: linear-gradient(120deg, var(--ia-vinho) 0%, var(--ia-vinho-escuro) 70%);
  color: var(--ia-branco); border-radius: 20px; padding: 24px 28px; margin-bottom: 18px;
  position: relative; overflow: hidden;
}}
.ia-cabecalho::after {{
  content: ""; position: absolute; right: -60px; top: -60px; width: 220px; height: 220px;
  border-radius: 50%; background: rgba(255, 88, 37, 0.35);
}}
.ia-cabecalho h1 {{ color: var(--ia-branco); margin: 0; font-size: 2rem; }}
.ia-cabecalho p {{ color: var(--ia-branco); opacity: 0.85; margin: 4px 0 0; }}

.ia-vazio {{
  border: 2px dashed var(--ia-borda); border-radius: 18px; padding: 36px; text-align: center;
  background: var(--ia-laranja-claro);
}}
.ia-vazio .ia-vazio-icone {{ font-size: 2.4rem; }}
.ia-vazio h3 {{ margin: 8px 0 4px; }}

.ia-recomendacao {{
  border-radius: 18px; padding: 22px 24px; border: 1px solid var(--ia-borda);
  background: var(--ia-branco); box-shadow: 0 8px 28px -18px rgba(101, 20, 36, 0.6);
  display: flex; flex-wrap: wrap; align-items: center; gap: 18px 28px; margin: 6px 0 14px;
}}
.ia-badge {{
  display: inline-block; padding: 8px 18px; border-radius: 999px; font-weight: 800;
  letter-spacing: 0.06em; color: var(--ia-branco); font-size: 1.1rem;
}}
.ia-badge-pequena {{ padding: 3px 10px; font-size: 0.78rem; }}
.ia-recomendacao .ia-info span {{ display: block; font-size: 0.8rem; opacity: 0.7; text-transform: uppercase; }}
.ia-recomendacao .ia-info strong {{ font-size: 1.15rem; color: var(--ia-texto); }}

.ia-aviso {{
  border-left: 4px solid var(--ia-laranja); background: var(--ia-laranja-claro);
  border-radius: 10px; padding: 12px 16px; font-size: 0.9rem; color: var(--ia-texto);
}}

@media (max-width: 640px) {{
  .ia-painel-login {{ min-height: auto; padding: 24px 20px; border-radius: 18px; }}
  .ia-painel-login h1 {{ font-size: 1.6rem; margin: 14px 0 6px; }}
  .ia-recursos, .ia-rodape-login {{ display: none; }}
  .ia-cabecalho {{ padding: 18px; }}
  .ia-cabecalho h1 {{ font-size: 1.5rem; }}
  .block-container {{ padding-left: 1rem; padding-right: 1rem; }}
}}
</style>
"""


def aplicarEstilo() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def corRecomendacao(tipo: str) -> str:
    return CORES_RECOMENDACAO.get((tipo or "").upper(), CINZA_TEXTO)


def badge(tipo: str, pequena: bool = False) -> str:
    classe = "ia-badge ia-badge-pequena" if pequena else "ia-badge"
    return (
        f'<span class="{classe}" style="background:{corRecomendacao(tipo)}">'
        f"{escape(tipo or 'SEM ANÁLISE')}</span>"
    )


def corResultado(valor) -> str:
    if valor is None or valor == 0:
        return CINZA_TEXTO
    return VERDE if valor > 0 else VERMELHO


def cabecalho(titulo: str, subtitulo: str = "") -> None:
    st.markdown(
        f'<div class="ia-cabecalho"><h1>{escape(titulo)}</h1>'
        f"<p>{escape(subtitulo)}</p></div>",
        unsafe_allow_html=True,
    )


def aviso(texto: str) -> None:
    st.markdown(f'<div class="ia-aviso">{escape(texto)}</div>', unsafe_allow_html=True)
