# Relatório — como o InvestIA funciona

## Objetivo

Reunir em **um único documento** o funcionamento completo do InvestIA no
estado **atual** do código (atualizado em 06/11/2026): o que o sistema faz,
como cada parte funciona por dentro, o banco de dados, as integrações, o
ambiente e os testes. É propositalmente redundante com `overview.md`,
`architecture/overview.md` e as specs, para servir de base a um documento
separado (ex.: capítulo do TCC).

## Audiência

- **Autor / banca** — entender e explicar o sistema inteiro.
- **Devs e agentes IA** — ponto de partida antes de mexer em qualquer parte.

---

## 1. Visão geral

O InvestIA é um sistema web de apoio à decisão para **investidores iniciantes
em ações da B3**, desenvolvido como TCC (João Vitor Martins, Horus
Faculdades). O usuário escolhe uma ação e o sistema:

1. busca o histórico de preços no Yahoo Finance;
2. calcula indicadores de análise técnica (RSI, MACD e médias móveis), um
   resumo do período escolhido e a comparação com o Ibovespa;
3. envia esses dados a uma IA, que devolve **COMPRA, VENDA ou MANTER**,
   explica o que a empresa faz e justifica a recomendação em linguagem
   simples, listando os riscos.

Além disso, o sistema oferece:
- **login**;
- uma **carteira**: compras, vendas, preço médio e cotação atualizada;
- um **backtesting**: testa a estratégia MACD + RSI no passado, com custos, e
  a compara com o Buy and Hold e com o Ibovespa;
- a tela **Desempenho da IA**: mede quantas vezes as recomendações da IA
  acertaram, com margem de erro e teste estatístico.

A recomendação é sempre apoio à decisão, nunca garantia de retorno.

### Público-alvo: o investidor iniciante

O sistema foi pensado para quem **está começando a investir em ações** e
ainda não domina análise técnica nem o vocabulário do mercado. Isso orienta o
projeto inteiro:

- **Sem jargão:**
  - a IA é instruída a explicar em português simples e sem termos
    desnecessários;
  - cada indicador aparece na tela com uma frase do que significa (ex.:
    "Acima de 70: possível sobrecompra (preço esticado).");
  - a IA explica também o que a empresa faz.
- **Decisão em três opções claras:** COMPRA, VENDA ou MANTER, com cores
  distintas, em vez de números brutos para o usuário interpretar sozinho.
- **Riscos sempre visíveis:** toda recomendação traz a lista de riscos e o
  aviso de que é apoio à decisão, nunca garantia de retorno. O backtesting
  avisa que resultado passado não garante resultado futuro.
- **Poucos indicadores, e os clássicos:** RSI, MACD e médias móveis, os mais
  citados em material introdutório, em vez de dezenas de indicadores.
- **Aprender com o passado:** o backtesting mostra, de forma concreta, como a
  estratégia teria se saído e a compara com simplesmente comprar e segurar.
- **Organização da carteira:** preço médio, resultado e variação do dia
  calculados automaticamente, sem planilha.
- **Formato brasileiro:** R$, vírgula decimal e datas DD/MM/AAAA.
- **Funciona no celular:** o menu fica recolhido, as métricas aparecem 2 por
  linha e os gráficos se ajustam à largura da tela (ver `specs/interface.md`).
- **Nenhum custo para usar:** o provedor de IA padrão usa só modelos
  gratuitos, e os dados de mercado vêm do Yahoo Finance, também gratuito.

### Telas

| Tela | O que faz |
| ---- | --------- |
| Login / cadastro | Entrada no sistema; o cadastro já cria a carteira do usuário |
| Minha carteira (inicial) | Posições, valor investido, valor atual, resultado, variação do dia, última recomendação de cada ativo e gerenciamento (compra, venda, correção, remoção) |
| Análise de ativo | Análise de 1 a 5 ativos com recomendação da IA, indicadores, quadro comparativo e histórico |
| Backtesting | Simulação da estratégia MACD + RSI sobre o histórico, com custos, métricas, Ibovespa e operações |
| Desempenho da IA | Taxa de acerto das recomendações da IA, com margem de erro, teste estatístico e limitações |

## 2. Tecnologias e arquitetura

### 2.1 Tecnologias utilizadas

Versões conforme `requirements.txt`, `Dockerfile` e `docker-compose.yml`.

**Linguagem e interface**

| Tecnologia | Versão | Para que é usada |
| ---------- | ------ | ---------------- |
| Python | 3.11 (imagem `python:3.11-slim`) | Linguagem de todo o sistema |
| Streamlit | 1.66.1 | Interface web: telas, formulários, menu (`st.navigation`), sessão do usuário, atualização periódica (`st.fragment`) |
| Plotly | 7.1.0 | Gráficos interativos: candlestick com médias móveis, MACD com histograma, RSI e curva do backtesting |
| Fonte Inter (Google Fonts) | — | Tipografia do tema |

**Dados e cálculo**

| Tecnologia | Versão | Para que é usada |
| ---------- | ------ | ---------------- |
| pandas | ≥ 2.2, < 3 | Séries de preços e cálculo dos indicadores e das métricas |
| NumPy | ≥ 2.3, < 2.4 | Suporte numérico aos cálculos (ex.: semente da média exponencial) |
| PyArrow | ≥ 21, < 27 | Exigido pelo Streamlit para exibir tabelas (`st.dataframe`) |
| yfinance | 1.7.0 | Histórico de preços, dados da empresa e cotações do Yahoo Finance |

