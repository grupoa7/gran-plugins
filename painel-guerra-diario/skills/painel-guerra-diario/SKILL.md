---
name: painel-guerra-diario
description: Pipeline completo do Painel de Guerra do Gran Hortifruti — consome XLS extraídos automaticamente da SAMSUNG via Dropbox, roda motor v7 calibrado, render mobile-first e deploy GitHub Pages. Use SEMPRE que Hugo mencionar /painel-atualizar, /painel-status, /painel-share, atualizar painel, rodar BI, deploy painel, painel de guerra, ou pedir consolidado/atualização do BI operacional da loja Gran Caminho das Árvores. NÃO use para Survey semanal de vendas — use survey-gran. NÃO use para auditoria de caixas — use auditoria-caixas-gran.
---

# Painel de Guerra Diário — Gran Hortifruti

Você opera o **BI operacional 3x/dia** do Gran Hortifruti (loja única — Caminho das Árvores, Salvador/BA), atualizando https://grupoa7.github.io/painel-guerra-gran/ com a venda do dia, alvos por departamento, KPIs e ritmo intra-dia.

Hugo gerencia 110 pessoas, tem TDAH, opera no celular. **Painel é o único termômetro acionável da loja**.

## Arquitetura (atualizada 2026-05-09)

```
SAMSUNG (PC da loja, Windows, user "suporte")
  Task Scheduler 11:00 / 16:00 / 21:30
    extract_kw_daily.py: login KW → GET CSV → salva xls
      ↓
C:\Users\suporte\Dropbox\Operacoes GRAN\painel-guerra-csv\YYYY-MM-DD\HH-MM.xls
      ↓ (Dropbox sync automático)
~/Dropbox/Operacoes GRAN/painel-guerra-csv/YYYY-MM-DD/HH-MM.xls   ← Mac do Hugo
      ↓
ESTA SKILL (Mac do Hugo, Cowork)
  /painel-atualizar:
    1. Detecta XLS novo (mais recente no dia)
    2. Parser → kw_transacoes_v3.parquet
    3. Motor v7 + Render v9
    4. Health check (residual <1%)
    5. Push GitHub Pages
      ↓
https://grupoa7.github.io/painel-guerra-gran/
      ↓
Hugo abre no celular
```

**Health-check Mac (launchd 22:30 diário)** já instalado: se chegou <3 arquivos no dia, cria `~/Desktop/⚠️_KW_FALHANDO.txt` com diagnóstico.

Detalhes da extração SAMSUNG: ver `SAMSUNG_AUTOMATION_README.md` na raiz do projeto.

## Princípios Inegociáveis

1. **Dados reais ou nada.** Nunca inventar venda, alvo ou KPI. Se XLS do dia não existir no Dropbox, abortar e avisar.
2. **Residual DEPT=None < 1%.** Se alguma rodada gerar residual >1%, abortar push e investigar.
3. **Hierarquia visual já aprovada (v9):** Hero → Destaques sem venda → Âncoras → Booster → Departamentos (piores no topo).
4. **Cores:** 🔴 < 85% / 🟡 85-99% / 🟢 ≥ 100% (vocabulário operacional do time).
5. **80/20:** focar em informação acionável. Sem ruído. Sem novo card sem aprovação do Hugo.

---

## Comandos

### `/painel-atualizar` (principal)

Pipeline completo. Lê arquivo do Dropbox (NÃO extrai mais — extração é 100% automática na SAMSUNG):

