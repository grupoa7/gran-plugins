# Loop de Melhoria Contínua da Skill

A skill Passagem de Turno melhora a cada rodada. Este documento descreve **como** ela melhora, **quem** decide o que vira regra nova, e **onde** as mudanças são registradas.

## Princípio: nada vira regra sem aprovação explícita do Hugo

A skill **propõe** candidatos a calibração. Hugo **aprova ou rejeita** com 1 emoji no chat do Cowork. Apenas com OK explícito, a regra entra em `references/criterios.md` ou no doc canônico `CRITERIOS_AVALIACAO_FASE5.md`.

Nunca atualizar automaticamente. Sempre perguntar.

---

## Mecanismo 1 — Candidato de calibração (a cada avaliação)

Ao final de cada `/avaliar-passagem` ou rodada do ritual diário, a skill faz uma pergunta interna: **"detectei algo que merece virar regra nova?"**

Critérios pra acionar:

1. Padrão observado pela 3ª vez consecutiva no mesmo encarregado
2. Resposta nova que não estava na "lista de respostas pouco específicas" mas claramente é genérica
3. Bug do Pipefy não documentado em `notas_operacionais.md`
4. Caso atípico que a rubrica atual não cobre bem (ex: nota saiu artificialmente alta/baixa)
5. Calibração de threshold (ex: "o cenário C está disparando muito — talvez 5pp seja sensível demais")

Quando há candidato, **incluir no fim da resposta no chat do Cowork** (não no card Pipefy, não no WhatsApp dos encarregados):

```
💡 Candidato de calibração detectado:

{DESCRIÇÃO_CURTA_DO_PADRÃO_OU_REGRA}

Como ficaria a regra nova:
"{TEXTO_PROPOSTO_PRA_ENTRAR_NA_RUBRICA}"

Reage com:
👍 — aprova, eu atualizo o doc CRITERIOS
👎 — descarta
🤔 — me pergunte mais antes de decidir
```

Se Hugo reagir 👍, executar `/calibrar` automaticamente com o texto proposto. Se 👎, registrar em `references/calibracoes_rejeitadas.md` (cria se não existir) com motivo curto. Se 🤔, abrir conversa no chat.

**Limite:** máximo 1 candidato por rodada. Se houver 2+ detecções, apresentar só o mais relevante. Volume vira ruído.

---

## Mecanismo 2 — Revisão de saúde da skill (a cada 10 rodadas)

Toda 10ª rodada do ritual diário, a skill gera um **relatório de saúde** automático no chat do Cowork (não dispara WhatsApp). Conteúdo:

```
📋 Saúde da skill — Rodadas {N-9} a {N}

Critérios que saturaram (todos tiraram 100% nas últimas 10):
- {LISTA_OU_NENHUM}

Critérios que falharam consistentemente (média < 40%):
- {LISTA_OU_NENHUM}

Correlação score ↔ realidade da loja:
- Notas altas em dias com {EVENTO_LOJA_NEGATIVO}: {N_CASOS}
- Notas baixas em dias com {EVENTO_LOJA_POSITIVO}: {N_CASOS}

Calibrações aceitas neste bloco: {N}
Calibrações rejeitadas: {N}

Sugestões automáticas pra revisar:
1. {SUGESTAO_1}
2. {SUGESTAO_2}
3. {SUGESTAO_3}

Quer revisar agora (~15 min) ou agendar pra depois?
```

Hugo decide o momento. Se ele pedir "agendar", criar lembrete pra próxima sexta às 17h (fim de semana operacional).

---

## Mecanismo 3 — Captura de feedback no chat (sempre que Hugo discordar)

Quando Hugo discordar de uma avaliação no chat (ex: "essa nota tá muito alta", "o ponto crítico que você apontou tá errado"):

1. **NÃO refazer a avaliação isoladamente** — explicar primeiro o raciocínio aplicado
2. Identificar a discordância: é erro de aplicação OU calibração da regra?
3. Se aplicação: corrigir e mostrar diff
4. Se calibração: propor regra nova via Mecanismo 1
5. Sempre confirmar antes de mexer no doc CRITERIOS

**Nunca aplicar mudança "silenciosa" no doc canônico em resposta a desabafo do Hugo.**

---

## Onde as mudanças são registradas

| Tipo de aprendizado | Vai pra... |
|---|---|
| Regra nova de pontuação | `CRITERIOS_AVALIACAO_FASE5.md` (doc canônico, raiz do projeto) |
| Frase que vira "pouco específica" | `CRITERIOS_AVALIACAO_FASE5.md` → seção "termos-flag" |
| Bug do Pipefy ou workaround técnico | `references/notas_operacionais.md` |
| Calibração de threshold de cenário | `templates/config.md` |
| Padrão cruzado entre cards | `references/historico.md` → seção "padrões persistentes" |
| Mensagem que ressoou bem com encarregado | Adicionar exemplo positivo no template apropriado |
| Mensagem que machucou ou caiu mal | `references/calibracoes_rejeitadas.md` + ajustar template |

---

## Métricas de saúde do loop

A cada relatório de saúde (10 rodadas), monitorar:

- **Taxa de aceitação de candidatos** — sweet spot: 30-60%. Abaixo: skill propõe pouco. Acima: filtro de candidato fraco.
- **Tempo médio entre rodada e revisão de saúde** — alvo: < 7 dias
- **Volume de discordâncias do Hugo no chat** — declínio ao longo do tempo = skill calibrando
- **Reincidência de mesmo ponto crítico** — se aparece em 3+ avaliações consecutivas no mesmo encarregado, escalar pra Mecanismo 1 automaticamente

---

## Casos especiais

### Hugo viajando, sem conexão

Mecanismo 1 acumula candidatos em `references/calibracoes_pendentes.md` até Hugo voltar. Não bloqueia o ritual diário — só não aplica regras novas.

### Discordância de Marize/Mayara/RH (não Hugo)

Por enquanto, **só Hugo aprova mudanças nos critérios**. Se Marize/Mayara comentarem algo no grupo de Liderança, Hugo decide se levanta como candidato no Cowork.

### Skill autoanalisando mensagens privadas

Periodicamente (a cada 20 rodadas), a skill deve gerar **autorrevisão dos templates A/B/C**:

> "Olhando as últimas 20 mensagens disparadas, percebi que o cenário A está aparecendo em 85% dos dias. Provavelmente os thresholds estão largos demais. Sugestão: apertar pra ±3pp em vez de ±5pp. Aprova?"

Esse mecanismo evita que o sistema vire previsível ("é sempre cenário A, ninguém presta atenção mais").
