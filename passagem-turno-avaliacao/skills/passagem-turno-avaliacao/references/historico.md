# Workflow `/historico-passagem`

Comando para mostrar histórico de avaliações passadas e detectar padrões cruzados entre cards.

## Quando este workflow é acionado

Hugo digita `/historico-passagem` (com ou sem parâmetros), ou frases como:
- "histórico de passagem de turno"
- "como tá indo o Silvio nas últimas avaliações?"
- "evolução da nota da loja"
- "padrões recorrentes da Alyne"

Parâmetros opcionais:
- `período=últimos N dias` (default: 30)
- `encarregado="Nome"` (filtra por pessoa)
- `só-padrões` (mostra só sinais cruzados, sem listar cards)

## Fontes de dados

| O que ver | Onde ler |
|---|---|
| Notas históricas + nomes | XLSX acumulativo: `{workspace}/passagem-turno-superGran.xlsx` |
| Texto das avaliações passadas | Cards da fase 5 com Card Pronto marcado (via GraphQL Pipefy) |
| Calibrações aplicadas | `{workspace}/calibracoes-passagem-turno.md` |

## Workflow

### Passo 1 — Carregar dados

```bash
python scripts/adicionar_excel.py --ler-historico --periodo 30
```

Retorna estrutura:
```json
{
  "total_cards": N,
  "encarregados": ["Alyne Bittencourt", "Silvio Rouzan", ...],
  "media_loja_periodo": 65,
  "tendencia": "subindo" | "estavel" | "caindo",
  "ultimos_5_cards": [...]
}
```

### Passo 2 — Detectar padrões cruzados

Olhar nos últimos 5-10 cards:

**Padrões por encarregado:**
- Mesma falha em ≥3 cards consecutivos (ex: ação sempre genérica em Carnes)
- Mesma virtude em ≥3 cards consecutivos (ex: resumo da noite sempre específico)
- Tendência de %: subindo / caindo / estável

**Padrões da loja:**
- Pior departamento que se repete (sinal de problema estrutural, não pontual)
- SKU recorrente em Zero Vendas (sinal de abastecimento quebrado)
- Distância Alvo R$ sistematicamente errada (sinal de não conferir painel)

**Padrões de repetição cross-card (cross-check da régua v2):**
- Fotos visualmente idênticas em cards consecutivos (repetição cross-turno = nota 0 automática pela v2; repetição cross-dia em balcão tolera 3 dias)
- Long_texts copiados-e-colados entre cards
- Pior depto que não muda nunca (pode indicar problema estrutural — ou erro de cópia)
- Perdedores que ficam dias seguidos sem mudança visível na foto (alerta progressivo da v2: dia 2 leve, dia 3 médio, dia 4+ forte + escalação)
- Ruptura mencionada sem campo próprio preenchido (regra ouro — automação WhatsApp não dispara)

### Passo 3 — Apresentar relatório

Estrutura do output (no chat, formatado):

```
═══ HISTÓRICO PASSAGEM DE TURNO — últimos {N} dias ═══

📊 RESUMO
  • {N} cards avaliados
  • Média da loja: {%}
  • Tendência: {↑ subindo / ↔ estável / ↓ caindo}
  • Melhor card do período: {data, encarregado, %}
  • Pior card do período: {data, encarregado, %}

▸ POR ENCARREGADO

  {Nome A} — {N} cards
    Média individual: {%}
    Tendência: {↑/↔/↓}
    Padrão mais frequente (positivo): {observação}
    Padrão mais frequente (a aperfeiçoar): {observação}

  {Nome B} — {N} cards
    ...

▸ PADRÕES CRUZADOS DETECTADOS

  1. {Padrão observado} — apareceu em {N} cards
     Hipótese: {explicação}
     Sugestão: {ação prática}

  2. ...

▸ SUGESTÕES DE CALIBRAÇÃO

  Se algum padrão for novo e merecer regra estruturada,
  oferecer rodar /calibrar com a sugestão.
```

### Passo 4 — Oferecer ações de follow-up

No final do relatório, sugerir:
- **Quer detalhar um encarregado?** "Hugo, posso aprofundar a análise do {Nome}"
- **Algum padrão merece virar regra?** "Hugo, o padrão #1 aparece em 5 cards — quer formalizar uma regra de coerência cruzada via /calibrar?"
- **Exportar relatório?** "Posso gerar um Excel com a tendência dos últimos 30 dias se você quiser levar pra reunião"

## Limites e cuidados

- **Nunca usar como auditoria sem aviso ao avaliado.** Histórico vira monitoria injusta se Hugo só usar pra "pegar" o encarregado.
- **Padrões baseados em <3 cards não são padrões** — são coincidências. Não reportar como padrão.
- **Tendências baseadas em <7 dias** são ruído. Reportar com cautela.
- **Sem painel BI disponível pra um card** = aquele card tem confiabilidade reduzida; flagar.
- **Não comparar encarregados diretamente** sem contexto. "Alyne tira 70% e Silvio 50%" sem nota explicativa cria injustiça (Silvio pode ter pegado dias mais difíceis).

## Quando o histórico não é suficiente

Se Hugo pedir `/historico-passagem` com menos de 5 cards no log:
- Não inventar tendências
- Reportar: "Ainda temos só {N} cards avaliados — pouco pra detectar padrões com confiança. Volta a perguntar depois de {5-N} cards a mais."
- Listar os cards existentes com nota, sem cruzamentos.
