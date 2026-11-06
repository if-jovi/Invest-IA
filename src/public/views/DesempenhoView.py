import pandas as pd
import streamlit as st
from src.models.Parametros import FAIXA_MANTER_PCT, HORIZONTE_AVALIACAO
from src.models.services.DesempenhoIaService import FONTES, TIPOS, DesempenhoIaService
from src.public.views import Estilo
from src.public.views.Formatacao import dataBr, decimal, moeda, percentual, variacao

COMANDO = "python -m src.scripts.AvaliarIA"


@st.cache_data(ttl=3600, show_spinner=False)
def avaliar(fonte: str, registros: int) -> dict:
    # `registros` entra na chave do cache: recomendações novas recalculam a avaliação
    return DesempenhoIaService().avaliar(fonte)


def intervalo(ic) -> str:
    return f"{percentual(ic[0])} a {percentual(ic[1])}" if ic else "-"


def renderVazio(fonte: str, pendentes: int) -> None:
    if pendentes:
        st.info(f"{pendentes} recomendação(ões) aguardando {HORIZONTE_AVALIACAO} pregões para serem conferidas.",
                icon=":material/hourglass_top:")
    if fonte == "historico":
        st.info(
            "Ainda não há avaliação histórica. Para gerar, rode no servidor (no container do app): "
            f"`{COMANDO}`. O script pede à IA recomendações para datas passadas e é retomável: "
            "faz até 40 chamadas por vez e continua de onde parou.",
            icon=":material/lightbulb:",
        )
    else:
        st.info(f"As recomendações geradas na tela de análise aparecem aqui {HORIZONTE_AVALIACAO} pregões depois.",
                icon=":material/lightbulb:")


def renderCards(resumo: dict) -> None:
    compra = resumo["porTipo"]["COMPRA"]
    linha = st.columns(3)
    linha[0].metric("Recomendações avaliadas", str(resumo["total"]),
                    help=f"Conferidas {HORIZONTE_AVALIACAO} pregões depois da recomendação.")
    if resumo["pendentes"]:
        linha[0].caption(f"{resumo['pendentes']} aguardando o prazo.")
    linha[1].metric("Acerto geral", percentual(resumo["geral"]["taxa"]),
                    help="COMPRA acerta se o preço subiu; VENDA, se caiu; "
                         f"MANTER, se variou no máximo {decimal(FAIXA_MANTER_PCT, 0)}%.")
    linha[1].caption(f"Margem (95%): {intervalo(resumo['geral']['ic'])}")
    linha[2].metric("Acerto de COMPRA", percentual(compra["taxa"]),
                    help="Comparado à taxa base: quantas vezes o preço subiu, ou seja, o acerto de quem compra sempre.")
    linha[2].caption(f"Taxa base: {percentual(resumo['taxaBase'])} · margem: {intervalo(compra['ic'])}")

    linha = st.columns(3)
    linha[0].metric("Acerto contra o Ibovespa", percentual(resumo["contraIbovespa"]["taxa"]),
                    help="COMPRA acerta se a ação rendeu mais que o Ibovespa no mesmo prazo; VENDA, se rendeu menos.")
    linha[0].caption(f"{resumo['contraIbovespa']['n']} recomendações de compra/venda com Ibovespa disponível.")
    linha[1].metric("Retorno médio após COMPRA", variacao(compra["retornoMedio"]),
                    help=f"Quanto o preço variou, em média, {HORIZONTE_AVALIACAO} pregões depois de cada COMPRA.")
    linha[1].caption(f"Média de todos os casos: {variacao(resumo['retornoMedioGeral'])}")
    p = resumo["pValorCompra"]
    if p is not None:
        conclusao = ("acima do acaso (p < 0,05)" if p < 0.05
                     else "não dá para afirmar que é melhor que comprar sempre")
        linha[2].metric("Chance de ser sorte (COMPRA)", decimal(p, 3),
                        help="Teste binomial: probabilidade de acertar tanto quanto a IA se a chance de acerto "
                             "fosse igual à taxa base. Abaixo de 0,05, o acerto é considerado acima do acaso.")
        linha[2].caption(f"Conclusão: {conclusao}.")


