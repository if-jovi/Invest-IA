"""Avaliação histórica da IA (spec desempenho-ia.md).

"Volta no tempo": para cada ativo e data passada, monta a análise só com os
dados até aquela data, pede a recomendação à IA (mesmo prompt do app) e grava
em `avaliacoes_ia`. A taxa de acerto aparece na tela "Desempenho da IA".

Uso (na raiz do projeto ou no container):
    python -m src.scripts.AvaliarIA                       # 40 chamadas por execução
    python -m src.scripts.AvaliarIA --limite 20 --pausa 6
    python -m src.scripts.AvaliarIA --ativos PETR4,VALE3 --meses 6

É retomável: rodar de novo continua de onde parou (pula o que já foi gravado).
"""
import argparse
import os
import sys
import time

import pandas as pd

ATIVOS_PADRAO = ["PETR4", "VALE3", "ITUB4", "BBDC4", "BBAS3", "ABEV3", "WEGE3", "B3SA3", "RENT3", "SUZB3"]
CODIGO_LIMITE_IA = 2


def datasAvaliacao(indice, meses: int = 12, intervalo: int = 10, horizonte: int = 20) -> list:
    """Pregões com data >= último - meses, menos os últimos `horizonte`; um a cada `intervalo`."""
    indice = pd.DatetimeIndex(indice)
    if len(indice) <= horizonte:
        return []
    candidatos = indice[indice >= indice[-1] - pd.DateOffset(months=meses)]
    candidatos = candidatos[candidatos <= indice[-1 - horizonte]]
    return list(candidatos[::intervalo])


def limiteDeUso(erro: Exception) -> bool:
    texto = str(erro).lower()
    return "limite" in texto or "429" in texto or "rate limit" in texto


def argumentos(argv):
    from src.models.Parametros import HORIZONTE_AVALIACAO
    parser = argparse.ArgumentParser(description="Avaliação histórica das recomendações da IA.")
    parser.add_argument("--ativos", default=",".join(ATIVOS_PADRAO), help="códigos separados por vírgula")
    parser.add_argument("--meses", type=int, default=12, help="quantos meses para trás avaliar")
    parser.add_argument("--intervalo", type=int, default=10, help="um pregão a cada N")
    parser.add_argument("--periodo", default="1y", choices=["3mo", "6mo", "1y", "2y"], help="período da análise")
    parser.add_argument("--limite", type=int, default=40, help="máximo de chamadas à IA nesta execução")
    parser.add_argument("--pausa", type=float, default=4.0, help="segundos entre chamadas à IA")
    parser.add_argument("--horizonte", type=int, default=HORIZONTE_AVALIACAO, help="pregões até conferir o preço")
    return parser.parse_args(argv)


def main(argv=None, servicoIa=None) -> int:
    from src.models.base import Session, criarTabelas
    from src.models.entities.AvaliacoesIaEntity import AvaliacoesIaEntity
    from src.models.Parametros import DIAS_AQUECIMENTO, MESES_PERIODO, SIMBOLO_IBOVESPA
    from src.models.services.IaService import criarServicoIa
    from src.models.services.IndicatorsService import IndicatorsService
    from src.models.services.YfinanceService import YfinanceService

    args = argumentos(argv)
    criarTabelas()
    ia = servicoIa or criarServicoIa()
    modelo = ia.modelo()
    provedor = (os.getenv("IA_PROVEDOR") or "openrouter").strip().lower()
    yahoo, indicadores = YfinanceService(), IndicatorsService()
    ativos = [a.strip().upper() for a in args.ativos.split(",") if a.strip()]

    inicio = (pd.Timestamp.today().normalize() - pd.DateOffset(months=args.meses + MESES_PERIODO[args.periodo])
              - pd.Timedelta(days=DIAS_AQUECIMENTO))
    try:
        ibovespa = yahoo.buscarHistoricoDesde(SIMBOLO_IBOVESPA, inicio, indice=True)
    except Exception as erro:
        print(f"Aviso: Ibovespa indisponível ({erro}); a avaliação segue sem a comparação.")
        ibovespa = None

    print(f"Avaliação histórica | modelo {modelo} | período {args.periodo} | até {args.limite} chamadas")
    geradas = puladas = falhas = chamadas = 0

    def resumo():
        print(f"Geradas: {geradas} | Puladas (já existiam): {puladas} | Falhas: {falhas}")

    for ativo in ativos:
        try:
            historico = yahoo.buscarHistoricoDesde(ativo, inicio)
            stock = yahoo.buscarInfo(ativo)
        except Exception as erro:
            print(f"{ativo}: sem dados do Yahoo ({erro}); pulando o ativo.")
            falhas += 1
            continue

        with Session() as session:
            feitas = {str(r.data_referencia) for r in session.query(AvaliacoesIaEntity.data_referencia)
                      .filter_by(item=ativo, periodo=args.periodo, modelo=modelo)}

        for data in datasAvaliacao(historico.index, args.meses, args.intervalo, args.horizonte):
            dia = str(pd.Timestamp(data).date())
            if dia in feitas:
                puladas += 1
                continue
            if chamadas >= args.limite:
                resumo()
                print(f"Limite de {args.limite} chamadas desta execução atingido. "
                      "Rode o mesmo comando de novo para continuar de onde parou.")
                return 0

            ateData = historico[historico.index <= data]
            try:
                ind = indicadores.calcular(ativo, ateData, args.periodo)
            except ValueError as erro:
                print(f"{ativo} {dia}: {erro}")
                falhas += 1
                continue
            if ibovespa is not None:
                ind.ibovespa = indicadores.compararIndice(indicadores.recortarPeriodo(ateData, args.periodo),
                                                          ibovespa)

            chamadas += 1
            try:
                rec = ia.gerarRecomendacao(stock, ind)
            except RuntimeError as erro:
                if limiteDeUso(erro):
                    resumo()
                    print(f"Parado: {erro}\nO que já foi feito está salvo. "
                          "Rode o mesmo comando de novo (mais tarde) para continuar de onde parou.")
                    return CODIGO_LIMITE_IA
                print(f"{ativo} {dia}: falha da IA ({erro})")
                falhas += 1
                continue
            except ValueError as erro:
                print(f"Configuração da IA: {erro}")
                return 1

            with Session() as session:
                session.add(AvaliacoesIaEntity(
                    item=ativo, data_referencia=dia, periodo=args.periodo, recomendacao=rec.recomendacao,
                    preco=ind.preco_atual, provedor=provedor, modelo=modelo,
                    resposta_completa=rec.resposta_completa))
                session.commit()
            geradas += 1
            print(f"{ativo} {dia}: {rec.recomendacao}")
            if args.pausa > 0:
                time.sleep(args.pausa)

    resumo()
    print("Avaliação concluída. Veja o resultado na tela 'Desempenho da IA'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
