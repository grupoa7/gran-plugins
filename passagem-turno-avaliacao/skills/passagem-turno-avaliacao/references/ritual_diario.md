# Workflow `/ritual-diario` — Avaliação + WhatsApp privado

Comando rodado automaticamente pelo scheduled task **seg-sáb 13h20**. Avalia o card do **dia anterior** e dispara mensagens privadas pra Sílvio e Alyne via WhatsApp Web.

## Quando este workflow é acionado

- Scheduled task `passagem-turno-ritual-diario` (seg-sáb 13h20)
- Hugo digita `/ritual-diario` manualmente (debug ou rodada perdida)

## Pré-requisitos antes de rodar

1. Chrome MCP conectado, Hugo logado em:
   - Pipefy (`hugo@grupoa7.com.br`)
   - WhatsApp Web (sessão da Fran, onde Sílvio e Alyne estão na agenda)
2. Ler `references/notas_operacionais.md`
3. Ler `references/loop_melhoria_continua.md`
4. Ler doc canônico CRITERIOS
5. Ler `templates/config.md` para IDs, paths, contatos

## Workflow ponta a ponta

### Passo 0 — Health check de sessão

Antes de qualquer outro passo do ritual, fazer verificação silenciosa das duas sessões de que o ritual depende:

1. **Pipefy.** Navegar pra `https://app.pipefy.com/pipes/306798124`. Se a URL final contiver `signin.pipefy.com`, considerar deslogado.
2. **WhatsApp Web (sessão da Fran).** Navegar pra `https://web.whatsapp.com`. Se permanecer na tela de QR code, considerar deslogado.

**Se qualquer uma falhar:**

1. Abortar o ritual imediatamente. **Não executar Passo 1 nem nenhum passo subsequente.**
2. Postar 1 mensagem única no chat do Cowork:
   > ⚠️ Ritual diário 13h20 pausado — [Pipefy / WhatsApp Web / ambos] deslogado. Faz login e me chama com `/ritual-diario` manual.
3. **Não disparar nada** nos privados de Sílvio/Alyne nem em qualquer outro contato.
4. Não fazer retry automático.

### Passo 0.5 — Auditoria da pasta + leitura do MANUAL_PIPEFY

**Adicionado em 19/05/2026 após erro grave de avaliação.**

1. **Auditoria da pasta:** listar `/Users/hugogusmao/Documents/Claude/Projects/[GRAN] Passagem de Turno/` e abrir todo arquivo que case com `CRITERIOS_*.md`, `REGUA_*`, `VALIDACAO_*`, `PADRAO_GRAN_*`, `*_v[0-9]*.md`. Conflito = STOP + pergunta ao Hugo.

2. **Leitura ativa do `MANUAL_PIPEFY_RELATORIO_PASSAGEM_TURNO.md`** (NOVO — obrigatório toda rodada):
   - **Seção 1.1** (fases do pipe e contagens atuais)
   - **Seção 2** (inventário detalhado campo a campo das 5 fases)
   - **Seção 3 — TABELA MESTRE DE FOTOS** (44 slots de attachment mapeados por fase)
   - **Seção 5** (bugs ativos — especialmente 5.1 sobre as 6 condicionais órfãs do Painel 16h)
   - **Cabeçalho** (data da última varredura). Se > 30 dias atrás, AVISAR Hugo.

3. **Quando for redigir os 4 long_texts da fase 5**, cruzar cada cobrança ("faltou foto de X") com a tabela da seção 3 do manual.

4. **Detecção de drift do manual:** se ao ler o card alvo você encontrar (a) campo cujo label não bate com nenhuma entrada do manual, OU (b) campo do manual ausente no card, OU (c) número de fotos diferente do esperado, **PARAR** e postar no Cowork.

### Passo 0.7 — Validação de turnos canônicos

**Turnos canônicos da loja Gran Caminho das Árvores:**

- **Alyne** = abertura, 6h10 às 14h30
- **Sílvio** = tarde + fechamento, 13h às 21h20
- **Folga:** quarta-feira E domingo são **REVEZADAS** entre os dois.
- **Folga compensatória de feriado:** pode existir. **NUNCA presumir.**

**Validação a aplicar no card alvo (ANTES de calcular notas):**

