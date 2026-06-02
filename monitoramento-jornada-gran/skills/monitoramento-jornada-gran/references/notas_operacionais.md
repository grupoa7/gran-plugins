# Notas Operacionais — Skill Monitoramento de Jornada

Arquivo de auto-melhoria. Cada rodada da skill que descobrir algo novo, edge case ou ajuste deve ser registrada aqui.

---

## Aprendizados acumulados

### 2026-05-08 — Construção da v1

**Sobre extração via Chrome MCP:**
- Patch de `fetch` em escala (interceptar todas as requests) tende a TRAVAR a aba do RHID. Evitar.
- Pra capturar URLs internas do Angular, usar `XMLHttpRequest.prototype.open` patch sem patchar `send`.
- Todos os 20 cartões já estão no DOM ao gerar HTML → não precisa iterar via `>`.
- "Imprimir Tudo" no relatório HTML abre print dialog do navegador e pode travar — não usar.
- `read_console_messages` corta em ~50KB. Dump em chunks de até 15 mensagens.

**Sobre o cadastro do RHID:**
- Filtro "Ativos" omite quem saiu da empresa MAS o RHID lista 20 ativos quando deveriam ser 19 (Josemaria Maximiana saiu mas continua ativa). Pedir RH desativar.
- Alana (estagiária) está na escala mas NÃO aparece no Cartão de Ponto — possivelmente nome diferente ou regime alternativo.
- Filtro "Todos" puxa 45 colaboradores em Fev/26 (incluindo demitidos como Arthur Vasconcelos, Eduardo Ramos, etc.).

**Sobre as escalas:**
- Setores em Fev/26 usavam "OPERAÇÃO DE LOJA" e "OP. CAIXAS"; em Mar/Abr/Mai mudou pra "OPERADOR DE LOJA" e "OPERADOR DE CAIXAS". Skill normaliza.
- Códigos: F (folga), FF (feriado), FD (folga domingo), Férias, **BH (banco de horas — código novo descoberto em Abr/26)**.
- Marcação "X" = inativo (admitido depois ou demitido antes). Não aplicar regras.
- Marcação "Rescisão" = pós-demissão. Não aplicar regras.

**Sobre as regras:**
- "Atraso Intervalo" do Extrato por Período tem semântica ambígua. Não usar diretamente. Calcular intervalo via SAÍ.x → ENT.(x+1) das batidas reais.
- Padrão observado: muitos colaboradores fazem intervalo curto (38-58 min) que viola a regra interna 1h-1h05.
- 18 casos reais de "descanso em janela proibida" detectados na S19/2026 (Robson 4x, Silvio 4x, Joelison 3x, Alyne 3x, Jilney 2x, Daniel 1x, Luciene 1x).

### Casos especiais encontrados na S19/2026

- **Daniel Pereira sáb 02/05:** bateu 05:20 entrada, depois 07:20 saída pro intervalo, retornou 13:09 — intervalo de 5h49 cruzando toda janela proibida 11-13h. Combinação de janela proibida + intervalo absurdo.
- **Daniel Pereira qui 30/04:** bateu só 05:15 entrada e 14:28 saída. Sem intervalo registrado, jornada de 9h13 — pulou intervalo + jornada > 6h (CRÍTICO CLT).
- **Elissandro Nascimento:** 6 faltas secas seguidas (29/04 a 04/05) + 1 dia parcial trabalhado. Sem nenhuma justificativa lançada. Caso clássico de abandono — alertar RH.
- **Grasiela Conceição:** férias a semana toda (fev 22 a mai 5). RHID continuou marcando "Falta" — escala manda, não conta como falta.
- **Alyne sáb 02/05:** turno fragmentado (3 pares de batida) com intervalo médio em janela 14:09-15:18 (não cruza janela proibida).

### 2026-05-21 — Rodada S21 (qua 13/05 a ter 19/05)

