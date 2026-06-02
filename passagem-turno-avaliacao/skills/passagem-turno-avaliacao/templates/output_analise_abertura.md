# Template — Análise — Encarregado Abertura

Estrutura do long_text que vai no campo `coment_rio_da_l_der_de_loja_orienta_o_feedback` (internal_id 421632739).

## Esqueleto

```
▸ {NOME_ENCARREGADO_ABERTURA} — {pts}/{max} ({pct}%)

   Pontuação por etapa:
   {ICONE} Etapa 1 — Formulário Inicial:    {pts}/{max}  ({pct}%)
   {ICONE} Etapa 2 — Painel 11h:           {pts}/{max}  ({pct}%)
   {ICONE} Etapa 3 — Passagem de Turno:    {pts}/{max}  ({pct}%)
   {marcar a etapa MELHOR e a PIOR com "← MELHOR" / "← onde pode aperfeiçoar mais"}

   ✓ O que foi bem feito:
     • {observação concreta, citando o campo + o que viu}
     • {...}
     • {3 a 5 itens, todos positivos e concretos}

   → O que pode aperfeiçoar:
     • {observação} → exemplo concreto de como ficaria melhor
     • {...}
     • {3 a 5 itens, cada um com exemplo de melhoria}
```

## Ícones por faixa de % (régua v2 — calibrada 17/05/2026)

- `✓` se ≥ 85% (padrão Gran de excelência)
- `→` se 70-84% (bom com espaço pra crescer)
- `!` se 50-69% (mediano, precisa subir o nível)
- `⚠` se < 50% (atenção imediata)

## Regras de redação

1. **Cada item das listas começa com fato neutro do que foi preenchido no card.**
2. **Em "O que pode aperfeiçoar":** sempre incluir um **exemplo concreto de boa resposta** após "→". Sem o exemplo, o apontamento vira crítica sem caminho.
3. **Não usar "termo-flag", "teatro", "gaming"** — proibido. Veja seção 2 do CRITERIOS.
4. **Citar valor numérico de perda quando aplicável:** "ação genérica (−2 pts)" — ajuda o encarregado entender a magnitude.
5. **Nunca usar pontuação > max possível.** Sanity check antes de escrever.

## Exemplo real (card 10/05/2026 — Alyne)

```
▸ ALYNE BITTENCOURT — 26/48 (54%)

   Pontuação por etapa:
   → Etapa 1 — Formulário Inicial:     5/8   (63%)
   ! Etapa 2 — Painel 11h:           12/23  (52%)  ← onde pode aperfeiçoar mais
   → Etapa 3 — Passagem de Turno:     9/17  (53%)

   ✓ O que foi bem feito:
     • Todas as fotos obrigatórias do turno presentes (3 do form +
       4 fotos de setor no Painel 11h + 6 fotos de setor na Passagem)
     • Foto do Painel de Guerra 11h presente como evidência
     • 1 âncora vermelha declarada às 11h coerente com 1 foto registrada
     • 3 fotos de Zero Vendas presentes na fase Painel 11h
     • Conversa com próximo encarregado confirmada

   → O que pode aperfeiçoar:
     • Resumo da manhã "Tudo organizado, abastecido e limpo" funciona
       como descrição geral, mas serviria igual pra qualquer dia da
       semana. Mais útil seria citar 1-2 fatos do dia, como:
       "Movimento alto de morango desde 9h, abastecimento do açougue
       terminou às 10h30."
     • Ação sobre Legumes e Granjeiros (pior depto 11h) lista 4 áreas
       mas não diz O QUE fazer em cada uma. Fica mais útil quando
       vira ação concreta: "Repor melancia inteira até 11h30,
       conversar com José Silva da loja antes do pico do almoço."
```
