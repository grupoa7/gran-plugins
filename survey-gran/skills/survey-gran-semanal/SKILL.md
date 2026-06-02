---
name: survey-gran-semanal
description: Geração semanal do Survey Gran — relatório executivo de vendas com YoY ajustado por feriado móvel. Use SEMPRE que Hugo mencionar Survey, relatório semanal Gran, fechamento da semana, /survey, rodar Survey, gerar Survey, atualizar Survey, atualização semanal, ou qualquer tarefa relacionada ao consolidado semanal de vendas do Gran Hortifruti. Inclui workflow completo: extração KW (Chrome MCP local OU AnyDesk SAMSUNG), classificação ARIUS+KVI em cascata, comparação YoY com ajuste por feriado, e geração do HTML final v12. NÃO use para auditoria de caixas — use auditoria-caixas-gran. NÃO use para CRM — use crm-proativo-gran.
---

# Skill: Survey Gran Semanal

## Visão geral

Este skill gera o **Survey Gran** — relatório executivo HTML interativo com 11 abas analisando a última semana fechada do Gran Hortifruti (cadência **quarta → terça**), comparando com:

- Última semana (LW)
- Média 4 semanas anteriores (L4W)
- Média 8 semanas anteriores (L8W)
- Mesma semana ano anterior (YoY) — com **ajuste automático por feriado móvel**

A semana atual é sempre a **última semana terça-encerrada**. Por exemplo, se hoje é quarta 22/04/2026, a semana atual é S13 (15-21/04/2026).

## Entrada

```
/survey
```

ou trigger natural: "rodar Survey", "fechar semana Gran", "atualizar Survey", "gerar relatório semanal", "Survey atualizado".

## Saída

Arquivo HTML em `/Users/<usuario>/Documents/SurveyGran/relatorios/Survey_Gran_S{NN}_v12.html` (Mac) com 11 abas, cobertura ~97%, comparativos completos.

## Pré-requisitos

1. Pasta de trabalho local em `~/Documents/SurveyGran/` (será criada se não existir).
2. Acesso ao KW (rede local OU AnyDesk para a SAMSUNG).
3. Cadastro ARIUS atualizado (`export_base_arius.xlsx`) e tabela KVI (`kvi.xlsx`) salvos em `~/Documents/SurveyGran/cadastros/`.
4. Python 3.8+ instalado no Mac com pandas, numpy, openpyxl.

---

## Fluxo principal

### FASE 0 · Detectar contexto (defaults inteligentes — não perguntar redundantemente)

1. **Identificar usuário**: `whoami` → guardar em `<USERNAME>`.
2. **Caminho base**: `~/Documents/Claude/Projects/[GRAN] Survey/data/`. Override via `SURVEY_DATA_DIR` env var. NÃO perguntar a Hugo — path estável, conhecido.
3. **Verificar cadastros** (em `data/cadastros/`):
   - `export_base_arius.xlsx` — se ausente, PARAR e pedir para Hugo extrair via ARIUS.
   - `kvi.xlsx` — se ausente, PARAR e pedir para Hugo subir.
4. **Verificar base histórica + backup**:
   - `data/base/base_historica.pkl` — preferencial.
   - `data/base/base_historica.parquet` — fallback portável (mais robusto entre versões pandas).
   - `data/base/backup/{YYYY-MM-DD}/` — backups semanais automáticos.
   - Se nenhum existe: **primeira execução**, extrai histórico completo (~3-5 min com janelas quinzenais via Chrome MCP).
5. **Defaults silenciosos** (não pedir confirmação a menos que algo desvie):
   - Período: última semana fechada quarta→terça (calculado automaticamente)
   - Origem dos dados: Chrome MCP local (KW em `192.168.1.150`)
   - PDV 103 ausente: padrão operacional (esporádico) — **não alertar**, **não perguntar**

### FASE 1 · Calcular janela da semana

