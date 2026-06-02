# Workflow `/ritual-semanal` — Resumo semanal pro grupo Liderança

Comando rodado automaticamente pelo scheduled task **quarta 13h35** (15 min depois do ritual diário). Fecha o ciclo da semana qua-anterior → terça e posta no grupo [LIDERANÇA] Gran.

## Quando este workflow é acionado

- Scheduled task `passagem-turno-ritual-semanal` (quarta 13h35)
- Hugo digita `/ritual-semanal` manualmente

## Pré-requisitos antes de rodar

1. Chrome MCP conectado, WhatsApp Web logado (sessão da Fran)
2. `passagem-turno-superGran.xlsx` atualizado (ritual diário das últimas 7 dias rodou)
3. Ler `templates/whatsapp_resumo_semanal_lideranca.md`
4. Ler `templates/config.md` para nome do grupo

## Workflow ponta a ponta

### Passo 0 — Auditoria da pasta + Health check de sessão

1. **Auditar a pasta** `/Users/hugogusmao/Documents/Claude/Projects/[GRAN] Passagem de Turno/`. Conflito de versões = parar e perguntar ao Hugo.
2. **Health check de WhatsApp Web:** navegar pra `https://web.whatsapp.com`. Se ficar na tela de QR, postar 1 mensagem única no chat do Cowork e PARAR. Não postar nada no grupo.

### Passo 1 — Definir janela da semana

```python
hoje = date.today()  # sempre quarta
fim_semana = hoje - timedelta(days=1)  # terça
inicio_semana = hoje - timedelta(days=7)  # quarta anterior
```

### Passo 2 — Ler XLSX e filtrar avaliações da janela

Abrir `passagem-turno-superGran.xlsx` e extrair:

- Todas as linhas com data entre `inicio_semana` e `fim_semana`
- Separar por encarregado (Sílvio, Alyne)

**Cuidado:** mesma pessoa pode aparecer em Abertura E Tarde/Noite em dias diferentes.

### Passo 3 — Calcular métricas

Para cada encarregado:

```python
notas_silvio = [linha.nota for linha in linhas if encarregado(linha) == "Silvio"]
media_silvio = sum(notas_silvio) / len(notas_silvio)
n_silvio = len(notas_silvio)
```

Calcular também:
- Média da semana anterior → delta
- Pontuação por critério agregada → campo com pior média da semana

### Passo 4 — Identificar padrão da semana

Heurísticas (em ordem de prioridade):

1. Critério com pior média agregada nas 2 pessoas → "O ponto que mais apareceu na semana foi {CAMPO}..."
2. Se nenhum critério < 60%: critério com melhor média
3. Se médias muito estáveis (variação < 3pp): "Sem padrão recorrente esta semana..."

**Honestidade > completude.** Se não houver padrão claro, dizer que não há padrão.

### Passo 5 — Detectar queda relevante (alerta RH)

Se delta de Sílvio ou Alyne ≤ -8pp:

- Acrescentar linha no resumo: "Uma das operações teve queda relevante esta semana. Conversa 1:1 já agendada pra próxima segunda."
- **Não nomear quem caiu.** Preservar privacidade.
- Pingar Hugo no Cowork separadamente.

### Passo 6 — Gerar texto do resumo

Usar `templates/whatsapp_resumo_semanal_lideranca.md`. Selecionar variação apropriada:
- Padrão: variação "Esqueleto" simples
- 1 encarregado em afastamento: variação correspondente
- Primeira semana: variação "Primeira semana de rodagem"
- Queda relevante detectada: variação com alerta

### Passo 7 — Enviar no grupo de Liderança

**Guarda-rails:**
- Confirmar envio via screenshot
- Se grupo não for encontrado, pingar Hugo
- NUNCA postar duas vezes na mesma quarta

### Passo 8 — Registrar em log

`data/log_resumos_semanais.csv`

### Passo 9 — Resposta no chat do Cowork

```
✅ Resumo semanal enviado — Janela {INICIO} a {FIM}

▸ Sílvio: {X}% ({N} avaliações) {DELTA}
▸ Alyne: {Y}% ({N} avaliações) {DELTA}

Padrão: {DESCRIÇÃO_CURTA}

🔗 Postado em: [LIDERANÇA] Gran
```

---

## Falhas e fallbacks

| Falha | Ação |
|---|---|
| XLSX não atualizado | Pingar Hugo: "Faltam {N} avaliações na semana." |
| Grupo de Liderança não encontrado | Pausar. Pedir confirmação. |
| WhatsApp Web deslogado | Pingar Hugo. Sem retry automático. |
| Erro na geração do texto | Apresentar 2-3 versões pro Hugo escolher |

---

## Notas operacionais

**Por que quarta 13h35:** 15 min depois do ritual diário. Garante que a média da semana já está atualizada no XLSX.

**Por que ciclo qua → ter:** mesmo padrão do monitoramento-jornada-gran. Quarta é dia de "fechamento" semanal da liderança operacional do Gran.

**Por que postar no grupo de Liderança em vez de criar relatório separado:** normalizar a presença do sistema de avaliação na rotina da Liderança sem expor individuos. Resumo curto chega, RH lê, ninguém é pego de surpresa.
