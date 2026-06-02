---
name: triagem-whatsapp-compras
description: |
  Triagem do WhatsApp da Compras do Gran Hortifruti (número (71) 99642-8061 — Marize). Varre conversas 3× por semana (seg/qua/sex 01h-02h30, America/Bahia), classifica em 7 categorias (Cotação, Confirmação/Logística, Financeiro, Problema, Oferta, Interna, Ruído), identifica threads abertas e entrega panorama no grupo "Super Gran" em 2 mensagens (resumo + drill-down). HTML local serve de memória. Use SEMPRE que Hugo mencionar triagem, triagem WhatsApp, Compras WhatsApp, /triagem, /triagem-rodada0, /triagem-status, varredura do WhatsApp da Marize, panorama Compras, painel Compras, categorizar mensagens da Compras, threads abertas Compras, ou qualquer tarefa de triagem do canal WhatsApp da área de Compras. Janela proibida seg+qua 03h-08h respeitada via scripts/janela_critica. NÃO use para WhatsApp pessoal do Hugo. NÃO use para cotação FLV (use cotacao-flv-gran). NÃO use para NPS/CRM/receptivo Gran (skills próprias).
---

# Triagem WhatsApp Compras — [GRAN] WhatsApp Compras

> Frente: **Triagem de mensagens (frente #1 do escopo evolutivo)**
> Status: **Esqueleto + rodada 0 pendente. NÃO está em operação 3×/semana ainda.**
> Última atualização: 2026-05-30
> Spec congelado: [`SPEC.md`](./SPEC.md) v0.3
> Primeira rodada: [`RODADA-0.md`](./RODADA-0.md)

---

## 1. Dor atendida

Marize hoje processa ~1 número de WhatsApp da Compras como hub bruto: cotações, NFs, confirmações, reclamações, listas de transmissão e ruído puro misturados. Tempo dela vai embora em rolar a inbox; risco de NF/boleto/reclamação crítica vazar é alto.

Esta skill devolve uma **caixa de entrada triada, priorizada e acompanhada** — 3× por semana, panorama curto no grupo, sem ela precisar abrir o aplicativo pra saber o estado da fila.

**Move qual ponteiro do KPI-mãe (produtividade da Marize)?**
- [x] Tempo no WhatsApp ↓ (panorama substitui scroll)
- [x] Tempo até resposta a fornecedor crítico ↓ (🚨/⚠️ no painel)
- [x] Pedidos sem follow-up = 0 (threads abertas explícitas)
- [x] Risco de mensagem perdida ↓ (categorização exaustiva, sem "indefinido")

---

## 2. Comandos

| Comando | O que faz | Disponibilidade |
|---|---|---|
| `/triagem-rodada0` | Calibração inicial sobre backlog. **NÃO é panorama operacional.** Lógica de 4 faixas etárias — ver [`RODADA-0.md`](./RODADA-0.md). | Primeira execução da skill — única vez |
| `/triagem` | Pipeline operacional completo (boot → coleta → classificação → agregação → entrega → persistência). 3×/sem (seg/qua/sex 01h-02h30). | Liberado após calibração da rodada 0 |
| `/triagem-status` | Diagnóstico sem tocar WhatsApp: janela crítica, última rodada, threads abertas em memória, tokens consumidos no mês. | Sempre |

Convenção: a skill **nunca dispara automaticamente** no MVP. Hugo invoca o comando (manual ou agendado via `mcp__scheduled-tasks`). O scheduler só agenda depois que a rodada 0 fechar.

---

## 3. Workflow operacional (`/triagem`)

> Fluxo da operação 3×/semana. Para a primeira rodada (backlog), ver [`RODADA-0.md`](./RODADA-0.md).

1. **Pré-checagem** — `scripts/janela_critica.exigir_fora_da_janela()`. Aborta se na janela seg+qua 03h-08h. Também aborta sáb/dom integral (regra da skill).
2. **Validação visual de boot** — screenshot da tela inicial do WhatsApp Desktop. Compara com layout conhecido. **Falhou? Aborta + posta no grupo Super Gran: "triagem falhou — manual hoje".** Loga em `dados/logs/`.
3. **Coleta incremental** — itera chats via `mcp__computer-use`. Usa cursor por chat (timestamp da última msg lida na rodada anterior). Reprocessa chats com thread aberta marcada. Salva bruto em `dados/estado/triagem-whatsapp-compras/mensagens/AAAA-MM-DD.jsonl`.
4. **Classificação** — aplica 7 categorias do §2 do SPEC + score 0-1. Detecta autor (Marize via lado do balão verde-claro vs cinza/escuro). Atualiza ou abre threads em `threads.jsonl`.
5. **Agregação** — top 5 ações, contagens por categoria, idade de threads abertas, marca críticas com 🚨 (financeiro venc. ≤48h) / ⚠️ (problema grave).
6. **Aprovação Hugo** — toda mensagem que sairia em nome da Compras passa por aqui (§5). No MVP da triagem, **só sai uma mensagem ao mundo**: o panorama no grupo Super Gran. Aprovação dele exigida na primeira semana; após N panoramas aprovados sem edição, libera autonomia (decisão futura, não MVP).
7. **Entrega** — 2 mensagens no grupo Super Gran (Msg 1 resumo, Msg 2 drill-down). Dia vazio: msg única "✅ Nada pra ação hoje. Volume: X msgs, Y% ruído."
8. **Persistência + log** — atualiza identidade, VIP orgânico, cursor por chat. Gera HTML local. Loga métricas em `dados/logs/triagem-whatsapp-compras/AAAA-MM-DD.jsonl`. Hard stop 02h30: se não terminou, posta parcial e loga `parcial=true`.

---

## 4. Persistência

Conforme §5.5 do `CLAUDE.md` e §3 do `PRIVACIDADE.md`.

| Dado | Pasta | Formato | TTL | Justificativa |
|---|---|---|---|---|
| Cursor por chat (última msg lida) | `dados/estado/triagem-whatsapp-compras/cursor.json` | JSON | indefinido | sem isso, recoleta tudo a cada rodada (custo proibitivo) |
| Identidade do remetente (salvo? VIP orgânico? broadcast?) | `dados/estado/triagem-whatsapp-compras/identidade.json` | JSON | indefinido | base da classificação e VIP orgânico |
| Threads abertas (chat_id, tipo, abertura, deadline, status) | `dados/estado/triagem-whatsapp-compras/threads.jsonl` | JSONL append | até fechamento + 30d | medir KPI primary (threads fechadas no prazo) |
| Decisões de Hugo (panorama aprovado/editado; aprovação batch da rodada 0) | `dados/aprovacoes/AAAA-MM.jsonl` | JSONL | 12 meses | rastreabilidade + pavimenta autonomia futura |
| Log de rodada (start, fim, tokens, screenshots, falhas, parcial?) | `dados/logs/triagem-whatsapp-compras/AAAA-MM-DD.jsonl` | JSONL | 90 dias | debug + estimativa de custo + auditoria |
| Mensagens classificadas (bruto da coleta) | `dados/estado/triagem-whatsapp-compras/mensagens/AAAA-MM-DD.jsonl` | JSONL | 30 dias | reprocessamento se calibração mudar; **classe Comercial/Conteúdo bruto — NÃO vai pra logs** |
| Panorama HTML local | `dados/estado/triagem-whatsapp-compras/panorama/AAAA-MM-DD.html` | HTML | 90 dias | memória + auditoria opcional do Hugo |
| Calibração (régua de legítimo, limiar de confiança, exclusões prévias) | `dados/estado/triagem-whatsapp-compras/calibracao.json` | JSON | indefinido (sobrescrito em recalibração) | parâmetros vivos da skill — produzido pela rodada 0 |

**Classes de dado (`PRIVACIDADE.md`):**
- `mensagens/*.jsonl` carrega **Comercial** (preço de fornecedor) e **Conteúdo bruto** (texto integral) → fica em `estado/`, nunca em `logs/`. TTL 30d.
- `aprovacoes/*.jsonl` pode conter conteúdo do panorama → 12 meses, conforme política.
- `logs/*.jsonl` só métrica operacional. **Zero conteúdo de mensagem.**

---

## 5. Aprovação Hugo

No MVP, **a única mensagem que sai em nome da Compras** é o panorama no grupo Super Gran. Rascunho apresentado assim:

```
🛒 Panorama Compras — {dd/mm} 01h-02h
[corpo da Msg 1]
---
[corpo da Msg 2]

[A]provar e enviar  |  [E]ditar  |  [R]ejeitar  |  [P]ular hoje
```

Aprovação obrigatória nas primeiras 4 semanas (12 panoramas). Cada decisão grava em `dados/aprovacoes/AAAA-MM.jsonl` no schema declarado em `dados/aprovacoes/README.md`. Depois disso, Hugo decide se libera envio direto (default) e reserva edição manual.

**Caso especial — rodada 0:** aprovação batch para "marcar como lida" chats >60d. Hugo vê o volume agregado (ex: "47 chats >60d candidatos a marcar lida — confirma?"), aprova uma vez, skill executa o batch. Decisão registrada em `aprovacoes/` com `categoria=batch_marcar_lida_rodada0`.

---

## 6. Limites declarados

Esta skill **não faz**:
- Não responde fornecedor. Só posta panorama no grupo Super Gran.
- Não cancela, confirma ou edita pedido. Só identifica e categoriza.
- Não toca WhatsApp pessoal do Hugo (instância separada — Safari/Web).
- Não opera fora da janela 01h-02h30 seg/qua/sex (e nunca dentro de seg+qua 03h-08h).
- Não escala mensagem fora do ciclo. Críticas viram 🚨/⚠️ no próximo panorama (reavaliar em 4 semanas).
- Não inventa nome de fornecedor, valor, prazo ou histórico. Marca `revisar` se ambíguo.
- Não decide preço, prioridade comercial ou aprovação de produto. Marize/Hugo decidem.

---

## 7. Quando falhar

| Falha | Comportamento |
|---|---|
| Janela crítica ativa (seg+qua 03h-08h) | `JanelaCriticaError` no boot. Aborta sem tocar WhatsApp. |
| Sáb/dom | Aborta no boot (regra da skill, não do `janela_critica`). |
| WhatsApp Desktop fora de foco / não logado | Aborta. Posta no Super Gran: "triagem falhou — manual hoje". Loga screenshot do estado. |
| Layout do WhatsApp mudou (validação visual de boot falhou) | Idem acima. Hugo recalibra layout antes da próxima rodada. |
| Hard stop 02h30 atingido | Posta panorama parcial. Loga `parcial=true` + nome dos chats não processados (vão pro topo da próxima rodada). |
| Msg ambígua (`confiança<0.6`) | Vai pra aba "Revisar" do HTML local. **Não entra no top do panorama.** |
| Detecção "lado do balão" falhou (chat com muita mídia) | Marca thread com `autor=desconhecido`. KPI primary não conta esses casos até calibrar (rodada 0 testa em ≥50 chats). |

---

## 8. Métricas a expor

Logadas em `dados/logs/triagem-whatsapp-compras/AAAA-MM-DD.jsonl` ao final de cada rodada.

**KPI primary (calibrar pós-4 semanas):**
- `% threads fechadas no prazo / total threads vencidas no período`, por tipo (tabela §7 do SPEC).

**Secundários:**
- `% conversas relevantes deixadas em aberto pela Marize` (era primary no v0.2).
- `taxa de ruído (broadcasts + propaganda) / total`.
- `idade média de threads abertas pendentes`.

**Operacionais (custo + saúde):**
- `tokens_input`, `tokens_output`, `screenshots_tirados`, `chats_processados`, `chats_pulados`, `duracao_s`, `parcial`.
- `% rascunhos do panorama aprovados sem edição` (proxy de qualidade da agregação).
- `tempo médio Hugo aprovando` (proxy de fricção).

Sem métrica = não dá pra provar que move o KPI-mãe.

---

## 9. Referências cruzadas

- Spec congelado: [`SPEC.md`](./SPEC.md) v0.3 — fonte da verdade das decisões fechadas.
- Primeira rodada: [`RODADA-0.md`](./RODADA-0.md) — calibração sobre backlog, lógica de 4 faixas etárias.
- Base do projeto: `../../../CLAUDE.md`, `../../../PRIVACIDADE.md`, `../../../dados/README.md`.
- Guardião da janela: `../../../scripts/janela_critica.py`.