1. **Calcular última semana fechada (quarta→terça)**:
   - `hoje = data atual`
   - `ultima_terca = última terça-feira anterior a hoje`
   - `inicio_semana = ultima_terca - 6 dias` (= quarta)
   - `fim_semana = ultima_terca`
2. **Verificar se já foi processada**:
   - Ler `~/Documents/SurveyGran/base/ultima_semana_processada.txt`
   - Se for a mesma, perguntar Hugo se quer **regerar mesmo assim** ou **abortar**.
3. **Identificar gap de extração**:
   - Última data presente na base histórica = `ultima_data_base`
   - Janela a extrair = `(ultima_data_base + 1)` até `fim_semana`
   - Se janela > 30 dias, dividir em janelas de 30 dias.

### FASE 2 · Extrair dados do KW (Chrome MCP — caminho preferencial)

**Domínio fixo**: `192.168.1.150` (rede local da loja). Lido de `conhecimento/dominio_kw.txt`.

**Detecção automática de rede** (não perguntar):
1. Tentar `fetch('http://192.168.1.150/sistema/principal.php')` via Chrome MCP.
2. Se 200 e não redireciona para `/index.php` → na rede + logado → seguir Chrome MCP (`extracao_kw_local.md`).
3. Se 200 mas redireciona para `/index.php` → na rede mas deslogado → **parar e pedir Hugo logar manualmente**.
4. Se erro de rede → fora da rede → fallback AnyDesk (`extracao_kw_anydesk.md`).

**Workflow Chrome MCP** (ler `conhecimento/extracao_kw_local.md` para detalhes técnicos):
- Endpoint correto: `http://192.168.1.150/ferramentas/relatorios/lista_mercadorias_vendidas/selecaocsv.php?...&csv=1` (sem prefix `/sistema/`)
- JS `fetch` + `TextDecoder('windows-1252')` + `DOMParser`
- Janelas máx **15 dias** (mensal estoura timeout silenciosamente)
- Disparar `<a download>` com Blob → cai em `~/Downloads/`
- Mover via Finder (computer-use) para `data/extracoes/incoming/`

**Saída esperada**: CSV(s) em `data/extracoes/incoming/<DD-MM-AAAA_a_DD-MM-AAAA>.csv`.

**Validação obrigatória pós-extração** (faixas calibradas em S18/2026):

| PDVs ativos na janela | Linhas/dia | Cupons/dia | Fat/dia |
|---|---|---|---|
| 1 PDV (raro — só 101 ou só 102) | 600–1.000 | 150–250 | R$ 7k–13k |
| 2 PDVs (101+102 — padrão da maioria dos dias) | 1.000–1.700 | 240–360 | R$ 11k–19k |
| 3 PDVs (101+102+103 — em ~10-15% dos dias) | 1.200–1.800 | 280–400 | R$ 14k–21k |

**PDV 103 é esporádico por padrão operacional confirmado por Hugo.** Não gerar alerta quando ausente — só quando TODOS os 3 estiverem ausentes em dia útil.

Encoding do KW: **windows-1252** (latin1). Em Python: `pd.read_csv(..., encoding='utf-8')` funciona porque o JS já decodificou com TextDecoder antes de salvar como UTF-8.

**Detecção automática de gap KW** (calibrado em S18/2026):
```python
if pkl_existente_recente and df_new['Data'].min() > df_old['Data'].min() + pd.Timedelta(days=30):
    print('⚠️  KW PERDEU DADOS — restaurar de backup, abrir ticket SUPORTE KW')
    # Mesclar OLD (antes do cutoff) + NEW (a partir do cutoff)
```

PARAR e perguntar Hugo só se:
- ≥3 dias consecutivos zerados E não são feriados.
- Faturamento total < 60% do mínimo esperado.
- Colunas obrigatórias ausentes no CSV.
- Sessão KW deslogada (redirect para `/index.php`).