**Sobre extração via Chrome MCP (MUDOU — importante):**
- O relatório HTML do RHID agora abre como **visualizador PAGINADO** ("Página 01 de 17"), 1 colaborador por vez. NÃO vem mais com todos os cartões no DOM na primeira carga.
- ⚠️ **NUNCA chamar `scope.openAll()`** — tenta renderizar as N páginas de uma vez e **TRAVA o renderer** (mesma dor do "Imprimir Tudo"). Foi preciso fechar a aba.
- ✅ **Truque que funcionou:** depois que o `openAll` travou e fechei a aba, **reabrir o mesmo GUID numa aba nova** (`reporthtml.html#/html/{guid}`) renderizou TODAS as ~137 tabelas de uma vez e responsiva. Ou seja: reabrir o GUID = relatório completo no DOM. Extração via anchor "Nome do funcionário" + tabela seguinte com "Total Trabalhado".
- O escopo Angular do controller tem `people_opt` (lista das pessoas) e `funcProximo()`/`personIndex` (navegação 1 a 1) caso precise paginar manualmente.
- O retorno do `javascript_tool` **trunca em ~3KB na exibição** mesmo com a string maior. Puxar dados em fatias de ~2 colaboradores por chamada (ou browser_batch com vários slices).
- **Desalinhamento de coluna:** ENT.1..SAÍ.3 estão nos índices 4-9 (confiáveis). Total Normais/Trabalhado/Intervalo ficam DESLOCADOS -1 vs o cabeçalho. Não usar essas colunas calculadas; recalcular intervalo das batidas reais.

**Regra de classificação de dia (classify_day) — folga/férias deferida vence escala:**
- Quando escala dizia JORNADA mas o cartão marca explicitamente "Folga"/"Folga Domingo Trabalhado"/"Folga Feriado"/"Férias" (refletido nas Alterações: "Folga habilitada em DD/MM", "Férias de ... a ..."), a marcação do **cartão VENCE** a escala publicada — é um deferimento posterior. Senão geram-se faltas falsas.
- "Escala vence" continua valendo no sentido inverso (RHID marca "Falta" mas escala diz folga → não é falta). As duas regras coexistem: o evento mais recente/deferido (folga habilitada, férias concedida) é o que vale.

**Casos S21:**
- **17/05 (domingo):** Silvio/Joelison/Grasiela tinham escala JORNADA (trabalham domingo) → regras aplicam, inclusive janela manhã 11-13h. Joelison cruzou 12:54-13:54 → janela proibida no domingo. Solange tinha escala F mas trabalhou → trabalhou_em_folga (REG-S4 INFO).
- **Robert sáb 16/05:** batida espúria **"04:00" na ENT.3** (cronologicamente impossível). Marcado MARCACOES_INCOERENTES + PULOU_INTERVALO (06:30→13:05, 6h35 sem pausa). RH precisa conferir/corrigir o "04:00" no RHID.
- **Jair 16/05:** falta seca real (escala 09:00-17:20, "Falta" total, sem atestado).
- **Grasiela** virou reincidente forte de janela proibida (3x) nos turnos 13:00-21:20 com intervalo cruzando 16:00.

**Sobre o orquestrador:** a skill canônica tem `scripts/run_jornada_completo.py` (comando único 2-8). Nesta rodada o pipeline foi remontado à mão (`outputs_s21/processar_s21.py` + `gerar_html_s21.py`) porque o plugin ativo estava na v3.2. Próxima rodada: rodar o instalador clicável ANTES pra garantir plugin na v3.3+, depois usar o orquestrador.

---

## Edge cases conhecidos a investigar

- [ ] Quando colaborador trabalha sem ter previsto na escala (folga indo trabalhar)
- [ ] Quando colaborador tem 4 ou mais pares de batida (situação rara mas possível)
- [ ] Como o RHID marca "Banco" no cartão (vimos em Daniel sáb 14/02 e seg 16/02)
- [ ] Como interpretar marcações com "(I)" (Incluído manualmente) — pode indicar correção pelo gestor

## Decisões pendentes