**Inteligência artificial**

| Tecnologia | Versão | Para que é usada |
| ---------- | ------ | ---------------- |
| OpenRouter (API) | — | Provedor padrão; dá acesso aos modelos NVIDIA Nemotron gratuitos (`:free`) |
| httpx | ≥ 0.28, < 1 | Cliente HTTP da chamada ao OpenRouter e do script do catálogo |
| google-genai | ≥ 2.0, < 3 | SDK do Google Gemini (provedor opcional) |
| anthropic | ≥ 1.0, < 2 | SDK da Anthropic Claude (provedor opcional) |
| Pydantic | 2 (dependência do `google-genai`) | Valida o JSON devolvido pela IA antes de gravar |

**Banco de dados**

| Tecnologia | Versão | Para que é usada |
| ---------- | ------ | ---------------- |
| PostgreSQL | 16 (imagem `postgres:16-alpine`) | Banco relacional do sistema |
| SQLAlchemy | 2.0.30 | ORM: entidades, sessões e consultas |
| psycopg2-binary | 2.9.9 | Driver PostgreSQL usado pelo SQLAlchemy |
| Alembic | 1.13.1 | Migrações de schema (`migracoes/`), aplicadas automaticamente na inicialização |
| SQLite | (embutido no Python) | Banco em memória dos testes automatizados |

**Configuração, ambiente e ferramentas**

| Tecnologia | Versão | Para que é usada |
| ---------- | ------ | ---------------- |
| python-dotenv | 1.0.1 | Lê o `.env` (chaves de IA, conexão com o banco) |
| Docker / Docker Compose | — | Sobe app, banco e pgAdmin com um comando |
| pgAdmin 4 | imagem `dpage/pgadmin4` | Administração visual do banco (porta 5051) |
| brapi.dev (API) | — | Fonte da lista de ações da B3 (só no script de atualização do catálogo) |
| Biblioteca padrão do Python | — | `hashlib`/`hmac` (senhas), `concurrent.futures` (análises em paralelo), `subprocess` (execução da suíte de testes) |
| Git | — | Controle de versão |

### 2.2 Arquitetura em camadas (MVC)

| Camada | Diretório | Responsabilidade |
| ------ | --------- | ---------------- |
| View | `src/public/views/`, `src/public/paginas/` | Telas Streamlit; só chamam controllers |
| Controller | `src/controllers/` | Valida a entrada e levanta `ValueError` com mensagem ao usuário |
| Service | `src/models/services/` | Regra de negócio, banco e integrações |
| Entity | `src/models/entities/` | Tabelas SQLAlchemy e objetos de transporte |

Os services abrem a sessão do banco (`with Session()`) e devolvem
dicionários (DTOs) às telas, nunca entidades ligadas à sessão.

## 3. Decisões importantes de projeto

Cada decisão traz o que foi escolhido, o motivo e o custo (o que se abre mão).
As escolhas estão no código; os motivos registram a intenção do projeto e
podem ser ajustados pelo autor.

