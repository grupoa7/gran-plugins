# Notas Operacionais — Skill Passagem de Turno

Aprendizados práticos descobertos durante execuções reais. Cada entrada tem: data, contexto, aprendizado, solução.

**Regra:** só registra aprendizados que tenham aparecido em ≥1 execução real. Não tratar como TODO list de melhorias hipotéticas.

---

## 12/05/2026 — Bug API: reorder de campo recém-criado retorna "Acesso negado"

**Contexto:** ao criar campo `Sinais de Atenção` na fase 5 via `createPhaseField` e tentar reordenar com `updatePhaseField` na mesma sessão, retorna `PERMISSION_DENIED` consistentemente.

**Aprendizado:** mesmo bug do Painel 16h documentado no `MANUAL_PIPEFY_RELATORIO_PASSAGEM_TURNO.md` cap. 5.2. Alguns campos / fases têm essa anomalia silenciosa.

**Solução:** após criar campo via API, **pedir ao Hugo pra arrastar manualmente** na UI das configurações da fase. Não tentar mais de 2x via API — perde tempo.

**Sinal pra detectar:** se a query de fields lista o campo com `index` muito acima do esperado (ex: 502 quando você pediu 300), é o bug. Drag manual resolve em 30s.

---

## 12/05/2026 — Filtro de segurança bloqueia output com URLs assinadas

**Contexto:** ao tentar retornar valores de campos `attachment` num output de javascript_tool, o filtro retorna `[BLOCKED: Cookie/query string data]`.

**Aprendizado:** URLs assinadas do storage do Pipefy disparam o filtro. Não tentar retornar valor bruto do attachment.

**Solução:** filtrar `f.field.type !== 'attachment'` no output. Pra analisar fotos, abrir o card no Pipefy via `navigate` + screenshot agrupado das miniaturas.

---

## 12/05/2026 — Painel de Guerra não existe pra dias antes de 11/05/2026

**Contexto:** tentei `BIv10_20260510_p11h.html` pra card de teste sábado 10/05 e bateu 404.

**Aprendizado:** o BI do painel começou em 11/05/2026. Cards anteriores não têm painel pra cruzamento numérico.

**Solução:** se data do card < 11/05/2026, pular o cruzamento e flagar como limitação nos Sinais de Atenção: "sem painel pra confrontar Distância Alvo R$".

---

## 12/05/2026 — Tom acusatório quebra adesão de equipe baixa escolaridade

**Contexto:** primeira execução do sistema usou termos como "teatro de checklist" e "gaming visual". Hugo pediu pra moderar — palavras soam ofensivas pra equipe.

**Aprendizado:** equipe Gran tem cultura informal, baixa escolaridade. Tom de juiz quebra adesão. Tom de treinador funciona.

**Solução:** vocabulário aprovado vs proibido está na seção 2 do doc CRITERIOS canônico. Sempre consultar antes de redigir output. Cada apontamento crítico tem 3 partes: o que observei + por que importa + exemplo de como ficaria melhor.

---

## 12/05/2026 — Checkbox obrigatório em fase condicional gera falso positivo

**Contexto:** primeira avaliação penalizou checkbox "Li as Pendências" e bônus "Resolvi todas" quando a fase 2 declarava "Há Pendências = Não". Hugo apontou que o checkbox é obrigatório no template — encarregado é forçado a marcar mesmo sem pendência.

**Aprendizado:** antes de criar regra de coerência cruzada que penalize um campo, conferir se o campo é obrigatório no template. Penalizar comportamento forçado = injusto.

**Solução:** removida a regra. Quando "Há Pendências = Não", checkbox e long_text são neutros (não somam nem subtraem). Registrado no doc CRITERIOS seção 7 (Regra removida).

---

## 14/05/2026 — Regra de transição de label de campo

**Contexto:** ao avaliar o card 11/05, descobri que o campo "Distância do Alvo (11h/16h) – R$" tinha label antigo na época em que o card foi preenchido. A interpretação anterior do campo era diferente. Hugo decidiu que neste caso a pontuação deveria ser INTEGRAL — não punir o encarregado por seguir o texto que ele viu.