### FASE 3 · Consolidar e classificar

Executar `pipeline_consolidacao.py` (mesma pasta do skill).

O script:
1. Carrega base histórica `.pkl` existente.
2. Anexa as novas linhas da extração.
3. Re-aplica casamento em cascata ARIUS (EAN → Código → Descrição → Prefixo → N/A) sobre **todo o histórico**.
4. Re-aplica enriquecimento KVI.
5. Re-calcula `sem_id_global` (numeração sequencial de semanas desde a primeira data).
6. Salva nova base em `~/Documents/SurveyGran/base/base_historica.pkl`.
7. Imprime relatório de validação:
   - Total de linhas, faturamento, cobertura %.
   - Período inicial e final.
   - Linhas adicionadas nesta execução.

### FASE 4 · Gerar dados do Survey

Executar `gerar_html_survey.py` que:
1. Carrega base classificada.
2. Identifica **13 semanas focais** (últimas 13 quarta→terça encerradas).
3. Calcula:
   - KPIs macro (fat, cupons, ticket, dia médio).
   - Heatmap setor × semana com toggle L4W/YoY.
   - Tornado chart 2026 vs 2025 (13sem + S atual).
   - Cards por setor com sparkline YoY.
   - Top 30 lojas e Top 30 setor.
   - Ruptura recorrente, KVIs, elasticidade.
   - Cash & Carry, ofertas full.
   - **YoY com ajuste por feriado móvel** (ler `conhecimento/feriados_2025_2026.md`).
   - Sazonalidade mensal e tabelas comparativas semanais.
4. Renderiza HTML com 11 abas e tabelas compactas comparativas.

### FASE 5 · Salvar e apresentar

1. **Arquivo final**: `~/Documents/SurveyGran/relatorios/Survey_Gran_S{NN}_v12.html`.
2. **Marcar semana como processada**: gravar em `ultima_semana_processada.txt`.
3. **Apresentar a Hugo**:
   - Caminho do arquivo.
   - 3 destaques rápidos (extraídos de alertas):
     - Maior queda do YoY 13sem.
     - Maior crescimento do YoY 13sem.
     - Variação macro da semana atual.
4. **Sugerir abrir** no Safari ou Chrome.

---

## Decisões e regras de negócio

### Cadência semanal: quarta → terça

A "semana Gran" começa na quarta e termina na terça. Isso é decisão operacional do negócio (não negociável). Toda lógica do skill assume isso.

### YoY com ajuste por feriado móvel

Quando uma semana de 2026 tem feriado em data diferente da semana correspondente de 2025 (Carnaval, Páscoa, Cinzas), o skill marca a semana com ⚠️ e oferece comparação alternativa.

Mapeamento atual está em `conhecimento/feriados_2025_2026.md`. **Atualizar anualmente** quando virar 2027.

### Cobertura mínima aceitável

Cobertura ARIUS deve ser ≥ 95%. Se cair abaixo, alertar Hugo: provavelmente o cadastro ARIUS está desatualizado e precisa ser re-extraído.

### Dados B2B

Vendas corporativas eventuais (ex: cupons acima de R$ 5.000) podem distorcer ticket médio. Hoje **não estão marcadas** na base. Quando Hugo quiser separar, criar coluna `tipo_venda` na base.

---

## Arquivos do skill

- **`pipeline_consolidacao.py`** — script Python de classificação e consolidação.
- **`gerar_html_survey.py`** — gerador do HTML.
- **`conhecimento/extracao_kw_local.md`** — passo a passo via Chrome MCP local.
- **`conhecimento/extracao_kw_anydesk.md`** — passo a passo via AnyDesk + Python.
- **`conhecimento/manual_anydesk.md`** — manual de conexão AnyDesk (referência: pasta conhecimento do Cowork).
- **`conhecimento/feriados_2025_2026.md`** — feriados nacionais e regionais (atualização anual).
- **`conhecimento/glossario_metricas.md`** — definições de KPIs, comparadores, métodos de matching.
- **`templates/prompt_extracao.md`** — template do prompt de extração para AnyDesk.

