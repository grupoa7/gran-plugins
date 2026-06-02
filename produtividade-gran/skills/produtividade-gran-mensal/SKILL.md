---
name: produtividade-gran-mensal
description: Geração mensal do relatório de Produtividade Gran — análise de custo de pessoal vs margem por equipe (Gran Mesa | Gran Horti). Use SEMPRE que Hugo mencionar /produtividade, produtividade, custo da equipe, custo de pessoal, margem por equipe, equipe Gran Mesa, equipe Gran Horti, Gran Mesa Pro, GMPro, fechamento mensal de pessoal, ou qualquer tarefa relacionada ao consolidado mensal de produtividade do Gran Hortifruti. NÃO use para Survey semanal de vendas (use survey-gran). NÃO use para auditoria de caixas (use auditoria-caixas-gran). NÃO use para CRM (use crm-proativo-gran).
---

# Skill: produtividade-gran-mensal

## Contexto

Esta skill responde à pergunta-mãe que Hugo (sócio do Grupo A7) e a sócia precisam acompanhar mês a mês:

> **Em qual área do Gran estou gastando mais do que produzindo com a equipe?**

A análise compara as duas equipes do Gran:
- **Gran Mesa** — produção própria (setor Gran Mesa do KW + grupo Fatiados + 65% da Padaria Gran + Gran Mesa Pro/Omie). 9 funcionários CLT + R$ 2.000/mês de diaristas.
- **Gran Horti** — operação de varejo geral (todos os demais setores + 35% da Padaria Gran + cód 760). 8 funcionários CLT.
- **Retaguarda** — 4 funcionários rateados pró-rata por faturamento entre as duas equipes.

## Quando rodar

- Comando direto: `/produtividade` — assume mês de referência = mês anterior fechado
- Com parâmetro: `/produtividade mes=03/2026` — mês específico
- Cadência sugerida: dia 5 de cada mês (após fechamento da folha)

## Inputs (ler nesta ordem)

```
[GRAN] Survey/data/
├── base/
│   └── base_classificada.pkl     ← gerado pelo survey-gran v0.12.6+ (KW: fat + qtd últimos 30d)
├── cadastros/
│   └── export_base_arius.xlsx    ← cadastro ARIUS (mapeamento setor/grupo por SKU)
└── produtividade/
    └── inputs/
        ├── gran_margens.xlsx     ← coluna DADOS MARGENS / P. CUSTO por SKU (custo unitário)
        ├── cadastro_equipe.xlsx  ← folha CLT classificada por equipe (Gran Mesa / Gran Horti / Retaguarda)
        ├── omie_gmpro.xlsx       ← faturamento Gran Mesa Pro (Omie, B2B refeições coletivas)
        └── parametros.json       ← premissas editáveis (CMV GMPro, fator encargos, regra rateio, etc.)
```

## Pipeline (build_dados.py)

1. **Ler KW**: filtrar `base_classificada.pkl` para os últimos N dias (parâmetro, default 30). Se `.pkl` falhar (incompatibilidade pandas), fallback para `dados_survey.json` ou avisa para regenerar via /survey.
2. **Cruzar margens**: para cada SKU vendido, buscar P. Custo em `gran_margens.xlsx` via campo COD. CMV = qtd × P. Custo. Margem = fat - CMV.
3. **Atribuir equipe** por linha (regra em `parametros.json`):
   - Setor "GRAN MESA" → 100% Gran Mesa
   - Grupo "FATIADOS" → 100% Gran Mesa
   - Códigos `[1, 589-595, 602, 616, 759, 763, 6424, 6584]` (Padaria Gran exceto 760) → 65% Gran Mesa, 35% Gran Horti
   - Cód 760 → 100% Gran Horti
   - Demais → 100% Gran Horti
4. **Adicionar Omie GMPro**: somar últimos 30 dias rolling de `omie_gmpro.xlsx` (aba NFs Detalhe). Aplicar CMV de `parametros.json` (default 49%). Adicionar 100% à Gran Mesa.
5. **Custo pessoal**:
   - Folha CLT: somar Total Vencimentos por equipe × `fator_encargos_clt` (default 1.55)
   - Diaristas: + `custo_diaristas_gran_mesa` (default R$ 2.000) → 100% Gran Mesa
   - Retaguarda: ratear pró-rata por faturamento total (Gran Mesa + GMPro vs Gran Horti)
