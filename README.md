# Pontualidade Aérea no Brasil — Pipeline de Dados ANAC

Pipeline de dados usando os registros públicos de voos da ANAC (Agência Nacional de Aviação Civil). O projeto baixa os arquivos mensais de voos direto do portal de dados abertos, trata e padroniza os dados em Python, modela um esquema estrela em PostgreSQL rodando no Docker, responde perguntas de negócio com SQL e apresenta os resultados em um dashboard de pontualidade no Power BI.

```
Ingestão (portal ANAC) → Tratamento (pandas) → Modelo estrela (PostgreSQL/Docker) → SQL → Power BI
```

## Fonte de dados

Dados abertos da ANAC — a base Voo Regular Ativo (VRA), publicada mensalmente com os voos das empresas de transporte aéreo regular: companhia, origem, destino, horários previstos e realizados de partida e chegada e situação do voo. A base registra atrasos, antecipações e cancelamentos, e é formada pela integração de dois conjuntos da própria ANAC: os voos planejados (Registro de Serviços Aéreos) e os realizados (Dados Estatísticos do Transporte Aéreo).

Links oficiais:

- [Base VRA — dados abertos da ANAC](https://www.gov.br/anac/pt-br/acesso-a-informacao/dados-abertos/areas-de-atuacao/voos-e-operacoes-aereas/voo-regular-ativo-vra)
- [VRA no Portal Brasileiro de Dados Abertos](https://dados.gov.br/dados/conjuntos-dados/dadosabertos-areas-de-atuacao-voos-e-operacoes-aereas-voo-regular-ativo-vra)
- [Consulta Interativa de Pontualidade e Regularidade](https://www.gov.br/anac/pt-br/assuntos/dados-e-estatisticas/passageiros/consulta-interativa-pontualidade-e-regularidade) — usada para validar os indicadores calculados

Além dos voos, o projeto usa os cadastros públicos da própria ANAC como tabelas de referência: aeródromos (com município e UF) e empresas aéreas. Período analisado: [preencher — ex.: jan/2023 a dez/2025].

Diferente de um dataset pronto do Kaggle, aqui os dados vêm "achatados" em arquivos mensais, com encoding e layout que variam ao longo dos anos. A modelagem dimensional (fato + dimensões) é construída no próprio projeto.

O dicionário de dados, com a descrição das tabelas e os problemas de qualidade encontrados, está em `docs/dicionario_dados.md`. O diagrama do modelo estrela está em `docs/modelo_estrela.png`.

## Perguntas de negócio

As queries em `sql/analises/` respondem, entre outras:

1. Qual o percentual de voos pontuais (atraso de até 15 minutos) por companhia, e como ele evolui mês a mês?
2. Quais aeroportos concentram os maiores atrasos médios, na partida e na chegada?
3. O atraso se acumula ao longo do dia? Voos do fim da tarde atrasam mais que os da manhã?
4. Quais são as rotas mais movimentadas do país e como está a concorrência em cada uma?
5. Qual a taxa de cancelamento por companhia e por período, e onde ela dispara?
6. As companhias conseguem recuperar no ar o atraso da decolagem?
7. Existe sazonalidade nos atrasos (férias, fim de ano, dia da semana, hora do dia)?
8. Quanto tempo de "gordura" as companhias embutem na duração prevista de cada rota?

Cada arquivo `.sql` tem um comentário no topo com a pergunta, a lógica usada e o insight encontrado.

## Estrutura

```
├── data/
│   ├── raw/               # arquivos mensais da ANAC, não versionados
│   └── processed/         # dados tratados, prontos para carga
├── src/
│   ├── 01_ingestao.py     # download dos arquivos do portal da ANAC
│   ├── 02_tratamento.py   # limpeza, padronização e validações
│   └── 03_carga.py        # carga do modelo estrela no PostgreSQL
├── sql/
│   ├── ddl/               # criação da tabela fato, dimensões e índices
│   ├── analises/          # queries das perguntas de negócio
│   └── views/             # views usadas pelo Power BI
├── powerbi/
│   └── dashboard.pbix
├── docs/
│   ├── dicionario_dados.md
│   ├── modelo_estrela.png
│   └── prints/
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

Algumas escolhas do projeto:

- Os arquivos em `data/raw/` nunca são editados. Todo tratamento gera novos arquivos em `data/processed/`, então dá para refazer qualquer etapa do zero.
- O banco segue um modelo estrela: `fato_voos` no centro, com dimensões de empresa, aeroporto e calendário. Métricas de atraso são calculadas uma única vez, na construção da fato.
- Adotei o padrão amplamente usado no setor para pontualidade: voo pontual é o que parte/chega com até 15 minutos de atraso (indicador D15).
- Os indicadores calculados são conferidos contra a Consulta Interativa de Pontualidade e Regularidade da ANAC, construída a partir da mesma base. Se os números divergem, o erro está no pipeline — a validação contra a fonte oficial faz parte do projeto.
- O Power BI se conecta às views de `sql/views/`, não às tabelas diretamente. Assim a lógica das métricas fica versionada no repositório.
- Credenciais ficam em variáveis de ambiente (`.env`, fora do versionamento). O `.env.example` mostra o que precisa ser preenchido.

## Escopo e limitações

- A base VRA cobre apenas o transporte aéreo regular. Aviação executiva, geral e voos não regulares ficam fora da análise.
- A análise se restringe a voos domésticos. Voos internacionais foram excluídos porque os aeroportos estrangeiros não constam no cadastro de aeródromos usado nas dimensões (decisão documentada no dicionário de dados).
- Os horários realizados dependem do reporte das próprias empresas aéreas à ANAC; a qualidade do dado reflete a qualidade desse reporte.
- Antecipações (voos que partem antes do previsto) são mantidas na base e tratadas como categoria própria, não como "atraso negativo" descartado.
- O tratamento de fuso horário adotado está documentado no dicionário de dados — análises por hora do dia dependem diretamente dessa decisão.

## Como executar

Pré-requisitos: Python 3.11+, Docker com Compose e, para abrir o dashboard, Power BI Desktop.

```bash
git clone https://github.com/SEU_USUARIO/pontualidade-aerea-anac.git
cd pontualidade-aerea-anac

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # preencher com as credenciais locais

docker compose up -d

python src/01_ingestao.py
python src/02_tratamento.py
python src/03_carga.py
```

O dashboard está em `powerbi/dashboard.pbix`. Quem não tiver o Power BI instalado pode ver as capturas de tela em `docs/prints/`.

## Resultados

Em construção. Ao final, esta seção vai trazer os principais insights com números e os prints do dashboard.

## Stack

- Python (pandas, requests, SQLAlchemy)
- PostgreSQL 16 (Docker Compose)
- SQL: modelo estrela, CTEs, window functions e views
- Power BI

## Convenções de Git

Branches:

- `main` — versão estável
- `develop` — integração do que está em andamento
- `feature/<nome>`, `fix/<nome>`, `docs/<nome>` — ex.: `feature/dim-aeroportos`, `fix/encoding-vra`

Commits seguem o padrão [Conventional Commits](https://www.conventionalcommits.org/pt-br/), no formato `tipo(escopo): descrição no imperativo`:

```
feat(ingestao): adiciona download dos arquivos mensais da ANAC
fix(tratamento): corrige parse de horários com fuso
docs: adiciona dicionário de dados
refactor(carga): extrai conexão para função própria
chore: atualiza .gitignore
test(tratamento): valida chaves da dimensão aeroporto
```

Dados, `.env` e arquivos gerados não entram no repositório (ver `.gitignore`).

## Licença

Código sob MIT. Os dados da ANAC são públicos, disponibilizados no portal de dados abertos do governo federal.

## Autor

João Pedro — [LinkedIn](#) · [GitHub](#)