1. **Auto-melhoria pré-flight** (`scripts/auto_melhoria.py`) — sync master ARIUS, calibrar regex faltantes
2. **Detecta XLS do dia** (`scripts/extrair_kw.py`) — pega o mais recente em `~/Dropbox/Operacoes GRAN/painel-guerra-csv/YYYY-MM-DD/`. Aborta se nenhum arquivo do dia ou se mais antigo que `--max-idade-horas` (default 4h).
3. **Parser KW** — XLS → `data/processed/kw_transacoes_v3.parquet` (lógica em `scripts/parser_kw_v4.py`)
4. **Motor v7 + Render v9** — `python scripts/v7/render_v9.py` (gera HTML mobile-first)
5. **Health check** — residual <1%, totais batem, 12 deptos presentes. Aborta push se falhar.
6. **Deploy GitHub Pages** — copia BIs pra `/tmp/pg-deploy/painel-guerra-gran/`, regenera `index.html`, commit + push SSH
7. **Auto-melhoria pós-flight** — atualiza `notas_operacionais.md` com aprendizados (tempo, novos produtos, gargalos)
8. **Mensagem WhatsApp** — gera resumo pro grupo da loja com link

Argumentos (opcionais):
- `data="2026-05-09"` (default: hoje)
- `hora_corte=11|16|None` (default: detecta pela hora do XLS mais novo; None = fim do dia)
- `--skip-extract` — usa parquet existente (debug, sem reprocessar XLS)
- `--no-push` — só gera HTML local (debug)
- `--max-idade-horas=N` — quanto tempo o XLS pode ter pra ser aceito (default 4h)

### `/painel-status`

Mostra:
- Último deploy (timestamp + commit)
- XLS mais recente do Dropbox (path, idade, tamanho)
- Próxima execução agendada na SAMSUNG (calculada por horário atual)
- Residual atual, % órfãos
- Alertas pendentes do `notas_operacionais.md`
- Status do `~/Desktop/⚠️_KW_FALHANDO.txt` (existe ou não)

### `/painel-share`

Gera mensagem pronta pra colar no grupo de WhatsApp da loja com link do BI mais recente, totais do dia e top 3 ofensores.

---

## Arquivos do projeto

```
[GRAN] Survey/
├── SAMSUNG_AUTOMATION_README.md      # Pipeline SAMSUNG (extração 3x/dia)
├── MANUAL_SETUP_SAMSUNG_v2.md         # Histórico do setup remoto
├── scripts/
│   ├── healthcheck_kw.py              # Mac launchd 22:30 (já ativo)
│   ├── com.granhortifruti.kw_healthcheck.plist
│   └── install_healthcheck.command    # Já executado
└── painel-guerra/
    ├── scripts/
    │   ├── parser_kw_v4.py            # Parser XLS KW → parquet (autoritativo)
    │   └── v7/
    │       ├── motor.py               # Motor v7 calibrado (MAPE 11,3%)
    │       ├── render_v9.py           # Renderer mobile-first
    │       └── reclassificar_na.py
    ├── data/
    │   ├── raw/                       # Cópia do XLS mais recente (cache local)
    │   ├── processed/
    │   │   ├── kw_transacoes_v3.parquet         # Transações
    │   │   ├── cadastro_arius_master.parquet    # Master EAN→DEPT (4.172 EANs)
    │   │   └── v5/fator_*.parquet                # Fatores sazonalidade
    │   └── calendario/calendario_hugo.parquet
    ├── output/                        # BIs HTML gerados localmente
    └── skill_package/painel-guerra-diario/
        ├── SKILL.md                   # Este arquivo
        └── scripts/
            ├── pipeline.py            # Orquestrador
            ├── extrair_kw.py          # Detecta XLS no Dropbox + parsea
            ├── auto_melhoria.py
            ├── health_check.py
            ├── deploy.py
            ├── notas_operacionais.md
            └── changelog.md
```

**Path do Dropbox (fonte de verdade):**
- Mac: `~/Dropbox/Operacoes GRAN/painel-guerra-csv/YYYY-MM-DD/HH-MM.xls`
- SAMSUNG: `C:\Users\suporte\Dropbox\Operacoes GRAN\painel-guerra-csv\YYYY-MM-DD\HH-MM.xls`

---

## AUTO-MELHORIAS TÉCNICAS (sem pedir aprovação)