6. **Calcular KPIs**:
   - Custo / Faturamento (%)
   - **Custo / Margem (%)** ← KPI mãe
   - Margem / Custo (×)
   - Faturamento / Funcionário
   - Margem / Funcionário
   - Margem % por equipe
7. **Top SKUs** por equipe (top 10 por margem em R$, com margem %).
8. **Salvar**: `dados_produtividade.json` em `data/produtividade/`.

## Output (gerar_html_produtividade.py)

`data/produtividade/relatorios/Produtividade_MM_AAAA.html` com **4 abas**:

### Aba 1 — Headline Executivo
- Título com mês de referência
- Alerta no topo (vermelho/amarelo/verde conforme thresholds)
- 3 cards grandes: Gran Mesa | Gran Horti | Total — todos com KPI Custo/Margem em destaque
- Frase de leitura em prosa
- 3 hipóteses para investigação (sub-escala / quadro inflado / mistura de funções)

### Aba 2 — Composição por Equipe
Sub-abas:
- **Faturamento**: stacked bar (KW vs Omie por equipe)
- **Margem**: composição por origem
- **Custo Pessoal**: composição (folha CLT / diaristas / rateio retaguarda)
- **Lista Nominal**: tabela com 21+ funcionários, função, custo individual, equipe

### Aba 3 — Top SKUs por Equipe
- Coluna Gran Mesa: top 10 por margem em R$, margem % colorida
- Coluna Gran Horti: idem
- Highlight: verde >50% margem, amarelo 30-50%, vermelho <30%

### Aba 4 — Sensibilidade
- Sliders interativos para 3 eixos:
  - Eixo A: faturamento Gran Mesa Pro (R$ 70k → R$ 200k)
  - Eixo B: redução de quadro Gran Mesa (-1, -2 funcionários)
  - Eixo C: % de tempo da Gran Mesa realocado para Gran Horti
- Tabela mostra como o KPI Custo/Margem responde a cada cenário

## Princípios inegociáveis

1. **Verdade dura > validação vazia**: se algum dado estiver bagunçado ou faltando, o relatório destaca como bandeira amarela. Não inventa.
2. **Premissas explícitas**: tudo que é assumido (CMV GMPro, fator encargos, etc.) aparece no rodapé do HTML.
3. **80/20**: 4 abas, máximo. Sem inflar.
4. **Cobertura ARIUS**: se >5% do faturamento ficar não-classificado no ARIUS, alerta.
5. **Para a sócia ler em 5 min**: Aba 1 deve responder a pergunta-mãe sem precisar ir além.

## Comando interno

```bash
python skills/produtividade-gran-mensal/build_dados.py
python skills/produtividade-gran-mensal/gerar_html_produtividade.py
```

Ou via skill agentic: Claude executa os 2 scripts em sequência quando Hugo pedir `/produtividade`.

## Path resolution

Mesma convenção do survey-gran v0.12.6:
- Default: lê de `~/Documents/Claude/Projects/[GRAN] Survey/data/`
- Override: variável de ambiente `SURVEY_DATA_DIR` (compartilhada com survey-gran)

## Decisões consolidadas (v1)

| Tópico | Decisão |
|---|---|
| Custo total empresa | Total Vencimentos × 1.55 |
| CMV GMPro | 49% (margem 51%) |
| Diaristas | R$ 2.000/mês fixo, 100% Gran Mesa |
| Rateio Retaguarda | Pró-rata por faturamento |
| Regra Padaria Gran | 65% Gran Mesa / 35% Gran Horti, **exceto cód 760** (100% Gran Horti) |
| Período | 30 dias rolling |
| Cadência | Mensal, dia 5 |
| Mockup | 4 abas (Headline / Composição / Top SKUs / Sensibilidade) |

## Fora do escopo v1 (próximas versões)

- Histórico mês a mês (precisa folhas dos meses anteriores)
- Análise individual por funcionário (sem mapping operador↔PDV ainda)
- Benchmark de varejo externo
- Diff vs mês anterior
- Upload automático de NFs do Omie (manual via planilha por enquanto)
