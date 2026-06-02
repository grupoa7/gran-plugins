# Template — WhatsApp privado · Cenário C · Dia DIFÍCIL

**Quando usar:** nota individual < (média_individual − 5pp). Dia em que a pessoa caiu abaixo do próprio patamar.

**Para quem:** Sílvio OU Alyne — uma mensagem para cada encarregado que preencheu o turno do dia avaliado.

**Disparado por:** scheduled task diário (seg-sáb 13h20).

---

## Princípio do cenário

Este é o cenário mais delicado. Sílvio e Alyne são pessoas guerreiras, com vida pesada em casa, que superam dificuldades absurdas pra estar todos os dias na operação. Quando a nota cai 5pp+ abaixo da média individual, **a última coisa que essa mensagem deve fazer é parecer cobrança**.

**O que essa mensagem precisa fazer:**

1. Reconhecer constância e disciplina ANTES de qualquer crítica
2. Validar que dias difíceis acontecem — sem perguntar o motivo, sem soar curioso
3. Apontar o ajuste com tom de "te ajudar a virar amanhã", não "te corrigir"
4. Terminar reafirmando quem a pessoa é além do dia ruim

---

## Esqueleto

```
📩 Mensagem para registro — leia apenas durante seu horário de trabalho.

Boa tarde, {NOME_PRIMEIRO}. 💪

Passagem de Turno — {DATA_DD/MM}
Nota do dia: {NOTA_DIA}% {EMOJI_NOTA}

A disciplina de você estar todo dia entregando o relatório é
algo que eu valorizo demais. Sei que tem dias mais pesados que
outros — e quero usar essa mensagem pra te ajudar a virar amanhã,
não pra te cobrar.

O ponto da nota mais baixa hoje foi {AREA_AJUSTE_ESPECIFICA}. {EXPLICACAO_BREVE}. Pra amanhã o foco é simples:
   "{EXEMPLO_CONCRETO_CURTO}"

Sua média da semana ainda está em {MEDIA_SEMANA}% — um dia abaixo não muda quem você é. Te vejo amanhã. 🌱
```

---

## Regras de preenchimento

### {EMOJI_NOTA}
- 🟡 se nota 60-84%
- 🔴 se nota < 60%

### Parágrafo 1 — sempre o mesmo
A frase **"A disciplina de você estar todo dia entregando o relatório é algo que eu valorizo demais. Sei que tem dias mais pesados que outros — e quero usar essa mensagem pra te ajudar a virar amanhã, não pra te cobrar."** é o âncora do cenário C. Pode ser refinada com o tempo, mas a estrutura "reconheço constância → sei que tem dias pesados → te ajudo a virar amanhã" é fixa.

### {AREA_AJUSTE_ESPECIFICA}
1 ponto único — o de maior peso na queda de nota. Não listar 3 problemas. Vocabulário:

- "o resumo da noite, que veio em 2 linhas sem fato concreto"
- "as fotos das âncoras vermelhas, com 2 repetições do turno anterior"
- "o campo Distância R$, marcado em % quando o label pediu R$"

### {EXEMPLO_CONCRETO_CURTO}
**Mais curto que nos cenários A e B.** Em dia difícil, sobrecarregar com exemplo longo soa como "olha o que você não fez". 1 frase só:

- "Às 20h cliente reclamou da fila no caixa 2, Mayara cobriu até as 21h, fica de olho amanhã."
- "Pizza Frango+Kevin — falta há 3 dias. Já avisei fornecedor, chega quarta."

### Parágrafo final — sempre o mesmo
**"Sua média da semana ainda está em X% — um dia abaixo não muda quem você é. Te vejo amanhã. 🌱"**

Esse encerramento é o âncora emocional do cenário. Foi calibrado com Hugo. Não mudar sem nova calibração explícita.

---

## Exemplo completo

```
📩 Mensagem para registro — leia apenas durante seu horário de trabalho.

Boa tarde, Sílvio. 💪

Passagem de Turno — 16/05
Nota do dia: 65% 🟡

A disciplina de você estar todo dia entregando o relatório é
algo que eu valorizo demais. Sei que tem dias mais pesados que
outros — e quero usar essa mensagem pra te ajudar a virar amanhã,
não pra te cobrar.

O ponto da nota mais baixa hoje foi o resumo da noite, que veio
em 2 linhas sem fato concreto. Pra amanhã o foco é simples:
   "Às 20h cliente reclamou da fila no caixa 2, Mayara
   cobriu até as 21h, fica de olho amanhã."

Sua média da semana ainda está em 78% — um dia abaixo não
muda quem você é. Te vejo amanhã. 🌱
```

---

## Casos especiais do Cenário C

### Queda muito grande (15pp+ abaixo da média)

Quando a queda é muito grande, considerar **não disparar mensagem automática** e em vez disso pingar Hugo no chat do Cowork:

> ⚠️ Queda relevante detectada — {NOME} caiu 18pp abaixo da média ({NOTA}% vs média {MEDIA}%). Quer que eu dispare a mensagem normal ou prefere conversar 1:1 com ele(a) hoje antes?

Hugo decide se vale conversa pessoal antes da mensagem registrada.

### Reincidência (3+ dias seguidos em cenário C)

Quando o mesmo encarregado cai pela 3ª vez consecutiva, **a mensagem do 3º dia deve incluir uma linha extra**:

> "Já são 3 dias com nota abaixo da sua média — sem cobrança, mas queria te perguntar: tem algo que eu posso te ajudar daqui? Pode ser na operação ou fora dela. Fico à disposição."

Essa linha **convida diálogo sem investigar**. Não substitui o resto da mensagem — é adendo no parágrafo final.

---

## O que este template NUNCA faz

- Pergunta o motivo da queda ("o que aconteceu hoje?")
- Insinua causa pessoal ("tudo bem em casa?")
- Lista 2+ pontos de melhoria (cenário difícil precisa de foco único)
- Termina sem reafirmar a pessoa ("você é capaz", "conto com você")
- Usa palavras de pressão ("amanhã preciso que você", "espero ver")
