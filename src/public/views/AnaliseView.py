from html import escape
import pandas as pd
import streamlit as st
from src.models.Parametros import SMA_SHORT, SMA_LONG, RSI_OVERBOUGHT, RSI_OVERSOLD, ROTULOS_PERIODO
from src.controllers.AnaliseController import AnaliseController, LIMITE_ATIVOS_ANALISE
from src.controllers.ItensCarteiraController import ItensCarteiraController
from src.public.views import Estilo, Paginas, Seletores
from src.public.views.charts import renderGraficoTecnico
from src.public.views.Formatacao import moeda, variacao, decimal, dataBr, dataHora, percentual

SEM_PERIODO = "—"
AVISO = (
    "Protótipo acadêmico de apoio à decisão: a recomendação não é garantia de retorno nem "
    "aconselhamento financeiro. A decisão final e a responsabilidade são do investidor."
)


def renderIntroducao() -> None:
    st.info(
        f"Escolha até {LIMITE_ATIVOS_ANALISE} ações da B3 (busque por código ou nome) e clique em Analisar.",
        icon=":material/lightbulb:",
    )
    etapas = st.columns(4)
    textos = [
        ("1. Coleta", "Histórico de preços via Yahoo Finance."),
        ("2. Indicadores", "RSI, MACD e médias móveis de 20 e 50 períodos."),
        ("3. IA", "Um modelo de linguagem interpreta os indicadores."),
        ("4. Resultado", "COMPRA, VENDA ou MANTER, explicado em linguagem simples."),
    ]
    for coluna, (titulo, texto) in zip(etapas, textos):
        with coluna.container(border=True):
            st.markdown(f"**{titulo}**")
            st.caption(texto)


def rotuloPeriodo(periodo) -> str:
    return ROTULOS_PERIODO.get(periodo, SEM_PERIODO) if periodo else SEM_PERIODO


def variacaoPeriodo(ind) -> float:
    resumo = getattr(ind, "resumo_periodo", None)
    return resumo["retornoPct"] if resumo else None


def renderResumoPeriodo(ind) -> None:
    resumo = getattr(ind, "resumo_periodo", None)
    if not resumo:
        return
    st.markdown(f"#### Comportamento em {rotuloPeriodo(ind.periodo)}")
    colunas = st.columns(3)
    colunas[0].metric("Retorno no período", variacao(resumo["retornoPct"]),
                      help="Quanto o preço variou do primeiro ao último dia do período.")
    colunas[1].metric("Máxima do período", moeda(resumo["maxima"]),
                      help="Maior preço de fechamento no período.")
    colunas[1].caption(f"Preço atual {percentual(abs(resumo['distanciaMaximaPct']))} abaixo.")
    colunas[2].metric("Mínima do período", moeda(resumo["minima"]),
                      help="Menor preço de fechamento no período.")
    colunas[2].caption(f"Preço atual {percentual(resumo['distanciaMinimaPct'])} acima.")
    colunas = st.columns(3)
    colunas[0].metric("Volatilidade anualizada", percentual(resumo["volatilidadeAnualPct"]),
                      help="Quanto o preço costuma oscilar; quanto maior, mais arriscado.")
    colunas[1].metric("Drawdown máximo", variacao(resumo["drawdownMaximoPct"]),
                      help="Maior queda de um pico até um fundo dentro do período.")
    ibovespa = getattr(ind, "ibovespa", None)
    colunas[2].metric("Ibovespa no período", variacao(ibovespa["retornoPct"] if ibovespa else None),
                      help="Quanto o índice da B3 variou no mesmo período: a referência do mercado.")
    if ibovespa:
        lado = "acima" if ibovespa["diferencaPct"] >= 0 else "abaixo"
        colunas[2].caption(f"A ação ficou {decimal(abs(ibovespa['diferencaPct']))} p.p. {lado} do índice.")


