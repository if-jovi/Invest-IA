import pandas as pd
import streamlit as st
from src.controllers.BacktestController import BacktestController
from src.public.views import Paginas
from src.public.views.charts import renderGraficoBacktesting
from src.public.views.Formatacao import dataBr

ROTULOS_PERIODO = {"3mo": "3 meses", "6mo": "6 meses", "1y": "1 ano", "2y": "2 anos"}


def renderMetricas(metricas: dict) -> None:
    primeira = st.columns(3)
    primeira[0].metric("Operações simuladas", metricas["totalOperacoes"])
    primeira[1].metric("Taxa de acerto", f"{metricas['taxaAcerto']}%")
    primeira[2].metric("Retorno acumulado", f"{metricas['retornoAcumulado']}%")

    segunda = st.columns(3)
    segunda[0].metric("Buy and Hold", f"{metricas['retornoBuyHold']}%")
    segunda[1].metric("Drawdown máximo", f"{metricas['drawdownMaximo']}%")
    segunda[2].metric("Índice Sharpe (por operação)", metricas["sharpe"])


def renderCriterios(metricas: dict) -> None:
    criterios = [
        ("Taxa de acerto acima de 55%", metricas["taxaAcerto"] > 55),
        ("Índice Sharpe acima de 1,0", metricas["sharpe"] > 1.0),
        ("Retorno acumulado acima do Buy and Hold", metricas["retornoAcumulado"] > metricas["retornoBuyHold"]),
    ]
    st.subheader("Critérios de avaliação do protótipo")
    st.dataframe(
        pd.DataFrame(
            [{"Critério": nome, "Resultado": "Atendido" if ok else "Não atendido"} for nome, ok in criterios]
        ),
        use_container_width=True,
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
                        "Preço de entrada": op["precoEntrada"],
                        "Saída": dataBr(str(op["dataSaida"])),
                        "Preço de saída": op["precoSaida"],
                        "Resultado (%)": op["resultadoPct"],
                    }
                    for op in resultado["operacoes"]
                ]
            ),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Preço de entrada": st.column_config.NumberColumn(format="R$ %.2f"),
                "Preço de saída": st.column_config.NumberColumn(format="R$ %.2f"),
                "Resultado (%)": st.column_config.NumberColumn(format="%.2f"),
            },
        )

    if resultado["persistido"]:
        st.caption("As operações simuladas foram salvas no seu histórico.")

    st.warning(
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

    colunas = st.columns([2, 1])
    item = colunas[0].text_input(
        "Código do ativo na B3", key=Paginas.CHAVE_BACKTEST, placeholder="Ex.: PETR4"
    )
    periodo = colunas[1].selectbox(
        "Período",
        list(ROTULOS_PERIODO),
        index=2,
        format_func=lambda p: ROTULOS_PERIODO[p],
        key="backtestPeriodo",
    )

    if st.button("Executar backtesting", type="primary"):
        try:
            with st.spinner(f"Simulando a estratégia para {item.strip().upper()}..."):
                st.session_state["backtestResultado"] = controller.executar(
                    item, periodo, usuario["id"]
                )
        except (ValueError, RuntimeError) as erro:
            st.error(str(erro))
        except Exception as erro:
            st.error(f"Não foi possível executar o backtesting: {erro}")

    resultado = st.session_state.get("backtestResultado")
    if resultado is None:
        st.info("Informe um ativo e clique em Executar backtesting.")
    else:
        renderResultado(resultado)
