-- Modelo estrela — pontualidade aérea (docs/modelo_estrela.md)
-- Ordem: dimensões -> fato -> índices

DROP TABLE IF EXISTS fato_voos;
DROP TABLE IF EXISTS dim_empresa;
DROP TABLE IF EXISTS dim_aeroporto;
DROP TABLE IF EXISTS dim_calendario;

CREATE TABLE dim_calendario (
    data                  date PRIMARY KEY,
    ano                   int NOT NULL,
    mes                   int NOT NULL,
    nome_mes              varchar NOT NULL,
    dia                   int NOT NULL,
    dia_semana            varchar NOT NULL,
    flag_fim_de_semana    boolean NOT NULL,
    flag_feriado_nacional boolean NOT NULL,
    flag_alta_temporada   boolean NOT NULL
);

CREATE TABLE dim_empresa (
    sigla_empresa    varchar PRIMARY KEY,
    sigla_iata       varchar,
    nome_empresa     varchar NOT NULL,
    pais_sede        varchar,
    flag_no_cadastro boolean NOT NULL
);

CREATE TABLE dim_aeroporto (
    sigla_icao     varchar PRIMARY KEY,
    sigla_iata     varchar,
    nome_aeroporto varchar,
    municipio      varchar,
    uf             varchar,
    pais           varchar,
    regiao         varchar NOT NULL,
    latitude       varchar,
    longitude      varchar
);

CREATE TABLE fato_voos (
    id                   bigserial PRIMARY KEY,
    data_voo             date NOT NULL REFERENCES dim_calendario(data),
    sigla_empresa        varchar NOT NULL REFERENCES dim_empresa(sigla_empresa),
    icao_origem          varchar NOT NULL REFERENCES dim_aeroporto(sigla_icao),
    icao_destino         varchar NOT NULL REFERENCES dim_aeroporto(sigla_icao),
    numero_voo           varchar NOT NULL,
    codigo_di            varchar,
    codigo_tipo_linha    varchar,
    modelo_equipamento   varchar,
    situacao_voo         varchar NOT NULL,
    partida_prevista     timestamp,
    partida_real         timestamp,
    chegada_prevista     timestamp,
    chegada_real         timestamp,
    atraso_partida_min   double precision,
    atraso_chegada_min   double precision,
    duracao_prevista_min double precision,
    duracao_real_min     double precision,
    flag_pontual_d15     boolean,
    flag_antecipado      boolean,
    flag_cancelado       boolean NOT NULL,
    flag_sem_prevista    boolean NOT NULL
);

CREATE INDEX idx_fato_data     ON fato_voos (data_voo);
CREATE INDEX idx_fato_empresa  ON fato_voos (sigla_empresa);
CREATE INDEX idx_fato_origem   ON fato_voos (icao_origem);
CREATE INDEX idx_fato_destino  ON fato_voos (icao_destino);
