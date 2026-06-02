# Template — WhatsApp privado · Cenário A · Dia NORMAL

**Quando usar:** nota individual dentro da faixa esperada — entre (média_individual − 5pp) e (média_individual + 5pp).

**Para quem:** Sílvio OU Alyne — uma mensagem para cada encarregado que preencheu o turno do dia avaliado.

**Disparado por:** scheduled task diário (seg-sáb 13h20), avaliando card do dia anterior.

---

## Estrutura obrigatória

1. Disclaimer fixo (linha 1)
2. Saudação + emoji 🌱 (cenário normal)
3. Linha de identificação (data + nota)
4. Parágrafo de reconhecimento (1 ponto forte específico do card)
5. Parágrafo de evolução (1 ajuste com exemplo de "como ficaria bom")
6. Linha de média da semana

---

## Esqueleto

```
📩 Mensagem para registro — leia apenas durante seu horário de trabalho.

Boa tarde, {NOME_PRIMEIRO}. 🌱

Passagem de Turno — {DATA_DD/MM}
Nota do dia: {NOTA_DIA}% {EMOJI_NOTA}

{PARÁGRAFO_RECONHECIMENTO}

Pra evoluir amanhã, o foco é {AREA_AJUSTE}. {EXPLICACAO_CURTA_DO_PROBLEMA}. Um bom exemplo seria:
   "{EXEMPLO_CONCRETO_DE_COMO_FICARIA_BOM}"

Sua média da semana: {MEDIA_SEMANA}%.
```

---

## Regras de preenchimento

### {NOME_PRIMEIRO}
Primeiro nome apenas. "Sílvio" ou "Alyne".

### {EMOJI_NOTA}
- 🟢 se nota ≥ 85%
- 🟡 se nota 70-84%
- 🔴 se nota < 70% (mas se a nota está nessa faixa, provavelmente é Cenário C — verificar)

### {PARÁGRAFO_RECONHECIMENTO}
1 ponto forte específico do card avaliado, com vocabulário do painel-guerra. Padrões aprovados:

- "Quero te dizer que o seu {CAMPO_X} ficou muito bem feito hoje. {EXPLICACAO_POR_QUE_AJUDA_PROXIMO_TURNO}. Esse cuidado faz diferença."
- "O {CAMPO_X} de hoje veio redondo — {DETALHE_QUE_BRILHOU}. É exatamente o que o próximo turno precisa pra agir."
- "Acabamos de olhar o card de ontem e o {CAMPO_X} entrou ligado: {DETALHE}. Continua nesse ritmo."

**Nunca usar elogio genérico** ("parabéns pelo trabalho!", "você tá indo bem"). Sempre nomear o campo + por que aquilo ajuda quem vem depois.

### {AREA_AJUSTE} e {EXPLICACAO_CURTA_DO_PROBLEMA}
1 ponto único — o mais relevante do dia, não 3 pequenos. Vocabulário aprovado:

- "no resumo da noite. Hoje veio genérico ('movimento constante de clientes')"
- "no detalhamento das âncoras vermelhas. Hoje vieram sem a causa de cada produto faltando"
- "na distinção entre R$ e %. O campo Distância Alvo 16h pediu R$ mas você marcou %."

### {EXEMPLO_CONCRETO_DE_COMO_FICARIA_BOM}
Exemplo curto, mostrando exatamente o output esperado. Sempre que possível, puxar de algo que **o próprio encarregado já fez** em cards anteriores. Se não houver, usar exemplo genérico do tipo:

- Resumo da noite: "Às 19h faltou banana prata, falei com Joelma da padaria, ela disse que repor só na terça."
- Top 5 ruptura: "Pizza Frango+Kevin — falta há 3 dias. Já falei com fornecedor, chega quarta."
- Distância Alvo: "R$ 754 abaixo do alvo das 16h."

### {MEDIA_SEMANA}
Média móvel das últimas N avaliações do mesmo encarregado (mínimo 3, máximo 7).

---

## Exemplo completo

```
📩 Mensagem para registro — leia apenas durante seu horário de trabalho.

Boa tarde, Sílvio. 🌱

Passagem de Turno — 16/05
Nota do dia: 82% 🟡

Quero te dizer que o seu top 5 de ruptura ficou muito bem feito
hoje. Cada produto com a causa identificada é exatamente o que o
próximo turno precisa pra agir. Esse cuidado faz diferença.

Pra evoluir amanhã, o foco é no resumo da noite. Hoje veio
genérico ("movimento constante de clientes"). Um bom exemplo
seria:
   "Às 19h faltou banana prata, falei com Joelma da
   padaria, ela disse que repor só na terça."

Sua média da semana: 78%.
```

---

## Vocabulário proibido neste template

- "Falhou", "errou", "deixou a desejar"
- "Precisamos melhorar" (sem o sujeito claro = soa coletivo, não específico)
- "Espero mais de você", "esperava mais"
- Comparações com a outra pessoa ("a Alyne fez melhor", "diferente do Sílvio")
- Linguagem motivacional vazia ("você consegue!", "vai dar tudo certo!")

## Vocabulário aprovado neste template

- "Evoluir", "afiar", "subir o nível", "destravar"
- "Faz diferença", "ajuda o próximo turno", "entrou ligado"
- "Pra continuar afiando", "pra ir um passo além"