A cada rodada, executar `scripts/auto_melhoria.py` que pode automaticamente:

1. **Sincronizar master ARIUS** — se houver `*estoque*arius*.xlsx` mais novo na pasta uploads, regenerar `cadastro_arius_master.parquet`
2. **Detectar novos produtos órfãos** — produtos sem GRUPO E sem EAN no master → log `notas_operacionais.md` pra Hugo cadastrar no Arius
3. **Calibrar regex de descrição** — quando residual > 0,5%, adicionar palavras-chave detectadas em `map_descricao_to_dept`
4. **Otimizar tempo** — se etapa demora > 60s, log gargalo e tentar paralelizar/cachear
5. **Auto-rollback** — se health_check falhar, reverter commit e manter último BI bom no ar
6. **Cachear se sem novidade** — se total e DEPT breakdown ≈ idêntico ao último, skip render
7. **Detectar drift do motor** — se erro abs(real - alvo) por dept exceder 30% por 3 dias seguidos, log alerta de recalibração
8. **Garbage collect** — manter só últimos 30 dias de BIs no GitHub Pages (zera bloat)
9. **Detectar XLS atrasado** — se XLS mais novo do Dropbox > 4h e for horário comercial, log alerta no `notas_operacionais.md` e checar `~/Desktop/⚠️_KW_FALHANDO.txt`

Tudo isso silencioso, atualiza `notas_operacionais.md` e segue o pipeline.

---

## SUGESTÕES QUALITATIVAS (sempre perguntar antes)

Quando detectar oportunidade de melhoria QUALITATIVA, NÃO aplicar automaticamente. Em vez disso, criar entrada em `scripts/sugestoes_pendentes.md` E perguntar ao Hugo no fim da rodada:

> "Detectei N sugestões qualitativas a avaliar:
> 1. [descrição da sugestão]
> 2. [...]
> Quer revisar agora?"

**Categorias de sugestões qualitativas (sempre perguntam):**
- Mudança de cor, fonte ou layout
- Novo card, KPI ou métrica
- Reorganização de hierarquia visual
- Mudança no tom/copy da mensagem WhatsApp
- Nova lógica de previsão (ex: incluir clima, temperatura)
- Mudança em thresholds (ex: ajustar 85%/100% pra 90%/110%)
- Inclusão de comparativos novos (vs concorrente, vs ano passado)
- Modificar mapeamento DEPT (juntar/separar departamentos)

---

## Cadência

**Extração na SAMSUNG (automática, 3x/dia):**
- 11:00 — parcial manhã
- 16:00 — parcial tarde
- 21:30 — fim do dia

Cada extração gera `~/Dropbox/Operacoes GRAN/painel-guerra-csv/YYYY-MM-DD/HH-MM.xls`.

**Atualização do BI no Mac (skill):**
- Pode ser disparada a qualquer momento via `/painel-atualizar`
- Recomendado: rodar pouco depois de cada extração (ex: 11:05, 16:05, 21:35)
- Em uma sessão Cowork agendada (futuro), pode disparar automático ao detectar arquivo novo no Dropbox

**Health-check Mac (automático, 22:30):**
- launchd já instalado (`~/Library/LaunchAgents/com.granhortifruti.kw_healthcheck.plist`)
- Roda `~/Documents/Claude/Projects/[GRAN] Survey/scripts/healthcheck_kw.py`
- Se < 3 arquivos no dia, cria `~/Desktop/⚠️_KW_FALHANDO.txt` com diagnóstico

---

## Recuperação de falhas (catch-up automático)

**Toda rodada começa com `catch_up.py` antes do pipeline principal.** Ele:

1. Olha os últimos 14 dias no Dropbox
2. Pra cada dia que tem XLS de fechamento (>= 21h) mas **não** tem `BIv9_YYYYMMDD_fim.html` em `output/`, processa parser + render fim de dia
3. Acumula tudo num único deploy ao final

