# Critérios de Avaliação — referência da skill

> **IMPORTANTE — fonte canônica:** A rubrica completa, viva e calibrada está em:
> `/Users/hugogusmao/Documents/Claude/Projects/[GRAN] Passagem de Turno/CRITERIOS_AVALIACAO_FASE5.md`
>
> Esta skill **sempre lê o doc canônico** antes de qualquer avaliação. Não duplica conteúdo aqui para evitar drift entre cópias.

## Por que apontar em vez de copiar

- O doc CRITERIOS é atualizado a cada calibração que Hugo pedir (comando `/calibrar`)
- Se a skill tivesse cópia interna, ela ficaria desatualizada
- Manter 1 fonte de verdade evita conflitos

## O que a skill deve consultar no doc canônico (régua v2)

| Quando | Consultar seção |
|---|---|
| Antes de pontuar fotos | Seção 4 (Escala universal 0-3) + Seção 5 (Descritores por categoria — Âncoras, ZV, Perdedores, Balcões, Pendências/Rupturas) |
| Antes de calcular total de pontos por etapa | Seção 6 (Inventário recalibrado: cada foto vale 3 pts) |
| Antes de avaliar long_texts de ação | Seção 7 (Escala 0-2 mantida da v1) |
| Antes de pontuar number/radio/select | Seção 8 (escala 0-1; exceção: "Precisou sinalizar RUPTURA?" peso 3) |
| Pra decidir tom do output | Seção 2 (Vocabulário aprovado vs rejeitado + princípios cultural-operacionais) |
| Pra aplicar coerência cruzada (incluindo REGRA OURO de ruptura) | Seção 9 (Regras de coerência cruzada) |
| Pra calcular notas % e classificar faixas | Seção 10 (Como nasce a nota + faixas calibradas ≥85/70-84/50-69/<50) |
| Pra estruturar os 4 long_texts da fase 5 | Seção 11 (Templates dos 4 long_texts + Alerta de Governança) |

## Quando o doc precisa ser atualizado

Sempre que Hugo discordar de uma avaliação ou pedir mudança de regra, abrir `references/calibrar.md` desta skill — ela orquestra a atualização do doc canônico + registra no log de calibrações.

## Resumo executivo da rubrica v2 (caso urgência)

Se por algum motivo o doc canônico estiver inacessível, este resumo dá pra rodar uma avaliação de fallback:

- **3 eixos:** Evidenciar (fotos — peso ALTO na v2), Corrigir (long_texts de ação), Alcançar Objetivos (numbers/radios)
- **5 etapas:** Form Inicial (11 pts) + Painel 11h (~51) + Passagem (~28) + Painel 16h (~51) + Fechamento (~21) = ~162 pts max típico
- **Por tipo de campo (v2):** Foto 0/1/2/3 (4 níveis, descritores por categoria), Long_text de ação 0/1/2 (escala v1 mantida), Number/Radio/Select 0/1 (exceção: "Precisou sinalizar RUPTURA?" peso 3), Checkbox/Datetime 0/1
- **Faixas calibradas (cards 14-16/05):** ≥85% padrão Gran · 70-84% bom com espaço · 50-69% mediano · <50% atenção imediata
- **Nota Loja = soma ponderada** = pontos ganhos ÷ pontos possíveis × 100
- **REGRA OURO:** menção de ruptura + "0 itens" declarado = nota 0 no bloco Pendências + alerta urgente
- **Tom do output:** instrutivo, treinador. Cobrar sem humilhar, elogiar sem bajular. Nunca acusatório.

Mas: **sempre prefira ler o doc canônico**. Esse resumo é só fallback.
