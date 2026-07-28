# Dicionário de dados — Pontualidade Aérea (VRA/ANAC)

Este documento descreve os dados brutos do projeto e registra as decisões de tratamento tiradas da exploração feita em `notebooks/01_exploracao.ipynb`. Ele é o contrato da fase de tratamento: toda regra aplicada aos dados deve ter justificativa aqui, e todo número citado aqui sai do notebook ou do resumo impresso pela ingestão (`src/ingestao.py`). O mês de referência da exploração é janeiro de 2023; quando um número vem de outro mês, o texto diz qual.

## Fonte

Os microdados de Voo Regular Ativo (VRA) são publicados mensalmente pela ANAC em `https://siros.anac.gov.br/siros/registros/diversos/vra/{ano}/VRA_{ano}_{mês}.csv`. O projeto cobre janeiro de 2023 a maio de 2026: 41 arquivos mensais em `data/raw/`, com nome `AAAA-MM.csv`, somando cerca de 980 MB segundo o resumo da ingestão. Nos três meses abertos no notebook (2023-01, 2024-07 e 2026-05), o volume ficou entre 82 e 88 mil linhas por mês. Cada linha é uma etapa de voo: um trecho origem–destino operado por uma empresa.

Dois cadastros de apoio vêm do mesmo sistema SIROS e são atualizados diariamente pela ANAC: `aerodromos.csv`, com 10.560 aeródromos do mundo inteiro (3.548 brasileiros), e `empresas.csv`, com 70 operadores aéreos. Os arquivos em `data/raw/` são uma fotografia de julho de 2026 e o pipeline não os reatualiza.

Formato: UTF-8, separador ponto e vírgula, datas como texto no padrão `DD/MM/AAAA HH:MM`. Se os acentos aparecerem corrompidos (`CÃ³digo` no lugar de `Código`), o problema está no programa que abriu o arquivo assumindo outra codificação — tipicamente o Excel — e não no dado.

## Colunas dos arquivos mensais

Percentuais de nulos medidos em janeiro de 2023, exceto onde indicado.

