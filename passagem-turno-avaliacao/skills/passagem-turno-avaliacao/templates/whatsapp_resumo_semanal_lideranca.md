# Template — WhatsApp resumo semanal · Grupo [LIDERANÇA] Gran

**Quando usar:** quartas-feiras às 13h35, fechando o ciclo da semana qua-anterior → terça.

**Para onde:** grupo [LIDERANÇA] Gran no WhatsApp.

**Finalidade:** RH e demais líderes acompanharem a evolução agregada **sem expor individualmente** os encarregados Sílvio e Alyne. Dados frios, padrão observado em 1 frase.

**Disparado por:** scheduled task semanal (quarta 13h35).

---

## Princípio do resumo semanal

Este formato é diferente da mensagem privada diária. Aqui o público não é o encarregado avaliado — é o grupo de Liderança inteiro (Marize, Mayara, Hugo, RH, demais líderes de outras áreas).

**O que esse formato NUNCA faz:**
- Lista detalhes pessoais sobre Sílvio ou Alyne
- Mostra exemplos de mensagens privadas que foram enviadas
- Compara Sílvio vs Alyne como ranking
- Usa linguagem de cobrança ou denúncia

**O que esse formato FAZ:**
- Nota agregada por encarregado (média da semana)
- Delta vs semana anterior (↑ ↓ →)
- 1 padrão observável da semana (sem nomear individualmente o problema)
- Sinaliza que existe um sistema rodando

---

## Esqueleto

```
📊 Passagem de Turno — Semana {DATA_INICIO} a {DATA_FIM}

Sílvio: média {MEDIA_SILVIO}% ({N_AVALIACOES_SILVIO} avaliações) {DELTA_SILVIO}
Alyne: média {MEDIA_ALYNE}% ({N_AVALIACOES_ALYNE} avaliações) {DELTA_ALYNE}

{PADRÃO_OBSERVADO_DA_SEMANA}

Próxima atualização: quarta {DATA_PROXIMA}.
```

---

## Regras de preenchimento

### {DATA_INICIO} e {DATA_FIM}
Ciclo qua-anterior → terça. Formato `DD/MM`.

Exemplo: rodando quarta 20/05/2026 → fecha semana 13/05 a 19/05.

### {MEDIA_SILVIO} e {MEDIA_ALYNE}
Média aritmética simples das notas individuais do encarregado no período. Sem arredondamento agressivo — manter 1 casa decimal só se for relevante (ex: 81,5%). Se inteiro, sem decimal.

### {N_AVALIACOES_SILVIO} e {N_AVALIACOES_ALYNE}
Quantos cards do encarregado entraram na média. Cobre rotação de folga (quem trabalhou no domingo folgou na quarta seguinte) — não inflar.

### {DELTA_SILVIO} e {DELTA_ALYNE}
Comparação com semana anterior:
- ↑Xpp se subiu 1pp ou mais
- ↓Xpp se caiu 1pp ou mais
- → se variação ≤ 0,9pp (estabilidade)

Sem cor/emoji adicional além do símbolo.

### {PADRÃO_OBSERVADO_DA_SEMANA}
1 frase descritiva do padrão mais relevante observado nos 2 encarregados juntos. Não nomeia indivíduo. Não atribui causa. Apenas descreve o fato.

Padrões aprovados:

- "O ponto que mais apareceu na semana foi {CAMPO} — nas duas operações ainda vem genérico em parte dos dias."
- "{CAMPO} foi o ponto mais consistente positivo da semana — vem aparecendo bem em quase todos os dias."
- "A confusão entre R$ e percentual no campo Distância Alvo segue aparecendo — vale tooltip no Pipefy pra eliminar de vez."
- "Sem padrão recorrente esta semana. Pontuações estáveis, sem destaques positivos ou negativos significativos."

Se não houver padrão claro, **dizer que não há padrão** em vez de inventar. Honestidade > completude.

### {DATA_PROXIMA}
Próxima quarta-feira, formato `DD/MM`.

---

## Exemplo completo

```
📊 Passagem de Turno — Semana 13/05 a 19/05

Sílvio: média 84% (5 avaliações) ↑3pp
Alyne: média 79% (4 avaliações) →

O ponto que mais apareceu na semana foi o resumo da noite —
nas duas operações ainda vem genérico em parte dos dias.
Conversa direcionada nesse campo pode destravar 3-4pp de média.

Próxima atualização: quarta 27/05.
```

---

## Variações por contexto

### Semana com 1 encarregado em férias/atestado

```
📊 Passagem de Turno — Semana 13/05 a 19/05

Sílvio: média 84% (5 avaliações) ↑3pp
Alyne: em afastamento esta semana, retorna {DATA}.

[Padrão observado focado só no Sílvio]

Próxima atualização: quarta 27/05.
```

### Primeira semana de rodagem (sem comparação anterior)

```
📊 Passagem de Turno — Semana {INICIO} a {FIM}

Sílvio: média {X}% ({N} avaliações)
Alyne: média {Y}% ({N} avaliações)

Primeira semana com avaliação diária estruturada. A partir
de quarta {PROX}, passaremos a mostrar a evolução semana
a semana.

Próxima atualização: quarta {PROX}.
```

### Semana com queda relevante (alerta ao RH)

Quando algum dos dois cair 8pp+ vs semana anterior, **incluir linha curta sinalizando**, mas SEM nomear individualmente:

```
📊 Passagem de Turno — Semana 13/05 a 19/05

Sílvio: média 70% (5 avaliações) ↓10pp
Alyne: média 81% (4 avaliações) →

Uma das operações teve queda relevante esta semana. Conversa
1:1 já agendada pra próxima segunda.

Próxima atualização: quarta 27/05.
```

A frase "Uma das operações teve queda" preserva privacidade — o RH sabe que vai existir conversa, sem o grupo todo identificar quem.

---

## O que este template NUNCA faz

- Cita o conteúdo de mensagens privadas enviadas
- Mostra exemplos de "como Sílvio escreveu X"
- Atribui causa pessoal a queda ("Sílvio teve problema em casa")
- Faz ranking ("o melhor da semana foi Y")
- Usa emoji de coração, festa, fogo, palmas
- Promete ações públicas ("vamos cobrar mais")