| # | Decisão | Motivo | Custo / consequência |
| - | ------- | ------ | -------------------- |
| D1 | **Análise técnica** (RSI, MACD, SMA20/50) como base da recomendação, e não análise fundamentalista | Usa só o histórico de preços, disponível de graça e diariamente; os indicadores são clássicos, fáceis de explicar e de verificar | Ignora balanços, dividendos e notícias; a recomendação reflete o comportamento do preço |
| D2 | **A IA interpreta, não calcula** | Os indicadores são calculados em código (determinístico e testável); a IA só traduz os números em recomendação e explicação para o iniciante. O prompt proíbe inventar dados | A qualidade do texto depende do modelo; a decisão final da IA não é determinística |
| D3 | **Três saídas fixas:** COMPRA, VENDA ou MANTER | Fácil de entender para o iniciante, de colorir na tela e de comparar entre ativos | Perde nuances (ex.: "comprar aos poucos") |
| D4 | **Linguagem simples e riscos obrigatórios** | O público não domina o jargão; deixar claro que é apoio à decisão reduz o risco de o usuário tratar a recomendação como garantia | Respostas mais longas |
| D5 | **Vários provedores de IA, escolhidos no `.env`**, com o mesmo prompt | Não ficar preso a um fornecedor; trocar de modelo sem mudar código; comparar provedores no TCC | Três integrações para manter e testar |
| D6 | **OpenRouter com modelos gratuitos como padrão**, recusando modelos pagos | Custo zero para o autor e para quem roda o projeto | Limites de uso por minuto e por dia; modelos gratuitos podem mudar ou sair do ar |
| D7 | **Yahoo Finance via `yfinance`** como fonte de dados | Gratuito, sem cadastro, cobre a B3 (sufixo `.SA`) e traz dados da empresa | API não oficial: pode mudar, limitar requisições ou falhar; por isso há cache, tradução de erros e o script de diagnóstico |
| D8 | **Cache de recomendações** por ativo + data de referência | Evita chamar a IA de novo para os mesmos dados (economiza limite e tempo) e mantém a resposta estável no dia | O período entra na chave: análises de 3 meses e de 1 ano no mesmo dia são diferentes |
| D9 | **Catálogo de ações local** (JSON versionado + seed) | O autocomplete funciona sem internet e sem chamar API externa a cada uso | A lista precisa ser atualizada pelo script de tempos em tempos |
| D10 | **Streamlit** para a interface | Interface web inteira em Python, sem front-end separado; adequado ao escopo de um TCC | Menos controle de layout; o app roda a tela de novo a cada interação |
| D11 | **MVC em camadas** (View → Controller → Service → Entity) | Separa tela, validação e regra de negócio; permite testar a regra sem a interface | Mais arquivos e camadas que um script único |
| D12 | **PostgreSQL + SQLAlchemy** (ORM), com SQLite nos testes | Banco robusto e gratuito no app; o ORM permite rodar a mesma regra num banco em memória nos testes | Diferenças entre os dois bancos precisam de atenção (ex.: tipos de data) |
| D13 | **Senhas com PBKDF2-SHA256** (200 mil iterações, salt) e mensagem genérica no login | Segurança adequada usando só a biblioteca padrão; não revela quais emails estão cadastrados | Sem recuperação de senha nem login social |
| D14 | **Uma carteira por usuário**, com **preço médio ponderado** | Modelo mais simples para o iniciante, igual ao que a corretora mostra | Não guarda o histórico de cada compra e venda |
| D15 | **Backtesting com regra fixa, sem IA** | Mede a coerência dos sinais técnicos de forma objetiva e reproduzível, e compara com o Buy and Hold | Não mede a qualidade das recomendações da IA (isso é feito em D24) |
| D16 | **Docker Compose** para o ambiente | Qualquer pessoa (inclusive a banca) sobe o sistema completo com um comando | Exige Docker instalado |
| D17 | **Integrações simuladas nos testes** | A suíte roda sem internet, sem chaves e sem gastar limite de uso | Os simuladores precisam acompanhar mudanças das APIs reais |
| D18 | **Spec-Driven Development** (`.agents/docs/`) | Mudanças com comportamento novo começam pela spec com critérios de aceite, depois testes, depois código; facilita o trabalho com assistentes de IA | Mais documentação para manter atualizada |
| D19 | **Resposta da IA em JSON validado**, com `seed` fixo | Formato à prova de variações de escrita; resposta incompleta ou fora do contrato é recusada em vez de exibida pela metade; mesmos dados → resposta mais estável | Uma resposta recusada exige nova tentativa |
| D20 | **Raciocínio baixo no modelo do OpenRouter** (`reasoning: low`, `max_tokens` 8192) | O modelo "pensa" antes de responder e isso consumia o limite: num teste real a resposta saiu cortada | Explicações um pouco menos elaboradas; ainda ~1 min por análise |
| D21 | **Aquecimento dos indicadores** (150 dias extras antes do período) | Indicadores corretos desde o 1º dia do período; o período de 3 meses passa a ser útil | Busca mais dados no Yahoo |
| D22 | **Comparação com o Ibovespa** | "Subiu 12%" só é bom se o mercado subiu menos; dá referência ao iniciante e à IA | Uma consulta a mais ao Yahoo (com cache de 1 hora) |
| D23 | **Custos da B3 no backtesting** (0,03% por ponta) e **posição aberta contabilizada** | Resultado mais realista, sem esconder a última operação | Resultados um pouco menores que antes |
| D24 | **Medir o acerto da IA** com avaliação histórica, margem de erro (Wilson) e teste binomial contra "comprar sempre" | Responde à pergunta central do TCC com números defensáveis e honestos | Gasta chamadas do plano gratuito (≈ 200, em várias execuções); limitações declaradas |

## 4. Inicialização e navegação

- `src/public/Main.py` configura a página, aplica o tema e, **uma vez por
  processo** (`st.cache_resource`), cria as tabelas ausentes
  (`criarTabelas()` → `migrar()`, que aplica as migrações Alembic pendentes) e semeia o catálogo de ações. Se o
  banco estiver fora do ar, mostra o erro e para.
- Sem usuário na sessão, mostra o login. Com usuário, monta o menu lateral
  (`st.navigation`) com as quatro telas (Minha carteira, Análise de ativo,
  Backtesting e Desempenho da IA), o nome e o email do usuário e o botão
  **Sair**, que limpa a sessão.
- Erros inesperados de uma tela aparecem como mensagem, sem derrubar o app.

## 5. Autenticação

- **Cadastro** (`AuthController.cadastrar`): exige nome, email válido, senha
  com no mínimo 6 caracteres e confirmação igual. O email é normalizado para
  minúsculas e é único. Junto com o usuário é criada a carteira "Minha
  carteira".
- **Senha:** PBKDF2-HMAC-SHA256 com 200.000 iterações e salt aleatório de 16
  bytes, gravada como `salt$hash`. A comparação usa `hmac.compare_digest`.
- **Login:** mensagem genérica "Email ou senha inválidos." nos dois casos. Se
  o email não existe, o sistema verifica a senha contra um hash falso para o
  tempo de resposta não revelar quais emails existem.
