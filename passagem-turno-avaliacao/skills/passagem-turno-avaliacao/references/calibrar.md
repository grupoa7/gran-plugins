# Workflow `/calibrar`

Comando para Hugo registrar discordância de uma avaliação, ou aprendizado livre que deve atualizar o doc CRITERIOS.

## Quando este workflow é acionado

Hugo digita `/calibrar` seguido de texto livre, ou frases como:
- "calibra a rubrica: …"
- "discordo da avaliação do card X porque …"
- "adiciona à lista de frases gerais: …"
- "muda a regra de coerência cruzada de Y"

## Pré-requisitos

1. Ler o doc canônico CRITERIOS antes de propor alteração
2. Ler `references/notas_operacionais.md` se o feedback for sobre bug operacional

## Workflow

### Passo 1 — Classificar o tipo de calibração

Identifique uma das categorias:

| Categoria | O que muda no doc CRITERIOS (numeração v2) |
|---|---|
| **Mudança de vocabulário ou princípio cultural** | Seção 2 (Vocabulário aprovado vs rejeitado + princípios) |
| **Mudança na escala universal de fotos (0-3)** | Seção 4 (Escala universal) |
| **Mudança em descritor por categoria de foto** | Seção 5 (5.1 Âncoras, 5.2 ZV, 5.3 Perdedores, 5.4 Balcões, 5.5 Pendências/Rupturas) |
| **Mudança em peso/total possível de etapa** | Seção 6 (Inventário por etapa) |
| **Mudança em escala de long_text** | Seção 7 |
| **Nova frase em "respostas pouco específicas"** | Seção 7 (subseção referente à lista) |
| **Mudança em peso de number/radio/select** | Seção 8 |
| **Mudança em regra de coerência cruzada (inclui regra ouro de ruptura)** | Seção 9 |
| **Mudança em faixas de nota ou cálculo** | Seção 10 |
| **Mudança no template de output da fase 5** | Seção 11 (templates dos 4 long_texts + Alerta de Governança) |
| **Bug operacional ou workaround** | `references/notas_operacionais.md` (não CRITERIOS) |
| **Discordância pontual sem regra nova** | Apenas registrar no log; não muda doc |

Se Hugo passar texto ambíguo, perguntar a categoria.

### Passo 2 — Propor a edição

Apresentar pra Hugo:
1. **O que vou mudar:** trecho exato antes/depois
2. **Onde:** seção do doc
3. **Justificativa:** com base no que Hugo disse

Esperar **OK explícito** antes de aplicar. Sem alteração silenciosa do doc.

### Passo 3 — Aplicar a edição

Editar o arquivo canônico (sem sufixo `_v*` no nome):
```
/Users/hugogusmao/Documents/Claude/Projects/[GRAN] Passagem de Turno/CRITERIOS_AVALIACAO_FASE5.md
```

**ATENÇÃO** — aprendizado 18/05/2026: NUNCA salvar a nova versão como `_v3.md` ou nome alternativo paralelo. Editar o arquivo canônico in-place. Se for mudança grande que mereça preservar versão anterior, copiar o arquivo atual pra `.archive-DDMMAAAA.md` ANTES de editar o canônico — nunca deixar 2 arquivos ativos com nomes diferentes.

**Sempre atualizar:**
- Bumpar a data de "Última atualização" no topo
- Adicionar entrada no "Histórico de calibrações" (seção 10) com:
  - Data (DD/MM/YYYY)
  - Tipo de calibração
  - Resumo curto do que mudou (1 linha)
  - Motivo (1 linha)

### Passo 4 — Registrar no log de calibrações

Arquivo: `/Users/hugogusmao/Documents/Claude/Projects/[GRAN] Passagem de Turno/calibracoes-passagem-turno.md`

Se não existir, criar com cabeçalho:
```markdown
# Log de Calibrações — Skill Passagem de Turno

Histórico cronológico de todas as calibrações solicitadas por Hugo.
```

Adicionar entrada:
```markdown
## DD/MM/YYYY — Calibração #N

**Categoria:** {tipo}
**Origem:** {card que motivou, se houver}
**Mudança:** {antes → depois}
**Motivo (Hugo):** {citação literal do que ele falou}
**Seção do CRITERIOS:** {qual seção}
```

### Passo 5 — Confirmar e oferecer próximo passo

Mensagem final:

```
✅ Calibração #N registrada.

Mudança aplicada em:
  → CRITERIOS_AVALIACAO_FASE5.md (seção {X})
  → calibracoes-passagem-turno.md (log)

Próxima avaliação já vai usar a regra nova.

Quer revisar a avaliação do card {Y} aplicando a regra atualizada? (s/n)
```

Se for discordância pontual (sem regra nova): só registra no log, sem editar CRITERIOS.

## O que NÃO entra em `/calibrar`

- Mudanças no template do pipe (campos da fase 5, condicionais, etc.) — essas exigem aprovação campo a campo via mexida direta no Pipefy.
- Mudanças na lógica de ler/escrever (workflows). Isso é alteração da skill em si, não calibração.
- Comentários genéricos sem ação clara ("achei meio chato") — pedir pra Hugo especificar.

## Sinais de que uma calibração está madura

Acumular calibrações estabiliza a rubrica. Se nas últimas **5 avaliações consecutivas Hugo não pediu nenhuma calibração**, a skill está madura. Esse é um bom momento pra:
- Reduzir a frequência de notas_operacionais
- Considerar promover algumas regras pra inegociáveis (seção 1 do SKILL.md)
- Avaliar se chegou hora de automatizar partes (export pro Super Gran automático, notificação WhatsApp programada, etc.)
