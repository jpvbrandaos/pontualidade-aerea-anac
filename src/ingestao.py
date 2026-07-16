import sys
import requests
import pandas as pd
from requests.exceptions import HTTPError, ConnectionError, Timeout, RequestException
from pathlib import Path



# Acessar config.py
ROOT_DIR = Path(__file__).resolve().parent.parent
if ROOT_DIR not in sys.path:
    sys.path.append(str(ROOT_DIR))

from config import PROJECT_ROOT, DATA_RAW, DATA_PROCESSED, URLS_POR_DATA



# Função para avaliação dos csv
def avaliar_csv(caminho_arquivo: Path):
    try:
        df_amostra = pd.read_csv(caminho_arquivo, sep= ";", nrows = 5)

        print("\n" + "=" * 40)
        print(f"Avaliação do arquivo: {caminho_arquivo}")
        print(df_amostra.shape)
        print(f"Colunas do csv: {df_amostra.columns.tolist()}")
        print("\n" + "=" * 40)
        print(df_amostra)
        print("\n" + "=" * 40)
    
    except Exception as e:
        print(f"Erro ao ler e avaliar o arquivo csv: {caminho_arquivo}")



def main():
    # Garantir pasta
    DATA_RAW.mkdir(parents = True, exist_ok = True)
    for data, fonte_url  in URLS_POR_DATA.items():
        try:
            caminho_atual = DATA_RAW/f"{data}.csv"

            if caminho_atual.exists() and caminho_atual.stat().st_size > 0:
                continue

            with requests.get(url = fonte_url, stream = True, timeout= 30) as resp:
                # Erros de servidor
                resp.raise_for_status()

                # Verificar se é CSV | Camada 1 de verificação
                if "html" in resp.headers.get("Content-Type", ""):
                    raise ValueError("Erro! arquivo é um HTML e espera-se um csv")

                # Salvar arquivo no destino com streaming:

                with open(caminho_atual, "wb") as f:
                    for chunk in resp.iter_content(chunk_size =8192):
                        if chunk:
                            f.write(chunk)

            # Verificar tamanho do arquivo | Camada 2 de verificação
            if (caminho_atual).stat().st_size == 0:
                raise ValueError("Erro! Arquivo vazio")

            print(f"Download de {data} Concluído com sucesso!")

            # Chamar a função de avaliação:
            avaliar_csv(caminho_atual)

        except HTTPError as e:
            print(f"Erro no servidor ({data}): {e}")
            caminho_atual.unlink(missing_ok=True)
            continue

        except ConnectionError:
            print(f"Erro de conexão ({data})")
            caminho_atual.unlink(missing_ok=True)
            continue

        except Timeout:
            print(f"Conexão ultrapassou o tempo de resposta ({data})")
            caminho_atual.unlink(missing_ok=True)
            continue

        except RequestException as e:
            print(f"Erro inesperado na requisição ({data}): {e}")
            caminho_atual.unlink(missing_ok=True)
            continue

        except ValueError as e:
            print(f"Erro de validação ({data}): {e}")
            caminho_atual.unlink(missing_ok=True)
            continue


if __name__ == "__main__":
    main()