- A sessão do usuário fica no `st.session_state` do Streamlit.

## 6. Catálogo de ativos

- A tabela `itens_b3` guarda os ativos conhecidos (código, nome, setor e se
  está ativo). Formato aceito: `^[A-Z][A-Z0-9]{3}[0-9]{1,2}$` (ex.: PETR4,
  VALE3, TAEE11). O sufixo `.SA` do Yahoo é removido.
- Na inicialização, `semearCatalogo` insere as ações de
  `src/data/ativos_b3.json` que ainda não estão no banco.
- O JSON é atualizado pelo script `src/scripts/AtualizarCatalogoB3.py`, que
  baixa a lista da brapi.dev.
- `obterOuCadastrar`: se o ativo existe e está ativo, usa o cadastro; se está
  desativado, recusa; se não existe, consulta o Yahoo para validar o código e
  cadastra.
- As telas usam o catálogo no autocomplete dos campos de ativo.

## 7. Carteira

- Cada usuário tem **uma** carteira, com um item por ativo
  (`itens_carteiras`, único por carteira e ativo).
- **Compra:** soma a quantidade e recalcula o **preço médio ponderado**:
  `(qtd_atual × preço_médio + qtd_comprada × preço_compra) / nova_qtd`.
- **Venda:** reduz a quantidade sem mudar o preço médio. Vender mais do que
  se tem é recusado. Se a posição zera, o item sai da carteira.
- **Correção:** permite definir quantidade e preço médio manualmente.
  **Remoção:** apaga o item.
- **Resumo** (`CarteiraService.obterResumo`), por ativo e total:
  - valor investido = quantidade × preço médio;
  - valor atual = quantidade × cotação atual;
  - resultado em R$ e em %;
  - variação do dia contra o fechamento anterior;
  - última recomendação gerada para o ativo.

  Ativos sem cotação ficam fora do valor atual e são sinalizados.
- **Cotações:** uma única chamada `yf.download` para todos os ativos (últimos
  5 dias). O cache é de 60 s por ativo, ou 30 s depois de uma falha. A tela
  recarrega o resumo a cada 60 s (`st.fragment(run_every=60)`).

## 8. Análise de ativo (recomendação com IA)

### Resumo em uma frase

O sistema baixa os preços diários do ativo no período escolhido (mais ~100
pregões de aquecimento) e calcula os indicadores técnicos. Depois, tira uma
**"foto" do último pregão** (preço, RSI, MACD e médias móveis) e resume o
período: retorno, máxima e mínima, volatilidade, maior queda e comparação com
o Ibovespa. Tudo isso, com os dados da empresa, vai para a IA, que responde
em JSON. A recomendação validada é gravada e reaproveitada se o mesmo ativo
for analisado de novo com a mesma data de referência e o mesmo período.

### 8.1 Tela e validação

- O usuário escolhe de 1 a 5 ativos, o período (`3mo`, `6mo`, `1y` ou `2y`;
  padrão 1 ano) e, se quiser, marca **"Gerar nova análise"** (`forcar`), que
  ignora o cache.
- `AnaliseController.analisarVarios`:
  - normaliza os códigos e remove duplicados;
  - valida o limite de 5 ativos e o período;
  - roda `AnaliseService.analisar` para cada ativo, **2 em paralelo**.

  Um erro em um ativo não derruba os demais: ele aparece na lista de erros.

### 8.2 Histórico de preços

`YfinanceService.buscarHistorico` chama
`yf.Ticker("<CÓDIGO>.SA").history(start=<hoje − período − 150 dias>, interval="1d")`.
Volta um pregão por dia: o **período** (3 meses ≈ 62 pregões, 1 ano ≈ 250)
**mais ~100 pregões de aquecimento** antes dele, usados só para calcular os
indicadores (spec [`historico-aquecimento.md`](../specs/historico-aquecimento.md)).
Ficam as colunas Open, High, Low, Close e Volume, e as linhas com valor
faltando são removidas.

O **período** começa no 1º pregão com data ≥ `último pregão − N meses`.

### 8.3 Indicadores técnicos (`IndicatorsService.calcular`)

Exige pelo menos 52 pregões e calcula, para **cada dia**, sobre o fechamento:

| Indicador | Parâmetros | Como |
| --------- | ---------- | ---- |
| RSI | 14 | médias exponenciais de ganhos e perdas (alfa = 1/14, estilo Wilder) |
| MACD | 12, 26, 9 | EMA12 − EMA26; linha de sinal = EMA9 do MACD; histograma = diferença |
| SMA20 / SMA50 | 20 e 50 | médias móveis simples |

Os indicadores são calculados sobre o histórico inteiro (aquecimento +
período). Depois o sistema fica só com os pregões do **período**, todos com
indicadores completos (3 meses ≈ 62 pregões no gráfico). Os indicadores do
último dia já vêm "aquecidos", ou seja, mais precisos.

Do **último dia** sai a "foto" (`IndicatorsEntity`):

- preço de fechamento e data de referência;
- RSI e o sinal correspondente: `sobrecompra` (> 70), `sobrevenda` (< 30) ou
  `neutro`;
- MACD, linha de sinal e histograma;
- cruzamento: `alta` ou `baixa`, pelo cruzamento entre ontem e hoje ou, sem
  cruzamento, pela posição atual do MACD em relação ao sinal;
