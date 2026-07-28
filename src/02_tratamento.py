import pandas as pd
from pathlib import Path
import sys
import holidays

# imports do config
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

# Caminho dos dados crus, colunas do df
from config import (DATA_RAW, # Caminhos
                    COLUNAS_VRA, COLUNAS_DATAS, COLUNAS_DESCARTADAS, RENOMEAR_COLUNAS, COLUNAS_FATO, # Colunas
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


def converter_datas(df : pd.DataFrame) -> pd.DataFrame:
    """Converte as colunas de texto de data e hora para o tipo datetime.

    Processa as colunas especificadas na lista global COLUNAS_DATAS,
    aplicando a conversão baseada no padrão brasileiro de data e hora.

    A coluna referencia tem dois formatos na série, acompanhando a troca
    de layout da ANAC: ISO (2023-01-01) nos 10 meses sem Codeshare e
    brasileiro (01/07/2024 00:00:00) nos 31 meses com a coluna. A conversão
    tenta os dois e falha se sobrar algo em outro formato.
    """
    nulos_antes = df[COLUNAS_DATAS].isna().sum()

    for coluna in COLUNAS_DATAS:
        df[coluna] = pd.to_datetime(df[coluna], format ="%d/%m/%Y %H:%M")

    ref_iso = pd.to_datetime(df["referencia"], format="%Y-%m-%d", errors="coerce")
    ref_br = pd.to_datetime(df["referencia"], format="%d/%m/%Y %H:%M:%S", errors="coerce")
    referencia = ref_iso.fillna(ref_br)
    if referencia.isna().any():
        exemplos = df.loc[referencia.isna(), "referencia"].dropna().unique()[:5]
        raise ValueError(f"referencia com formato não previsto: {exemplos}")
    df["referencia"] = referencia

    nulos_depois = df[COLUNAS_DATAS].isna().sum()
    diferenca = nulos_depois - nulos_antes

    print("\nConversão de datas — nulos antes x depois:")
    print(f"{'coluna':<20}{'antes':>10}{'depois':>10}{'diferença':>12}")

    for coluna in COLUNAS_DATAS:
        print(f"{coluna:<20}{nulos_antes[coluna]:>10}{nulos_depois[coluna]:>10}{diferenca[coluna]:>12}")

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

    # flags
    dim['flag_fim_de_semana'] = dim['data'].dt.day_of_week >= 5

    feriados_br = holidays.Brazil(years = range(dim["ano"].min(), dim['ano'].max() + 1))
    dim['flag_feriado_nacional'] = dim['data'].dt.date.isin(feriados_br)

    dim['flag_alta_temporada'] = (
        dim['mes'].isin(MESES_ALTA_TEMPORADA)
        | ((dim['mes'] == 12) & (dim['dia'] >= DIA_INICIO_ALTA_TEMPORADA_DEZ))
    )

    return dim

def construir_dim_aeroporto() -> pd.DataFrame:
    """Constroi a dimensão de aeroportos a partir do cadastro do SIROS.

    Mantém apenas aeródromos com país BRASIL (escopo doméstico do projeto,
    decisão 6 do dicionário) e deriva a região a partir da UF.
    """
    dim = pd.read_csv(DATA_RAW / "aerodromos.csv", sep = ";", dtype="str", encoding="utf-8-sig")

    dim = dim[dim["PAÍS AERÓDROMO"] == "BRASIL"].copy()
    dim = dim.rename(columns=RENOMEAR_AERODROMOS)
    dim = dim[list(RENOMEAR_AERODROMOS.values())]

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
    if dim_aeroporto.empty:
        raise ValueError("dim_aeroporto vazia: o filtro descartaria todos os voos")

    icao_brasil = set(dim_aeroporto["sigla_icao"])
    mask = df["icao_origem"].isin(icao_brasil) & df["icao_destino"].isin(icao_brasil)

    mantidas = int(mask.sum())
    excluidas = len(df) - mantidas
    print(f"\nEscopo doméstico: {mantidas} mantidas, {excluidas} excluídas ({excluidas / len(df):.1%})")

    return df[mask].copy()


def construir_fato(df: pd.DataFrame) -> pd.DataFrame:
    """Constroi a fato_voos: data-âncora, métricas em minutos e flags.

    Regras em docs/modelo_estrela.md. Espera o VRA padronizado, com datas
    convertidas e já filtrado para o escopo doméstico.
    """
    fato = df.copy()

    # Data-âncora: dia da partida prevista. Voos sem prevista, ou com prevista
    # fora do período do calendário (voos na virada do último mês), usam a
    # data de referência da ANAC (já convertida em converter_datas).
    referencia = fato["referencia"].dt.normalize()
    data_voo = fato["partida_prevista"].dt.normalize()
    fora_do_calendario = (
        data_voo.isna()
        | (data_voo < pd.Timestamp(DATA_INICIO))
        | (data_voo > pd.Timestamp(DATA_FIM))
    )
    fato["data_voo"] = data_voo.mask(fora_do_calendario, referencia)

    # Métricas — calculadas uma única vez, aqui (decisão do modelo estrela)
    fato["atraso_partida_min"] = (fato["partida_real"] - fato["partida_prevista"]).dt.total_seconds() / 60
    fato["atraso_chegada_min"] = (fato["chegada_real"] - fato["chegada_prevista"]).dt.total_seconds() / 60
    fato["duracao_prevista_min"] = (fato["chegada_prevista"] - fato["partida_prevista"]).dt.total_seconds() / 60
    fato["duracao_real_min"] = (fato["chegada_real"] - fato["partida_real"]).dt.total_seconds() / 60

    # Flags — dtype boolean (nullable), nunca bool puro
    fato["flag_cancelado"] = (fato["situacao_voo"] == "CANCELADO").astype("boolean")
    fato["flag_sem_prevista"] = fato["partida_prevista"].isna().astype("boolean")
    fato["flag_antecipado"] = (fato["atraso_partida_min"] < 0).astype("boolean")
    fato["flag_pontual_d15"] = (fato["atraso_partida_min"] <= 15).astype("boolean")

    # Sem atraso calculável (cancelado, não informado ou sem prevista),
    # pontualidade e antecipação são nulas — False diria "atrasou"
    sem_atraso = fato["atraso_partida_min"].isna()
    fato.loc[sem_atraso, ["flag_pontual_d15", "flag_antecipado"]] = pd.NA

    return fato[COLUNAS_FATO]


def validar(fato: pd.DataFrame, df_domestico: pd.DataFrame,
            dim_empresa: pd.DataFrame, dim_aeroporto: pd.DataFrame,
            dim_calendario: pd.DataFrame) -> None:
    """Valida a fato antes da escrita. Qualquer falha derruba o pipeline.

    Cobre integridade referencial com as dimensões, coerência das flags e
    os números de janeiro de 2023 conhecidos da exploração.
    """
    # Integridade referencial: toda chave da fato existe na dimensão
    assert fato["sigla_empresa"].isin(dim_empresa["sigla_empresa"]).all(), \
        "empresa órfã na fato"
    assert fato["icao_origem"].isin(dim_aeroporto["sigla_icao"]).all(), \
        "aeroporto de origem órfão na fato"
    assert fato["icao_destino"].isin(dim_aeroporto["sigla_icao"]).all(), \
        "aeroporto de destino órfão na fato"
    assert fato["data_voo"].isin(dim_calendario["data"]).all(), \
        "data_voo fora da dim_calendario"

    # Coerência das flags e métricas
    cancelados = fato["flag_cancelado"].fillna(False)
    assert fato.loc[cancelados, "atraso_partida_min"].isna().all(), \
        "voo cancelado com atraso de partida calculado"
    assert fato.loc[cancelados, "atraso_chegada_min"].isna().all(), \
        "voo cancelado com atraso de chegada calculado"
    assert (fato["flag_pontual_d15"].isna() == fato["atraso_partida_min"].isna()).all(), \
        "flag_pontual_d15 deve ser nula exatamente onde não há atraso calculável"
    assert (fato["flag_antecipado"].isna() == fato["atraso_partida_min"].isna()).all(), \
        "flag_antecipado deve ser nula exatamente onde não há atraso calculável"

    # Teste de ouro: números de jan/2023 conhecidos da exploração
    jan23 = df_domestico[df_domestico["referencia"].dt.strftime("%Y-%m") == "2023-01"]
    assert len(jan23) == 74168, \
        f"jan/2023: esperadas 74168 linhas domésticas, vieram {len(jan23)}"
    cancelados_jan = (jan23["situacao_voo"] == "CANCELADO").sum()
    assert cancelados_jan == 2485, \
        f"jan/2023: esperados 2485 cancelados domésticos, vieram {cancelados_jan}"

    # Duplicata de linha inteira: não deve existir, mas se existir é aviso
    # (o dicionário registra 1 par real por mês na chave de negócio)
    duplicadas = int(fato.duplicated().sum())
    if duplicadas:
        print(f"Aviso: {duplicadas} linhas totalmente duplicadas na fato — investigar")

    print("Validações OK")


def main():
    df = carregar_vra()
    print(f"Linhas lidas do VRA: {len(df)}")

    df = padronizar_colunas(df)
    df = converter_datas(df)

    # Dimensão calendário
    dim_cal = construir_dim_calendario()
    assert len(dim_cal) == 1247, f"Esperado 1247 linhas, veio {len(dim_cal)}"

    ano_novo = dim_cal[dim_cal["data"] == "2023-01-01"].iloc[0]
    assert ano_novo["flag_feriado_nacional"], "1º de janeiro deveria ser feriado"
    assert ano_novo["flag_alta_temporada"], "1º de janeiro deveria ser alta temporada"
    print("dim_calendario OK:", len(dim_cal), "linhas")

    # Dimensão aeroporto
    dim_aero = construir_dim_aeroporto()
    assert len(dim_aero) == 3548, f"Esperado 3548 linhas, veio {len(dim_aero)}"

    ufs_sem_regiao = dim_aero[dim_aero["regiao"].isna()]["uf"].unique()
    assert len(ufs_sem_regiao) == 0, f"UFs fora do mapa: {ufs_sem_regiao}"
    print("dim_aeroporto OK:", len(dim_aero), "linhas")

    # Dimensão empresa
    dim_emp = construir_dim_empresa(df)
    orfas = (~dim_emp["flag_no_cadastro"]).sum()
    assert len(dim_emp) >= 70, f"Esperado >= 70 linhas, veio {len(dim_emp)}"
    print(f"dim_empresa OK: {len(dim_emp)} linhas ({orfas} órfãs)")

    # Escopo doméstico e fato
    df_dom = filtrar_domestico(df, dim_aero)
    fato = construir_fato(df_dom)

    validar(fato, df_dom, dim_emp, dim_aero, dim_cal)

    # Resumo
    print(f"\nfato_voos: {len(fato)} linhas x {len(fato.columns)} colunas")
    for flag in ["flag_pontual_d15", "flag_antecipado", "flag_cancelado", "flag_sem_prevista"]:
        verdadeiras = int((fato[flag] == True).sum())
        nulas = int(fato[flag].isna().sum())
        print(f"  {flag}: {verdadeiras} verdadeiras, {nulas} nulas")


if __name__ == "__main__":
    main()
