# Melhorias técnicas v12.7 (calibradas em S18/2026)

Lista de débitos técnicos identificados durante a rodada de S18/2026 e que foram corrigidos OU estão documentados para correção futura.

## ✅ Corrigidos em v12.7

### 1. Endpoint KW estava errado
- **Sintoma**: pipeline antigo retornava 404 silenciosamente
- **Fix**: novo endpoint em `conhecimento/extracao_kw_local.md`
- **Impacto**: rodada totalmente bloqueada antes da correção

### 2. browser_cookie3 frágil
- **Sintoma**: requer Python local + venv específico, não funciona em sandbox
- **Fix**: workflow Chrome MCP + JS fetch (sem deps externas)
- **Impacto**: agora roda do sandbox sem precisar Python no Mac do Hugo

### 3. Janela mensal estoura timeout
- **Sintoma**: KW retorna HTML vazio para janelas grandes (sem alertar erro)
- **Fix**: janelas máx **15 dias**
- **Impacto**: 6/16 janelas mensais retornavam vazio na S18; quinzenais 0/16 falharam

### 4. PDV 103 esporádico gerava ruído
- **Sintoma**: alertas falsos quando PDV 103 ausente em dia normal
- **Fix**: regra "alerta só se TODOS os 3 ausentes em dia útil"
- **Impacto**: -X alertas falsos por mês

### 5. Pkl quebra entre versões pandas
- **Sintoma**: `NotImplementedError` no NDArrayBacked.__setstate__
- **Fix**: salvar parquet em paralelo + fallback no load + snippet de recovery em `recovery_pkl.md`
- **Impacto**: base não fica refém da versão exata de pandas

### 6. Mesa usava ISO week (S19) vs Gran usava sem_gran_no_ano (S18)
- **Sintoma**: HTML nomeado "Survey_Gran_Mesa_S19_26" para a mesma semana que o Gran chama de S18/2026
- **Fix**: Mesa lê `sem_label` do JSON do Gran global como fonte da verdade
- **Impacto**: nomenclatura consistente entre os dois Surveys

### 7. NaN em DESCRICAO quebrava Mesa
- **Sintoma**: `'float' object has no attribute 'upper'` em buscar_tempo_min
- **Sintoma 2**: `'float' object is not subscriptable` em `t["desc"][:32]` no gerar_html
- **Fix**: NaN guards no buscar_tempo_min + sanitização do JSON antes de salvar
- **Impacto**: build não quebra mais com SKUs sem mapping

### 8. Detecção de gap KW
- **Sintoma**: KW silenciosamente perdeu 8 meses de histórico entre 02/05 e 06/05/2026 (set/2024-abr/2025)
- **Fix**: comparar `df_old.Data.min()` com `df_new.Data.min()` antes de sobrescrever; alertar e restaurar de backup se gap > 30 dias
- **Impacto**: dado não some mais sem aviso

### 9. Backup snapshot semanal automático
- **Fix**: `_backup_snapshot()` antes de cada rodada salva pkl/parquet em `data/base/backup/{YYYY-MM-DD}/`
- **Retenção**: 8 últimos snapshots (~2 meses)
- **Impacto**: proteção contra perda silenciosa do KW

## 🟡 Pendentes (documentados para próximo ciclo)

### 10. Migrar pkl → parquet como formato canônico
- **Hoje**: pkl é primário, parquet é backup
- **Futuro**: parquet primário, pkl deprecado
- **Justificativa**: parquet é estável entre versões pandas; pkl tem risco de Cython incompatível
- **Esforço**: refactor build_dados.py para `pd.read_parquet()` primeiro

### 11. Detecção automática de login KW
- **Hoje**: tenta extrair, se cair em /index.php (login screen) o JS nem nota
- **Futuro**: pré-check `fetch('/sistema/principal.php')` retorna URL final; se redirecionou, parar
- **Esforço**: 5 linhas no início do workflow

### 12. KW retenção de dados — abrir ticket SUPORTE KW
- **Hoje**: assumimos perda silenciosa, restauramos de backup
- **Futuro**: confirmar com SUPORTE KW se há política de TTL configurável
- **Esforço externo**: Hugo precisa abrir ticket

### 13. Skill Mesa pré-checa Gran rodou primeiro
- **Hoje**: roda independente, gera resultado mesmo se base do Gran está estale
- **Futuro**: Mesa lê `data/base/dados_survey.json` e valida que data >= hoje-7d. Senão, parar e pedir rodar /survey antes
- **Esforço**: 3 linhas no FASE 0 do build_dados Mesa

### 14. Migrar de download via Finder para File System Access API
- **Hoje**: Chrome MCP dispara download → cai em ~/Downloads → mover via Finder com computer-use
- **Futuro**: usar `window.showSaveFilePicker()` para Hugo escolher pasta uma vez (memorizado)
- **Esforço**: experimental — File System Access API ainda exige interação manual

### 15. ARIUS desatualizado — alerta proativo
- **Hoje**: alerta se cobertura < 95%
- **Futuro**: alerta também se ARIUS último update > 30d (data do arquivo)
- **Esforço**: 2 linhas comparando `ARIUS_FILE.stat().st_mtime` com hoje
