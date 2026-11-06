import pandas as pd
import streamlit as st
from src.controllers.BacktestController import BacktestController
from src.public.views import Estilo, Paginas, Seletores
from src.public.views.charts import renderGraficoBacktesting
from src.public.views.Formatacao import dataBr, decimal, moeda, percentual, variacao

from src.models.Parametros import ROTULOS_PERIODO


def textoSaida(op: dict) -> str:
    return "Em aberto" if op.get("emAberto") else dataBr(str(op["dataSaida"]))


def renderMetricas(metricas: dict) -> None:
    st.markdown("#### Estratégia MACD + RSI × Buy and Hold")
    primeira = st.columns(4)
    primeira[0].metric("Retorno da estratégia", variacao(metricas["retornoAcumulado"]))
    primeira[1].metric("Buy and Hold", variacao(metricas["retornoBuyHold"]),
                       help="Comprar no primeiro dia do período e vender no último.")
    primeira[2].metric("Ibovespa no período", variacao(metricas.get("retornoIbovespa")),
                       help="Referência de mercado: quanto o índice da B3 variou no mesmo período (sem custos).")
    diferenca = metricas["retornoAcumulado"] - metricas["retornoBuyHold"]
    primeira[3].metric("Estratégia − Buy and Hold", variacao(diferenca), delta=variacao(diferenca))

    segunda = st.columns(4)
    segunda[0].metric("Operações simuladas", metricas["totalOperacoes"])
    segunda[1].metric("Taxa de acerto", percentual(metricas["taxaAcerto"]))
    segunda[2].metric("Drawdown máximo", percentual(metricas["drawdownMaximo"]))
    segunda[3].metric("Índice de Sharpe (anualizado)", decimal(metricas["sharpe"]),
                      help="Retorno médio diário ÷ oscilação diária × √252, sem taxa livre de risco.")
    st.caption(
        f"Custos incluídos: {percentual(metricas.get('custoOperacaoPct', 0))} em cada compra e em cada venda "
        "(taxas da B3), também no Buy and Hold. Uma posição ainda aberta no último dia é encerrada pelo "
        "fechamento desse dia e aparece como \"Em aberto\"."
    )


def renderCriterios(metricas: dict) -> None:
    criterios = [
        ("Taxa de acerto acima de 55%", metricas["taxaAcerto"] > 55),
        ("Índice de Sharpe acima de 1,0", metricas["sharpe"] > 1.0),
        ("Retorno acumulado acima do Buy and Hold", metricas["retornoAcumulado"] > metricas["retornoBuyHold"]),
    ]
    st.subheader("Critérios de avaliação do protótipo")
    st.dataframe(
        pd.DataFrame(
            [{"Critério": nome, "Resultado": "Atendido" if ok else "Não atendido"} for nome, ok in criterios]
        ),
        width="stretch",
        hide_index=True,
    )


def renderResultado(resultado: dict) -> None:
    st.subheader(f"Backtesting - {resultado['item']}")
    st.caption(f"Período: {ROTULOS_PERIODO[resultado['periodo']]}")

    renderMetricas(resultado["metricas"])
    renderGraficoBacktesting(resultado["curvaAcumulada"], resultado["item"])
    renderCriterios(resultado["metricas"])

    if resultado["operacoes"]:
        st.subheader("Operações simuladas")
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Entrada": dataBr(str(op["dataEntrada"])),
                        "Preço de entrada": moeda(op["precoEntrada"]),
                        "Saída": textoSaida(op),
                        "Preço de saída": moeda(op["precoSaida"]),
                        "Resultado": variacao(op["resultadoPct"]),
                    }
                    for op in resultado["operacoes"]
                ]
            ).style.map(
                lambda v: f"color: {Estilo.corResultado(-1 if v.startswith('-') else 1)}; font-weight: 600"
                if isinstance(v, str) and v not in ("-", "0,00%") else "",
                subset=["Resultado"],
            ),
            width="stretch",
            hide_index=True,
        )

    if resultado["persistido"]:
        st.caption("As operações simuladas foram salvas no seu histórico.")
    elif resultado["operacoes"]:
        st.warning(
            "Não foi possível salvar as operações simuladas no seu histórico. "
            "O resultado acima continua válido; veja o log do servidor para o motivo."
        )

    Estilo.aviso(
        "O backtesting simula a estratégia sobre dados históricos. Resultados passados não garantem "
        "desempenho futuro e estratégias muito ajustadas ao passado podem sofrer de overfitting."
    )


def renderBacktest() -> None:
    usuario = st.session_state["usuario"]
    controller = BacktestController()

    st.title("Backtesting")
    st.caption(
        "Simula compras e vendas pelos sinais de MACD e RSI no histórico do ativo, "
        "para avaliar a coerência da estratégia."
    )

    with st.container(border=True):
        colunas = st.columns([3, 1], vertical_alignment="bottom")
        item = Seletores.seletorAtivo("Ativo", key=Paginas.CHAVE_BACKTEST, container=colunas[0])
        periodo = colunas[1].selectbox(
            "Período",
            list(ROTULOS_PERIODO),
            index=2,
            format_func=lambda p: ROTULOS_PERIODO[p],
            key="backtestPeriodo",
        )
        clicou = st.button("Executar backtesting", type="primary", icon=":material/play_arrow:")

    if clicou:
        try:
            with st.spinner(f"Simulando a estratégia para {(item or '').strip().upper()}..."):
                st.session_state["backtestResultado"] = controller.executar(
                    item, periodo, usuario["id"]
                )
            Seletores.atualizarSeNovos([st.session_state["backtestResultado"]["item"]])
        except (ValueError, RuntimeError) as erro:
            st.error(str(erro))
        except Exception as erro:
            st.error(f"Não foi possível executar o backtesting: {erro}")

    resultado = st.session_state.get("backtestResultado")
    if resultado is None:
        st.info("Escolha um ativo e clique em Executar backtesting.", icon=":material/lightbulb:")
    else:
        renderResultado(resultado)