**Aprendizado:** quando há mudança de label / texto de um campo entre a data do card e a data atual, NÃO penalizar o encarregado por resposta consistente com o label anterior. Mas SEMPRE alertar isso no texto da avaliação (Sinais de Atenção) — pra ficar claro que a pontuação integral é por contexto, não por aprovação da resposta.

**Solução:** antes de penalizar inconsistência de campo, conferir histórico de mudanças do label no Pipefy. Se houve mudança entre data do card e hoje, aplicar pontuação integral + escrever sinal explícito explicando.

**Sinal pra detectar:** olhar a data de criação do campo no Pipefy ou cruzar com memória de mudanças aplicadas (ver memória `project_pipe_passagem_turno_estado_atual.md`).

---

## 14/05/2026 — Distinção "distância da hora" × "% do desafio" é fonte recorrente de erro

**Contexto:** ao cruzar 3 cards consecutivos com o Painel de Guerra, descobri padrão: encarregados confundem o número da "Distância do Alvo R$" com o "% do desafio do dia" do painel.

**Aprendizado:** o painel mostra DOIS números visualmente similares: "R$ X acima/abaixo do alvo" (distância da hora) e "Z% do desafio / faltam R$ Y" (distância do desafio). Sem treinamento dirigido, encarregados copiam o número mais visível, que não é o pedido pelo campo.

**Solução:** (1) o doc CRITERIOS já flagou que o tooltip do campo precisa ser ajustado no Pipefy. (2) Quando detectar Distância R$ inconsistente com painel, escrever no Sinal explicação completa do que é "distância da hora" vs "% do desafio" + exemplo concreto do número correto. (3) Recomendar conversa de calibração com o encarregado mostrando os dois blocos do painel lado a lado.

---

## 14/05/2026 — Regra de cobertura única por encarregado

**Contexto:** detectei padrão atípico nos cards 12/05 e 13/05 — mesmo encarregado em Resp Abertura + Resp Tarde/Noite num dia útil.

**Aprendizado:** Resp Abertura == Resp Tarde/Noite NÃO é por si só um sinal — depende de dia da semana e da pessoa. Regra completa:

| Dia | Quem | Status |
|---|---|---|
| Domingo | Qualquer | NORMAL (turno único é padrão dominical) |
| Quarta | Sílvio ou Alyne | NORMAL (folga padrão de quem cobriu domingo) |
| Quarta | Marize, Mayara ou Hugo | NORMAL com observação no Sinais (cobertura confirmada) |
| Outro dia útil | Sílvio ou Alyne | ATÍPICO — flagar nos Sinais pedindo contexto |
| Outro dia útil | Marize, Mayara ou Hugo | COBERTURA — flagar como cobertura confirmada |
| Qualquer | Card com flag "plantão" | NORMAL (folga adicional justificada) |

**Solução:** ao montar Sinais de Atenção, aplicar esse fluxo de decisão. Adicionar no doc CRITERIOS e no references/avaliar.md como passo dedicado.

---

## 18/05/2026 — Régua v2 estava em arquivo paralelo, não promovida; ritual rodou com régua v1

**Contexto:** primeira rodada automática do ritual diário (ritual de domingo 17/05 avaliado em 18/05). Apliquei a régua v1 (12/05) ao card e dei nota 99% (turno único Sílvio). Hugo apontou que tinha calibrado a régua v2 ontem (17/05) em sessão investigativa dos cards 14-16/05 — e que pela v2, as notas reais ficam em 73% (Alyne 15/05), 54% (Sílvio 14/05), 48% (Sílvio 16/05).

**Aprendizado:** o erro tem 2 camadas:

1. **Sistêmica** — a sessão de 17/05 terminou com `CRITERIOS_AVALIACAO_FASE5_v2.md` salvo como arquivo paralelo na raiz do projeto, **sem substituir** o `CRITERIOS_AVALIACAO_FASE5.md` (v1). Todos os ponteiros da skill continuaram apontando pro nome sem sufixo (= v1).

2. **Operacional** — eu segui o scheduled task sem auditar a pasta do projeto. Se tivesse feito `ls` antes de começar, os arquivos `_v2.md`, `REGUA_*`, `VALIDACAO_*`, `PADRAO_GRAN_*` todos datados de 17/05 saltariam aos olhos.

