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