```
DIA ÚTIL PADRÃO (seg, ter, qui, sex, sáb):
  Resp Abertura     deve ser  Alyne Bittencourt
  Resp T/N          deve ser  Sílvio Rouzan
  Resp Fechamento   deve ser  Sílvio Rouzan
  → Qualquer desvio = FLAG

QUARTA (revezamento rígido):
  1. Consultar `data/revezamento_qua_dom.csv` pela data alvo
  2. Se data tem entrada → quem_trabalha esperado nos 3 slots
  3. Se data NÃO tem entrada no CSV → FLAG automático

DOMINGO (turno único é a regra — calibrado 01/06/2026):
  1. Se data tem entrada no CSV → CSV é fonte de verdade
  2. Se data NÃO tem entrada no CSV:
     a) Se Resp Abertura == Resp T/N == Resp Fechamento E
        responsável é Sílvio OU Alyne:
        → NORMAL (turno único padrão dominical)
        → seguir avaliação normalmente
     b) Se responsáveis divergem OU é Marize/Mayara/Hugo:
        → FLAG + STOP + perguntar Hugo no Cowork

FERIADO / COMPENSATÓRIA:
  NUNCA presumir. Validar como dia útil padrão a menos que Hugo
  tenha pre-confirmado no Cowork em mensagem do mesmo dia.
```

**Se houver FLAG:**

1. **STOP imediato.** Não gravar nada no Pipefy. Não disparar WhatsApp.
2. Postar 1 mensagem no chat do Cowork no formato:
   ```
   ⚠ Ritual diário pausado — Card {DATA_DD/MM} ({DIA_SEMANA}) tem responsáveis fora do padrão canônico:
     • Resp Abertura: {nome}  (esperado: {esperado})
     • Resp T/N: {nome}        (esperado: {esperado})
     • Resp Fechamento: {nome} (esperado: {esperado})

   Como prosseguir? Me responde no Cowork antes que eu siga.
   ```
3. Aguardar resposta do Hugo.

### Passo 1 — Detectar data alvo

```python
hoje = date.today()
data_alvo = hoje - timedelta(days=1)
dia_semana_hoje = hoje.weekday()  # 0=seg, 6=dom
```

### Passo 2 — Buscar card da fase 5 com data alvo

```javascript
// snippet em scripts/snippets_graphql.md → "Listar cards fase 5"
```

**Fallback se não encontrar:**
1. Tentar buscar em fases anteriores (4, 3, 2, 1) — pode ter ficado preso
2. Se ainda não encontrar: enviar alerta SÓ pro Hugo no chat do Cowork
3. **Não disparar nada nos privados.**

### Passo 3 — Executar avaliação completa

Rodar todo o workflow de `references/avaliar.md` (Passos 1-7 daquele doc). Isso já preenche o card no Pipefy e atualiza o XLSX.

### Passo 4 — Calcular cenário de mensagem por encarregado

Para cada encarregado:

```python
nota_dia = nota_individual_calculada
media_individual = media_movel_ultimas_7_avaliacoes(encarregado)

if nota_dia > media_individual + 5:
    cenario = "B"  # excelente
elif nota_dia < media_individual - 5:
    cenario = "C"  # difícil
else:
    cenario = "A"  # normal
```

**Casos especiais:**
- Mesma pessoa nos 2 turnos: gerar 1 mensagem só, mencionar "turno único hoje"
- Pessoa em folga (quarta): pular essa pessoa
- Primeira semana (< 3 avaliações no histórico): usar cenário A sempre

### Passo 5 — Gerar mensagem do cenário escolhido

Para cada encarregado:
1. Ler `templates/whatsapp_privado_cenario_{A|B|C}_*.md`
2. Substituir todos os `{PLACEHOLDERS}` com dados do card e histórico
3. Para `{EXEMPLO_CONCRETO}`, preferir puxar do histórico real do mesmo encarregado

### Passo 5.5 — Política de envio (vigente desde 25/05/2026 — dry-run encerrado)

Nova política permanente:

- **Cenário A e B → envio automático direto.** Grava Pipefy + envia WhatsApp + planilha + log, sem checkpoint.
- **Cenário C (QUALQUER queda) → NÃO enviar automático.** Postar o pacote completo no Cowork via AskUserQuestion e aguardar OK do Hugo.
- Travas duras permanecem ativas em todos os cenários: Passo 0 (health check), Passo 0.7 (turnos canônicos), card não encontrado.

**Procedimento para Cenário C:**

1. Roda avaliação completa do card (Passos 1-5 acima já feitos).
2. **Não gravar no Pipefy ainda.**
3. Postar no chat do Cowork via `AskUserQuestion` com a pergunta:
   ```
   Avaliação do card {DATA} pronta. Aprova envio?
   ```
   Opções: "Aprovar e enviar tudo" / "Aprovar com ajustes" / "Rejeitar — não enviar nada hoje"

   ANTES da pergunta, postar no chat o pacote completo:
   - Notas: Alyne {X}% · Sílvio {Y}% · Loja {Z}%
   - Pontos a cobrar/elogiar com trecho exato do card
   - Rascunho da mensagem privada Sílvio
   - Rascunho da mensagem privada Alyne
   - Rascunho dos 4 long_texts da fase 5