**Solução aplicada em 18/05/2026:**

1. Renomeação física: v1 virou `.archive-20260512.md`; v2 virou o canônico.
2. Adicionado **Passo 0 — Auditoria da pasta** em `references/avaliar.md`.
3. Memória nova marcando "régua v2 oficial desde 18/05/2026".
4. Histórico de calibrações no doc CRITERIOS bumpado com data de promoção.

**Sinal pra detectar (futuro):** quando começar uma sessão, se vir arquivos com `_v[0-9]+`, `_draft`, `_rascunho`, `VALIDACAO_*`, `REGUA_*` na pasta do projeto, **abrir todos antes** de qualquer trabalho substantivo.

---

## 19/05/2026 — Atribuição trocada (Resp T/N) + lições da 2ª rodada automática

**Contexto:** ritual diário automático rodou pro card 18/05 (segunda). Card tinha "Resp Abertura = Alyne, Resp T/N = Alyne, Resp Fechamento = Sílvio" preenchido. Em vez de parar e perguntar, presumi narrativa de "cobertura atípica" e segui o ritual inteiro. Resultado: a mensagem WhatsApp pra Alyne cobrou ela pela tripla repetição de foto no Painel 16h que era do Sílvio, e a elogiei pela ação Granel 16h que era do Sílvio. Hugo apontou, foi enviada retratação curta pra Alyne.

**Aprendizado central:** *qualquer aparente desvio da estrutura de turnos canônicos = parar e perguntar, NUNCA presumir.* Turnos canônicos da loja Gran:
- Alyne abre 6h10-14h30
- Sílvio faz tarde + fechamento 13h-21h20
- Quartas E domingos = folga revezada entre os dois (revezamento interno à dupla, não regra fixa de dia)
- Feriado / folga compensatória = pode existir mas só com confirmação Hugo

**Outros 3 aprendizados desta rodada:**

1. **Comparação de filename serve só pra detectar REPETIÇÃO, não pra calibrar nível de foto.** Inspeção visual real (via screenshot Pipefy) é a única forma de calibrar nível 2 ou 3 com confiança. Sem screenshot disponível = parar e pedir, ou nível 1 default com declaração de limitação.

2. **Antes de cobrar "faltou foto X", validar no MANUAL_PIPEFY que o template oferece slot pra essa foto.** Cobrança injusta destrói confiança no processo.

3. **Skill em modo dry-run por 7 dias (19/05 → 26/05) por decisão Hugo.** Ritual diário roda avaliação completa mas para no checkpoint, posta rascunho no Cowork via AskUserQuestion, espera OK explícito antes de gravar no Pipefy ou disparar WhatsApp.

**Solução aplicada em 19/05/2026 (mudanças codadas na skill):**

1. **Passo 0.5** novo em `references/ritual_diario.md`: auditoria da pasta + leitura ativa do MANUAL_PIPEFY toda rodada.
2. **Passo 0.7** novo: validação de turnos canônicos.
3. **Passo 5.5** novo: checkpoint Hugo dry-run.
4. **Regra crítica de filename** em `references/avaliar.md`.

---

## 19/05/2026 — Varredura completa do pipe e atualização do manual

**Contexto:** após a cobrança injusta no card 18/05, rodou-se a investigação completa. Manual antigo era de 11/05/2026 (67 campos declarados). Estado real em 19/05/2026: 88 campos.

**Aprendizado:**

1. **Drift de manual em 8 dias = 21 campos novos.** Manuais técnicos envelhecem mais rápido do que sentimos.

2. **Bug crítico descoberto na varredura:** as 6 condicionais "Ancora 16h 0-5" do Painel 16h estão ÓRFÃS. Skill agora trata essas 5 fotos como OPCIONAL até bug ser corrigido.

3. **Confirmação operacional:** Fechamento tem APENAS 3 attachments. NÃO HÁ slot pra foto de pendência operacional. Cobrança inválida.

4. **GraphQL primeiro, UI só pra validar.** 1 query GraphQL deu 90% do manual em 1 fetch.

