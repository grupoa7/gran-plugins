# Regras de Negócio — Skill Monitoramento de Jornada

As 6 regras de inconsistência aplicadas pra cada (colaborador, dia) durante o processamento. Ordem de implementação no script `aplicar_regras.py`.

---

## Regra 0 — Pré-condições por dia

Antes de aplicar qualquer regra, classificar o dia conforme a escala mensal:

| Tipo de escala | Tratamento |
|---|---|
| `JORNADA` (HH:MM às HH:MM) | Aplicar regras 1 a 6 |
| `F` (folga regular) | Pular dia. Não conta como falta. |
| `FF` (folga feriado) | Pular dia. Não conta como falta. |
| `FD` (folga domingo) | Pular dia. Não conta como falta. |
| `Férias` | Pular dia. Não conta como falta. |
| `BH` (banco de horas) | Pular dia. Tratado como ajuste. |

**Importante:** se o RHID marcar "Falta" mas a escala disser folga/férias/BH → **escala vence**. Não conta como inconsistência.

---

## Regra 1 — Atraso de entrada

**Condição:** ENT.1 (primeira batida) > horário previsto da escala + 15 min

**Severidade:** 🟡 ALERTA

**Mensagem:** `"Atraso de {N} min na entrada"` · evidência: `"Bateu HH:MM · previsto HH:MM"`

**Threshold:** 15 minutos (decisão Hugo · 2026-05-21 — voltou de 10 para 15 min; saída e hora extra seguem em 10)

**Edge case:** se ENT.1 for vazio mas houver outras batidas (ENT.2 etc.), tratar como marcação incoerente (Regra 6).

---

## Regra 2 — Saída fora do horário previsto

**Condição:** última batida do dia (SAÍ.3 → SAÍ.2 → SAÍ.1, na ordem) comparada com horário de saída previsto da escala.

| Diferença | Classificação | Severidade |
|---|---|---|
| Saída < previsto − 10 min | Saída antecipada | 🟡 ALERTA |
| previsto − 10 min ≤ Saída ≤ previsto + 10 min | Dentro da tolerância | ✓ OK |
| Saída > previsto + 10 min | Hora extra | ℹ INFO (sempre informativo) |

**Hora extra:** sempre alerta amarelo informativo, nunca bloqueante (decisão Hugo).

---

## Regra 3 — Intervalo (faixa permitida 1h00 a 1h05)

**Aplica a TODOS os intervalos do dia** quando há múltiplos pares de batida (ENT.2/SAÍ.2, ENT.3/SAÍ.3) (decisão Hugo).

Pra cada intervalo SAÍ.x → ENT.(x+1):
- duração < 60 min → 🟡 INTERVALO_CURTO
- 60 ≤ duração ≤ 65 min → ✓ OK
- duração > 65 min → 🟡 INTERVALO_LONGO

**Mensagem:** `"Intervalo de {N} min (abaixo de 1h)"` ou `"Intervalo de HH:MM (acima de 1h05)"` · evidência: `"HH:MM → HH:MM"`

**Não aplica:** estagiária Alana (regime diferente).

---

## Regra 4 — Descanso em janela proibida

**Aplica APENAS** aos setores restritos:
- ENCARREGADOS
- OPERADOR DE LOJA
- OPERADOR DE CAIXAS
- MANOBRISTA

**Janelas proibidas:**
- 11:00 — 13:00 (almoço — fluxo de cliente alto)
- 16:00 — 19:30 (final da tarde — fluxo de cliente alto)

**Critério:** se **qualquer minuto** de **qualquer intervalo** do dia cair dentro da janela → 🔴 CRÍTICO (decisão Hugo).

Exemplo: SAÍ.1 = 10:50 e ENT.2 = 11:30 → cruza janela 11h-13h por 30 min → CRÍTICO.

**Mensagem:** `"Descanso em janela proibida ({janela}) — setor restrito"` · evidência: `"HH:MM → HH:MM"`.

**Razão de negócio (Hugo):** evitar fila no caixa/loja durante horário de pico. É a dor principal que motiva o relatório.

