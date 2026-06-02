# Glossário de Métricas · Survey Gran Mesa

Definições oficiais dos KPIs e métodos do Survey Gran Mesa. Quando houver dúvida sobre o que cada número representa, esta é a fonte.

## Comparadores temporais (herdados do Survey global)

| Sigla | Significado | Cálculo |
|---|---|---|
| **LW** | Last Week | Semana imediatamente anterior |
| **L4W** | Last 4 Weeks | Média das 4 semanas anteriores |
| **L8W** | Last 8 Weeks | Média das 8 semanas anteriores |
| **YoY** | Year over Year | Mesma semana 52 semanas atrás (mesma posição calendária) |
| **YoY 13sem** | YoY acumulado | Soma das 13 semanas focais 2026 vs mesmas 13 semanas 2025 |
| **YoY ajustado** | YoY com ajuste por feriado móvel | Substitui semana YoY por semana 2025 com o mesmo feriado quando há divergência (Carnaval, Páscoa, Cinzas) |

## KPIs macro Gran Mesa (Aba 01)

| KPI | Definição |
|---|---|
| **Faturamento Gran Mesa** | Soma do `Valor` no escopo Gran Mesa (134 SKUs) no período |
| **Cupons Gran Mesa** | Distintos por (Pdv, Cupom, Data) **com pelo menos 1 SKU Gran Mesa** |
| **Ticket médio Gran Mesa** | Faturamento Gran Mesa / Cupons Gran Mesa |
| **Itens/NF Gran Mesa** | Linhas Gran Mesa / Cupons Gran Mesa |
| **% do fat total da loja** | Faturamento Gran Mesa / Faturamento total da loja (todos setores) |
| **Margem R$ Gran Mesa** | Soma de (Valor − qtd × P. Custo) por linha |
| **Margem % consolidada** | Margem R$ / Faturamento Gran Mesa × 100 |
| **GMPro (B2B)** | Faturamento Omie GMPro últimos 30d, separado de KW |

## Indicadores de compartilhamento (em TODAS as abas que mostram SKU)

| Indicador | Cálculo | Para que serve |
|---|---|---|
| **share_fat_mesa** | fat SKU / fat total Gran Mesa × 100 | Mostra peso real do SKU no escopo Gran Mesa |
| **cupons_unicos_sem** | média de cupons únicos por semana (média 13sem) | Mostra penetração entre clientes |
| **selo_relevancia** | verde se share ≥ 0,5% **E** cupons ≥ 30/sem; cinza caso contrário | Bloqueia foco em ruído |

**Regra de uso**: SKUs com selo cinza ainda aparecem no relatório (transparência), mas em **painel secundário** com aviso "baixo impacto agregado — decisões aqui movem pouco o ponteiro".

## Margem (Aba 05 e em todo SKU)

| KPI | Definição |
|---|---|
| **CMV linha** | qtd × P. Custo (de `gran_margens.xlsx`) |
| **Margem R$ linha** | Valor − CMV |
| **Margem % linha** | Margem R$ / Valor × 100 |
| **Margem indisponível** | SKU sem custo no `gran_margens.xlsx` — marca `margem_indisponivel = true`, exclui da matriz Margem×Volume mas mantém em Faturamento |

### Quadrantes (Matriz Margem × Volume — Aba 05)

| Quadrante | Critério | Ação típica |
|---|---|---|
| **Estrelas** | Volume ≥ mediana **E** Margem % ≥ mediana | Proteger preço, manter exposição |
| **Vacas** | Volume ≥ mediana **E** Margem % < mediana | Manter eficiência, tentar +5% margem sem perder volume |
| **Interrogação** | Volume < mediana **E** Margem % ≥ mediana | Puxar exposição/promo, candidato a alavanca |
| **Abacaxis** | Volume < mediana **E** Margem % < mediana | Candidato a corte ou repricing radical |

Mediana calculada sobre todo o escopo Gran Mesa (134 SKUs) na semana atual.

## Lift por dia da semana (Aba 04)

