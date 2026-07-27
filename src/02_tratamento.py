import pandas as pd
from pathlib import Path
import sys
import  holidays

# imports do config
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

# Caminho dos dados crus, colunas do df
from config import (DATA_RAW, # Caminhos
                    COLUNAS_VRA, COLUNAS_DATAS, COLUNAS_DESCARTADAS, RENOMEAR_COLUNAS, # Colunas
                    DATA_INICIO, DATA_FIM, NOMES_MESES, NOMES_DIAS_SEMANA, MESES_ALTA_TEMPORADA, DIA_INICIO_ALTA_TEMPORADA_DEZ, #DIM_CALENDARIO
                    RENOMEAR_AERODROMOS, UF_REGIAO, # DIM_AEROPORTO
                    RENOMEAR_EMPRESAS # DIM_EMPRESA

)


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

def padronizar_colunas(df: pd.DataFrame) -> pd.DataFrame:
    """ Descarta colunas vazias e colunas redundantes (descrições) e renomeia as restantes

    Exclui as colunas especificadas na lista global COLUNAS_DESCATADAS).
    Renomeia as colunas restantes espeficificadas na lista global (RENOMEAR_COLUNAS)
    """
    df = df.drop(COLUNAS_DESCARTADAS, axis = 1)
    df = df.rename(columns=RENOMEAR_COLUNAS)
    return df


def converter_datas(df : pd.Dataframe) -> pd.DataFrame:
    """Converte as colunas de texto de data e hora para o tipo datetime.

    Processa as colunas especificadas na lista global COLUNAS_DATAS,
    aplicando a conversão baseada no padrão brasileiro de data e hora.

    
    """
    nulos_antes = df[COLUNAS_DATAS].isna().sum()

    for coluna in COLUNAS_DATAS:
        df[coluna] = pd.to_datetime(df[coluna], format ="%d/%m/%Y %H:%M")

    nulos_depois = df[coluna].isna().sum()
    diferenca = nulos_depois - nulos_antes

    print("\nConversão de datas — nulos antes x depois:")
    print(f"{'coluna':<20}{'antes':>10}{'depois':>10}{'diferença':>12}")

    for coluna in COLUNAS_DATAS:
        print(f"{coluna:<20}{nulos_antes[coluna]:>10}{nulos_depois:>10}{diferenca:>12}")

    if diferenca.sum() != 0:
        raise ValueError(
            f"Conversão de datas gerou nulos novos que exploração não previu: "
            f"{diferenca[diferenca>0].to_dict()}"
        )
    return df

def construir_dim_calendario() -> pd.DataFrame:
    datas = pd.date_range(DATA_INICIO, DATA_FIM, freq="D")

    dim = pd.DataFrame({"data" : datas})

    dim["ano"] = dim["data"].dt.year
    dim['mes'] = dim["data"].dt.month
    dim['nome_mes'] = dim["mes"].map(NOMES_MESES)
    dim["dia"] = dim['data'].dt.day
    dim['dia_semana'] = dim['data'].dt.day_of_week.map(NOMES_DIAS_SEMANA)

    # frags
    dim['frag_fim_de_semana'] = dim['data'].dt.day_of_week >= 5

    feriados_br = holidays.Brazil(years = range(dim["ano"].min(), dim['ano'].max() + 1))
    dim['frag_feriado_nacional'] = dim['data'].dt.date.isin(feriados_br)

    dim['frag_alta_temporada'] = (
        dim['mes'].isin(MESES_ALTA_TEMPORADA)
        | ((dim['mes'] == 12) & dim['dia'] >= DIA_INICIO_ALTA_TEMPORADA_DEZ)
    )

    return dim

def construir_dim_aeroporto():
     dim = pd.read_csv(DATA_RAW / "aerodromos.csv", sep = ";", dtype="str", encoding="utf-8-sig")

     dim = dim[dim["PAÍS AERÓDROMOS"]].copy()
     dim.rename(columns= RENOMEAR_AERODROMOS)
     dim = dim[list[RENOMEAR_AERODROMOS.values()]]

     dim['regiao'] = dim['uf'].map(UF_REGIAO)

     return dim.reset_index(drop=True)