---

## Regra 5 — Pulou intervalo + jornada > 6h

**Condição:**
- Sem ENT.2/SAÍ.2 (ou seja, só houve 1 par de batida ENT.1/SAÍ.1)
- E (SAÍ.última − ENT.1) > 6 horas

**Severidade:** 🔴 CRÍTICO (CLT exige intervalo após 6h consecutivas)

**Mensagem:** `"Trabalhou HH:MM sem intervalo registrado (limite CLT 6h)"` · evidência: `"Entrou HH:MM · saiu HH:MM"`

**Não aplica:** estagiária Alana.

---

## Regra 6 — Falta seca

**Condição:** todas as batidas do dia são "Falta" ou vazias **E** escala dizia jornada **E** sem justificativa registrada (atestado/férias/folga/licença/feriado).

**Severidade:** 🔴 CRÍTICO

**Mensagem:** `"Falta sem justificativa registrada"` · evidência: `"Previsto: HH:MM → HH:MM"`

**Justificativas que excluem falta seca** (ver `tipos_justificativa.md`):
- Atestado Médico / Comparecimento / Óbito
- Exame de Retorno ao Trabalho
- Férias
- Feriado / Folga Feriado
- Folga (qualquer tipo)
- Licença Casamento / Maternidade / Paternidade
- Afastamento Temporário
- Suspensão (entra como observação separada)

---

## Regra 7 — Marcações incoerentes (auxiliar)

**Condições:**
- Sequência de batidas fora de ordem (ex: 13:55 antes de 13:42)
- ENT.1 sem SAÍ.1 ou só SAÍ sem ENT
- Batidas que não fecham os pares

**Severidade:** 🟡 ALERTA com texto **"VERIFICAR MANUALMENTE"** + evidência

**Não tenta inferir o que aconteceu.** Sinaliza pra revisão humana.

---

## Cálculo de status do colaborador

Após processar os 7 dias da semana:

```
SE alguma inconsistência crítica (Falta seca, Janela proibida, Pulou intervalo) →
   status = CRÍTICO
SENÃO se houver alertas (atrasos, intervalos fora, saídas fora, hora extra, incoerentes) →
   status = ALERTA
SENÃO →
   status = OK
```

---

## Casos especiais

### Estagiária Alana
- Aplica apenas Regra 6 (falta seca).
- **Não aplica:** intervalo (Regra 3), janela proibida (Regra 4), pulou intervalo (Regra 5), hora extra.
- Atraso de entrada (Regra 1) e saída fora (Regra 2): aplicam normal.

### Múltiplos pares de batida (3 entradas e 3 saídas)
Quando há 6 batidas (turno fragmentado), tratar todos os intervalos com Regra 3 e Regra 4. Decisão Hugo: "qualquer intervalo > 1h05 vira alerta; qualquer intervalo cruzando janela proibida vira crítico se setor restrito".

### Conflito escala × RHID
Sempre **escala vence**. Sem registro de inconsistência adicional. Decisão Hugo.

### Suspensos do monitoramento
Lista em `references/suspensoes.json`. Atualmente:
- **Emilly Brito** — modalidade alternativa de trabalho temporariamente.

Suspensos **não aparecem** nos contadores nem nas tabelas. Aparecem apenas no rodapé do relatório como "Colaboradores suspensos do monitoramento".

---

## Thresholds resumidos

| Threshold | Valor | Decisão |
|---|---|---|
| Atraso entrada | > 15 min | Hugo |
| Saída antecipada | > 10 min | Hugo |
| Hora extra | > 10 min | Hugo |
| Intervalo curto | < 60 min | Hugo (regra interna Gran) |
| Intervalo longo | > 65 min | Hugo (regra interna Gran) |
| Janela proibida (manhã) | 11:00 — 13:00 | Hugo |
| Janela proibida (tarde) | 16:00 — 19:30 | Hugo |
| Pulou intervalo + jornada | > 6h | CLT |

---

**Mudanças nessas regras requerem aprovação do Hugo. Não inferir, não inventar.**
