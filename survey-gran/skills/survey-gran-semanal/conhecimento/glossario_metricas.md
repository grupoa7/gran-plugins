# Glossário de Métricas · Survey Gran

Definições oficiais dos KPIs e métodos do Survey. Use em caso de dúvida sobre o que cada número representa.

## Comparadores temporais

| Sigla | Significado | Cálculo |
|---|---|---|
| **LW** | Last Week | Semana imediatamente anterior |
| **L4W** | Last 4 Weeks | Média das 4 semanas anteriores |
| **L8W** | Last 8 Weeks | Média das 8 semanas anteriores |
| **YoY** | Year over Year | Mesma semana 52 semanas atrás (mesma posição calendária) |
| **YoY 13sem** | YoY acumulado | Soma das 13 semanas focais 2026 vs mesmas 13 semanas 2025 |

### YoY com ajuste por feriado móvel

Quando uma semana atual tem feriado em data diferente da semana YoY (Carnaval, Páscoa, Cinzas), o skill marca a semana com ⚠️ e oferece **comparação alternativa**: a semana de 2025 que tem o **mesmo feriado** (não a posição calendária).

Exemplo: S04/2026 tem Carnaval. S04/2025 era semana normal (Carnaval caiu na S06/2025). A comparação alinhada substitui S04/2025 por S06/2025.

## KPIs macro

| KPI | Definição |
|---|---|
| **Faturamento** | Soma da coluna `Valor` no período |
| **Cupons** | Distintos por (Pdv, Cupom, Data) |
| **Ticket médio** | Faturamento / cupons |
| **Itens/NF** | Linhas / cupons |
| **Média/dia** | Faturamento / dias com vendas |
| **Cobertura** | % do faturamento classificado pelo cadastro ARIUS |

## KVI · Key Value Items

São SKUs estratégicos com perfil de:
- **KVI+**: SKUs ultracríticos (top sensibilidade preço, alta presença).
- **KVI**: SKUs críticos (sensibilidade média).
- **ATT**: SKUs de atenção (oscilação).

Lista atualizada em `~/Documents/SurveyGran/cadastros/kvi.xlsx`.

## Métodos de matching ARIUS

Aplicado em cascata. Pra cada linha do KW, tenta:

1. **EAN exato** — bate código de barras com cadastro.
2. **Código interno** — se o "Codigo EAN" for na verdade um código ARIUS interno.
3. **Descrição exata** — bate texto da descrição com cadastro normalizado.
4. **Prefixo único** — se a descrição KW é prefixo único de um SKU ARIUS.
5. **N/A** — não casou; vai pra "SEM CLASSIFICAÇÃO".

Cobertura típica: **95–98%**. Abaixo de 95% = ARIUS desatualizado.

## Cash & Carry

Promoção de fim de semana (sex/sáb/dom). Ranqueada por:
- **Lift L4W**: variação vs média do mesmo dia-da-semana nas 4 sem anteriores.
- **Cupons leve3**: cupons que carregaram 3+ unidades do produto.

## Ofertas dia-temáticas

| Dia | Tema | Filtro |
|---|---|---|
| Segunda | Mercearia → Funcionais | subgrupo='FUNCIONAIS' |
| Terça | Hortifruti completo | setor começa com 'HORTIFRUTI' |
| Quarta | Carnes, Aves & Pescados | setor='CARNES, AVES & PESCADOS' |
| Quinta | Gran Mesa | setor='GRAN MESA' |

Comparação dupla:
- **Lift intra-semana**: dia da oferta vs média dos outros dias.
- **Lift L4W**: dia da oferta vs mesmo dia-da-semana nas 4 sem anteriores.

Oferta "pegou" se ambos lifts ≥ 15%. "Não pegou" se algum lift < 0%.

## Elasticidade

Coeficiente de correlação entre preço médio e quantidade vendida nas 13 sem focais. Valores próximos de -1 indicam alta elasticidade (descontos puxam volume). Valores próximos de 0 indicam SKU inelástico (preço quase não afeta venda).

Filtros: SKU precisa de ≥ 4 semanas com venda no período.

## Ruptura recorrente

SKU classificado como KVI+ ou KVI que teve venda em **menos de 4 das últimas 6 semanas** focais. Indica problema de abastecimento ou descontinuação não-marcada no cadastro.