def renderCardRecomendacao(resultado: dict) -> None:
    recomendacao, ind = resultado["recomendacao"], resultado["indicadores"]
    st.markdown(
        '<div class="ia-recomendacao">'
        f'<div>{Estilo.badge(recomendacao["recomendacao"])}</div>'
        f'<div class="ia-info"><span>Preço de referência</span><strong>{moeda(ind.preco_atual)}</strong></div>'
        f'<div class="ia-info"><span>Dados de</span><strong>{dataBr(ind.data_referencia)}</strong></div>'
        f'<div class="ia-info"><span>Variação no período</span><strong>{variacao(variacaoPeriodo(ind))}</strong></div>'
        "</div>",
        unsafe_allow_html=True,
    )
    if resultado["doCache"]:
        st.caption(
            f"Recomendação reaproveitada, gerada em {dataHora(recomendacao['geradoEm'])} para esta mesma "
            "data de referência. Marque 'Gerar nova análise' para solicitar outra."
        )


def renderExplicacao(recomendacao: dict) -> None:
    with st.container(border=True):
        if recomendacao["sobreEmpresa"]:
            st.markdown("#### Sobre a empresa")
            st.markdown(recomendacao["sobreEmpresa"])
        st.markdown("#### Por que esta recomendação?")
        st.markdown(recomendacao["justificativa"])
        if recomendacao["riscos"]:
            st.markdown("#### Riscos")
            st.markdown(recomendacao["riscos"])


def fraseRsi(ind) -> str:
    if ind.rsi is None:
        return "Sem dados suficientes."
    if ind.rsi > RSI_OVERBOUGHT:
        return "Acima de 70: possível sobrecompra (preço esticado)."
    if ind.rsi < RSI_OVERSOLD:
        return "Abaixo de 30: possível sobrevenda (preço deprimido)."
    return "Entre 30 e 70: zona neutra."


def renderIndicadores(ind) -> None:
    st.markdown("#### Indicadores técnicos")
    colunas = st.columns(4)
    colunas[0].metric("RSI (14)", decimal(ind.rsi), help="Índice de força relativa.")
    colunas[0].caption(fraseRsi(ind))
    colunas[1].metric("MACD", decimal(ind.macd, 4), help="Diferença entre médias exponenciais de 12 e 26.")
    colunas[1].caption(
        f"Cruzamento de {ind.macd_cruzamento}: "
        + ("força compradora." if ind.macd_cruzamento == "alta" else "força vendedora.")
    )
    colunas[2].metric(f"Média {SMA_SHORT}", moeda(ind.sma_short), help="Média móvel simples curta.")
    colunas[2].caption("Preço médio das últimas 20 sessões.")
    colunas[3].metric(f"Média {SMA_LONG}", moeda(ind.sma_long), help="Média móvel simples longa.")
    colunas[3].caption(
        f"Tendência de {ind.tendencia_sma}: média curta "
        + ("acima" if ind.tendencia_sma == "alta" else "abaixo")
        + " da longa."
    )


def renderHistorico(controller: AnaliseController, item: str) -> None:
    historico = controller.buscarHistorico(item)
    if not historico:
        return
    with st.expander(f"Histórico de recomendações de {item}"):
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Data de referência": dataBr(h["dataReferencia"]),
                        "Período": rotuloPeriodo(h["periodo"]),
                        "Recomendação": h["recomendacao"],
                        "Preço": moeda(h["precoAtual"]),
                        "RSI": decimal(h["rsi"]),
                        "Gerada em": dataHora(h["geradoEm"]),
                    }
                    for h in historico
                ]
            ),
            width="stretch",
            hide_index=True,
            key=f"historico{item}",
        )


def renderRegistroCompra(usuario: dict, item: str, precoSugerido: float) -> None:
    with st.expander(f"Registrar compra de {item} na carteira"):
        with st.form(f"formCompraAnalise{item}", clear_on_submit=True, border=False):
            colunas = st.columns(2)
            qtd = colunas[0].number_input("Quantidade", min_value=1, value=100, step=1, key=f"qtd{item}")
            preco = colunas[1].number_input(
                "Preço unitário (R$)", min_value=0.01, value=float(round(precoSugerido or 10.0, 2)),
                step=0.01, format="%.2f", key=f"preco{item}",
            )
            enviar = st.form_submit_button("Registrar compra", type="primary")

        if enviar:
            try:
                ItensCarteiraController().adicionarCompra(usuario["carteiraId"], item, qtd, preco)
            except (ValueError, RuntimeError) as erro:
                st.error(str(erro))
            else:
                st.success(f"Compra de {qtd} unidade(s) de {item} registrada na carteira.")


