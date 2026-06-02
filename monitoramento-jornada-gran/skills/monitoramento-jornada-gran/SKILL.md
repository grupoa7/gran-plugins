---
name: monitoramento-jornada-gran
description: >-
  Relatório semanal de monitoramento de jornada do Gran Hortifruti + GRSM. Roda
  toda quarta cobrindo a semana quarta-anterior até terça. Cruza batidas reais do
  RHID (Cartão de Ponto) com a escala mensal em PDF e aplica 6 regras de
  inconsistência (atraso de entrada maior que 15 min, intervalo fora 1h-1h05,
  descanso em janela proibida 11h-13h em sáb/dom/feriado e 16h-19:30 todos os dias
  só pra setores restritos, pulou intervalo + jornada maior que 6h, falta seca,
  marcações incoerentes), detecta casos suspeitos (REG-S1 a S6) e publica
  automaticamente no GitHub Pages. Gera relatório executivo em HTML com 4 abas
  (Histórico cumulativo, Panorama, Detalhe, Tratativa RH). Use SEMPRE que Hugo
  mencionar /jornada-semana, jornada, monitoramento de jornada, relatório semanal
  de jornada, faltas, atrasos, descanso fora do horário, intervalos, janela
  proibida, banco de horas semanal, ponto, RHID. NÃO use para survey de vendas
  (use survey-gran). NÃO use para auditoria de caixas (use auditoria-caixas-gran).
---

# Monitoramento de Jornada — Gran + GRSM (v3.3)

> Skill operacional do Cowork. Hugo dispara `/jornada-semana` toda quarta de manhã.

---

## 1. O que essa skill faz (resumo)

Pega batidas reais do RHID, cruza com escala mensal, detecta casos suspeitos (REG-S1 a S6),
separa Tratativa RH dos indicadores, gera HTML executivo com 4 abas, e **publica automaticamente no GitHub Pages** (v3.3). **Aba 01 alimenta-se automaticamente do histórico cumulativo** — toda rodada nova adiciona uma coluna ao heatmap multi-semana e atualiza tornado/reincidentes/tendência.

URL pública: **https://grupoa7.github.io/gran-rh-monitoramento/**

---

## 2. Workflow v3.3

> **Extração RHID (atualização 2026-05-21):** o relatório de Cartão de Ponto agora é um visualizador **paginado**. ⚠️ NUNCA chamar `openAll()` (trava o renderer). Truque: **reabrir o GUID numa aba nova** renderiza todos os cartões no DOM de uma vez. Detalhes em `references/notas_operacionais.md`.

```
1. EXTRAÇÃO        → Cartão de Ponto (RHID via Chrome MCP) + Escala (PDF) + Afastamentos
                    [feito por Claude via tools de navegação — produz cartao_ponto_S{N}_2026.json]

2-8 (orquestrador) → python3 scripts/run_jornada_completo.py ...
                    2. Parsear escala mensal (PDF)
                    3. Match RHID ↔ escala (token-based, 1ª palavra prefix-match)
                    4. Aplicar 6 regras + detector REG-S1..S6
                    5. Persistir JSON da semana + CSV cumulativo
                    6. Gerar HTML v3.3 → relatorios/
                    7. Atualizar staging repo_publico_pra_subir/
                    8. Git push origin/main → GitHub Pages atualiza em 30-60s
```

### Comando único (passo 1 já executado, cartão JSON na pasta)
```bash
python3 .claude/skills/monitoramento-jornada-gran/scripts/run_jornada_completo.py \
  --projeto "/Users/hugogusmao/Documents/Claude/Projects/[GRAN RH] Monitoramento de jornada" \
  --cartao cartao_ponto_S{N}_2026.json \
  --escala "escalas/ESCALA GRAN_MAIO26_REV001.pdf" \
  --semana-id S{N} \
  --periodo-ini 2026-MM-DD \
  --periodo-fim 2026-MM-DD \
  --suspensos "Emilly Brito,Alana"
```

Use `--no-publish` pra testar sem subir no GitHub.

---

## 3. Estrutura das 4 abas

### Aba 01 — Histórico & Tendência (v3.2)
**Alimentação automática** dos JSONs em `historico/`. Quanto mais semanas, mais sólida a leitura.
- KPIs cumulativos (CRIT/ALERT/OK · faltas · janela proibida · atrasos)
- Gráfico de tendência (Chart.js — barra empilhada + linha)
- Tabela semana a semana
- Heatmap colaborador × semana (auto-expansão horizontal)
- Top reincidentes (janela proibida, atrasos, intervalos)
- Tornado piora vs melhora (split automático no último 1/3 do período)

