# Template — Recomendação ao Líder

Estrutura do long_text que vai no campo `recomenda_o_ao_l_der` (internal_id 429243740).

## Esqueleto

```
PRIORIDADE DA SEMANA: {1 frase curta sobre o ponto principal}

Conversa com {nome encarregado A}:
  • {Tópico principal a abordar}
  • {Exemplo concreto pra ilustrar}
  • {Pergunta de calibração: "como pretende fazer diferente amanhã?"}

Conversa com {nome encarregado B}:
  • {idem}

ALERTA DE GOVERNANÇA (se aplicável):
  • {Inconsistência grave detectada — regra ouro de ruptura, repetição
    cross-dia em foto âncora, pendência operacional sem foto, etc.}
  • {Sugestão objetiva de correção pra próximo card}

CALIBRAÇÃO DO SISTEMA (se aplicável):
  • {Algo que esta avaliação revelou sobre a rubrica — sugestão de
    ajuste no doc CRITERIOS pra ficar mais justa ou objetiva}
```

## Quando incluir a seção "ALERTA DE GOVERNANÇA" (v2 — adicionada 17/05/2026)

Sempre que detectar uma das inconsistências graves:
- **Regra ouro de ruptura** — menção de ruptura em qualquer campo + "0 itens" declarado no campo próprio
- **Repetição cross-turno em foto âncora ou Zero Venda** — nota 0 automática + alerta de tom progressivo se for reincidência
- **Pendência operacional declarada sem foto correspondente** — quem pegar o relatório no dia seguinte não sabe o que falta
- **"Há Pendências = Não" + comentários do dia citam pendências** — incoerência grave entre campos
- **Foto-fora-do-slot** (screenshot de WhatsApp ruptura no slot de foto âncora sem declaração correta no campo)

Se não houver inconsistência grave, **remover a seção** (não deixar vazia).

## Quando incluir a seção "CALIBRAÇÃO DO SISTEMA"

Apenas quando, durante a avaliação, você descobrir:
- Regra do CRITERIOS que está pegando casos injustamente
- Palavra/frase nova que merece entrar na "Lista de respostas pouco específicas"
- Bug operacional novo

Se não houver descoberta de calibração, **remover a seção** (não deixar vazia).

## Regras de redação

1. **Prioridade da semana = 1 frase curta.** Se ela tem ≥2 linhas, está difusa demais.
2. **Cada conversa tem 3 partes:** tópico + exemplo + pergunta de calibração.
3. **Pergunta de calibração:** sempre aberta, não-acusatória. "Como você escreveria diferente amanhã se…?" funciona melhor que "Por que você fez X?".
4. **Se for turno único:** uma única seção de conversa, omitir a segunda.

## Exemplo real (card 10/05/2026 — Alyne)

```
PRIORIDADE DA SEMANA: ensinar como é uma "boa resposta" antes do
primeiro card real do início oficial.

Conversa com Alyne Bittencourt:
  • Mostrar 2 exemplos concretos de respostas curtas mas específicas:
    - Vaga: "Bom abastecimento"
    - Boa: "Repor melancia até 11h30, conversar com Pedro"
  • Explicar que o objetivo de cada campo de ação é deixar registrado
    O QUE foi feito (ou vai ser feito), PRA QUEM, QUANDO — pra qualquer
    pessoa que pegar o relatório no dia seguinte entender sem precisar
    perguntar.
  • Pergunta de calibração: "Como você escreveria diferente amanhã se
    o pior departamento de novo for Legumes e Granjeiros?"
  • Alinhar como ela quer usar os campos Responsável Tarde/Noite e
    Responsável Fechamento.

CALIBRAÇÃO DO SISTEMA (registrado no doc CRITERIOS):
  • Regra removida: penalidade do checkbox "Li as Pendências" quando
    a fase 2 declara "Há Pendências = Não". O checkbox é obrigatório
    no template — penalizar marca obrigatória é injusto.
```