**Garantia:** se uma rodada falhar (SAMSUNG desligada, Dropbox dessincronizado, erro pontual), a próxima rodada bem-sucedida resgata os fechamentos pendentes automaticamente. **Nunca fica fechamento perdido.**

Casos cobertos:
- SAMSUNG desligada por engano numa noite → próxima rodada (ex: 11h do dia seguinte) processa o fechamento de ontem
- Sandbox Cowork sem mount Dropbox numa rodada → próxima rodada com Dropbox disponível resgata
- Falha pontual no render/deploy → mantém o BI antigo no ar; próxima rodada redeploya correto

Argumentos do pipeline.py:
- `--catch-up-janela 14` — janela de dias pra trás (default 14)
- `--no-catch-up` — desliga catch-up (debug)

Se Dropbox está indisponível, `catch_up.py` retorna 0 sem falhar (pipeline segue normal — a rodada principal pode até falhar depois, mas a próxima resgata).

---

## Acesso ao Dropbox via Cowork sandbox

Quando a skill roda como **scheduled task no Cowork**, o sandbox Linux **não monta o Dropbox automaticamente**. Solução: symlink dentro do projeto.

**Setup (1x, no Mac):** rodar `~/Documents/Claude/Projects/[GRAN] Survey/setup_dropbox_symlink.command` (duplo-clique no Finder). Cria:

```
[GRAN] Survey/painel-guerra/data/dropbox-mirror → ~/Dropbox/Gran Hortifruti/Operacoes GRAN/painel-guerra-csv
```

`extrair_kw._resolve_dropbox()` reconhece esse symlink antes do path nativo Mac. Funciona tanto no Cowork quanto rodando direto no Mac.

---

## Tratamento de Erros

- **XLS do dia ausente no Dropbox** → não gerar BI, alertar Hugo, manter último BI bom no ar. Sugerir checar AnyDesk SAMSUNG → Task Scheduler.
- **XLS muito velho (>4h)** → avisar Hugo (extração pode estar atrasada). Continua se Hugo confirmar `--max-idade-horas=24`.
- **Residual > 1%** → não dar push, alertar Hugo, salvar BI gerado em `output/QUARANTENA/`
- **Falha render** → não dar push, alertar Hugo, manter último BI
- **Falha push GitHub** → tentar 3x com backoff, alertar Hugo
- **Dropbox dessincronizado** → detectar via `~/Desktop/⚠️_KW_FALHANDO.txt` ou idade do XLS. Pedir Hugo verificar status do Dropbox.

Sempre preferir "BI desatualizado mas correto" a "BI atualizado com dado errado".

---

## Mudanças vs versão anterior

**v3 (2026-05-09 noite)** — recuperacao de falhas:
- Adicionado: `catch_up.py` roda no Step 0 de toda rodada — recupera fechamentos pendentes automaticamente
- Adicionado: suporte a symlink `[GRAN] Survey/painel-guerra/data/dropbox-mirror/` em `_resolve_dropbox()` — funciona no sandbox Cowork
- Adicionado: `setup_dropbox_symlink.command` na raiz do projeto pra Hugo rodar 1x
- Bug fix: `_resolve_dropbox()` aceitava `Path('')` vazio (resolvia pra `./`)
- Garantia operacional: nunca fica fechamento perdido. Falha → próxima rodada resgata.

**v2 (2026-05-09)** — pipeline simplificado:
- Removido: extração via Chrome MCP / AnyDesk (era manual e frágil)
- Adicionado: leitura direta do Dropbox (extração agora é automática na SAMSUNG)
- Adicionado: integração com health-check Mac (launchd)
- `extrair_kw.py` agora é apenas detector + parser (não mais extrator)

**v1 (anterior)** — extração via Chrome MCP local OU AnyDesk SAMSUNG (depreciado).

## Responda em PT-BR. Comunicação direta, sem inflar texto.
