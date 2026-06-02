# Template — WhatsApp privado · Cenário B · Dia EXCELENTE

**Quando usar:** nota individual > (média_individual + 5pp). Dia em que a pessoa superou seu próprio patamar.

**Para quem:** Sílvio OU Alyne — uma mensagem para cada encarregado que preencheu o turno do dia avaliado.

**Disparado por:** scheduled task diário (seg-sáb 13h20).

---

## Princípio do cenário

Reconhecer **especificamente** o que foi feito diferente e que elevou a nota. Sem fofice, sem "uau!", sem inflação. O reconhecimento real é dizer "esse é o nível que vocês conseguem entregar quando focam".

Mesmo nesse cenário, **mantém 1 ponto de ajuste** — mas com ângulo "pra continuar afiando", não "pra corrigir".

---

## Esqueleto

```
📩 Mensagem para registro — leia apenas durante seu horário de trabalho.

Boa tarde, {NOME_PRIMEIRO}. ✨

Passagem de Turno — {DATA_DD/MM}
Nota do dia: {NOTA_DIA}% 🟢

Hoje foi um dia muito acima da sua média e quero registrar isso. {PARÁGRAFO_RECONHECIMENTO_QUALIFICADO}

Pra continuar afiando amanhã, mantém esse mesmo nível no {AREA_AJUSTE}. {EXPLICACAO_CURTA_DO_QUE_AINDA_PODE_SUBIR}. Um bom exemplo seria:
   "{EXEMPLO_CONCRETO}"

Sua média da semana subiu pra {MEDIA_SEMANA}%. Tá entregando mais que ontem.
```

---

## Regras de preenchimento

### {PARÁGRAFO_RECONHECIMENTO_QUALIFICADO}

2-4 linhas. Mencionar **2 ou 3 itens específicos** que justificam a nota alta. Padrões aprovados:

- "O detalhamento das âncoras vermelhas e o resumo da noite com nome, horário e pendência específica — isso é o nível que faz a próxima equipe trabalhar melhor por causa de você."
- "Top 5 ruptura com causa, fotos das gôndolas com ângulo aberto, e o resumo da tarde com 1 fato útil. Três peças que separam um relatório de cumprimento de um relatório que ajuda mesmo."
- "Você escreveu o pior depto com a hipótese de causa, marcou as distâncias R$ certas nos dois turnos, e o resumo da noite veio com nome + horário + pendência. Esse é o relatório que a Mayara consegue acionar amanhã sem precisar te perguntar nada."

**Nunca usar:** "incrível!", "show de bola!", "uau, parabéns!", emoji de fogo 🔥, "arrasou".

### {AREA_AJUSTE}

Mesmo num dia excelente, escolher 1 área que ainda pode subir. Não é cobrança — é convite a manter o nível. Tom: "agora que você chegou aqui, dá pra subir mais um degrau".

Frases âncora:
- "mantém esse mesmo nível no campo Distância R$"
- "leva esse mesmo cuidado da Gran Mesa pra padaria"
- "replica esse padrão de fotos na cobertura dos perdedores"

### {EXEMPLO_CONCRETO}

Sempre que possível, mostrar como aquele detalhe especificamente ficaria bom. Mesmo no cenário excelente.

### {MEDIA_SEMANA}

Inclui "subiu pra X%" se realmente subiu vs semana passada. Se estável, dizer "está em X%". Se ainda em recuperação, dizer "começa a subir, X%".

---

## Exemplo completo

```
📩 Mensagem para registro — leia apenas durante seu horário de trabalho.

Boa tarde, Alyne. ✨

Passagem de Turno — 16/05
Nota do dia: 94% 🟢

Hoje foi um dia muito acima da sua média e quero registrar isso.
O detalhamento das âncoras vermelhas, o resumo da noite com nome
e horário específico, e as fotos da Gran Mesa Frontal com ângulo
aberto — esse é o nível que faz a próxima equipe trabalhar
melhor por causa de você.

Pra continuar afiando amanhã, mantém esse mesmo nível no campo
Distância R$ — hoje ainda apareceu uma confusão entre R$ e
percentual, vale conferir o label antes de preencher. Um bom
exemplo seria:
   "Distância 16h: R$ 754 abaixo do alvo."

Sua média da semana subiu pra 82%. Tá entregando mais que ontem.
```

---

## Quando NÃO usar este template

- Cards de teste (Hugo preenche): pular avaliação ou usar cenário A com nota "(teste, não conta na média)"
- Domingo/feriado com turno único: usar mesmo cenário mas mencionar "turno único hoje" no primeiro parágrafo
- Quarta-feira do encarregado de folga: não enviar mensagem nenhuma pra quem está de folga
