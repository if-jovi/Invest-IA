# InvestIA - MVC com login, carteira, analise e backtesting

## Estrutura

```
src/
  controllers/   Auth, Carteira, ItensCarteira, Analise, Backtest (validam a entrada)
  models/
    base.py      engine, Session, horario de Brasilia e criarTabelas()
    entities/    Usuarios, Carteiras, ItensB3, ItensCarteiras, Operacoes,
                 Recomendacoes (tabelas) + StockEntity (dados temporarios do yfinance)
    services/    Auth, Carteira, ItensB3, ItensCarteira, Yfinance, Indicators,
                 Claude, Recomendacoes, Analise, Backtest (regra de negocio e banco)
  public/
    Main.py      ponto de entrada do Streamlit
    views/       Login, CarteiraDashboard, AnaliseView, BacktestView,
                 charts, Paginas, Formatacao
  scripts/       Diagnostico (testa as integracoes) e SeedItensB3 (pre-cadastro opcional)
tests/           quatro baterias automatizadas (ver abaixo)
```

Fluxo: View -> Controller -> Service -> Entity.

## Como aplicar no projeto

1. Copie o conteudo desta pasta por cima do projeto, mantendo as pastas.
2. Apague os arquivos antigos substituidos:
   - `base.py` da raiz (agora fica em `src/models/base.py`)
   - `src/controllers/analysis_controller.py` e `history_controller.py`
   - `src/models/services/claude_service.py`, `database_service.py`, `indicators_service.py`
3. O Dockerfile inicia `src/public/Main.py` (M maiusculo: no Linux a caixa importa).
4. Recrie as tabelas (as antigas `operacoes`/`recomendacoes` tinham a coluna `ticker`, agora e `item`;
   o `create_all` nao altera tabelas existentes). Apaga os dados de teste dessas tabelas:

```
docker compose exec db psql -U postgres -d invest_ia -c "DROP TABLE IF EXISTS recomendacoes, operacoes, itens_carteiras, itens_carteira, carteiras, itens_b3, ativos_b3, usuarios CASCADE;"
```

5. `docker compose up --build` (o `requirements.txt` mudou, entao o build reinstala as dependencias).

## Por que o requirements.txt mudou

| Pacote | Antes | Agora | Motivo |
|--------|-------|-------|--------|
| yfinance | 0.2.40 | >=1.7,<2 | O Yahoo responde HTTP 429 a clientes `requests`; as versoes novas usam `curl_cffi` |
| anthropic | 0.28.0 | >=1.0,<2 | A 0.28.0 quebra com o httpx atual (`unexpected keyword argument 'proxies'`) |
| pyarrow | sem versao | 17.0.0 | O pyarrow mais novo exige NumPy 2; com `numpy==1.26.4` as tabelas do Streamlit quebram |

## Diagnostico das integracoes (rode isto primeiro)

```
docker compose exec app python -m src.scripts.Diagnostico
docker compose exec app python -m src.scripts.Diagnostico --completo
```

Testa banco, Yahoo (historico, dados da empresa, cotacao), indicadores e Claude (chamada minima),
mostra [ OK ] ou [FALHA] em cada etapa e a dica de correcao. Com `--completo` roda a analise inteira.
O modelo da Claude pode ser trocado sem editar codigo: `CLAUDE_MODEL=claude-sonnet-5-5` no `.env`.

## Testes automatizados

```
docker compose exec app python -m tests.executar_todos
```

- teste_logica: cadastro, login, carteira, compra/venda, cache da IA, backtest, horario de Brasilia, B3SA3
- teste_yfinance: biblioteca yfinance real com a camada HTTP simulada (sucesso, 429, rede fora, ticker inexistente)
- teste_claude: SDK anthropic real contra um servidor local (sucesso, 401, 403, 404, 429, 500, timeout, formato)
- teste_interface: o Main.py rodando no Streamlit (AppTest) do cadastro ao backtesting

Os testes nao acessam a internet nem gastam creditos: o que depende de Yahoo e Claude e simulado.
O Diagnostico e o que confirma as conexoes reais.

## Uso

- Cadastro cria o usuario e a carteira (1:1) na mesma transacao.
- Ao registrar uma compra, o ativo e validado e cadastrado em `itens_b3` pelo yfinance.
- Analise: calcula RSI, MACD e medias, pede a recomendacao ao Claude e reaproveita a recomendacao
  ja gerada para o mesmo ativo e a mesma data de referencia. Resposta fora do formato nunca e gravada.
- Backtesting: simula a estrategia (cruzamento do MACD + RSI) e salva as operacoes do usuario.
- Pre-cadastro opcional do catalogo: `docker compose exec app python -m src.scripts.SeedItensB3 PETR4 VALE3`
