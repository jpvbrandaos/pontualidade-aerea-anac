from pathlib import Path
from datetime import datetime
import calendar

# Caminhos
PROJECT_ROOT = Path(__file__).resolve().parent

DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"

# Data : URL 
# Dicionário de datas e url

# periodo: jan/2023 - maio/2026
PERIODO_INICIO = datetime(2023, 1, 1)
PERIODO_FIM = datetime(2026, 5, 1)

data_atual = PERIODO_INICIO 

URLS_POR_DATA = {}

while data_atual <= PERIODO_FIM:
    ano = data_atual.year
    mes = data_atual.month

    chave_data = f"{ano}-{mes:02d}"
    url_do_mes = f"https://siros.anac.gov.br/siros/registros/diversos/vra/{ano}/VRA_{ano}_{mes:02d}.csv"

    URLS_POR_DATA[chave_data] = url_do_mes

    if data_atual.month == 12:
        data_atual = data_atual.replace(year = data_atual.year + 1, month = 1)
    else:
        data_atual = data_atual.replace(month = data_atual.month + 1)


# URLs dos cadastros de referência (SIROS) — atualizados diariamente pela ANAC
URLS_CADASTROS = {
    "aerodromos": "https://siros.anac.gov.br/siros/registros/aerodromo/aerodromos.csv",
    "empresas": "https://siros.anac.gov.br/siros/registros/cia/cias.csv",
}


# Mapeamento das regiões
UF_REGIAO = {
    "AC": "Norte", "AP": "Norte", "AM": "Norte", "PA": "Norte",
    "RO": "Norte", "RR": "Norte", "TO": "Norte",
    "AL": "Nordeste", "BA": "Nordeste", "CE": "Nordeste", "MA": "Nordeste",
    "PB": "Nordeste", "PE": "Nordeste", "PI": "Nordeste", "RN": "Nordeste",
    "SE": "Nordeste",
    "DF": "Centro-Oeste", "GO": "Centro-Oeste", "MT": "Centro-Oeste",
    "MS": "Centro-Oeste",
    "ES": "Sudeste", "MG": "Sudeste", "RJ": "Sudeste", "SP": "Sudeste",
    "PR": "Sul", "RS": "Sul", "SC": "Sul",
}

# Lista fixa das colunas (Para fixar ordem)
COLUNAS_VRA = [
    "Sigla ICAO Empresa Aérea", "Empresa Aérea", "Número Voo",
    "Código DI", "Código Tipo Linha", "Modelo Equipamento",
    "Número de Assentos", "Sigla ICAO Aeroporto Origem",
    "Descrição Aeroporto Origem", "Partida Prevista", "Partida Real",
    "Sigla ICAO Aeroporto Destino", "Descrição Aeroporto Destino",
    "Chegada Prevista", "Chegada Real", "Situação Voo", "Justificativa",
    "Referência", "Situação Partida", "Situação Chegada", "Codeshare",
]

COLUNAS_DATAS = ["partida_prevista", "partida_real", "chegada_prevista", "chegada_real"]

RENOMEAR_COLUNAS = {
    "Sigla ICAO Empresa Aérea": "sigla_empresa",
    "Número Voo": "numero_voo",
    "Código DI": "codigo_di",
    "Código Tipo Linha": "codigo_tipo_linha",
    "Modelo Equipamento": "modelo_equipamento",
    "Número de Assentos": "numero_assentos",
    "Sigla ICAO Aeroporto Origem": "icao_origem",
    "Sigla ICAO Aeroporto Destino": "icao_destino",
    "Partida Prevista": "partida_prevista",
    "Partida Real": "partida_real",
    "Chegada Prevista": "chegada_prevista",
    "Chegada Real": "chegada_real",
    "Situação Voo": "situacao_voo",
    "Situação Partida": "situacao_partida",
    "Situação Chegada": "situacao_chegada",
    "Referência": "referencia",
    "Codeshare": "codeshare",
}

RENOMEAR_EMPRESAS = {
    "ICAO OPERADOR AÉREO": "sigla_empresa",
    "IATA OPERADOR AÉREO": "sigla_iata",
    "NOME OPERADOR AÉREO": "nome_empresa",
    "PAÍS SEDE": "pais_sede",
}

COLUNAS_DESCARTADAS = [
    "Justificativa",
    "Empresa Aérea",
    "Descrição Aeroporto Origem",
    "Descrição Aeroporto Destino",
]


# Dim calendário
# Período do projeto
_ultimo_dia = calendar.monthrange(PERIODO_FIM.year, PERIODO_FIM.month)[1]

DATA_INICIO = PERIODO_INICIO.strftime("%Y-%m-%d")
DATA_FIM = PERIODO_FIM.replace(day=_ultimo_dia).strftime("%Y-%m-%d")

data_atual = PERIODO_INICIO   # cursor consumido pelo loop

# Alta temporada: janeiro, julho e 15 a 31 de dezembro
MESES_ALTA_TEMPORADA = [1, 7]
DIA_INICIO_ALTA_TEMPORADA_DEZ = 15

NOMES_MESES = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}

NOMES_DIAS_SEMANA = {
    0: "Segunda-feira", 1: "Terça-feira", 2: "Quarta-feira",
    3: "Quinta-feira", 4: "Sexta-feira", 5: "Sábado", 6: "Domingo",
}


# Fato — colunas na ordem do modelo (docs/modelo_estrela.dbml)
COLUNAS_FATO = [
    "data_voo", "sigla_empresa", "icao_origem", "icao_destino",
    "numero_voo", "codigo_di", "codigo_tipo_linha", "modelo_equipamento",
    "situacao_voo",
    "partida_prevista", "partida_real", "chegada_prevista", "chegada_real",
    "atraso_partida_min", "atraso_chegada_min",
    "duracao_prevista_min", "duracao_real_min",
    "flag_pontual_d15", "flag_antecipado", "flag_cancelado", "flag_sem_prevista",
]


# Dim aeroporto

RENOMEAR_AERODROMOS = {
    "SIGLA ICAO AERÓDROMO": "sigla_icao",
    "SIGLA IATA AERÓDROMO": "sigla_iata",
    "NOME AERÓDROMO": "nome_aeroporto",
    "MUNICÍPIO AERÓDROMO": "municipio",
    "ESTADO AERÓDROMO": "uf",
    "PAÍS AERÓDROMO": "pais",
    "LATITUDE": "latitude",
    "LONGITUDE": "longitude",
}