5. **Output truncado em volumes grandes:** usar `window._var` e ler em chunks de ~800 chars.

**Solução pra próximas rodadas:**

- Rodar a investigação completa do manual **mensalmente como mínimo**, OU ao primeiro sinal de drift.
- Skill já lê manual no Passo 0.5. Manter esse passo religioso.

---

## 20/05/2026 — START form ampliado (Sem Venda/Perdedores de ONTEM) + automação WhatsApp de abertura

**Contexto:** Hugo incluiu no Formulário Inicial (fase 0) um bloco onde o encarregado da abertura registra, lendo o painel de fechamento de ONTEM, os 3 destaques sem venda e os 3 maiores perdedores, mais um radio de RUPTURA e o campo "QUAIS produtos?".

**Aprendizado:**

1. **START form passou de 6 → 15 campos.** Pipe: 88 → 97 campos · 44 → 50 fotos.

2. **🚨 Gatilho "campo atualizado" NÃO dispara na criação via START form.** Solução validada: gatilho **"Um card for criado" + condição "QUAIS produtos? está preenchido"**.

3. **"QUAIS produtos?" é obrigatório e não-condicional** → o encarregado preenche todo dia → a automação dispara em TODA abertura.

**Solução:**

- 2 automações Pipefy novas. Config completa em `AUTOMACAO_WHATSAPP_RUPTURA.md`.
- **Implicação para a avaliação:** o encarregado de abertura agora tem +6 fotos obrigatórias + "QUAIS produtos?" no START form. A skill PODE avaliar a qualidade desse registro, mas isso é mudança de ESCOPO da régua — NÃO foldar no scoring sem Hugo aprovar.

---

## 27/05/2026 — Calibração aprovada: erro estrutural no campo "Responsável Tarde/Noite" (7 cards seguidos)

**Contexto:** ritual diário 27/05 avaliando card 26/05. 7º card consecutivo com Resp T/N preenchido como "Alyne" quando a tarde/noite real foi do Sílvio.

**Aprendizado:** a validação canônica de turnos (Passo 0.7) foi pensada pra parar em qualquer desvio, mas frente a erro estrutural conhecido, parar todo dia vira ruído e bloqueia a operação.

**Decisão do Hugo:** aprovou agir na origem (👍) e escolheu **treinar a Alyne pessoalmente**. NÃO mexer no template do Pipefy.

**Política transitória até resolver:** quando assinatura for `Resp Abertura=Alyne + Resp T/N=Alyne + Resp Fechamento=Sílvio` em dia útil padrão, o ritual procede tratando T/N real = Sílvio E flagar nos Sinais. Não parar.

---

## 01/06/2026 — Calibração Passo 0.7: domingo é turno único por padrão

**Contexto:** ritual 01/06 (segunda) avaliando card 31/05 (domingo). Passo 0.7 atual exige entrada no `revezamento_qua_dom.csv` para domingos. O CSV não tinha entrada para 31/05, então bloqueei e perguntei ao Hugo. Ele respondeu: "Domingo é um dia de um único encarregado".

**Aprendizado:** a regra do Passo 0.7 estava boa para QUARTA (revezamento real), mas falsamente rígida para DOMINGO. Domingo é estruturalmente turno único por padrão da loja Gran.

**Solução pra próximas rodadas:**

```
DOMINGO (nova regra):
  Se Resp Abertura == Resp T/N == Resp Fechamento E
     responsável é Silvio OU Alyne:
    → NORMAL (turno único padrão dominical)
    → seguir avaliação normalmente

  Se responsáveis divergem OU é Marize/Mayara/Hugo:
    → FLAG + parar + perguntar Hugo (mesma lógica de quarta)
```

---

## Template pra adicionar entradas novas

Quando registrar um aprendizado novo, copie esse formato:

```
## DD/MM/YYYY — Título curto (1 linha)

**Contexto:** o que aconteceu durante a execução.

**Aprendizado:** o que isso revela sobre como o sistema/pipe/Pipefy/equipe funciona.

**Solução:** como contornar nas próximas execuções. Comando, snippet ou regra.

**Sinal pra detectar (opcional):** como reconhecer que o problema voltou.
```