def renderDetalhe(controller: AnaliseController, resultado: dict, usuario: dict) -> None:
    ativo, ind = resultado["ativo"], resultado["indicadores"]
    st.markdown(f"### {escape(ativo['nome'])} ({ativo['item']})")
    st.caption(f"Setor: {ativo['setor']}")
    renderCardRecomendacao(resultado)
    renderExplicacao(resultado["recomendacao"])
    renderIndicadores(ind)
    renderResumoPeriodo(ind)
    st.markdown("#### Gráfico histórico")
    renderGraficoTecnico(ind.historico, ativo["item"])
    renderHistorico(controller, ativo["item"])
    renderRegistroCompra(usuario, ativo["item"], ind.preco_atual)


def renderComparativo(resultados: list) -> None:
    st.markdown("### Comparativo")
    linhas = [
        {
            "Código": r["ativo"]["item"],
            "Empresa": r["ativo"]["nome"],
            "Preço": moeda(r["indicadores"].preco_atual),
            "Variação no período": variacao(variacaoPeriodo(r["indicadores"])),
            "RSI": decimal(r["indicadores"].rsi),
            "Tendência": r["indicadores"].tendencia_sma,
            "Recomendação": r["recomendacao"]["recomendacao"],
        }
        for r in resultados
    ]
    tabela = pd.DataFrame(linhas).style.map(
        lambda v: f"color: {Estilo.corRecomendacao(v)}; font-weight: 700"
        if v in Estilo.CORES_RECOMENDACAO else "",
        subset=["Recomendação"],
    )
    st.dataframe(tabela, width="stretch", hide_index=True, key="comparativo")


def renderResultado(controller: AnaliseController, analise: dict, usuario: dict) -> None:
    for erro in analise["erros"]:
        st.warning(f"{erro['item']}: {erro['mensagem']}", icon=":material/warning:")

    resultados = analise["resultados"]
    if len(resultados) == 1:
        renderDetalhe(controller, resultados[0], usuario)
    elif resultados:
        renderComparativo(resultados)
        abas = st.tabs([r["ativo"]["item"] for r in resultados])
        for aba, resultado in zip(abas, resultados):
            with aba:
                renderDetalhe(controller, resultado, usuario)

    if resultados:
        Estilo.aviso(AVISO)


def executarAnalise(controller: AnaliseController, itens: list, periodo: str, forcar: bool) -> None:
    barra = st.progress(0.0, text="Preparando a análise...")

    def progredir(concluidos: int, total: int, item) -> None:
        texto = f"Analisando {min(concluidos + 1, total)} de {total}..." if concluidos < total else "Concluído."
        barra.progress(concluidos / total, text=texto)

    try:
        analise = controller.analisarVarios(itens, periodo, forcar, aoProgredir=progredir)
    except (ValueError, RuntimeError) as erro:
        barra.empty()
        st.error(str(erro))
        return
    barra.empty()
    st.session_state["analiseResultado"] = analise
    Seletores.atualizarSeNovos([r["ativo"]["item"] for r in analise["resultados"]])


def renderAnalise() -> None:
    usuario = st.session_state["usuario"]
    controller = AnaliseController()

    st.title("Análise de ativo")
    st.caption("Indicadores técnicos interpretados pela IA em linguagem acessível.")

    with st.container(border=True):
        colunas = st.columns([3, 1, 1], vertical_alignment="bottom")
        itens = Seletores.seletorAtivos(
            f"Ativos (até {LIMITE_ATIVOS_ANALISE})", key=Paginas.CHAVE_ANALISE,
            limite=LIMITE_ATIVOS_ANALISE, container=colunas[0],
        )
        periodo = colunas[1].selectbox(
            "Período", list(ROTULOS_PERIODO), index=2, format_func=lambda p: ROTULOS_PERIODO[p]
        )
        forcar = colunas[2].checkbox("Gerar nova análise", help="Ignora a recomendação já gerada hoje.")
        clicou = st.button("Analisar", type="primary", icon=":material/auto_awesome:")

    if clicou:
        executarAnalise(controller, itens, periodo, forcar)

    analise = st.session_state.get("analiseResultado")
    if analise is None:
        renderIntroducao()
    else:
        renderResultado(controller, analise, usuario)