| Coluna | Tipo | Descrição | Nulos | Observações |
|---|---|---|---|---|
| Sigla ICAO Empresa Aérea | texto | Designador ICAO da empresa que opera o voo | 0% | Chave para o cadastro de empresas; 19 siglas do mês não existem lá (decisão 7) |
| Empresa Aérea | texto | Nome da empresa | 0% | Redundante com a sigla |
| Número Voo | texto | Numeração do voo | 0% | Tem zeros à esquerda (`0904`); nunca converter para número |
| Código DI | texto | Dígito Identificador da etapa | 0% | `0` é o voo regular (83.076 linhas, 94,8% do mês); `1` a `9`, `D` e `E` marcam alterações e voos extras — significados a confirmar na documentação da ANAC |
| Código Tipo Linha | texto | Tipo de linha da etapa | 0% | Valores no mês: `N` (72.088), `I` (10.979), `G`, `C`, `X`; `N` é doméstica e `I` internacional, os demais a confirmar |
| Modelo Equipamento | texto | Modelo da aeronave no padrão ICAO | 0% | 50 modelos distintos no mês |
| Número de Assentos | inteiro | Assentos da aeronave | 0% | 5.214 registros com zero assentos (5,9% do mês), a maioria voos realizados; não usar em métrica de oferta sem filtro (célula 2.6) |
| Sigla ICAO Aeroporto Origem | texto | Designador ICAO da origem | 0% | Chave para o cadastro de aeródromos; cobertura de 100% |
| Descrição Aeroporto Origem | texto | Nome, cidade, estado e país da origem | 0% | Redundante com o cadastro |
| Partida Prevista | data/hora | Partida prevista informada pela empresa | 4,3% | Nula em voos extras, que não têm horário publicado (decisão 4) |
| Partida Real | data/hora | Partida realizada | 5,1% | Nula em cancelados e não informados (decisão 3) |
| Sigla ICAO Aeroporto Destino | texto | Designador ICAO do destino | 0% | Mesma chave da origem |
| Descrição Aeroporto Destino | texto | Nome, cidade, estado e país do destino | 0% | Redundante com o cadastro |
| Chegada Prevista | data/hora | Chegada prevista | 4,3% | Acompanha Partida Prevista |
| Chegada Real | data/hora | Chegada realizada | 5,1% | Acompanha Partida Real |
| Situação Voo | texto | REALIZADO, CANCELADO ou NÃO INFORMADO | 0% | 83.210 realizados no mês (94,9%), 4.386 cancelados, 51 não informados |
| Justificativa | — | Código de justificativa da alteração | 100% | Vazia nos três meses examinados; a exigência caiu em abril de 2020 com a revogação da IAC 1504, o que indica vazio na série toda; coluna descartada (decisão 8) |
| Referência | data | Data de referência da etapa | 0% | 31 valores no mês, um por dia; o formato acompanha a troca de layout — ISO (`2023-01-01`) nos 10 meses sem Codeshare, brasileiro (`01/07/2024 00:00:00`) nos 31 com a coluna |
| Situação Partida | texto | Faixa de atraso na partida: Antecipado, Pontual, Atraso 30-60, 60-120, 120-240, > 240 | 9,3% | Nula quando falta a prevista ou a real; os totais fecham (decisão 4) |
| Situação Chegada | texto | Faixa de atraso na chegada, mesmas categorias | 9,3% | Idem |
| Codeshare | texto | Voos comerciais de parceiros sobre a mesma operação, no formato `SIGLA/NÚMERO`, separados por vírgula | 49% em 2026-05 | Não existe em jan/2023; presente em 31 dos 41 meses (decisão 1); 10.839 combinações distintas em 2026-05 |

As colunas de data/hora chegam como texto e são convertidas com `format="%d/%m/%Y %H:%M"`. Nos três meses verificados, a conversão não gerou nenhum valor inválido além dos nulos originais.

## Colunas dos cadastros

`aerodromos.csv`: SIGLA ICAO AERÓDROMO, SIGLA IATA AERÓDROMO, NOME AERÓDROMO, MUNICÍPIO AERÓDROMO, ESTADO AERÓDROMO, PAÍS AERÓDROMO, AERONAVE CRÍTICA, LATITUDE, LONGITUDE. As coordenadas usam vírgula decimal. O cadastro é mundial, o que permite classificar qualquer voo do VRA por país.

`empresas.csv`: ICAO OPERADOR AÉREO, IATA OPERADOR AÉREO, NOME OPERADOR AÉREO, PAÍS SEDE.

## Decisões de tratamento

### 1. Layout e a coluna Codeshare

A série tem dois layouts: 20 colunas em dez meses de 2023 (janeiro a abril e junho a novembro) e 21 nos outros 31, com a coluna `Codeshare`. A transição é irregular — maio de 2023 tem a coluna e os meses vizinhos não. Na concatenação, o conjunto de colunas é fixado no layout de 21 e os meses antigos recebem `Codeshare` nula. Para a pontualidade a coluna é descritiva: o voo operado é um só e os parceiros comerciais não geram linhas próprias.

### 2. Fuso horário

Todos os horários estão em horário de Brasília, conforme os metadados da ANAC — inclusive os de aeroportos em outros fusos. Não há conversão para UTC nem para o fuso local do aeroporto. Análises por hora do dia refletem o horário de Brasília, e essa limitação deve acompanhar qualquer leitura sobre aeroportos fora desse fuso.

### 3. Cancelamentos

Voos cancelados e não informados não têm horários realizados, e esse nulo é informação, não erro: a verificação nos dois sentidos mostrou que nenhum voo REALIZADO está sem horário e nenhum voo sem horário está marcado como realizado. Cancelados permanecem na base para métricas de cancelamento e ficam de fora do cálculo de atraso.

