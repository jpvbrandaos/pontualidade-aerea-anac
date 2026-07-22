# Modelo estrela — decisões de modelagem

Este documento acompanha o diagrama de `modelo_estrela.png` (fonte editável em `modelo_estrela.dbml`) e registra o que o desenho sozinho não conta: o grão da tabela fato, o papel de cada dimensão e as decisões tomadas antes de qualquer código. As regras de qualidade e escopo citadas aqui vêm do `dicionario_dados.md`.

## Grão

Uma linha de `fato_voos` é uma etapa de voo doméstico do período de janeiro de 2023 a maio de 2026 — incluindo voos cancelados e voos extras sem horário previsto, ambos sinalizados por flags, e excluindo voos internacionais (decisão 6 do dicionário: origem e destino com país BRASIL no cadastro de aeródromos, o que cobre 84,6% das linhas no mês de referência).

Cancelados ficam na fato porque taxa de cancelamento é pergunta de negócio do projeto; suas métricas de atraso são nulas. Voos extras ficam porque são operação real; sem horário previsto não têm atraso calculável e a `flag_sem_prevista` os separa das análises de pontualidade.

## fato_voos

As colunas se dividem em quatro grupos. As chaves ligam o voo às dimensões: `data_voo`, `sigla_empresa`, `icao_origem` e `icao_destino`. Os atributos descrevem o evento e não justificam dimensão própria (o Kimball chama isso de degenerate dimension): `numero_voo`, `codigo_di`, `codigo_tipo_linha`, `modelo_equipamento`, `situacao_voo` e os quatro horários originais. O terceiro grupo são as métricas e o quarto, as flags.

| Métrica / flag | Regra |
|---|---|
| `atraso_partida_min` | partida real − partida prevista, em minutos; negativo indica antecipação; nula se cancelado ou sem prevista |
| `atraso_chegada_min` | chegada real − chegada prevista, mesmas condições |
| `duracao_prevista_min` | chegada prevista − partida prevista |
| `duracao_real_min` | chegada real − partida real |
| `flag_pontual_d15` | atraso de partida de até 15 minutos, antecipações incluídas; nula se cancelado ou sem prevista |
| `flag_antecipado` | atraso de partida menor que zero |
| `flag_cancelado` | situação do voo igual a CANCELADO |
| `flag_sem_prevista` | partida prevista nula (decisão 4 do dicionário) |

Toda métrica é calculada uma única vez, na construção da fato, e nenhuma query ou medida do Power BI refaz o cálculo. O motivo é prático: se cada consulta recalcular `real − prevista`, em algum momento uma delas vai truncar antecipação ou esquecer cancelado, e dois relatórios vão mostrar números diferentes para a mesma pergunta. Com a métrica materializada, existe uma definição só, num lugar só.

## Dimensões

`dim_empresa` vem do cadastro de operadores do SIROS (70 empresas), acrescido das siglas que aparecem no VRA sem constar no cadastro — 19 no mês de referência. Essas entram com nome "NÃO CADASTRADA" e `flag_no_cadastro` falsa, para que o join nunca perca voo (decisão 7 do dicionário).

`dim_aeroporto` vem do cadastro de aeródromos, filtrado para país BRASIL (3.548 registros). A coluna `regiao` não existe na fonte e será derivada da UF por um mapeamento fixo de 27 entradas, criado na fase de tratamento. A fato usa esta dimensão duas vezes — origem e destino —, o padrão que a literatura chama de role-playing dimension: uma tabela física, dois papéis. No Power BI isso vira duas relações (uma ativa e uma acionada por `USERELATIONSHIP`) ou a dimensão duplicada em "Aeroporto Origem" e "Aeroporto Destino"; a escolha fica para a fase do dashboard, o modelo suporta ambas.

`dim_calendario` é gerada por código: uma linha por dia de 2023-01-01 a 2026-05-31, 1.247 no total, com ano, mês, nome do mês, dia, dia da semana e três flags — fim de semana, feriado nacional (calendário do pacote `holidays` do Python) e alta temporada. Alta temporada não tem definição oficial; a adotada aqui é janeiro, julho e 15 a 31 de dezembro.

`dim_justificativa`, prevista no desenho inicial do projeto, foi avaliada e descartada: a coluna Justificativa está 100% vazia nos meses examinados, porque a exigência caiu em abril de 2020 com a revogação da IAC 1504.

## Decisões

**Chaves naturais, não surrogate.** As dimensões usam a própria sigla ICAO e a própria data como chave, em vez dos inteiros artificiais que o Kimball recomenda. Surrogate keys protegem contra mudança de código na fonte e economizam espaço em bases grandes; aqui as dimensões são pequenas (a maior tem 3.548 linhas), os códigos ICAO são estáveis por construção e a chave natural deixa o modelo legível e as queries mais simples de conferir. A troca é consciente.

**Data-âncora.** O voo liga ao calendário pela data da partida prevista. Para os voos extras, que não têm prevista, usa-se a coluna Referência do VRA — que existe em 100% das linhas e marca o dia da etapa.

**D15 medido na partida, antecipados contam como pontuais.** Pontual é o voo que parte com até 15 minutos de atraso sobre o previsto. Antecipados entram como pontuais porque não atrasaram; quem quiser analisá-los em separado usa a `flag_antecipado` — é para isso que as duas flags coexistem. A medição na partida, e não na chegada, segue o indicador da própria ANAC na Consulta Interativa de Pontualidade, que é a referência de validação do projeto. O atraso de chegada permanece disponível como métrica para a pergunta de recuperação de atraso no ar.