### Aba 02 — Panorama da semana (snapshot)
- KPIs da semana atual
- Top 5 (faltas/atrasos/janela proibida)
- Tabela panorama

### Aba 03 — Detalhe diário
Tabela espelhando escala. Cada célula com previsto/bateu/alertas.

### Aba 04 — Tratativa RH
Casos sob responsabilidade da Consultora RH com status pra acompanhamento de desempenho.

---

## 4. Regras (v3.1+)

- **Tolerância de atraso de entrada:** 15 min (v3.3.2). Saída antecipada e hora extra seguem em 10 min.
- **Janela proibida 11h-13h:** só vale em sáb/dom/feriado nacional
- **Janela proibida 16h-19:30:** vale todos os dias
- **Setores restritos:** ENCARREGADOS, OPERADOR DE LOJA, OPERADOR DE CAIXAS (MANOBRISTA fora desde v3)
- **Detector REG-S1 a S6:** ver `references/heuristicas_suspeitos.md`

---

## 5. Publicação automática no GitHub Pages (v3.3)

### Credenciais
- Token PAT (fine-grained) armazenado em `.env` da pasta do projeto (gitignored)
- Variáveis: `GITHUB_PAT`, `GITHUB_REPO`
- Token criado em https://github.com/settings/personal-access-tokens com scope **Contents: Read and write** no repo `grupoa7/gran-rh-monitoramento` apenas
- Expira a cada 90 dias — renovar antes de Aug/2026

### Fluxo automatizado (passo 8)
```bash
source .env
git clone "https://x-access-token:${GITHUB_PAT}@github.com/${GITHUB_REPO}.git" /tmp/grm_publish
cd /tmp/grm_publish
cp $PROJETO/repo_publico_pra_subir/*.{html,md} .
git config user.email "hugo@grupoa7.com.br"
git config user.name "Hugo Gusmao (via Claude/Cowork)"
git add -A
git commit -m "S{N}/2026 — Monitoramento de Jornada {periodo}"
git push origin main
rm -rf /tmp/grm_publish  # limpa clone com token no remote
```

### Onde atualizar staging antes do push
- `repo_publico_pra_subir/index.html` ← cópia do `relatorios/Relatorio_Jornada_Semanal_S{N}_2026.html`
- `repo_publico_pra_subir/relatorio_S{N}_2026.html` ← arquivo nominal
- `repo_publico_pra_subir/README.md` ← atualizar referências a S{N} e próxima rodada (DD/MM/2026)

### Validar publicação
- Aguardar ~30-60s e checar `curl -s https://grupoa7.github.io/gran-rh-monitoramento/ | grep -c "S{N}"` — deve retornar ≥1

---

## 6. Princípios não-negociáveis

1. Nunca inventar batidas
2. Escala manda em conflitos
3. Tratativa RH separada dos indicadores
4. Sem acusação — pedidos curtos pra Consultora ajustar
5. **Token PAT nunca commitado** — sempre via `.env` (gitignored)

---

## 7. Histórico de versões

| Versão | Data | Mudanças |
|---|---|---|
| v1 | 2026-05-08 | Versão original. Bug parser. |
| v2 | 2026-05-08 | SKILL.md vira instrução. HTML via Write. |
| v3 | 2026-05-09 | Detector REG-S1..S6. MANOBRISTA fora de restritos. Aba Tratativa RH. |
| v3.1 | 2026-05-09 | Janela manhã condicional. Aba Tratativa RH unificada. |
| v3.2 | 2026-05-09 | Aba 01 promovida ao formato Histórico Cumulativo. Backfill mar+abr/26 incorporado. |
| **v3.3** | **2026-05-14** | **Passo 8 — publicação automática no GitHub Pages via PAT em .env. Roda como etapa final do `/jornada-semana`.** |
| **v3.3.1** | **2026-05-21** | RHID virou relatório paginado (nunca usar `openAll`; reabrir GUID renderiza tudo). Regra `classify_day`: folga/férias deferida no cartão (folga habilitada / férias concedida) vence a escala publicada. Instalador clicável durável `instalar_skill_jornada.command` (sincroniza local → plugin ativo). |
| **v3.3.2** | **2026-05-21** | Tolerância de atraso de ENTRADA voltou de 10 → 15 min (decisão Hugo). Saída antecipada e hora extra mantidas em 10 min. Rótulos do HTML atualizados (">15min"). |
