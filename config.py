from pathlib import Path
from datetime import datetime

# Caminhos
PROJECT_ROOT = Path(__file__).resolve().parent

DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"

# Data : URL 
# Dicionário de datas e url
# periodo: jan/2023 - maio/2026

data_atual = datetime(2023, 1, 1)
data_final = datetime(2026, 5, 1)

URLS_POR_DATA = {}

while data_atual <= data_final:
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
