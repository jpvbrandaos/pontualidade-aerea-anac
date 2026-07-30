import io
import sys
import time
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

# Acessar config.py
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from config import DATA_PROCESSED, DB_URL

engine = create_engine(DB_URL)

# Ordem importa: as dimensões precisam existir populadas antes da fato,
# porque as chaves estrangeiras da fato apontam para elas.
DIMENSOES = ["dim_calendario", "dim_empresa", "dim_aeroporto"]


def limpar_tabelas() -> None:
    """Esvazia todas as tabelas do modelo.

    Torna a carga reexecutável: rodar o script duas vezes produz o mesmo
    resultado, sem duplicar dados. O CASCADE resolve as dependências de
    chave estrangeira e o RESTART IDENTITY zera o contador do id da fato.
    """
    with engine.begin() as conn:
        conn.execute(text(
            "TRUNCATE fato_voos, dim_empresa, dim_aeroporto, dim_calendario "
            "RESTART IDENTITY CASCADE"
        ))
    print("Tabelas esvaziadas.")


def carregar_dimensao(nome: str) -> int:
    """Carrega uma dimensão do Parquet para o banco via to_sql.

    Para tabelas de poucas milhares de linhas o to_sql resolve em segundos;
    o COPY fica reservado para a fato, onde o volume justifica.
    """
    df = pd.read_parquet(DATA_PROCESSED / f"{nome}.parquet")
    df.to_sql(nome, engine, if_exists="append", index=False)
    print(f"  {nome}: {len(df)} linhas")
    return len(df)


def derrubar_indices_da_fato() -> list[str]:
    """Remove os índices secundários da fato e devolve suas definições.

    Índice ativo durante a carga é atualizado a cada linha inserida —
    com milhões de linhas, isso domina o tempo. O padrão de warehouse é
    carregar sem índices e criá-los ao final, de uma vez. As definições
    vêm do próprio banco (pg_indexes), então o DDL continua sendo a única
    fonte da verdade: índice novo lá é automaticamente respeitado aqui.
    O índice da chave primária fica de fora — remover PK é outra história.
    """
    with engine.begin() as conn:
        indices = conn.execute(text(
            "SELECT indexname, indexdef FROM pg_indexes "
            "WHERE tablename = 'fato_voos' AND indexname NOT LIKE '%_pkey'"
        )).fetchall()
        for nome, _definicao in indices:
            conn.execute(text(f"DROP INDEX {nome}"))

    print(f"  {len(indices)} índices removidos para a carga")
    return [definicao for _nome, definicao in indices]


def recriar_indices(definicoes: list[str]) -> None:
    """Recria os índices removidos antes da carga, medindo o tempo."""
    inicio = time.perf_counter()
    with engine.begin() as conn:
        for definicao in definicoes:
            conn.execute(text(definicao))
    print(f"  {len(definicoes)} índices recriados em {time.perf_counter() - inicio:.1f}s")


def carregar_fato() -> int:
    """Carrega a fato_voos via COPY, o caminho rápido do PostgreSQL.

    O to_sql geraria milhões de INSERTs; o COPY transmite as linhas como um
    fluxo CSV único. Dois detalhes importantes: NULL '' converte campo
    vazio do CSV em NULL no banco (é assim que os pd.NA das flags e os NaT
    dos horários chegam inteiros), e a lista explícita de colunas existe
    porque o id da tabela é gerado pelo banco e não vem no Parquet.
    """
    df = pd.read_parquet(DATA_PROCESSED / "fato_voos.parquet")

    buffer = io.StringIO()
    df.to_csv(buffer, index=False, header=False)
    buffer.seek(0)

    colunas = ", ".join(df.columns)
    inicio = time.perf_counter()

    conn = engine.raw_connection()
    try:
        with conn.cursor() as cur:
            cur.copy_expert(
                f"COPY fato_voos ({colunas}) FROM STDIN WITH (FORMAT csv, NULL '')",
                buffer,
            )
        conn.commit()
    finally:
        conn.close()

    duracao = time.perf_counter() - inicio
    print(f"  fato_voos: {len(df)} linhas em {duracao:.1f}s via COPY")
    return len(df)


def conferir() -> None:
    """Confere se o banco reflete exatamente os arquivos processados.

    Duas camadas: contagem de cada tabela contra o Parquet correspondente
    e checagens de conteúdo com números conhecidos da exploração. A
    contagem de jan/2023 é informativa, não assert: o corte aqui é por
    data_voo, que difere da referência da ANAC nos voos de virada de mês.
    """
    with engine.connect() as conn:
        for tabela in DIMENSOES + ["fato_voos"]:
            no_parquet = len(pd.read_parquet(DATA_PROCESSED / f"{tabela}.parquet"))
            no_banco = conn.execute(text(f"SELECT count(*) FROM {tabela}")).scalar()
            assert no_banco == no_parquet, \
                f"{tabela}: banco tem {no_banco}, parquet tem {no_parquet}"
            print(f"  {tabela}: {no_banco} linhas — bate com o parquet")

        cancelados = conn.execute(text(
            "SELECT count(*) FROM fato_voos WHERE flag_cancelado"
        )).scalar()
        assert cancelados == 76271, \
            f"cancelados no banco: {cancelados}, esperados 76271"
        print(f"  cancelados: {cancelados} — bate com o tratamento")

        jan23 = conn.execute(text(
            "SELECT count(*) FROM fato_voos "
            "WHERE data_voo BETWEEN '2023-01-01' AND '2023-01-31'"
        )).scalar()
        print(f"  jan/2023 por data_voo: {jan23} (referência da exploração: 74168)")

    print("Conferência OK")


def main():
    print("Limpando tabelas:")
    limpar_tabelas()

    print("Carregando dimensões:")
    for dim in DIMENSOES:
        carregar_dimensao(dim)

    print("Carregando fato:")
    definicoes = derrubar_indices_da_fato()
    carregar_fato()
    recriar_indices(definicoes)

    print("Conferindo:")
    conferir()


if __name__ == "__main__":
    main()
