# Template — Sinais de Atenção

Estrutura do long_text que vai no campo `sinais_de_aten_o` (internal_id 429243739).

## Esqueleto

```
Padrões observados a partir do conteúdo do card {DD/MM/AAAA}:

1. {TÍTULO CURTO EM CAIXA ALTA}
   {Descrição neutra do padrão observado, citando os campos onde apareceu}
   {Hipótese de causa, se aplicável — sem julgamento de má-fé}

2. {...}

3. {...}

(Máximo 5 sinais por avaliação. Mais que isso vira ruído.)
```

## Categorias de sinais que entram

| Categoria | Quando flagar |
|---|---|
| **Estrutura repetida nas respostas** | Mesma fórmula de palavras em ≥3 campos de ação |
| **Ambiguidade de responsáveis** | Resp. Abertura/Tarde-Noite/Fechamento inconsistentes |
| **Pior departamento repetido** | Mesmo pior depto em 11h e 16h sem cruzamento com painel |
| **Padrão cruzado de cards** | "3º card consecutivo com X" — só se houver `/historico-passagem` rodado |
| **Limitação técnica** | Sem painel BI, sem histórico de fotos, datas de teste |
| **Distância Alvo R$ implausível** | Valores muito baixos/altos demais sem cruzamento possível |
| **Foto com sinais de repetição** | Comparação com cards anteriores indica reciclagem provável |
| **Inconsistência cruzada entre campos** | "Acima do alvo" vs distância negativa, etc. |
| **Alerta de Governança (v2)** | Regra ouro de ruptura, foto-fora-do-slot, pendência operacional sem foto, repetição cross-turno em âncora/ZV |
| **Perdedor cross-dia (v2)** | SKU perdedor pelo 2º+ dia sem mudança visível na foto — alerta progressivo |

## Regras de redação

1. **Tom neutro, não acusatório.** "Pode ser falta de modelo claro" em vez de "encarregado está enganando".
2. **Sempre citar dados concretos:** qual campo, qual valor, qual frase. Sem isso, vira opinião.
3. **Hipóteses devem ser plurais quando possível** ("Possíveis explicações: a, b, c") — evita acusar.
4. **Sinais que viram regra:** se algum padrão aparecer em múltiplos cards, considerar levar pra `/calibrar`.

## Exemplo real (card 10/05/2026)

```
Padrões observados a partir do conteúdo do card 10/05/2026:

1. ESTRUTURA REPETIDA NAS RESPOSTAS DE AÇÃO
   A Alyne usou em 4 campos diferentes uma estrutura parecida de
   "lista de palavras":
     • Resumo manhã: "organizado, abastecido, limpo"
     • Ação 11h: "abastecimento, precificação, limpeza, organização"
     • Ação 16h: "abastecimento, posicionamento, limpeza, organização"
     • Resolveu pendências: "Resolvi todas"
   Isso não significa má-fé — pode ser falta de modelo claro de
   "como é uma boa resposta". É uma oportunidade de instrução.

2. AMBIGUIDADE NOS RESPONSÁVEIS
   Alyne aparece como Responsável da Abertura E Responsável Tarde/Noite,
   mas Silvio Rouzan aparece como Responsável Fechamento.
   Possíveis explicações:
     • Foi turno único da Alyne e Silvio só assinou o fechamento
     • Houve troca de turno não registrada
     • Confusão no preenchimento dos campos de responsável
   Vale alinhar com a equipe como esses campos devem ser usados.
```
