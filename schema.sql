CREATE TABLE usuarios (
    id          SERIAL PRIMARY KEY,
    nome        VARCHAR(100) NOT NULL,
    email       VARCHAR(150) NOT NULL UNIQUE,
    senha_hash  VARCHAR(255) NOT NULL,
    criado_em   TIMESTAMP DEFAULT NOW()
);

CREATE TABLE carteiras (
    id          SERIAL PRIMARY KEY,
    usuario_id  INTEGER NOT NULL UNIQUE REFERENCES usuarios(id),
    nome        VARCHAR(100) NOT NULL DEFAULT 'Minha carteira',
    criado_em   TIMESTAMP DEFAULT NOW()
);

CREATE TABLE itens_b3 (
    item    VARCHAR(10) PRIMARY KEY,
    nome    VARCHAR(150) NOT NULL,
    setor   VARCHAR(100) DEFAULT 'Não disponível',
    ativo   BOOLEAN DEFAULT TRUE
);

CREATE TABLE itens_carteiras (
    id             SERIAL PRIMARY KEY,
    carteira_id    INTEGER NOT NULL REFERENCES carteiras(id),
    item           VARCHAR(20) NOT NULL REFERENCES itens_b3(item),
    quantidade     NUMERIC(14,4) NOT NULL DEFAULT 0,
    preco_medio    NUMERIC(10,2) NOT NULL DEFAULT 0,
    atualizado_em  TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uq_carteira_item UNIQUE (carteira_id, item)
);

CREATE TABLE operacoes (
    id             SERIAL PRIMARY KEY,
    usuario_id     INTEGER REFERENCES usuarios(id),
    item           VARCHAR(20) NOT NULL,
    data_entrada   DATE,
    preco_entrada  NUMERIC(10,2),
    data_saida     DATE,
    preco_saida    NUMERIC(10,2),
    resultado_pct  NUMERIC(6,2)
);

CREATE TABLE recomendacoes (
    id                 SERIAL PRIMARY KEY,
    item               VARCHAR(20) NOT NULL REFERENCES itens_b3(item),
    data_referencia    VARCHAR(10) NOT NULL,
    preco_atual        NUMERIC(10,2),
    rsi                NUMERIC(6,2),
    sinal_rsi          VARCHAR(20),
    macd               NUMERIC(10,4),
    macd_signal        NUMERIC(10,4),
    macd_cruzamento    VARCHAR(10),
    sma20              NUMERIC(10,2),
    sma50              NUMERIC(10,2),
    tendencia_sma      VARCHAR(10),
    recomendacao       VARCHAR(10) NOT NULL,
    justificativa      TEXT,
    riscos             TEXT,
    resposta_completa  TEXT,
    gerado_em          TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ix_recomendacoes_item_data ON recomendacoes (item, data_referencia);