- SMA20, SMA50 e a tendência: `alta` se a SMA20 está acima da SMA50.

### 8.4 Cache de recomendações

`RecomendacoesService.buscarPorItemDataEPeriodo(item, data_referencia, periodo)`
procura uma recomendação já gravada para o **mesmo ativo, a mesma data de
referência e o mesmo período** (a mais recente). Se ela existir e `forcar`
estiver desmarcado, é devolvida sem chamar a IA, e a tela avisa quando foi
gerada. Recomendações antigas, gravadas antes de o período existir
(`periodo` nulo), nunca são reaproveitadas.

### 8.5 Chamada à IA

- `criarServicoIa()` escolhe o provedor por `IA_PROVEDOR` no `.env`:
  `openrouter` (padrão), `gemini` ou `claude`. Os três usam o mesmo prompt
  (`ClaudeService.montarPrompt`), porque `OpenRouterService` e
  `GeminiService` herdam de `ClaudeService`.
- `YfinanceService.buscarInfo` traz nome, setor, segmento e descrição da
  empresa (em inglês; a IA resume em português).
- **O que vai no prompt:**
  - os dados da empresa;
  - a foto do último dia: preço, RSI e sinal, MACD, sinal e cruzamento,
    SMA20, SMA50 e tendência;
  - o **resumo do período** e o horizonte ("3 meses", "1 ano"…), calculados
    por `IndicatorsService.resumirPeriodo` sobre os pregões do período (sem o
    aquecimento):

    | Métrica | Cálculo |
    | ------- | ------- |
    | Retorno no período | último ÷ primeiro fechamento − 1 |
    | Máxima e mínima | maior e menor fechamento, com a distância % do preço atual até cada uma |
    | Volatilidade anualizada | desvio padrão dos retornos diários × √252 |
    | Drawdown máximo | maior queda de um pico até um vale dentro do período |
  - a **comparação com o Ibovespa** (`^BVSP`) no mesmo período: retorno do
    índice e diferença em pontos percentuais. Se o Ibovespa não puder ser
    obtido, a linha é omitida e a análise segue
    ([`comparacao-ibovespa.md`](../specs/comparacao-ibovespa.md)).
- **O que não vai:** a série histórica dia a dia.
- **Regras do prompt:**
  - usar só os dados fornecidos, sem inventar notícias ou números;
  - deixar claro que é apoio à decisão;
  - explicar cada indicador em linguagem simples;
  - considerar o horizonte informado na recomendação;
  - comparar o desempenho da ação com o do Ibovespa.
- **Formato da resposta: JSON** com quatro campos (`recomendacao`,
  `sobre_empresa`, `justificativa`, `riscos`), pedido com a saída estruturada
  de cada provedor:
  - **OpenRouter:** `response_format` json_schema;
  - **Gemini:** `response_json_schema`;
  - **Claude:** `output_config`.

  O JSON é validado (Pydantic) antes de gravar: recomendação só COMPRA,
  VENDA ou MANTER, textos não vazios, de 1 a 8 riscos. Resposta fora do
  contrato → "A IA respondeu fora do formato esperado"; resposta cortada pelo
  limite de tamanho → "A resposta da IA veio incompleta". Nos dois casos, nada
  é gravado ([`analise-ia.md`](../specs/analise-ia.md)).
- **Consistência:** `temperature` 0.3 e `seed` 42 (OpenRouter e Gemini).
- **OpenRouter:** `max_tokens` 8192 e raciocínio baixo (`reasoning: low`).
  O modelo padrão "raciocina" antes de responder, e num teste real esse
  raciocínio consumiu o limite e cortou a resposta.

### 8.6 Gravação e exibição

- `RecomendacoesService.salvar` grava em `recomendacoes`: ativo, data de
  referência, período, indicadores da foto, recomendação, sobre a empresa,
  justificativa, riscos (um por linha) e a resposta completa (o JSON).
- **A tela mostra:**
  - o card com a recomendação, o preço de referência, a data dos dados e a
    "Variação no período" (o retorno do período inteiro);
  - os quatro indicadores com frases explicativas;
  - o bloco "Comportamento em <período>", com as cinco métricas do resumo e o
    card "Ibovespa no período" (com a diferença em p.p.);
  - a explicação da IA, a empresa e os riscos;
  - um atalho para registrar a compra na carteira;
  - o quadro comparativo, quando há mais de um ativo;
  - o histórico de recomendações do ativo, com a coluna "Período" ("—" nas
    antigas).

### 8.7 Diagrama do fluxo

```
Tela (ativos, período, forçar?)
  └─ AnaliseController.analisarVarios        ≤ 5 ativos, 2 em paralelo
       └─ AnaliseService.analisar(ativo, período)
            ├─ ItensB3Service.obterOuCadastrar
            ├─ YfinanceService.buscarHistorico  ← período + ~100 pregões de aquecimento
            ├─ IndicatorsService.calcular       ← RSI, MACD, SMA (com aquecimento); resumo
            │                                     do período; foto do último dia
            ├─ YfinanceService.buscarHistoricoIndice ← Ibovespa (cache 1 h) → comparação
            ├─ cache: ativo + data + período ── achou? ─► devolve
            ├─ YfinanceService.buscarInfo       ← dados da empresa
            ├─ IA.gerarRecomendacao(empresa, foto + resumo + Ibovespa) → JSON validado
            └─ RecomendacoesService.salvar
```