def construir_dim_empresa(df_vra: pd.DataFrame) -> pd.DataFrame:
    """Constroi a dimensão de empresas aéreas.

    Parte do cadastro de operadores do SIROS (70 linhas) e acrescenta as
    siglas que aparecem no VRA sem constar no cadastro, marcadas com nome
    "NÃO CADASTRADA" e flag_no_cadastro falsa. Assim o join com a fato
    nunca descarta voo por falta de correspondência (decisão 7 do
    dicionário de dados).

    Args:
        df_vra: DataFrame do VRA já padronizado, com a coluna sigla_empresa.
    """
    cadastro = pd.read_csv(
        DATA_RAW / "empresas.csv",
        sep=";",
        dtype="str",
        encoding="utf-8-sig",
    )

    cadastro = cadastro.rename(columns=RENOMEAR_EMPRESAS)
    cadastro = cadastro[list(RENOMEAR_EMPRESAS.values())]
    cadastro["flag_no_cadastro"] = True

    siglas_vra = set(df_vra["sigla_empresa"].dropna().unique())
    orfas = sorted(siglas_vra - set(cadastro["sigla_empresa"]))

    dim_orfas = pd.DataFrame(
        {
            "sigla_empresa": orfas,
            "sigla_iata": pd.NA,
            "nome_empresa": "NÃO CADASTRADA",
            "pais_sede": pd.NA,
            "flag_no_cadastro": False,
        }
    )

    dim = pd.concat([cadastro, dim_orfas], ignore_index=True)

    return dim


def filtrar_domestico(df: pd.DataFrame, dim_aeroporto: pd.DataFrame) -> pd.DataFrame:
    """Filtra apenas os voos domésticos nos dados (foco do projeto).

    Voo doméstico é aquele em que origem e destino existem na dim_aeroporto,
    que contém apenas aeródromos com país BRASIL no cadastro da ANAC.
    O critério alternativo, prefixo "SB" na sigla, foi rejeitado na exploração
    por deixar de fora aeródromos brasileiros menores (SD, SI, SJ, SN, SS, SW).
    """

if __name__ == "__main__":
    df = carregar_vra()
    print(f"Formato: {df.shape}")
    print(f"Nulos em Codeshare: {df['Codeshare'].isna().sum()} de {len(df)} linhas")

    # Dimensão Calendário checagem
    dim_cal = construir_dim_calendario()
    assert len(dim_cal) == 1247, f"Esperado 1247 linhas, veio {len(dim_cal)}"

    ano_novo = dim_cal[dim_cal["data"] == "2023-01-01"].iloc[0]
    assert ano_novo["flag_feriado_nacional"], "1º de janeiro deveria ser feriado"
    assert ano_novo["flag_alta_temporada"], "1º de janeiro deveria ser alta temporada"
    print("dim_calendario OK:", len(dim_cal), "linhas")

    # Dimensão Aeroporto checagem
    dim_aero = construir_dim_aeroporto()
    assert len(dim_aero) == 3548, f"Esperado 3548 linhas, veio {len(dim_aero)}"

    ufs_sem_regiao = dim_aero[dim_aero["regiao"].isna()]["uf"].unique()
    assert len(ufs_sem_regiao) == 0, f"UFs fora do mapa: {ufs_sem_regiao}"
    print("dim_aeroporto OK:", len(dim_aero), "linhas")


    # Dimensão Empresa

    df = padronizar_colunas(df)
    dim_emp = construir_dim_empresa(df)
    orfas = (~dim_emp["flag_no_cadastro"]).sum()
    assert len(dim_emp) >= 70, f"Esperado >= 70 linhas, veio {len(dim_emp)}"
    print(f"dim_empresa OK: {len(dim_emp)} linhas ({orfas} órfãs)")