| KPI | Definição |
|---|---|
| **Lift dia X** | (fat SKU no dia X / fat médio dos outros dias do SKU) − 1 |
| **Lift L4W dia X** | (fat SKU no dia X / fat médio do mesmo dia X nas 4 sem anteriores) − 1 |

Heatmap dia × subgrupo mostra ambos. Drill SKU individual mostra também contexto absoluto (selo de relevância) para evitar foco em SKU com lift alto mas volume insignificante.

## Subprodução defensiva (Aba 06)

Hipótese: foco em reduzir perdas levou a sub-produção, derrubando teto de venda.

| KPI | Definição |
|---|---|
| **hora_ultimo_cupom_med** | Média da hora do último cupom diário do SKU nos últimos 7 dias |
| **dias_esgotamento_precoce_pct** | % de dias com último cupom antes das 17h |
| **alerta_subproducao** | true se SKU está no top 30 fat **E** dias_esgotamento_precoce_pct ≥ 40% |

Curva intra-dia: distribuição de cupons por hora (0-23) para os top 20 SKUs Gran Mesa, identificando se há corte abrupto de venda à noite.

## Ruptura recorrente (Aba 06)

| KPI | Definição |
|---|---|
| **ruptura_recorrente** | KVI+ ou KVI **OU** SKU top 30 Gran Mesa que vendeu em <4 das últimas 6 semanas |

## Lançamentos (Aba 07 Bloco A)

| KPI | Definição |
|---|---|
| **lancamento** | SKU cuja primeira venda na base é ≤90 dias atrás |
| **adoção sem 1, 4, 8, 12** | Faturamento ou cupons únicos nas semanas 1, 4, 8 e 12 desde lançamento |
| **status lançamento** | 🟢 (decolando: curva acima do benchmark mediano), 🟡 (mediano), 🔴 (não pegou: <50% do benchmark mediano) |
| **benchmark mediano** | Mediana das curvas de adoção dos lançamentos anteriores Gran Mesa |

## Carteiras de Produção (Aba 07 Bloco B — modo proxy)

| KPI | Definição |
|---|---|
| **fat_carteira** | Soma do fat dos SKUs do colaborador |
| **margem_carteira_R$** | Soma da margem R$ |
| **margem_carteira_%** | margem_R$ / fat_carteira |
| **share_carteira_mesa** | fat_carteira / fat total Gran Mesa |
| **n_skus_responsavel** | Nº de SKUs únicos atribuídos ao colaborador |
| **n_skus_em_alerta** | Nº de SKUs em ruptura ou queda YoY ≥ 20% |

**Importante**: este bloco é **proxy de carteira**, não medida de produtividade real. Para medir kg/hora, perdas físicas e sell-through real, é necessário apontamento diário de produção (input que ainda não existe).

## Métodos de matching ARIUS (herdado do Survey)

Aplicado em cascata para cada linha do KW:

1. EAN exato → bate código de barras
2. Código interno → caso "Codigo EAN" seja na verdade código ARIUS
3. Descrição exata → bate texto normalizado
4. Prefixo único → descrição KW é prefixo único de SKU ARIUS
5. N/A → "SEM CLASSIFICAÇÃO"

Cobertura típica esperada: 95-98%. Abaixo de 95% → alertar Hugo (ARIUS desatualizado).

## Cobertura Mapa de Produção

| Métrica | Definição |
|---|---|
| **cobertura_mapping** | (fat dos SKUs com colaborador atribuído) / fat total Gran Mesa × 100 |
| **bucket_nao_atribuido** | SKUs Gran Mesa cujo COD não está em `Mapa e Producao.xlsx` |
| **alerta_cobertura** | bandeira amarela se cobertura_mapping < 95% |

## Última atualização gran_margens

Selo no rodapé com data de modificação do arquivo `gran_margens.xlsx`:

| Idade | Selo |
|---|---|
| <60d | 🟢 verde |
| 60-90d | 🟡 amarelo |
| ≥90d | 🔴 vermelho + alerta no topo da Aba 05 |
