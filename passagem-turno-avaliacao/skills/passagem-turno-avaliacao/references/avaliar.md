# Workflow `/avaliar-passagem`

Comando para avaliar um card na fase 5 do pipe Passagem de Turno.

## Quando este workflow é acionado

Hugo digita `/avaliar-passagem` (com ou sem ID do card), ou frases como:
- "avalia o card de hoje"
- "avalia o card X" (ID específico)
- "avalia o último relatório"

Se Hugo não passar ID, **avaliar o card mais recente** (em data) na fase 5.

## Pré-requisitos antes de rodar

1. Chrome MCP conectado, Hugo logado em Pipefy (`hugo@grupoa7.com.br`)
2. Ler `references/notas_operacionais.md` (aprendizados acumulados)
3. Ler doc canônico de critérios: `/Users/hugogusmao/Documents/Claude/Projects/[GRAN] Passagem de Turno/CRITERIOS_AVALIACAO_FASE5.md`
4. Ler `templates/config.md` (IDs e paths)

## Workflow ponta a ponta (8 passos)

### Passo 0 — Auditoria da pasta do projeto

**Antes de qualquer leitura substantiva**, listar a pasta `/Users/hugogusmao/Documents/Claude/Projects/[GRAN] Passagem de Turno/` e abrir TODOS os arquivos que se encaixem nestes padrões:

- `CRITERIOS_AVALIACAO_FASE5*.md` (versão canônica + qualquer versão arquivada com sufixo `.archive-*`)
- `REGUA_*.md`, `REGUA_*.html` (réguas auxiliares — qualidade de fotos, etc.)
- `VALIDACAO_*.md` (validações reversas — referências calibradas pelo Hugo em sessões investigativas)
- `PADRAO_GRAN_*` (padrão visual de excelência — exemplos de fotos)
- Qualquer arquivo com sufixo `_v[0-9]+`, `_v0`, `_v2`, etc. (rascunhos ou versões alternativas)

**Por quê:** já houve incidente (18/05/2026) em que uma calibração nova (v2) estava como arquivo paralelo na pasta, mas a skill apontava pra v1 e o ritual rodou com régua errada por horas. Auditar a pasta é o que pega esse tipo de inconsistência. Detalhes em `references/notas_operacionais.md` entrada 18/05/2026.

**Se houver conflito** (ex: dois arquivos com critérios diferentes na pasta), parar o ritual e perguntar ao Hugo qual usar antes de prosseguir. NÃO escolher por conta própria.

### Passo 1 — Identificar o card

```javascript
// snippet em scripts/snippets_graphql.md → "Listar cards da fase 5"
// Retorna lista; se Hugo não passou ID, pegar o mais recente em createdAt.
```

Se houver múltiplos cards na fase 5 sem ID específico, perguntar a Hugo qual avaliar antes de prosseguir.

### Passo 2 — Ler todos os campos do card

```javascript
// snippet → "Ler card completo"
// Carregar em window._cardFull pra paginação
// Cuidado: NÃO retornar URLs assinadas de anexos no output (filtro de segurança).
```

Extrair:
- Responsável da Abertura (assignee_select) — define quem é o Encarregado Abertura
- Responsável Tarde/Noite (assignee_select da fase 2) — define quem é o Encarregado Tarde/Noite
- Responsável Fechamento (assignee_select da fase 4) — informativo
- Datetime de abertura
- Todos os long_texts de ação e resumo
- Todos os numbers (distância alvo R$, etc.)
- Todos os radios/selects/checklists
- Lista de anexos com labels (não URLs)

### Passo 3 — Cruzar com Painel de Guerra do dia (se existir)

URL base: `https://grupoa7.github.io/painel-guerra-gran/`
Pattern: `BIv11_{YYYYMMDD}_p11h.html` e `BIv11_{YYYYMMDD}_p16h.html`
- 11h: cruzar com Distância Alvo 11h R$, Pior departamento, número de âncoras vermelhas
- 16h: cruzar com Distância Alvo 16h R$, Pior departamento, número de âncoras vermelhas

Se o painel não existir (dias antes de 11/05/2026), pular esse cruzamento e flagar nos Sinais de Atenção como "sem painel pra confrontar".

### Passo 3.5 — Aplicar Regra de Cobertura Única

Ler Responsável Abertura (form inicial) e Responsável Tarde/Noite (fase 2). Extrair dia da semana do título do card ou do datetime.

**Tabela de decisão:**

