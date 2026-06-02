# Heurísticas do Detector de Suspeitos (Skill v3)

## REG-S1 — Falta excessiva em colaborador escalado
**Trigger:** colaborador com escala JORNADA em ≥3 dias da semana, e ≥3 desses dias com batidas zero
**Severidade:** 🔴 CRÍTICO
**Tratativa RH:** SIM (vai pra bloco separado, fora dos indicadores)
**Ação:** verificar com gestor + checar histórico do mês anterior
- Se padrão é novo (cara batia normal antes) = falha biométrica → ajuste manual
- Se padrão é cumulativo = abandono real → reincorporar nos indicadores como falta seca

## REG-S2 — Batida única isolada
**Trigger:** colaborador com escala JORNADA, mas só 1 batida no cartão
**Severidade:** 🟡 ALERTA
**Tratativa RH:** NÃO
**Ação:** confirmar com gestor + ajuste manual no RHID

## REG-S3 — Batidas ímpares (3 ou 5)
**Trigger:** 3 ou 5 batidas (esqueceu de bater 1 vez)
**Severidade:** 🟠 MÉDIO
**Tratativa RH:** NÃO
**Ação:** ajuste manual via "Esquecimento Marcação do Ponto" no RHID

## REG-S4 — Trabalhou em folga
**Trigger:** escala marca F/FF/FD/Férias/BH e colaborador bateu ponto
**Severidade:** 🔵 INFO
**Tratativa RH:** NÃO
**Ação:** verificar se foi convocação extraordinária. Pode gerar BH ou hora extra

## REG-S5 — Conflito escala vs RHID (afastamentos)
**Trigger:** escala diz Férias mas RHID lista afastamento terminando antes (ou vice-versa)
**Severidade:** 🟠 MÉDIO
**Tratativa RH:** NÃO
**Ação:** alinhar fonte de verdade com RH

## REG-S6 — Padrão suspeito de longo prazo
**Trigger:** colaborador com >5 dias consecutivos de falta total nos últimos 30 dias
**Severidade:** 🔴 CRÍTICO
**Tratativa RH:** SIM
**Ação:** investigação profunda — provável falha de cadastro ou abandono real

---

## Workflow do detector

```
Extração cartão → Cruzamento escala → Detector aplica REG-S1..S6 → Lista de casos
                                                                   │
                                                ┌──────────────────┴──────────────────┐
                                                ▼                                     ▼
                                  Casos com tratativa_rh=True            Casos com tratativa_rh=False
                                          ↓                                          ↓
                              EXCLUI dos indicadores                   PERMANECE nos indicadores
                              Vai pra Aba 05 (Tratativa RH)            Aparece também na Aba 04 (Casos Suspeitos)
                              Em rodadas futuras: Hugo decide          Consultora RH ajusta no RHID antes
                              se reincorpora (abandono) ou             do fechamento da folha
                              libera (falha técnica corrigida)
```

## Quando atualizar essas heurísticas
- Adicionar nova regra: confirmar com Hugo, atualizar este arquivo + `detector_suspeitos.py` + SKILL.md
- Calibrar threshold (ex: mudar "3 dias" pra "4 dias"): documentar a razão e a data
