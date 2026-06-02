# Changelog · Survey Gran Semanal

## v0.12.8 — 07/05/2026 (Tornado Ganhadores/Perdedores no Headline)

### Nova feature — painel Ganhadores e Perdedores

- **Headline (Aba 01)**: novo painel após os KPIs com Top 12 ganhadores | Top 12 perdedores em **3 visões empilhadas verticalmente**:
  1. **Semana atual** (S vs S-52): movimento pontual da semana
  2. **13 semanas acumuladas** (2026 vs 2025): problema crônico ou crescimento estrutural
  3. **L4W** (atual vs média 4 semanas anteriores): aceleração/desaceleração do ritmo recente
- Ordenação por **Δ R$ absoluto** (não por %), priorizando impacto financeiro.
- **Filtro setor** com dropdown (12 setores + "Loja toda") afeta as 3 visões em conjunto.
- **Universo (opção A)**: união Top 30 da loja + Top 12 de cada setor ≈ 527 SKUs.
- **Display limpo**: centro mostra apenas Δ R$. Tooltip nas barras (mesmo barras pequenas) traz nome SKU + cód + setor + valor R$ + Δ + %.

### Build

- `build_dados.py`: nova função `build_skus_tornado(v_clas, sem_atual_id, top30_loja, sku_por_setor)` que produz `D['skus_tornado']` com fat_atual, fat_yoy_rs (S-52), fat_l4w_media, fat_13sem_2026/2025 e os 3 deltas R$ correspondentes.
- `gerar_html_survey.py`: novo bloco CSS `.tsku-*` (sufixado pra não conflitar com tornado de SETOR já existente na Aba 03), HTML no Headline e função JS `applyFiltro()` com renderização dinâmica.

### Hardening — smoke test pós-build

- Novo `validate_publicado.py` (mesmo do plugin Mesa): varre o HTML gerado por chamadas a funções `fmt*`/`render*`/`format*` que não estão definidas no próprio HTML. Emite warning bloqueante.
- Lição importada da rodada anterior do Mesa (bug `fmtBRL` que quebrou 4 abas em produção).

## v12.7 — 06/05/2026 (calibrado em S18)

### Correções críticas (signal — sem isso o plugin não roda)

- **Endpoint KW corrigido**: era `/sistema/ferramentas/relatorios/lista_mercadorias_vendidas/selecaocsv.php` (404). Agora `/ferramentas/relatorios/lista_mercadorias_vendidas/selecaocsv.php` (sem `/sistema/`).
- **Protocolo HTTP** (não HTTPS) — KW em IP local 192.168.1.150.
- **Encoding `windows-1252`** (não UTF-8) — saída do KW vem em latin1.
- **Saída do endpoint é HTML** com `<table>`, não CSV puro. Skill agora parsea via DOMParser.
- **Workflow Python+browser_cookie3 substituído por Chrome MCP + JS fetch** — sem dep externa, roda no sandbox Cowork.
- **Janelas máx 15 dias** (mensal estoura timeout silenciosamente, retorna HTML vazio).

### Hardening (eficiência operacional)

- **Backup snapshot semanal automático** em `data/base/backup/{YYYY-MM-DD}/` antes de cada rodada (retém últimos 8 = ~2 meses).
- **Detecção de gap KW**: alerta se base re-extraída começa muito depois da base antiga (KW deletando dados antigos).
- **Suporte parquet** (engine='pyarrow') em paralelo ao pkl: portável entre versões pandas, fallback automático.
- **`_carregar_base_existente()`** com fallback pkl→parquet.
- **Snippet de recovery de pkl** com StringDtype incompatível em `conhecimento/recovery_pkl.md` (último recurso).

### Análise (melhorias pedidas por Hugo S18)

- **Aba 02 Gráfico 13sem**: eixo X mostra `[label, periodo]` (S05 / 04/02-10/02).
- **Aba 02 Padrão horário**: dropdown "Filtrar por dia" com 8 opções (Todos + 7 DOWs).
- **Aba 04 Top30 SKU loja**: 2 colunas novas — `var_yoy_fat_pct` e `var_yoy_qtd_pct`.
- **Aba 04 Top30 por setor (raio-X)**: alinhado com Top30 loja — todas as 5 colunas comparadoras (LW/L4W/L8W/YoY Fat/YoY Qtd).
- **Aba 04 Linha do tempo SKU**: 4 séries — barra 2026, barra 2025 (sobreposta), linha preço 2026, linha preço 2025 (tracejada).

### Comportamento operacional

- **PDV 103 esporádico**: confirmado por Hugo, não alertar quando ausente. Alerta apenas se TODOS 3 ausentes em dia útil.
- **Defaults silenciosos**: pipeline não pergunta a Hugo coisas conhecidas (path do projeto, origem dos dados, numeração de semana).
- **Detecção automática de rede**: `fetch('/sistema/principal.php')` antes de extrair. Redirect para `/index.php` = não logado.

## v12.6 — 02/05/2026

- Estrutura unificada: dados migrados de `~/Documents/SurveyGran/` para `~/Documents/Claude/Projects/[GRAN] Survey/data/`.
- Path configurável via env `SURVEY_DATA_DIR`.

## v12.5 e anteriores

- Sincronia entre build_dados e gerar_html.
- sem_label dinâmico baseado em `sem_gran_no_ano`.
- Validação playwright headless de todas as 10 abas (0 erros JS).
- Preço atual em Ruptura/NuncaVenderam puxando do KW (mais atualizado que ARIUS).