4. **Comportamento conforme resposta:**
   - "Aprovar e enviar tudo" → grava no Pipefy + envia WhatsApp + atualiza XLSX + log
   - "Aprovar com ajustes" → aguarda Hugo escrever os ajustes
   - "Rejeitar" → registra rodada como REJEITADA no log

5. **Se Hugo não responder a tempo (sem resposta até 18h00):**
   - Salvar todo o pacote em `data/rascunhos/rascunho_{YYYY-MM-DD}.md`
   - Não fazer retry. Não disparar nada.

### Passo 6 — Disparar via WhatsApp Web

Usando Chrome MCP:

```javascript
// 1. Navegar pra WhatsApp Web
mcp__Claude_in_Chrome__navigate({ url: "https://web.whatsapp.com" })

// 2. Buscar contato pelo nome OU número (ver config.md local)
// 3. Digitar e enviar mensagem
// 4. Aguardar confirmação de envio (2 checks)
```

**Guarda-rails:**
- NUNCA enviar a mesma mensagem 2x. Se já houver registro de envio, abortar.
- Confirmar via screenshot antes de declarar enviado.
- Se Sílvio aparecer offline há > 7 dias, alertar Hugo.

### Passo 7 — Registrar envio em log

Adicionar linha em `data/log_envios_whatsapp.csv`:

```
timestamp_envio,encarregado,data_avaliada,cenario,nota_dia,media_semana,sucesso
2026-05-19T13:21:34,Silvio,2026-05-18,A,82,78,True
```

### Passo 7.5 — Registro de ruptura no grupo [LIDERANÇA] Gran (desde 25/05/2026)

Todo dia, depois de enviar as mensagens aos encarregados. **Roda sempre, mesmo sem ruptura.**

1. **Coletar rupturas de ONTEM:** do card já avaliado, ler todos os blocos de ruptura. **Ignorar entradas de teste.**

2. **Cross-check no card de HOJE:** o card do dia atual já existe às 13h20. Ler dele o campo `O que Já Resolvi das Pendências`. Não inventar.

3. **Compor a mensagem:**
   - **Com ruptura:** listar cada item + status provável + pergunta de fechamento.
   - **Sem ruptura:** "✅ Zero ruptura registrada ontem ({DATA})."

4. **Postar no grupo `[LIDERANÇA] Gran`**. Confirmar envio (2 checks).

**Template (sempre abre com saudação ao time):**
```
Oi, equipe! 👋

📋 Fechamento de ruptura — card de ontem ({DATA_DD/MM})

• {Produto} — {✅ consta resolvido no card de hoje / ⏳ sem confirmação no card de hoje}

Já fechamos {esses itens / esse item}? Se tiver algum aberto, me avisem aqui.
```

**Guarda-rails:**
- Tom de fechamento/visibilidade, não de cobrança.
- Nunca postar 2x no mesmo dia (checar log antes).

### Passo 8 — Resposta no chat do Cowork (pro Hugo)

```
✅ Ritual diário 13h20 concluído — Card {DATA_DD/MM} ({DIA_SEMANA})

🏪 Nota Loja: {X}%
▸ Sílvio: {Y}% — Cenário {A|B|C}
▸ Alyne: {Z}% — Cenário {A|B|C}

📩 Mensagens enviadas:
✓ [GRAN] Silvio Rouzan
✓ [GRAN] Alyne Bittencourt

🔗 Card no Pipefy: {URL}
🔗 XLSX atualizado: passagem-turno-superGran.xlsx
```

### Passo 9 — Loop de melhoria contínua

Aplicar Mecanismo 1 de `references/loop_melhoria_continua.md` se houver candidato detectado.

---

## Falhas e fallbacks

| Falha | Ação |
|---|---|
| Card do dia não encontrado | Alerta no chat do Cowork. NÃO enviar nada nos privados. |
| WhatsApp Web não logado | Pingar Hugo. Pausa ritual até resolver. |
| Mensagem já enviada (re-execução) | Abortar. Mostrar log do envio original. |
| Avaliação inconsistente | Não enviar. Alertar Hugo. |
| Cenário C com queda > 15pp | Pingar Hugo ANTES de enviar. |

---

## Métricas a observar

- Tempo total do ritual (alvo: < 10 min)
- Taxa de envio com sucesso (alvo: ≥ 95%)
- Distribuição de cenários (sweet spot: 70% A, 15% B, 15% C)
- Reincidência de mesmo ponto crítico no mesmo encarregado (≥ 3 dias = escalar)
