# Template de Prompt · Extração KW (ad-hoc)

Use este template quando precisar de uma extração ad-hoc fora do fluxo normal do `/survey` (ex: gap histórico, re-extração de período problemático, janela arbitrária).

Para o fluxo normal de fechamento semanal, **prefira `/survey`** — ele faz tudo (detecta janela, extrai, consolida, gera HTML).

---

## Como preencher o template

Substitua os placeholders entre `[ ]`:

- `[INI]` e `[FIM]`: datas DD/MM/AAAA
- `[N_DIAS]`: número de dias entre INI e FIM (inclusive)
- `[CAMINHO]`: A (Chrome MCP no Mac) ou B (AnyDesk + Python na SAMSUNG)

Calcular volume esperado pela tabela em `conhecimento/extracao_kw_local.md` (faixas calibradas por número de PDVs ativos).

---

## Template (copiar daqui)

```
Execute uma EXTRAÇÃO DE VENDAS AD-HOC no KW.

Hugo está acompanhando. Execute autonomamente. Só interrompa para decisões reais.

## OBJETIVO
Extrair vendas de [INI] a [FIM] ([N_DIAS] dias).
Motivo: [explicar — gap histórico, re-extração, etc].

## CAMINHO
[A | B]
A = Chrome MCP local (Hugo na rede do KW).
B = AnyDesk + Python na SAMSUNG (Hugo fora da rede). Antes, ler `manual_anydesk.md`.

## DOMÍNIO DO KW
Ler de `conhecimento/dominio_kw.txt`. Se vazio, perguntar Hugo e gravar.

## PARÂMETROS
- Endpoint: /ferramentas/relatorios/lista_mercadorias_vendidas/selecaocsv.php
- PDVs: vazio (todos)
- Período: [INI] → [FIM]
- Janelas: máx 30 dias/request. Se [N_DIAS] > 30, dividir em janelas ≤30.

## CÓDIGO
Use o script de Fase 5/3 do arquivo `extracao_kw_anydesk.md` (caminho B) ou `extracao_kw_local.md` (caminho A). Ambos têm:
- Assert cookie jar não vazio
- Fallback de timeout (auto-partir janela em 2)
- Encoding utf-8-sig → utf-8 → windows-1252
- Salvar em `~/Documents/SurveyGran/extracoes/incoming/`

## VALIDAÇÃO
Faixas esperadas (depende de PDVs ativos no período):
- Antes de 26/01/2026 (2 PDVs): 1.000-1.700 linhas/dia, 240-360 cupons/dia, R$ 11k-19k/dia
- Desde 26/01/2026 (3 PDVs): 1.200-1.800 linhas/dia, 280-400 cupons/dia, R$ 14k-21k/dia

PARAR se:
- Cookie jar vazio
- Status ≠ 200 ou redirect login
- ≥3 dias consecutivos zerados (e nenhum é feriado em `feriados_2025_2026.md`)
- Faturamento total < 60% do mínimo esperado

ALERTAR (não-bloqueante) se:
- Faturamento médio diário < R$ 8k
- Volume um dia abaixo da faixa mas dentro de feriado/sábado pós-feriado

## RELATÓRIO FINAL
=== EXTRAÇÃO AD-HOC CONCLUÍDA ===
Período: [INI] a [FIM] ([N_DIAS] dias)
Arquivos: ~/Documents/SurveyGran/extracoes/incoming/<arquivo>.csv

Total linhas: X
Total cupons: X
Faturamento total: R$ X
PDVs presentes: [...]
Dias com registro: X de [N_DIAS]

Anomalias:
- [listar dias fora da faixa, dups exatas, encoding usado, etc]

## PRÓXIMO PASSO
Rodar `pipeline_consolidacao.py` para anexar à base e re-classificar.

Pode começar.
```

---

## Boas práticas

- **Não modifique o código embarcado** nos arquivos de conhecimento (`extracao_kw_*.md`). Os scripts já têm os asserts e fallbacks. Use o template só para dar contexto e definir a janela.
- **Volume esperado** é o sinal mais importante. Se for muito abaixo, é melhor PARAR e investigar do que prosseguir com base furada.
- **Mecanismos de PARAR**: usar `AskUserQuestion` ou `sys.exit('PARAR: motivo')`. Print solto não chega.
- **Domínio do KW**: o arquivo `conhecimento/dominio_kw.txt` evita perguntar a cada execução.