### 4. Voos extras sem partida prevista

3.739 linhas do mês de referência (4,3%) têm horários realizados mas não têm previsão — voos extras, com `Código DI` diferente de `0`. Sem previsão não existe atraso calculável, e é por isso que `Situação Partida` tem mais nulos do que `Partida Real`: 4.437 sem horário real somados a 3.739 sem prevista dão os 8.176 nulos de situação. Esses voos também explicam os falsos duplicados. Das 2.269 linhas com chave de negócio repetida (empresa + número do voo + partida prevista + origem + destino), 2.267 são voos extras colidindo na chave por terem prevista nula; a duplicata verdadeira do mês é um único par. Regra: voos sem prevista são segregados das análises de pontualidade — não são deduplicados nem descartados.

### 5. Antecipações

Quase metade dos voos parte antes do horário: 39.551 no mês de referência (45,1% das linhas), e o cálculo bate exatamente com a categoria `Antecipado` da ANAC. Nos outros dois meses examinados o quadro se repete e passa da metade: 46.555 em 2024-07 e 44.347 em 2026-05, sempre batendo com a categoria oficial. O efeito sobre médias é grande — atraso médio de 5,3 minutos incluindo antecipações contra 21,5 sem elas. Antecipações são mantidas como categoria própria, nunca descartadas nem truncadas em zero, e as métricas de atraso são reportadas separadas: percentual de pontualidade, atraso médio de quem atrasou e distribuição por faixa.

### 6. Escopo doméstico

O critério é o país do aeródromo no cadastro: voo doméstico é aquele em que origem e destino têm PAÍS AERÓDROMO igual a BRASIL. O critério alternativo, prefixo `SB` na sigla ICAO, foi rejeitado porque deixa de fora aeródromos brasileiros menores (prefixos SD, SI, SJ, SN, SS, SW) — a diferença é de 1.913 linhas no mês de referência. Pelo critério adotado, o escopo cobre 84,6% das linhas do mês; os 15,4% restantes, voos internacionais, ficam fora das análises.

### 7. Chaves órfãs e joins

Todos os 258 aeroportos citados no VRA do mês de referência existem no cadastro de aeródromos — zero órfãos, porque o cadastro é mundial. O cadastro de empresas não cobre tudo: 19 siglas (2.425 linhas, 2,8% do mês) não estão nele. Joins com o cadastro de empresas são sempre à esquerda, preservando as linhas órfãs com nome nulo; nenhuma linha é descartada por falta de correspondência.

### 8. Colunas descartadas

`Justificativa` não entra na base tratada. `Empresa Aérea` e as duas descrições de aeroporto são redundantes com os cadastros e também saem da base tratada, ficando disponíveis via join.

### 9. Extremos e virada de meia-noite

O mês de referência tem 15 voos com atraso de partida acima de 24 horas; 2024-07 tem 25 e 2026-05 tem 8. São registros legítimos na fonte e permanecem na base, mas as métricas agregadas devem usar estatísticas robustas (mediana, percentis, faixas da ANAC) além da média. Voos que cruzam a meia-noite não são problema: as colunas trazem a data completa e nenhuma chegada real veio antes da partida real nos três meses verificados.

### 10. Tipos de dados

`Número Voo` permanece texto para preservar os zeros à esquerda. As quatro colunas de data/hora viram `datetime`. `Número de Assentos` é inteiro, com a ressalva dos registros em zero. O restante permanece texto.

## Pendências

Três pontos ficaram sem resposta na exploração e precisam de verificação antes de qualquer filtro que dependa deles: o significado dos códigos DI `1` a `9`, `D` e `E`; o significado dos tipos de linha `G`, `C` e `X`; e a razão dos 5.214 registros com zero assentos, que pode estar ligada aos tipos de linha cargueiros.