### 8.8 Limitações conhecidas

1. **Tempo de resposta:** com o modelo gratuito do OpenRouter, uma análise
   leva **cerca de 1 minuto** (medido em 06/11/2026: 58 s). Na banca,
   recomenda-se gerar antes as análises que serão mostradas, para que o
   cache responda na hora.
2. **Limites do plano gratuito:** muitas análises seguidas podem esbarrar no
   limite de uso do modelo (mensagem traduzida na tela).
3. **A IA não é determinística:** mesmo com `seed` e `temperature` baixa, o
   texto pode variar entre execuções; por isso há o cache por ativo + data +
   período.

**Histórico de correções (06/11/2026):**
- [`analise-periodo.md`](../specs/analise-periodo.md): antes, a IA não recebia
  nada sobre o período, o cache ignorava o período e a "Variação no período"
  media só os pregões que sobravam depois do `dropna`.
- [`historico-aquecimento.md`](../specs/historico-aquecimento.md): antes, com
  3 meses, só ~12 pregões tinham indicadores.
- [`analise-ia.md`](../specs/analise-ia.md): antes, o texto da IA era recortado
  por títulos, e uma resposta cortada era aceita pela metade sem aviso.

## 9. Backtesting

Testa no passado uma regra fixa baseada nos mesmos indicadores. **Não usa
IA.**

- **Entrada:** ativo e período (3 meses a 2 anos). Usa o mesmo histórico
  (com aquecimento) e os mesmos indicadores da análise. Simula sobre **todos os
  pregões do período**: 3 meses ≈ 62. O cruzamento do 1º dia do período é
  comparado com o último dia do aquecimento.
- **Regra** (`BacktestService.simular`), dia a dia:
  - **compra**, se estiver fora de posição: o MACD cruza o sinal para cima e
    o RSI está abaixo de 70;
  - **venda**, se estiver posicionado: o MACD cruza o sinal para baixo ou o
    RSI passa de 70.

  Entrada e saída são pelo fechamento do dia. Uma posição ainda aberta no
  último dia é encerrada pelo fechamento desse dia, marcada como **"Em
  aberto"**, e entra nas métricas.
- **Custos:** `CUSTO_OPERACAO_PCT` = **0,03%** em cada compra e em cada venda
  (emolumentos e liquidação da B3, corretagem zero). Resultado líquido de uma
  operação: `(saída × (1 − c)) / (entrada × (1 + c)) − 1`. O Buy and Hold
  também desconta as duas pontas.
- **Métricas:**
  - total de operações;
  - taxa de acerto (% de operações com lucro);
  - retorno acumulado (os retornos compostos);
  - retorno do Buy and Hold (primeiro contra último fechamento, com custos);
  - retorno do **Ibovespa** no período (referência de mercado, sem custos);
  - drawdown máximo da curva acumulada;
  - **Índice de Sharpe anualizado:** média dos retornos diários da estratégia
    ÷ desvio padrão × √252, sem taxa livre de risco. Os custos entram nos
    retornos diários
    ([`specs/backtesting.md`](../specs/backtesting.md)).
- **Critérios do protótipo** exibidos na tela: taxa de acerto acima de 55%,
  Sharpe acima de 1,0 e retorno acima do Buy and Hold.
- **Persistência:** as operações substituem as anteriores do mesmo usuário e
  ativo na tabela `operacoes`. Se a gravação falhar, a tela só avisa.
- **Fora do cálculo:** taxa livre de risco (CDI), imposto de renda e
  derrapagem de preço.
- **Limitação:** avalia a regra fixa de MACD + RSI, **não a IA**. A IA é
  avaliada na tela "Desempenho da IA" (seção 10).

## 10. Desempenho da IA

Mede se as recomendações da IA acertam
([`desempenho-ia.md`](../specs/desempenho-ia.md)). É a resposta à pergunta
central do TCC.

- **Como se mede:** cada recomendação é conferida **20 pregões depois**
  (≈ 1 mês):
  - COMPRA acerta se o preço subiu;
  - VENDA acerta se o preço caiu;
  - MANTER acerta se o preço variou no máximo **3%** para cima ou para baixo.

  Também conta o **acerto contra o Ibovespa**: a COMPRA acerta se a ação
  rendeu mais que o índice no mesmo prazo, e a VENDA, se rendeu menos.
- **Duas fontes de dados:**
  - **Avaliação histórica:** o script `python -m src.scripts.AvaliarIA` "volta
    no tempo". Para 10 ações líquidas (PETR4, VALE3, ITUB4, BBDC4, BBAS3,
    ABEV3, WEGE3, B3SA3, RENT3, SUZB3), a cada 10 pregões dos últimos 12 meses,
    monta a análise **só com os dados até aquela data** e pede a recomendação
    à IA, com o mesmo prompt do app. Os resultados ficam na tabela
    `avaliacoes_ia`. O script é **retomável**: faz até 40 chamadas por
    execução, com pausa de 4 s entre elas, e para sem perder nada se o limite
    de uso da IA for atingido. São ≈ 200 chamadas no total.
  - **Uso no app:** as recomendações gravadas em `recomendacoes`, conferidas
    quando os 20 pregões se completam.