def renderPorTipo(resumo: dict) -> None:
    st.markdown("#### Por tipo de recomendação")
    linhas = [
        {
            "Recomendação": tipo,
            "Avaliadas": dados["n"],
            "Acertos": dados["acertos"],
            "Taxa de acerto": percentual(dados["taxa"]),
            "Margem (95%)": intervalo(dados["ic"]),
            "Retorno médio": variacao(dados["retornoMedio"]),
        }
        for tipo, dados in ((t, resumo["porTipo"][t]) for t in TIPOS)
    ]
    st.dataframe(pd.DataFrame(linhas), width="stretch", hide_index=True, key="desempenhoPorTipo")


def renderComoLer() -> None:
    with st.expander("Como ler estes números", expanded=False):
        st.markdown(
            f"""
- **Acerto:** a recomendação é conferida {HORIZONTE_AVALIACAO} pregões (≈ 1 mês) depois. COMPRA acerta se o
  preço subiu; VENDA, se caiu; MANTER, se variou no máximo {decimal(FAIXA_MANTER_PCT, 0)}% para cima ou para baixo.
- **Taxa base:** em quantos casos o preço subiu, ou seja, o acerto de quem "compra sempre". A COMPRA da IA só
  agrega valor se acertar mais do que isso.
- **Margem (95%):** intervalo de confiança de Wilson. Se a margem da COMPRA inclui a taxa base, não dá para dizer
  que a IA é melhor.
- **Chance de ser sorte:** teste binomial contra a taxa base. Abaixo de 0,05, o acerto é considerado acima do acaso.

**Limitações**
- **Amostra pequena:** algumas centenas de casos indicam uma tendência, não provam.
- **Conhecimento do modelo:** a IA foi treinada com dados que podem incluir o período avaliado; o prompt só leva
  números e o nome da empresa, o que reduz esse viés, mas não o elimina.
- **Viés de sobrevivência:** as ações avaliadas são grandes e negociadas hoje; empresas que caíram muito ou
  saíram da bolsa no período não entram, o que tende a favorecer os resultados.
- **Casos não independentes:** datas próximas do mesmo ativo se parecem, então a margem tende a ser otimista.
- **Descrição da empresa atual:** vem do Yahoo de hoje, mesmo nas datas passadas.
"""
        )


def renderCasos(casos: list) -> None:
    avaliados = [c for c in casos if c.get("retornoPct") is not None]
    if not avaliados:
        return
    with st.expander(f"Recomendações avaliadas ({len(avaliados)})"):
        st.dataframe(
            pd.DataFrame([
                {
                    "Data": dataBr(str(c["dataReferencia"])),
                    "Código": c["item"],
                    "Recomendação": c["recomendacao"],
                    "Preço": moeda(c["preco"]),
                    f"Variação em {HORIZONTE_AVALIACAO} pregões": variacao(c["retornoPct"]),
                    "Ibovespa": variacao(c.get("retornoIbovespaPct")),
                    "Acertou?": "Sim" if c.get("acerto") else "Não",
                }
                for c in reversed(avaliados)
            ]),
            width="stretch",
            hide_index=True,
            key="desempenhoCasos",
        )


def renderDesempenho() -> None:
    st.title("Desempenho da IA")
    st.caption(
        f"As recomendações da IA acertam? Cada uma é conferida {HORIZONTE_AVALIACAO} pregões depois "
        "e comparada com quem compra sempre e com o Ibovespa."
    )
    fonte = st.radio("Fonte", list(FONTES), format_func=FONTES.get, horizontal=True, key="desempenhoFonte")

    servico = DesempenhoIaService()
    try:
        registros = len(servico.carregar(fonte))
        with st.spinner("Conferindo os preços depois de cada recomendação..."):
            resultado = avaliar(fonte, registros)
    except Exception as erro:
        st.error(f"Não foi possível calcular o desempenho: {erro}")
        return

    resumo = resultado["resumo"]
    if resumo["total"] == 0:
        renderVazio(fonte, resumo["pendentes"])
        renderComoLer()
        return

    renderCards(resumo)
    renderPorTipo(resumo)
    renderComoLer()
    renderCasos(resultado["casos"])
    Estilo.aviso(
        "Desempenho passado não garante desempenho futuro. Estes números avaliam o protótipo; "
        "não são recomendação de investimento."
    )
