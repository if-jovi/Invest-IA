import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tests import simulacoes
from streamlit.testing.v1 import AppTest

def sem_excecao(at, etapa):
    assert not at.exception, f"{etapa}: {[e.value for e in at.exception]}"
    print("OK ", etapa)

def botao(at, rotulo):
    achados = [b for b in at.button if b.label == rotulo]
    assert achados, f"botao '{rotulo}' nao encontrado: {[b.label for b in at.button]}"
    return achados[0]

at = AppTest.from_file(str(simulacoes.RAIZ / "src" / "public" / "Main.py"), default_timeout=60)
at.run()
sem_excecao(at, "tela de login carrega e cria as tabelas")
assert [t.label for t in at.tabs] == ["Entrar", "Criar conta"]

at.text_input(key="cadastroNome").set_value("Maria")
at.text_input(key="cadastroEmail").set_value("maria@email.com")
at.text_input(key="cadastroSenha").set_value("segredo1")
at.text_input(key="cadastroConfirmarSenha").set_value("outra")
botao(at, "Criar conta").click(); at.run()
assert any("não coincidem" in e.value for e in at.error), [e.value for e in at.error]
print("OK  erro de senhas diferentes aparece na tela")

at.text_input(key="cadastroConfirmarSenha").set_value("segredo1")
botao(at, "Criar conta").click(); at.run()
sem_excecao(at, "cadastro conclui e abre o dashboard")
assert at.session_state["usuario"]["nome"] == "Maria"
assert any("Carteira de Maria" in t.value for t in at.title)
assert any("carteira ainda está vazia" in i.value for i in at.info)
print("OK  dashboard vazio com a carteira criada junto do cadastro")

at.text_input[0].set_value("petr4") if False else None
campo = [t for t in at.text_input if t.label == "Código do ativo"][0]
campo.set_value("petr4")
botao(at, "Registrar compra").click(); at.run()
sem_excecao(at, "registrar compra pelo formulario")
assert any("registrada" in s.value for s in at.success), [s.value for s in at.success]
tabela = at.dataframe[0].value
assert list(tabela["Código"]) == ["PETR4"] and tabela["Quantidade"][0] == 100
print("OK  compra aparece na tabela da carteira")
metricas = {m.label: m.value for m in at.metric}
assert metricas["Valor investido"] == "R$ 1.000,00" and metricas["Valor atual"] == "R$ 4.000,00", metricas
print("OK  metricas em reais formatadas:", metricas)

botao(at, "Analisar").click(); at.run()
sem_excecao(at, "atalho 'Analisar' navega para a analise com o ativo preenchido")
assert at.session_state["pagina"] == "Análise de ativo"
assert at.text_input(key="analiseItem").value == "PETR4"

botao(at, "Analisar").click(); at.run()
sem_excecao(at, "executar analise")
assert any("Recomendação: COMPRA" in s.value for s in at.success)
assert any("Sobre a empresa" in e.label for e in at.expander)
print("OK  recomendacao COMPRA, 'Sobre a empresa' e justificativa exibidas")

botao(at, "Analisar").click(); at.run()
assert any("reaproveitada" in c.value for c in at.caption)
print("OK  segunda analise reaproveita o cache")

at.sidebar.radio(key="pagina").set_value("Backtesting"); at.run()
sem_excecao(at, "navegar para backtesting pela barra lateral")
at.text_input(key="backtestItem").set_value("PETR4")
botao(at, "Executar backtesting").click(); at.run()
sem_excecao(at, "executar backtesting")
rotulos = {m.label for m in at.metric}
assert {"Taxa de acerto", "Retorno acumulado", "Buy and Hold", "Drawdown máximo"} <= rotulos, rotulos
print("OK  backtesting exibe metricas e criterios")

at.sidebar.radio(key="pagina").set_value("Minha carteira"); at.run()
sem_excecao(at, "voltar para a carteira")
tabela = at.dataframe[0].value
assert tabela["Recomendação"][0] == "COMPRA"
print("OK  carteira mostra a recomendacao gerada ao lado do ativo")

qtd = [n for n in at.number_input if n.label == "Quantidade vendida"][0]
qtd.set_value(30)
botao(at, "Registrar venda").click(); at.run()
sem_excecao(at, "registrar venda pela tela")
assert any("Venda de 30" in x.value for x in at.success), [x.value for x in at.success]
assert at.dataframe[0].value["Quantidade"][0] == 70
print("OK  venda parcial (100 -> 70) refletida na tabela")

qtd = [n for n in at.number_input if n.label == "Quantidade vendida"][0]
qtd.set_value(500)
botao(at, "Registrar venda").click(); at.run()
assert any("apenas 70" in e.value for e in at.error), [e.value for e in at.error]
print("OK  venda maior que a posicao mostra erro claro")

botao(at, "Remover ativo").click(); at.run()
assert any("Marque a confirmação" in e.value for e in at.error)
[c for c in at.checkbox if "Confirmo" in c.label][0].set_value(True)
botao(at, "Remover ativo").click(); at.run()
sem_excecao(at, "remover ativo pela tela")
assert any("carteira ainda está vazia" in i.value for i in at.info)
print("OK  remocao exige confirmacao e deixa a carteira vazia (sem erro no seletor de atalhos)")

campo = [t for t in at.text_input if t.label == "Código do ativo"][0]
campo.set_value("b3sa3")
botao(at, "Registrar compra").click(); at.run()
sem_excecao(at, "compra de B3SA3 pela tela")
assert list(at.dataframe[0].value["Código"]) == ["B3SA3"]
print("OK  B3SA3 aceito pela tela")

campo = [t for t in at.text_input if t.label == "Código do ativo"][0]
campo.set_value("XX")
botao(at, "Registrar compra").click(); at.run()
assert any("Código inválido" in e.value for e in at.error)
print("OK  codigo invalido mostra erro amigavel")


botao(at, "Sair").click(); at.run()
sem_excecao(at, "sair volta para o login")
assert "usuario" not in at.session_state
at2 = AppTest.from_file(str(simulacoes.RAIZ / "src" / "public" / "Main.py"), default_timeout=60)
at2.run()
at2.text_input(key="loginEmail").set_value("maria@email.com")
at2.text_input(key="loginSenha").set_value("senhaerrada")
botao(at2, "Entrar").click(); at2.run()
assert any("inválidos" in e.value for e in at2.error)
print("OK  login com senha errada e rejeitado")
at2.text_input(key="loginSenha").set_value("segredo1")
botao(at2, "Entrar").click(); at2.run()
sem_excecao(at2, "login com a conta criada")
assert at2.session_state["usuario"]["email"] == "maria@email.com"
assert any("Carteira de Maria" in t.value for t in at2.title)
tabela = at2.dataframe[0].value
assert list(tabela["Código"]) == ["B3SA3"]
print("OK  apos o login a carteira salva (B3SA3) continua la")
print("\nTeste de interface concluido")