- **Números mostrados** (`DesempenhoIaService`):
  - recomendações avaliadas e pendentes;
  - acerto geral e por tipo, com **margem de 95%** (intervalo de Wilson);
  - **taxa base**: o acerto de quem "compra sempre". A COMPRA da IA só agrega
    valor se superar esse número;
  - **chance de ser sorte**: teste binomial da COMPRA contra a taxa base.
    Abaixo de 0,05, o acerto é considerado acima do acaso;
  - acerto contra o Ibovespa;
  - retorno médio depois de cada tipo de recomendação, comparado à média
    geral (mostra se a IA ganha dinheiro, não só se acerta).
- **Limitações** (exibidas na tela):
  - **amostra pequena:** algumas centenas de casos indicam uma tendência, não
    provam;
  - **conhecimento do modelo:** a IA pode ter sido treinada com dados do
    período avaliado. O prompt só leva números e o nome da empresa, o que
    reduz esse viés, mas não o elimina;
  - **viés de sobrevivência:** as ações avaliadas são grandes e negociadas
    hoje. Empresas que caíram muito ou saíram da bolsa não entram, o que tende
    a favorecer os resultados;
  - **casos não independentes:** datas próximas do mesmo ativo se parecem,
    então a margem tende a ser otimista;
  - **descrição atual da empresa:** vem do Yahoo de hoje, mesmo nas datas
    passadas.

## 11. Banco de dados

| Tabela | Conteúdo |
| ------ | -------- |
| `usuarios` | nome, email (único), hash da senha, data de criação |
| `carteiras` | uma por usuário (`usuario_id` único), nome |
| `itens_b3` | catálogo: código (PK), nome, setor, ativo |
| `itens_carteiras` | posição por carteira e ativo: quantidade, preço médio (único por carteira + ativo) |
| `recomendacoes` | ativo, data de referência (`DATE`), período (`3mo`/`6mo`/`1y`/`2y`; nulo nas antigas), indicadores, recomendação, justificativa, riscos, sobre a empresa, resposta completa (JSON), data de geração; índice em ativo + data + período |
| `operacoes` | operações do backtesting por usuário: entrada, saída, preços e resultado % (líquido de custos) |
| `avaliacoes_ia` | avaliação histórica da IA: ativo, data, período, recomendação, preço, provedor, modelo, resposta; única por ativo + data + período + modelo |

- **Migrações Alembic** (`migracoes/versions/`), aplicadas automaticamente na
  inicialização por `base.migrar()`; o banco é alterado **sem perder dados**:

  | Revisão | O que faz |
  | ------- | --------- |
  | 0001 | schema inicial (o mesmo que o antigo `create_all` gerava) |
  | 0002 | `data_referencia` de texto para `DATE`; falha com mensagem clara se houver valor fora de `AAAA-MM-DD` |
  | 0003 | coluna `sobre_empresa` |
  | 0004 | coluna `periodo` e índice ativo + data + período |
  | 0005 | tabela `avaliacoes_ia` |
- **Bancos antigos** (criados pelo `create_all`, sem `alembic_version`) são
  reconhecidos, marcados na revisão 0001 e atualizados.
- **Uso manual:** `alembic upgrade head`, `alembic current` e
  `alembic history`, na raiz.
- **Carteira:** as últimas recomendações de todos os ativos vêm de **uma única
  consulta** (`row_number()` por ativo).
- **`schema.sql`:** referência do schema final.
- Detalhes em [`specs/persistencia.md`](../specs/persistencia.md).

## 12. Provedores de IA

| Provedor | Variáveis | Observações |
| -------- | --------- | ----------- |
| OpenRouter (padrão) | `OPENROUTER_API_KEY`, `OPENROUTER_MODEL` (padrão `nvidia/nemotron-3.5-super-vl:free`) | Só aceita modelos gratuitos (`:free`); chamada HTTP via `httpx`; JSON via `response_format`, `seed`, `max_tokens` 8192, raciocínio baixo |
| Gemini | `GEMINI_API_KEY`, `GEMINI_MODEL` (padrão `gemini-3.8-flash`) | SDK `google-genai`; JSON via `response_json_schema`, `seed` |
| Claude | `ANTHROPIC_API_KEY`, `CLAUDE_MODEL` (padrão `claude-sonnet-5-5`) | SDK `anthropic`; JSON via `output_config` (sem `seed`) |

Os erros dos provedores são traduzidos para mensagens em português: chave
inválida, permissão, faturamento, modelo inexistente, limite de uso, timeout,
rede, resposta fora do formato e resposta incompleta.

## 13. Configuração, ambiente e ferramentas

- **`.env`** (modelo em `.env.example`): provedor e chaves de IA e conexão
  com o banco (`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`).