- [ ] **Alana**: tratada como suspenso/excluído via flag `--suspensos`. Confirmado regime alternativo na v3.3.
- [x] **Josemaria Maximiana**: RH desativou ✓ (S20 já sem ela na lista)
- [ ] **Threshold de "trend"**: Δ vs semana anterior — quanto conta como melhora/piora? (Atual: qualquer Δ ≠ 0)
- [ ] **Apuração**: a skill deve checar se a semana já foi "fechada" no RHID antes de rodar? (Pode ter dados ainda flutuando)
- [ ] **Renovação PAT**: token `claude-cowork-jornada-gran` expira **12/08/2026** — criar novo + atualizar .env antes

---

### 2026-05-14 — Pipeline ponta-a-ponta automatizado (v3.3)

**Contexto:** rodada S20 cobrindo 06/05 a 12/05. Hugo pediu automação completa, incluindo publish no GitHub Pages.

**Aprendizados:**
- **Extração RHID via fetch direto NÃO funciona** — endpoint `report.svc/get_html/?guid=...` retorna 1.6KB de página de erro Microsoft IIS pra requests programáticas. **Iterar via botão ">"** clica+extrai do DOM é o caminho confiável. ~3s por colaborador. Total ~1min pra 18 pessoas.
- **DOM tem `no-border` celulas intercaladas** como separadores visuais. Mapping de colunas: dia=0, previsto=2, ent1=4, sai1=5, ent2=6, sai2=7, ent3=8, sai3=9, total_normais=11, ..., bh_saldo=43. Linha de TOTAIS tem mesma estrutura.
- **Listagem people_opt** está em scope Angular do reporthtml — 18 colab com id+nome+cpf. Usar pra batch validation.
- **Transferência sandbox→Mac via download HTML Blob**: dispara download em `~/Downloads` mas sandbox não lê direto. Hugo precisa mover manualmente, OU usa request_cowork_directory.
- **Matching RHID↔Escala robusto**: token-based só (intersect) confunde "Elissandro Nascimento" com "Jair Nascimento". Solução: primeiro nome bate exato OU prefix-5, depois desempate por interseção. Funciona 18/18.
- **GitHub Pages auto-publish**: PAT fine-grained scope `Contents:RW` no repo apenas, salvo em `.env` (gitignored). Clone temporário em `/tmp/grm_publish_*`, push, e `rm -rf` no final.
- **Cartões "Falta" no meio do dia**: ex Daniel Pereira sex 08/05 — bateu ENT.1 e SAI.1 normais mas ENT.2/SAI.2 = "Falta" (parcial). Regra atual trata como `Falta` puro. Avaliar se deveria ser um caso à parte.
- **gerar_html.py refatorado**: HIST, SEMANA_ATUAL e DIAS_LABELS agora via env vars (`JORNADA_PROJECT_DIR`, `JORNADA_HIST_DIR`, `JORNADA_SEMANA_ARQUIVO`, `JORNADA_RESULTADOS_FILE`). Auto-detect do último JSON do `historico/` se não setado.

**Casos especiais S20:**
- **Fernanda Santos Mascarenhas (Cozinha)**: ENT.1 = 04:06 nas qua/qui/sex/sáb/seg (previsto 06:40). Pattern repetido — provavelmente padrão real dela. Gerou 6 horas extras na semana. Confirmar com Consultora se é convocação extra ou apenas rotina dela.
- **Jair Nascimento (ASG)**: 2 faltas secas sem justificativa. Primeira ocorrência em meses. Investigar.
- **Silvio Rouzan (Encarregado)**: 5 janelas proibidas — encarregado dando exemplo errado. Conversa direta com a gestão.
- **Emanuele Maciel e Luis Guilherme**: pulou intervalo + jornada >6h. Crítico CLT, escalar pra Consultora.

**Ação:** ✓ run_jornada_completo.py criado · ✓ SKILL.md v3.3 · ✓ notas registradas

---

## Padrão pra adicionar nova nota

```markdown
### YYYY-MM-DD — Título curto

**Contexto:** o que aconteceu

**Aprendizado:** o que extrair pra próxima rodada

**Ação:** atualizar arquivo X, perguntar Hugo, etc.
```

---

**Skill auto-melhora a cada rodada.** Hugo pode editar este arquivo direto se quiser registrar algo.
