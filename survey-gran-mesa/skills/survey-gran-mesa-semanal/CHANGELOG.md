# Changelog · Survey Gran Mesa Semanal

## v2.1.5 — 07/05/2026 (hotfix + smoke test pós-publish)

### Bug crítico (P0) — 3 abas quebradas em produção

- **Aba 04 (venda casada), 05 (Margem×Volume), 06 (Ruptura), 07 (Lançamentos)** voltavam vazias na publicação online (Cloudflare Pages).
- **Causa raiz**: `gerar_html_survey_mesa.py` linha 2036 chamava `fmtBRL(co.fat_total_companheiro)` — função nunca definida no HTML (só existem `fmtR`, `fmtR2`, `fmtN`, `fmtP`, `fmtSignP`).
- **Cascata**: `ReferenceError` em `renderCesta()` abortava o IIFE inteiro logo no início. Tudo após linha 3420 nunca executava — incluindo `renderMatriz()` (Aba 05), listeners da Aba 06 e bloco da Aba 07.
- **Fix**: `fmtBRL` → `fmtR` (1 caractere). Validado online: 93 bolhas no scatter, 10 SKUs no cross-sell, console sem exceções.

### Smoke test pós-publish (impede regressão)

- Novo `validate_publicado.py`: varre o HTML gerado por chamadas a funções `fmt*` que não estão definidas no próprio HTML antes de publicar. Emite warning bloqueante.
- Lição da rodada: nenhum eval rodava sobre o HTML servido. Detecção dependia de inspeção manual.
- Não substitui o eval local (`build_dados.py`), complementa: catch-all para drift entre fonte e produção.

## v2.1.4 — 06/05/2026 (rodada de melhorias S18)

### Hardening (sem isso o plugin pode quebrar com SKUs mal-cadastrados)

- **NaN guard** em `buscar_tempo_min`: SKUs com `DESCRICAO=NaN` (float) quebravam com `'float' object has no attribute 'upper'`. Agora tolera.
- **Sanitização recursiva do JSON** antes de salvar: `_sanitize()` substitui qualquer NaN por string vazia. Resolvia `'float' object is not subscriptable` em `t["desc"][:32]` na render do HTML.

### Análise

- **Aba 02 Gráfico 13sem**: eixo X mostra `[label, periodo]`.
- **Aba 04 Top30 SKU**: nova coluna **YoY Qtd** ao lado de YoY Fat.
- **Aba 04 Venda casada — refatoração crítica**:
  - Callout dourado explicando o critério (Lift) e suas limitações (viés de companheiros raros).
  - Dropdown de ordenação com 5 opções: Lift / **Score combinado** (lift × √suporte) / Suporte / Cupons juntos / Fat companheiro.
  - Nova coluna `Score` calculada no JS.
  - Nova coluna `Fat companheiro` (R$ que o companheiro gera).
- **Aba 05 Margem R$/H — refatoração crítica** (resolve confusão Hugo S18):
  - Eram 1 coluna ambígua. Agora são 4 explícitas:
    1. **Margem R$ (bruta)** — fat − CMV.
    2. **Custo Horas R$** — horas × `custo_hora_homem_rs` (parâmetro novo em parametros.json, default R$ 15).
    3. **Margem Líq R$ (pós-custo)** — bruta − custo horas. Vermelha = SKU dá prejuízo operacional.
    4. **Eficiência R$/h** — bruta ÷ horas (em itálico, pra diferenciar visualmente).
  - Header explicativo com fórmulas inline.
- **Sem_label alinhado com Survey Gran global**: Mesa lê `dados_survey.json` do Gran e usa o `sem_label` de lá (S18/2026 em vez de S19/26 ISO).

### Parâmetros novos

- **`custo_hora_homem_rs: 15.0`** em `data/produtividade/inputs/parametros.json`. Configurável.

## v2.1.3 — versão intermediária (não publicada)

Mesmo conjunto de mudanças, fundido na v2.1.4.

## v2.1.2 — 06/05/2026 (manhã)

- Versão estável anterior. Estrutura 7 abas com profundidade equivalente ao Survey global.

## v2.1.0 — 05/05/2026

- Reconstrução profunda: identidade visual idêntica ao Survey global, chart-diario, chart-evolucao com toggle KPI, tornado dual subgrupo, cards subgrupo com sparkline 50px, heatmap subgrupo × semana, top 30 SKUs com tri-cmp completo, linha do tempo SKU, análise de cesta cross-sell, scatter Margem × Volume com bubbles, curva intra-dia, sparklines em cards de carteira.