---

## Tratamento de erros

- **KW retorna vazio**: PARAR, perguntar Hugo se há sessão expirada ou problema na rede.
- **PDV 103 ausente em uma janela onde deveria estar**: NÃO é erro fatal, registrar no log e seguir.
- **Cadastro ARIUS desatualizado** (cobertura < 90%): PARAR, pedir Hugo extrair ARIUS novo.
- **Sleep mode interrompeu execução**: Hugo precisa retomar manualmente (limitação Mac).
- **Encoding errado no CSV**: tentar utf-8 → utf-8-sig → windows-1252 nessa ordem.

## Limites e observações

- **Mac sleep mode** interrompe processos longos. Migração futura para cloud/VM resolve isso.
- **Cadastro ARIUS** precisa ser re-extraído mensalmente (manual, hoje).
- **Feriados** precisam ser atualizados a cada virada de ano.
- **Vendas B2B** não estão segregadas (futura iteração).

## Quando NÃO usar este skill

- Auditoria de caixas → use `auditoria-caixas-gran`.
- CRM/régua de retenção → use `crm-proativo-gran`.
- Pesquisa NPS → use `nps-gran-hortifruti`.
- Tendências SP → use `tendencias-sp`.
- Atendimento receptivo → use `receptivo-gran-hortifruti`.

## Histórico

- v1 — primeiro fechamento manual (S13/2026, 15-21/04).
- v12 — versão estável: YoY ajustado por feriado, tornado duplo, cards com sparkline, tabelas comparativas Aba 01 e Aba 02.
- v12.1 — endurecimento da extração (15 fixes): assert cookie jar, fallback timeout, encoding ordenado, Path.home() para OneDrive, validação de colunas obrigatórias, faixas de volume calibradas por nº de PDVs, mecanismos de PARAR explícitos no Cowork, manual AnyDesk consolidado, `dominio_kw.txt` para evitar redescobrir.
- v12.2 a 12.5 — sincronia entre build_dados e gerar_html, sem_label dinâmico, todas as 10 abas validadas via playwright headless, preço atual em Ruptura/NuncaVenderam puxando do KW.
- v12.6 — **estrutura unificada**: dados migrados de `~/Documents/SurveyGran/` para `~/Documents/Claude/Projects/[GRAN] Survey/data/`. Path configurável via env var `SURVEY_DATA_DIR`.
- **v12.7 (06/05/2026 — calibrado em S18) — corrigido endpoint KW**:
  - Endpoint correto: `http://192.168.1.150/ferramentas/relatorios/lista_mercadorias_vendidas/selecaocsv.php?...&csv=1` (SEM prefix `/sistema/` — era um erro do skill antigo que retornava 404).
  - Substituído workflow Python+browser_cookie3 por Chrome MCP + JavaScript fetch (mais robusto, sem dep externa).
  - Encoding `windows-1252` (latin1, não UTF-8 ordenado).
  - Janelas máx **15 dias** (mensal estoura timeout silenciosamente, retorna HTML vazio).
  - Saída do endpoint é tabela HTML, não CSV puro — parsear via DOMParser.
  - Fluxo Downloads → Finder (computer-use) → `data/extracoes/incoming/` (sandbox não vê `~/Downloads`).
  - Detecção automática de gap KW: se base re-extraída começa muito depois da base antiga, alertar e restaurar de backup. Calibrado quando S18 detectou que KW perdeu set/2024-abr/2025.
  - PDV 103 esporádico — não alertar quando ausente (confirmado por Hugo).
  - Backup pkl/parquet semanal recomendado em `data/base/backup/{YYYY-MM-DD}/`.
  - Snippet de recovery de pkl com StringDtype incompatível em `conhecimento/recovery_pkl.md`.