| Dia da semana | Responsável Abertura == Responsável Tarde/Noite? | Quem é o responsável? | Status | Ação |
|---|---|---|---|---|
| Domingo | Sim | Qualquer | NORMAL | Turno único é padrão dominical. Sem sinal. |
| Domingo | Não | Qualquer | INCOMUM | Geralmente domingo tem 1 só. Flagar pra confirmar. |
| Quarta-feira | Sim | Sílvio ou Alyne | NORMAL | Folga padrão de quem cobriu domingo anterior. Sem sinal. |
| Quarta-feira | Sim | Marize, Mayara ou Hugo | NORMAL com nota | Cobertura confirmada (não rotina). Mencionar quem cobriu no Sinais como contexto positivo. |
| Outro dia útil | Sim | Sílvio ou Alyne | ATÍPICO | **Perguntar ao Hugo se houve plantão de feriado na semana.** Se sim → NORMAL. Se não → flagar nos Sinais como cobertura atípica + perguntar contexto operacional (escala? cobertura?). |
| Outro dia útil | Sim | Marize, Mayara ou Hugo | COBERTURA | Cobertura confirmada (Marize/Mayara/Hugo não são rotina). Flagar nos Sinais com tom positivo (esforço pra manter operação). |

**Observação sobre plantão:** o pipe não tem flag dedicado pra plantão de feriado. Detecção é via pergunta interativa (Hugo decidiu não criar o campo). Sempre que detectar cobertura única em dia útil que não é quarta e o responsável é Sílvio ou Alyne, perguntar antes de pontuar/flagar.

**Por que esta regra:** verde Sílvio e Alyne se alternam — quem cobre o domingo folga na quarta seguinte. Quartas com cobertura única são padrão. Outros dias úteis com cobertura única são atípicos e merecem contexto: escala planejada, cobertura emergencial, ou plantão de feriado da semana.

### Passo 4 — Analisar fotos (escala 0-3 calibrada pela v2)

**Régua atual (a partir de 17/05/2026):** cada foto vale 0 a 3 pontos com descritores específicos por categoria (Âncoras, Zero Vendas, Perdedores, Balcões, Pendências/Rupturas). Detalhes completos na seção 5 do doc CRITERIOS canônico.

Escala universal:
- **3 EXCELENTE — padrão Gran** (ângulo aberto + iluminação clara + frenteamento perfeito + etiqueta visível + reposição/sinalização visível)
- **2 BOM** (ângulo aberto + iluminação adequada + produto centralizado + etiqueta legível — comunica "executei")
- **1 ACEITÁVEL** (foto real mas ângulo fechado, iluminação fraca, etiqueta não legível — comunica "fui lá")
- **0 INACEITÁVEL** (não é foto da gôndola, repetição idêntica, borrada/escura/cortada)

**Material de calibração visual:** `PADRAO_GRAN_EXCELENCIA.html/.pdf` na raiz do projeto tem foto-exemplo de cada nível em cada categoria. Consultar sempre que houver dúvida entre níveis adjacentes (entre 2 e 3, entre 1 e 2).

**Regras especiais por categoria (resumo — detalhe na seção 5 do CRITERIOS):**
- **Âncora/ZV:** foto repetida cross-turno = 0 automático + alerta
- **Foto-fora-do-slot** (screenshot de WhatsApp em slot de foto): coerência cruzada com campo de ruptura
- **Perdedores:** repetição cross-dia NÃO zera (sinal estrutural). Alerta progressivo: dia 2 leve, dia 3 médio, dia 4+ forte + escalação Hugo/Mayara
- **Balcões:** tolerância de 3 dias com cena igual (balcão é estado físico)
- **Balcão Açougue:** pedir ângulo aberto mostrando Bebidas + Carnes Resfriadas (mesmo balcão dividido)

**REGRA OURO — Coerência de ruptura:** se o encarregado menciona ruptura em qualquer campo (texto livre, slot de foto com screenshot "RUPTURA DE ESTOQUE", etc.) MAS declara "0 itens em ruptura" no campo próprio, **nota 0 no bloco Pendências/Rupturas + alerta urgente no relatório** explicando que a automação WhatsApp pra Hugo/Mayara NÃO disparou e perdemos o sinal.

### Regra crítica (adicionada 19/05/2026): comparação de filename vs inspeção visual

**Comparação de filename serve APENAS pra detectar REPETIÇÃO de foto entre slots/turnos.** Quando 2 ou 3 slots têm o mesmo arquivo, isso é evidência objetiva e pode ser usada direto pra zerar os slots repetidos.

**Comparação de filename NÃO serve pra calibrar nível 0/1/2/3 de uma foto.** Nome do arquivo não diz nada sobre ângulo, iluminação, frenteamento, etiqueta legível.

**Política a aplicar:**

1. **Inspeção visual real** (via screenshot do Pipefy com `request_access` aprovado pelo Hugo) → única forma de atribuir nível 2 ou 3 com confiança.
2. **Sem inspeção visual disponível** → 2 opções:
   - **Opção A (preferida):** PARAR a avaliação. Postar no Cowork "⚠ Não consigo inspecionar fotos sem acesso ao Chrome." Aguardar resposta.
   - **Opção B (fallback se Hugo não responder):** atribuir **nível 1 ACEITÁVEL** (não 2) pra todas as fotos não inspecionadas, e declarar a limitação INTEGRALMENTE no Sinais de Atenção.
