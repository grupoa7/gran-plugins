# Changelog v3.2 — 2026-05-09

## Mudanças
1. **Aba 01 promovida ao formato Histórico Cumulativo**
   - Antes: heatmap simples da semana atual (7 dias × N colab)
   - Agora: KPIs cumulativos, gráfico de tendência (Chart.js), tabela semana a semana, heatmap multi-semana (N semanas × N colab), top reincidentes, tornado piora/melhora
2. **Auto-alimentação:** lê todos os JSONs em `historico/` e gera tudo dinamicamente
3. **Backfill incorporado:** S10-S17/2026 (mar+abr) processados e disponíveis no histórico

## Arquivos novos no deploy
- `scripts/gerar_html.py` (substituído pela versão v3.2)
- `CHANGELOG_v32.md`

## Como deployar
Substituir os arquivos em `.claude/skills/monitoramento-jornada-gran/`:

```bash
cp v3_skill_deploy/scripts/* .claude/skills/monitoramento-jornada-gran/scripts/
cp v3_skill_deploy/references/* .claude/skills/monitoramento-jornada-gran/references/
cp v3_skill_deploy/SKILL.md .claude/skills/monitoramento-jornada-gran/
cp v3_skill_deploy/CHANGELOG_v3*.md .claude/skills/monitoramento-jornada-gran/
```

A próxima rodada (qua 13/05) já vai sair com formato v3.2 e a S20 entra automaticamente como nova coluna no heatmap multi-semana.