- **Parâmetros técnicos** (`src/models/Parametros.py`, sobrescrevíveis em
  `config/settings.py`):
  - períodos dos indicadores: RSI 14; MACD 12/26/9; SMA 20/50;
  - limites do RSI: 30 e 70;
  - período padrão: 1 ano; intervalo padrão: diário;
  - rótulos dos períodos (`ROTULOS_PERIODO`), usados no prompt e nas telas;
  - meses de cada período (`MESES_PERIODO`) e dias de aquecimento
    (`DIAS_AQUECIMENTO` = 150);
  - `SEED_IA` = 42 (também lido do `.env`);
  - `CUSTO_OPERACAO_PCT` = 0,03;
  - `HORIZONTE_AVALIACAO` = 20 pregões e `FAIXA_MANTER_PCT` = 3%.
- **Docker Compose:**
  - `app`: Streamlit na porta 8501, com o código montado em `/app`;
  - `db`: PostgreSQL 16, com volume persistente;
  - `pgadmin`: porta 5051.
- **Scripts:**
  - `Diagnostico.py`: testa banco, Yahoo, indicadores, IA e a análise
    completa, com dicas de correção;
  - `AtualizarCatalogoB3.py`: atualiza o JSON do catálogo;
  - `SeedItensB3.py`: cadastra ativos manualmente;
  - `AvaliarIA.py`: avaliação histórica da IA (seção 10). Exemplos:
    `python -m src.scripts.AvaliarIA` e
    `python -m src.scripts.AvaliarIA --ativos PETR4,VALE3 --limite 20`.

## 14. Testes

`python -m tests.executar_todos` (no container:
`docker compose exec app python -m tests.executar_todos`) roda 16 baterias,
cada uma em um processo separado:

1. regras de negócio e banco;
2. migrações e consultas do banco (inclui o PostgreSQL real, em bancos
   temporários);
3. integração com o yfinance;
4. integração com a API da Claude;
5. integração com a API do Gemini;
6. integração com o OpenRouter;
7. catálogo de ativos;
8. análise de vários ativos;
9. análise considerando o período;
10. resposta da IA em JSON;
11. aquecimento dos indicadores;
12. comparação com o Ibovespa;
13. backtesting (Sharpe, custos e posição aberta);
14. desempenho da IA (acerto, Wilson, teste binomial, script retomável);
15. tema, paleta e formatação;
16. interface Streamlit de ponta a ponta.

As contas estatísticas e financeiras são conferidas contra valores
calculados à mão (ex.: Wilson(6, 10) = 31,3% a 83,2%; Sharpe = 11,57).

As integrações externas são simuladas (`yahoo_simulado.py`, `simulacoes.py`,
`pandas_ta_simulado.py`), então a suíte não depende de internet nem de chaves.

## 15. Evoluções

**Implementadas em 06/11/2026:**
- [`persistencia.md`](../specs/persistencia.md);
- [`analise-periodo.md`](../specs/analise-periodo.md);
- [`analise-ia.md`](../specs/analise-ia.md);
- [`backtesting.md`](../specs/backtesting.md);
- [`historico-aquecimento.md`](../specs/historico-aquecimento.md);
- [`comparacao-ibovespa.md`](../specs/comparacao-ibovespa.md);
- [`desempenho-ia.md`](../specs/desempenho-ia.md).

**Ideias ainda não especificadas:**
- avaliar a IA em vários horizontes (5, 20 e 60 pregões);
- incluir ações que saíram da bolsa, para reduzir o viés de sobrevivência
  (exige dados pagos);
- usar o CDI como taxa livre de risco no Sharpe.

---

## Referências

- Entrada: [`src/public/Main.py`](../../../src/public/Main.py)
- Telas: [`src/public/views/`](../../../src/public/views/)
- Controllers: [`src/controllers/`](../../../src/controllers/)
- Análise: [`AnaliseService.py`](../../../src/models/services/AnaliseService.py),
  [`IndicatorsService.py`](../../../src/models/services/IndicatorsService.py),
  [`ClaudeService.py`](../../../src/models/services/ClaudeService.py),
  [`IaService.py`](../../../src/models/services/IaService.py),
  [`RecomendacoesService.py`](../../../src/models/services/RecomendacoesService.py)
- Dados de mercado: [`YfinanceService.py`](../../../src/models/services/YfinanceService.py)
- Carteira: [`CarteiraService.py`](../../../src/models/services/CarteiraService.py),
  [`ItensCarteiraService.py`](../../../src/models/services/ItensCarteiraService.py)
- Autenticação: [`AuthService.py`](../../../src/models/services/AuthService.py)
- Catálogo: [`ItensB3Service.py`](../../../src/models/services/ItensB3Service.py)
- Backtesting: [`BacktestService.py`](../../../src/models/services/BacktestService.py)
- Desempenho da IA: [`DesempenhoIaService.py`](../../../src/models/services/DesempenhoIaService.py),
  [`AvaliarIA.py`](../../../src/scripts/AvaliarIA.py),
  [`DesempenhoView.py`](../../../src/public/views/DesempenhoView.py)
- Provedores de IA: [`OpenRouterService.py`](../../../src/models/services/OpenRouterService.py),
  [`GeminiService.py`](../../../src/models/services/GeminiService.py)
- Migrações: [`migracoes/versions/`](../../../migracoes/versions/)
- Banco: [`src/models/base.py`](../../../src/models/base.py), [`schema.sql`](../../../schema.sql)
- Testes: [`tests/executar_todos.py`](../../../tests/executar_todos.py)