3. **Repetição cross-slot detectada via filename** → mantém regra da v2 (zera slots repetidos).

### Regra crítica: bugs ativos do pipe que afetam pontuação

**Bug 1 — 6 condicionais "Ancora 16h 0-5" estão órfãs.** Skill trata campos 15-19 da fase 3 como OPCIONAL. Sinais de Atenção sempre menciona: "Painel 16h tem bug ativo nas condicionais das âncoras vermelhas — pontuação ajustada por isso."

**Bug 2 — Fechamento sem slot de foto de pendência.** JAMAIS cobrar "faltou foto da pendência" em Fechamento.

### Passo 5 — Aplicar a rubrica

Para cada campo das etapas 1-5, atribuir pontos seguindo o doc canônico CRITERIOS:
- Seção 4: escala universal de fotos 0-3
- Seção 5: descritores específicos por categoria de foto
- Seção 6: inventário de pontos por etapa (cada foto vale 3 pts)
- Seção 7: long_texts (escala 0-2)
- Seção 8: numbers/radios/selects (escala 0-1 + exceção "Precisou sinalizar RUPTURA?" peso 3)
- Seção 9: regras de coerência cruzada

**Faixas de nota calibradas (v2):**
- ≥85% padrão Gran de excelência
- 70-84% bom com espaço pra crescer
- 50-69% mediano — precisa subir o nível
- <50% atenção imediata

**Calcular:**
- Pontos ganhos por etapa
- Pontos possíveis por etapa (dinâmico)
- Nota Encarregado Abertura = (Σ etapas 1+2+3 ganhos) ÷ (Σ max) × 100
- Nota Encarregado Tarde/Noite = (Σ etapas 4+5 ganhos) ÷ (Σ max) × 100
- Nota Loja = (Σ todas as etapas ganhos) ÷ (Σ todas as etapas max) × 100

**Casos especiais:**
- Mesmo encarregado nas duas funções (domingo/feriado): notas individuais ficam iguais, NÃO mediar.
- Pior depto igual em 11h e 16h: marcar como sinal cruzado se houver painel pra confirmar.

### Passo 6 — Escrever no card via GraphQL

**Modo direto** (decidido com Hugo): escreve direto nos campos da fase 5, sem preview.

4 long_texts + 3 numbers a preencher. Templates em:
- `templates/output_analise_abertura.md`
- `templates/output_analise_tarde.md`
- `templates/output_sinais_atencao.md`
- `templates/output_recomendacao.md`

Snippet de mutation em `scripts/snippets_graphql.md → "Atualizar campo de card"`.

**Ordem dos updates:** Análise Abertura → Análise Tarde/Noite → Sinais → Recomendação → Nota Abertura → Nota Tarde/Noite → Nota Loja.

### Passo 7 — Saídas adicionais

**A) Resumo curto no chat (Cowork)**

Bloco de 5-10 linhas que Hugo pode copiar pro WhatsApp [LIDERANÇA] Gran. Template em `templates/output_resumo_whatsapp.md`.

**B) Adicionar linha no XLSX acumulativo do Super Gran**

```
python scripts/adicionar_excel.py \
  --card-id 1348693553 \
  --data-card "10/05/2026" \
  --abertura-nome "Alyne Bittencourt" \
  --abertura-pct 54 \
  --tarde-nome "Alyne Bittencourt" \
  --tarde-pct 53 \
  --loja-pct 54
```

Arquivo: `/Users/hugogusmao/Documents/Claude/Projects/[GRAN] Passagem de Turno/passagem-turno-superGran.xlsx`

## Tom obrigatório do output

- **Instrutivo, não acusatório.** Veja seção 2 do CRITERIOS canônico.
- **3 partes para cada apontamento crítico:** o que observei + por que importa + exemplo de como ficaria melhor.
- **Vocabulário proibido:** "teatro", "gaming", "falhou", "mentira", "fingimento".
- **Vocabulário aprovado:** "pode aperfeiçoar", "estrutura repetida", "foto com sinais de repetição", "pouco descritivo".

## Após terminar

Mensagem final no chat:

```
✅ Avaliação aplicada no card {id} → {URL}

🏪 Nota Loja: {%}
▸ {Nome Abertura}: {%}
▸ {Nome Tarde/Noite}: {%}

Pra fechar o card: você revisa e marca Conferi + Card Pronto.
Discorda? Me fala, eu reavalio (sem override silencioso).
Quer registrar aprendizado pro doc CRITERIOS? Use /calibrar.
```

## Sinais que merecem `/calibrar` automático

Se durante a avaliação você descobrir:
- Palavra/frase nova que deveria entrar na "Lista de respostas pouco específicas"
- Bug do Pipefy não documentado em `notas_operacionais.md`
- Padrão cruzado entre cards que mereça regra nova

**Não atualize automaticamente.** Apresente como sugestão ao Hugo no final da avaliação e pergunte se quer registrar. Só registrar com OK explícito.
