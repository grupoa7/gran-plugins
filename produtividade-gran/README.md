# produtividade-gran v1.0.0

Plugin Cowork complementar ao **survey-gran**. Análise mensal de produtividade das equipes do Gran Hortifruti.

## Pergunta-mãe

> Em qual área do Gran estou gastando mais do que produzindo com a equipe?

## Como usar

1. Instale o plugin (drag & drop do `.plugin` no Cowork)
2. Abra o projeto `[GRAN] Survey` no Cowork
3. Comando: `/produtividade` (mês anterior fechado) ou `/produtividade mes=03/2026`

## Saída

`data/produtividade/relatorios/Produtividade_MM_AAAA.html` — relatório executivo com 4 abas.

## Inputs necessários (em `data/produtividade/inputs/`)

- `gran_margens.xlsx` — cadastro com base de precificação por SKU
- `cadastro_equipe.xlsx` — folha CLT classificada por equipe
- `omie_gmpro.xlsx` — vendas Gran Mesa Pro extraídas do Omie
- `parametros.json` — premissas editáveis

E reaproveita do survey-gran:
- `../base/base_classificada.pkl` — fat e qtd por SKU (KW)
- `../cadastros/export_base_arius.xlsx` — mapeamento setor/grupo

## Decisões consolidadas

Veja `skills/produtividade-gran-mensal/SKILL.md` para regras completas.

## Versão

v1.0.0 — primeira entrega. Cobre 30 dias rolling com KPIs Custo/Margem por equipe.
