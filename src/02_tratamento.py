import pandas as pd
from pathlib import Path
import sys

# Dados do config
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

# Caminho dos dados crus, colunas do df
from config import DATA_RAW, COLUNAS_VRA, COLUNAS_DATAS


def carregar_vra() -> pd.DataFrame:
    """Carrega, filtra e concatena os arquivos mensais da base VRA.

    Varre o diretório de dados brutos procurando por arquivos CSV que comecem
    com números (indicando o padrão de ano/mês), padroniza as colunas de cada
    mês de acordo com o layout esperado e une todos em um único DataFrame.

    Returns:
        pd.DataFrame: Tabela unificada contendo o histórico de todos os meses 
        carregados, com as colunas definidas em COLUNAS_VRA e tipo string.
    """
    arquivos_mensais = sorted(
        a for a in DATA_RAW.glob("*.csv") if a.stem[0].isdigit()
    )

    lista_dfs = []
    for arquivo in arquivos_mensais:
        df_mes = pd.read_csv(arquivo, sep = ";", dtype= "str")

        faltantes = set(COLUNAS_VRA) - set(df_mes.columns) - {"Codeshare"}
        if faltantes:
            raise ValueError(f"{arquivo.name}: colunas ausentes {faltantes}")
        
        df_mes = df_mes.reindex(columns = COLUNAS_VRA)
        lista_dfs.append(df_mes)

    df_vra = pd.concat(lista_dfs, ignore_index=True)

    return df_vra

def converter_datas(df: pd.Dataframe) -> pd.DataFrame:
    """Converte as colunas de texto de data e hora para o tipo datetime.

    Processa as colunas especificadas na lista global COLUNAS_DATAS,
    aplicando a conversão baseada no padrão brasileiro de data e hora.
    """
    for coluna in COLUNAS_DATAS:
        df[coluna] = pd.to_datetime(df[coluna], format ="%d/%m/%Y %H:%M")

    return df



if __name__ == "__main__":
    df = carregar_vra()
    print(f"Formato: {df.shape}")
    print(f"Nulos em Codeshare: {df['Codeshare'].isna().sum()} de {len(df)} linhas")
