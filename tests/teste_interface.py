"""App Streamlit de ponta a ponta (AppTest).

Specs: interface.md (UI4, UI6-UI10), catalogo-ativos.md (CA10-CA12),
analise-multipla.md (AM7-AM10), carteira.md (CT8).
Limitação do AppTest 1.66: selectbox não aceita simular valor digitado fora das
opções; nesses campos verifica-se a flag accept_new_options, e o caminho do
código digitado é coberto pelo multiselect da Análise e pelos testes de lógica.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests import simulacoes
from streamlit.testing.v1 import AppTest

MAIN = str(simulacoes.RAIZ / "src" / "public" / "Main.py")
MOEDA = re.compile(r"^-?R\$ \d{1,3}(\.\d{3})*,\d{2}$")
PCT = re.compile(r"^[+-]?\d{1,3}(\.\d{3})*,\d{2}%$")


def sem_excecao(at, etapa):
    assert not at.exception, f"{etapa}: {[e.value for e in at.exception]}"
    print("OK ", etapa)


def botao(at, rotulo):
    achados = [b for b in at.button if b.label == rotulo]
    assert achados, f"botao '{rotulo}' nao encontrado: {[b.label for b in at.button]}"
    return achados[0]


def textos(at):
    partes = []
    for grupo in (at.markdown, at.title, at.header, at.subheader, at.caption,
                  at.info, at.warning, at.error, at.success):
        partes += [str(e.value) for e in grupo]
    partes += [e.label for e in at.expander] + [t.label for t in at.tabs] + [m.label for m in at.metric]
    return "\n".join(partes)


def graficos(at):
    return at.get("plotly_chart")


def metricas(at):
    return {m.label: m.value for m in at.metric}


at = AppTest.from_file(MAIN, default_timeout=90)
at.run()
sem_excecao(at, "tela de login carrega, cria as tabelas e semeia o catálogo")

# UI7 — login em tela dividida
assert [t.label for t in at.tabs] == ["Entrar", "Criar conta"]
assert "Recomendações de ações da B3 explicadas em linguagem simples" in textos(at)
assert len(at.columns) >= 2, "painel de marca e formulário lado a lado"
print("OK  UI7 login com painel de marca + abas Entrar/Criar conta")

at.text_input(key="cadastroNome").set_value("Maria")
at.text_input(key="cadastroEmail").set_value("maria@email.com")
at.text_input(key="cadastroSenha").set_value("segredo1")
at.text_input(key="cadastroConfirmarSenha").set_value("outra")
botao(at, "Criar conta").click(); at.run()
assert any("não coincidem" in e.value for e in at.error), [e.value for e in at.error]
print("OK  UI7 validação de senhas diferentes mantida")

at.text_input(key="cadastroConfirmarSenha").set_value("segredo1")
botao(at, "Criar conta").click(); at.run()
sem_excecao(at, "cadastro conclui")
assert at.session_state["usuario"]["nome"] == "Maria"

# UI4 — abre a Carteira; UI8 — estado vazio
assert "Olá, Maria" in textos(at), "cabeçalho da carteira"
assert "primeira compra" in textos(at)
assert not graficos(at), "carteira vazia não mostra gráfico"
assert "maria@email.com" in "\n".join(str(e.value) for e in list(at.sidebar.caption) + list(at.sidebar.markdown))
assert any(b.label == "Sair" for b in at.sidebar.button)
print("OK  UI4/UI8 após cadastro abre a Carteira vazia, sem gráfico; usuário e Sair na lateral")

# CA10 — seletor da compra
compra = at.selectbox(key="compraItem")
assert compra.proto.accept_new_options, "compra deve aceitar código digitado"
assert any(o.startswith("PETR4 — ") for o in compra.options), compra.options[:5]
assert len(compra.options) >= 300, len(compra.options)
compra.set_value("PETR4")
at.number_input(key="compraQuantidade").set_value(100)
at.number_input(key="compraPreco").set_value(10.0)
botao(at, "Registrar compra").click(); at.run()
sem_excecao(at, "registrar compra pelo seletor")
assert any("registrada" in s.value for s in at.success), [s.value for s in at.success]
print("OK  CA10 compra com autocomplete do catálogo (PETR4 — Nome)")

# UI8, UI6, CT8 — dashboard
tabela = at.dataframe[0].value
for coluna in ("Código", "Empresa", "Quantidade", "Preço médio", "Cotação", "Variação do dia", "Resultado",
               "Recomendação"):
    assert coluna in tabela.columns, (coluna, list(tabela.columns))
linha = tabela.iloc[0]
assert linha["Código"] == "PETR4" and str(linha["Quantidade"]) == "100"
assert linha["Preço médio"] == "R$ 10,00" and linha["Cotação"] == "R$ 40,00", linha
assert linha["Variação do dia"] == "+5,26%", linha["Variação do dia"]
for coluna in tabela.columns:
    for valor in tabela[coluna]:
        if isinstance(valor, str) and valor.startswith(("R$", "-R$")):
            assert MOEDA.match(valor), (coluna, valor)
        if isinstance(valor, str) and valor.endswith("%"):
            assert PCT.match(valor), (coluna, valor)
        assert not isinstance(valor, float), f"coluna {coluna} com float cru {valor} (formato americano)"
print("OK  UI6 tabela da carteira com valores em pt-BR, sem float cru")
m = metricas(at)
assert {"Valor investido", "Valor atual", "Resultado", "Variação do dia", "Ativos na carteira"} <= set(m), m
assert m["Valor investido"] == "R$ 1.000,00" and m["Valor atual"] == "R$ 4.000,00", m
assert m["Variação do dia"] == "+5,26%", m
assert graficos(at), "gráfico de alocação por setor"
print("OK  UI8 cards (com variação do dia), tabela e gráfico de alocação")
todos = textos(at)
assert "atraso de até 15 min" in todos and "atualizado às 14:05" in todos, todos[-500:]
botao(at, "Atualizar cotações").click(); at.run()
sem_excecao(at, "CT8 botão Atualizar cotações")

# CA12 / AM10 — atalho Analisar
at.selectbox(key="atalhoItem").set_value("PETR4")
botao(at, "Analisar").click(); at.run()
sem_excecao(at, "atalho 'Analisar' abre a Análise")
assert any(t.value == "Análise de ativo" for t in at.title), [t.value for t in at.title]
seletor = at.multiselect(key="analiseItens")
assert seletor.value == ["PETR4"], seletor.value
print("OK  CA12/AM10 atalho abre a Análise com PETR4 pré-selecionado")

# AM7 — seletor múltiplo
assert seletor.proto.accept_new_options and seletor.proto.max_selections == 5
assert any(o.startswith("VALE3 — ") for o in seletor.options)
print("OK  AM7 seletor múltiplo do catálogo, aceita código digitado, máximo 5")

# UI9 / AM8 — um ativo: detalhe direto
botao(at, "Analisar").click(); at.run()
sem_excecao(at, "análise de um ativo")
todos = textos(at)
for trecho in ("COMPRA", "Sobre a empresa", "Por que esta recomendação?", "Riscos"):
    assert trecho in todos, trecho
assert {"RSI (14)", "MACD", "Média 20", "Média 50"} <= set(metricas(at)), metricas(at)
assert not [t for t in at.tabs if t.label == "PETR4"], "um ativo não usa abas"
print("OK  UI9/AM8 um ativo: card COMPRA, três seções e quatro indicadores")

botao(at, "Analisar").click(); at.run()
assert "reaproveitada" in textos(at)
print("OK  segunda análise reaproveita o cache")

# AM8 / CA11 — dois ativos, um digitado fora do catálogo
at.multiselect(key="analiseItens").set_value(["PETR4", "ABCD3"]); at.run()
botao(at, "Analisar").click(); at.run()
sem_excecao(at, "análise de dois ativos")
comparativo = [d.value for d in at.dataframe if "Recomendação" in d.value.columns and "RSI" in d.value.columns]
assert comparativo and list(comparativo[0]["Código"]) == ["PETR4", "ABCD3"], comparativo
assert {"PETR4", "ABCD3"} <= {t.label for t in at.tabs}
print("OK  AM8 quadro comparativo + uma aba por ativo")
at.run()
assert any(o.startswith("ABCD3") for o in at.multiselect(key="analiseItens").options)
print("OK  CA11 código digitado foi cadastrado e passa a constar na lista")

# AM9 — falha individual
at.multiselect(key="analiseItens").set_value(["PETR4", "XX"]); at.run()
botao(at, "Analisar").click(); at.run()
sem_excecao(at, "análise com um ativo inválido")
avisos = "\n".join(str(e.value) for e in list(at.warning) + list(at.error))
assert "XX" in avisos and "Código inválido" in avisos, avisos
assert "COMPRA" in textos(at), "o ativo válido continua exibido"
print("OK  AM9 ativo inválido vira aviso sem esconder o válido")

# CA10 / UI10 — Backtesting
at.switch_page("paginas/backtesting.py"); at.run()
sem_excecao(at, "navegar para o Backtesting")
bt = at.selectbox(key="backtestItem")
assert bt.proto.accept_new_options and any(o.startswith("PETR4 — ") for o in bt.options)
bt.set_value("PETR4")
botao(at, "Executar backtesting").click(); at.run()
sem_excecao(at, "executar backtesting")
m = metricas(at)
assert {"Operações simuladas", "Taxa de acerto", "Retorno da estratégia", "Buy and Hold",
        "Drawdown máximo"} <= set(m), m
assert any(rotulo.startswith("Índice Sharpe") for rotulo in m), m
for rotulo in ("Taxa de acerto", "Retorno da estratégia", "Buy and Hold", "Drawdown máximo"):
    assert PCT.match(m[rotulo]), (rotulo, m[rotulo])
print("OK  CA10/UI10 Backtesting com seletor do catálogo e cards em pt-BR")

# Carteira: recomendação, venda, remoção
at.switch_page("paginas/carteira.py"); at.run()
sem_excecao(at, "voltar para a carteira")
assert at.dataframe[0].value["Recomendação"][0] == "COMPRA"
print("OK  carteira mostra a recomendação gerada")

at.number_input(key="vendaQuantidade").set_value(30)
botao(at, "Registrar venda").click(); at.run()
sem_excecao(at, "registrar venda")
assert any("Venda de 30" in x.value for x in at.success), [x.value for x in at.success]
assert str(at.dataframe[0].value["Quantidade"][0]) == "70"
at.number_input(key="vendaQuantidade").set_value(500)
botao(at, "Registrar venda").click(); at.run()
assert any("apenas 70" in e.value for e in at.error), [e.value for e in at.error]
print("OK  venda parcial e venda excedente")

botao(at, "Remover ativo").click(); at.run()
assert any("Marque a confirmação" in e.value for e in at.error)
[c for c in at.checkbox if "Confirmo" in c.label][0].set_value(True)
botao(at, "Remover ativo").click(); at.run()
sem_excecao(at, "remover ativo")
assert "primeira compra" in textos(at)
print("OK  remoção com confirmação deixa a carteira vazia")

at.selectbox(key="compraItem").set_value("B3SA3")
botao(at, "Registrar compra").click(); at.run()
sem_excecao(at, "compra de B3SA3")
assert list(at.dataframe[0].value["Código"]) == ["B3SA3"]
print("OK  B3SA3 pelo seletor")

botao(at, "Sair").click(); at.run()
sem_excecao(at, "sair volta para o login")
assert "usuario" not in at.session_state
at2 = AppTest.from_file(MAIN, default_timeout=90)
at2.run()
at2.text_input(key="loginEmail").set_value("maria@email.com")
at2.text_input(key="loginSenha").set_value("senhaerrada")
botao(at2, "Entrar").click(); at2.run()
assert any("inválidos" in e.value for e in at2.error)
at2.text_input(key="loginSenha").set_value("segredo1")
botao(at2, "Entrar").click(); at2.run()
sem_excecao(at2, "login com a conta criada")
assert "Olá, Maria" in textos(at2)
assert list(at2.dataframe[0].value["Código"]) == ["B3SA3"]
print("OK  login rejeita senha errada; após login a carteira salva continua lá")
print("\nTeste de interface concluido")
