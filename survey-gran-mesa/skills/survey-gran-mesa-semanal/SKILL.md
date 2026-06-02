---
name: survey-gran-mesa-semanal
description: Geração semanal do Survey Gran Mesa — relatório executivo HTML com 7 abas focado APENAS nos produtos da equipe de produção (setor GRAN MESA + grupo FATIADOS + Padaria Gran + Omie GMPro, total ~134 SKUs). Eixo principal VENDA (faturamento, margem, mix, ruptura, lift por dia). Use SEMPRE que Hugo mencionar /survey-mesa, Survey Gran Mesa, Survey Mesa, atualização Mesa, fechamento Gran Mesa, performance Gran Mesa, vendas equipe produção, margem dos produtos da cozinha, ou qualquer tarefa relacionada ao consolidado semanal de vendas dos produtos produzidos pela equipe Gran Mesa. NÃO use para Survey global (todos os setores) — use survey-gran. NÃO use para análise mensal de custo de pessoal vs margem — use produtividade-gran. NÃO use para auditoria de caixas — use auditoria-caixas-gran.
---

# Skill: Survey Gran Mesa Semanal

## Visão geral

Gera o **Survey Gran Mesa** — relatório executivo HTML interativo com **7 abas** analisando a última semana fechada (cadência **quarta → terça**) **apenas dos produtos da equipe de produção**.

Comparativos:

- Última semana (LW)
- Média 4 semanas anteriores (L4W)
- Média 8 semanas anteriores (L8W)
- Mesma semana ano anterior (YoY) — com **ajuste automático por feriado móvel** (mesma lógica do survey-gran)

**Foco principal: VENDA.** Margem, mix, ruptura, lift, lançamentos. Produção/colaboradores entram como bloco proxy enquanto não existe apontamento real.

## Entrada

```
/survey-mesa
```

ou triggers naturais: "rodar Survey Mesa", "fechar Survey Gran Mesa", "atualizar Mesa", "Survey atualizado da equipe de produção".

## Saída

`~/Documents/Claude/Projects/[GRAN] Survey/data/gran-mesa/relatorios/Survey_Gran_Mesa_S{NN}_v1.html`

## Pré-requisitos

1. Base do Survey global atualizada (`base_classificada.pkl` em `data/base/`). Se ausente ou desatualizada, **rodar /survey antes**.
2. `gran_margens.xlsx` em `data/produtividade/inputs/` (mesma planilha usada pelo Produtividade).
3. `parametros.json` em `data/produtividade/inputs/` com `regra_atribuicao_equipe`.
4. `Mapa e Producao.xlsx` em `data/gran-mesa/inputs/` (mapeamento SKU → colaborador).
5. Python 3.8+ com pandas, numpy, openpyxl.

---

## Fluxo principal

### FASE 0 · Verificar pré-requisitos

1. Path resolution: `SURVEY_DATA_DIR` (env) → `~/Documents/Claude/Projects/[GRAN] Survey/data/` (default) → fallback legacy.
2. Verificar:
   - `data/base/base_classificada.pkl` existe e tem dados da última semana fechada. Se não, **PARAR**: pedir Hugo rodar `/survey` primeiro.
   - `data/produtividade/inputs/gran_margens.xlsx` existe.
   - `data/produtividade/inputs/parametros.json` existe e tem `regra_atribuicao_equipe`.
   - `data/gran-mesa/inputs/Mapa e Producao.xlsx` existe.
3. Calcular janela: última quarta→terça encerrada (mesma lógica do survey-gran).
4. Verificar se já foi processada: ler `data/gran-mesa/ultima_semana_processada.txt`. Se igual à atual, perguntar Hugo se quer regerar.

### FASE 1 · Filtrar escopo Gran Mesa

Aplicar regra de atribuição em cascata (do `parametros.json`):

```
PARA cada linha do KW:
  1. SE setor == 'GRAN MESA'        → escopo (categoria: gran_mesa)
  2. SENÃO SE grupo == 'FATIADOS'   → escopo (categoria: fatiados)
  3. SENÃO SE cod ∈ {1, 589, 590, 591, 592, 593, 594, 595, 602, 616, 759, 763, 6424, 6584} → escopo (categoria: padaria)
  4. SENÃO SE cod == 760            → FORA (é Gran Horti)
  5. SENÃO                          → FORA
```

**Observação importante**: Padaria Gran entra **inteira** no Survey Mesa (faturamento e margem 100%), com tag visual `[split 65/35 no Produtividade]` para deixar claro que isso é diferente da regra do plugin de Produtividade.

GMPro Omie é tratado em fluxo paralelo (ler `omie_gmpro.xlsx`) e segregado nas abas (não mistura com KW PDV).

### FASE 2 · Cruzar margens

Para cada linha filtrada, buscar `P. Custo` em `gran_margens.xlsx` (sheet `PRECIFICAÇÃO`, cabeçalho de 2 níveis):

- `CMV = qtd × P. Custo`
- `Margem R$ = fat - CMV`
- `Margem % = Margem / fat × 100`

SKUs sem custo: registrar em log e marcar `margem_indisponivel = true`.

Capturar `data_atualizacao` do arquivo `gran_margens.xlsx` para mostrar no rodapé do HTML (selo verde se <60d, amarelo 60-90d, vermelho >90d).

### FASE 3 · Cruzar mapa de produção

Ler `Mapa e Producao.xlsx` (sheet `MAPA PRODUÇÃO`, 4 colunas: COD, GRUPO, DESCRIÇÃO, COLABORADOR RESPONSÁVEL).

Lookup por COD:

- Match → `colaborador = <valor>`, `grupo_producao = <valor>`
- No match → `colaborador = 'Não Atribuído'`, `grupo_producao = 'Sem mapping'`

Identificar fornecedores (qualquer valor começando com `FORNECEDOR`) e separar em bucket `tipo: fornecedor_externo` vs `tipo: colaborador_interno` vs `tipo: nao_atribuido`.

### FASE 4 · Calcular KPIs

#### Macro Gran Mesa (Aba 01)

- Faturamento, cupons, ticket médio, itens/NF, dias com venda
- Margem R$ total, Margem % consolidada
- Comparativos LW / L4W / L8W
- YoY com ajuste por feriado (ler `feriados_2025_2026.md` do survey-gran)
- % do faturamento total da loja (Gran Mesa / Loja toda)
- KPIs separados Varejo (KW) vs B2B (GMPro)

#### Por SKU (todas as abas)

Para cada SKU:

- `share_fat_mesa` = fat SKU / fat total Gran Mesa
- `cupons_unicos_sem` = média de cupons únicos por semana (13sem)
- `selo_relevancia` = `verde` se share ≥ 0,5% E cupons ≥ 30/sem; senão `cinza`
- `evolucao_13sem` = lista [(sem, qtd, fat, preco_medio)] para gráfico Linha do Tempo
- `lift_por_dia` = dict {qua, qui, sex, sab, dom, seg, ter} com lift vs média geral
- `hora_ultimo_cupom_med` = média da hora do último cupom diário (proxy de subprodução)
- `dias_esgotamento_precoce_pct` = % de dias com último cupom antes das 17h
- `quadrante` = {Estrela, Vaca, Interrogação, Abacaxi} — baseado em volume × margem % vs medianas
- `dias_com_venda_sem_atual` = nº de dias da última semana com venda
- `ruptura_recorrente` = bool (venda em <4 das últimas 6 semanas)
- `data_primeira_venda` = se ≤90 dias atrás → marca como lançamento

#### Por subgrupo (Aba 02 e 03)

Subgrupos lidos do `Mapa e Producao.xlsx` (10 grupos: Frutas, Legumes & Hort, Sucos, Molhos, Wraps, Sanduíche, Galeto, Sopa, Refeições, Padaria) + agregação ARIUS para SKUs sem mapping.

#### Por colaborador (Aba 07 Bloco B)

- `fat_carteira`, `margem_carteira_R$`, `margem_carteira_%`
- `share_fat_mesa` da carteira
- `n_skus_responsavel`
- `n_skus_em_alerta` (ruptura ou queda YoY ≥ 20%)
- Top 3 SKUs da carteira

### FASE 5 · Gerar 5 alertas Aba 01 (regra de ouro)

**Máximo 5 alertas, ordenados por impacto absoluto em R$.**

Fontes de candidatos a alerta:

1. **Queda YoY R$ relevante** — SKU/subgrupo com queda absoluta YoY ≥ R$ X (threshold dinâmico por share)
2. **Subprodução defensiva** — SKU top com esgotamento precoce em ≥40% dos dias
3. **Margem desbalanceada** — SKU em quadrante "Abacaxi" com volume alto OU "Interrogação" com margem alta
4. **Ruptura recorrente** — KVI+/KVI com venda em <4 de 6 sem
5. **Lançamento underperformando** — SKU com >60d e curva abaixo do benchmark

Ranking por |impacto R$|. Top 5 entram. Resto fica nas abas detalhadas, sem virar alerta.

### FASE 6 · Renderizar HTML (7 abas)

Executar `gerar_html_survey_mesa.py` com paleta e identidade visual herdadas do survey-gran.

#### Aba 01 — Headline Gran Mesa
- KPIs macro com triplo comparador (LW/L4W/L8W) e YoY
- Bloco GMPro segregado
- 5 alertas ordenados por R$ absoluto
- Tornado top 10 ganhadores / top 10 perdedores YoY 13sem (Gran Mesa)

#### Aba 02 — Panorama
- Evolução semanal de fat/cupons/ticket/itens
- Hora de venda (curva intra-dia consolidada Gran Mesa)
- YoY 13sem ajustado por feriado
- Bloco subgrupo embutido (sparkline por subgrupo + lift YoY)

#### Aba 03 — Cards + Linha do tempo SKU
- Cards por subgrupo (sparkline 13sem, lift YoY, margem %, top 3, bottom 3 com selo de relevância)
- Componente "Linha do tempo SKU" replicando o anexo de Hugo: dropdown SKU (top 30 Gran Mesa) + toggle Quantidade × Preço / Faturamento × Preço
- Cada SKU no dropdown mostra share + selo

#### Aba 04 — Lift por dia da semana
- Heatmap dia × subgrupo
- Drill SKU com colunas obrigatórias: share Gran Mesa, cupons únicos/sem, selo
- SKUs com selo cinza vão para painel secundário "Baixo impacto agregado"

#### Aba 05 — Matriz Margem × Volume
- Quadrantes Estrelas / Vacas / Interrogação / Abacaxis
- Eixo X: Volume (qtd × preco médio do SKU normalizado)
- Eixo Y: Margem %
- Cada bolha proporcional ao fat
- Tooltip com selo de relevância e valor absoluto

#### Aba 06 — Ruptura + Subprodução defensiva
- Tabela de ruptura recorrente (igual lógica do Survey)
- Bloco novo: hora do último cupom por SKU top 20
- Curva intra-dia
- Alerta automático: "Produto X esgotou às 16h em ≥40% dos dias da semana"

#### Aba 07 — Lançamentos + Carteiras de Produção
- Bloco A: tabela de lançamentos últimos 90d com curva sem 1/4/8/12 e status 🟢🟡🔴
- Bloco B: cards por colaborador (5 internos + bucket Não Atribuído + 2 fornecedores em sub-bloco) com fat, margem, n_skus, top 3 SKUs, alertas

### FASE 7 · Salvar, validar e apresentar

1. Arquivo final em `data/gran-mesa/relatorios/Survey_Gran_Mesa_S{NN}_v2.html`
2. **Smoke test automático** (v2.1.5): `gerar_html_survey_mesa.py` chama `validate_publicado.py` no fim do main. Detecta funções `fmt*`/`render*`/`format*` chamadas mas não definidas (caso fmtBRL). Se exit=1, NÃO publicar — corrigir source antes.
3. Marcar semana processada em `ultima_semana_processada.txt`
4. Apresentar a Hugo:
   - Caminho do arquivo
   - 3 destaques: maior alavanca de margem, maior alerta de subprodução, lançamento campeão da semana
5. Sugerir abrir no Safari/Chrome
6. Se publicar online: copiar para `_publish/mesa/` e rodar `_push_workflow.command` (script no Mac)

---

## Decisões e regras de negócio

### Cadência: quarta → terça

Mesma janela do survey-gran. Não negociável.

### Padaria Gran no Survey Mesa

Entra **inteira** (100% fat e 100% margem), com tag visual `[split 65/35 no Produtividade]` em todas as visualizações que mostram Padaria. Diferente do plugin Produtividade que aplica o split.

### GMPro Omie

Tratado em paralelo. Aparece em **bloco separado** na Aba 01 e linha dedicada na Aba 02. Nunca misturado em ticket médio, heatmap, cupons ou matriz.

### Indicadores de compartilhamento em todas as abas

Toda visualização que mostra SKU/subgrupo deve trazer:

- `share_fat_mesa` (% do fat Gran Mesa)
- `cupons_unicos_sem` (cupons únicos médios/semana)
- `selo_relevancia` (verde se share ≥ 0,5% E cupons ≥ 30/sem; cinza caso contrário)

Sem isso, número absoluto pode ser lido sem contexto e levar a decisão errada (ex: "salvar" produto-de-nicho que não move o ponteiro).

### 5 alertas máximos na Aba 01

Ordenados por impacto absoluto em R$, não por % de desvio. Um SKU que caiu 40% mas representa 0,3% do fat **não vira alerta** — fica nas abas detalhadas.

### Última atualização gran_margens

Selo no rodapé com data do arquivo:
- <60d → verde
- 60-90d → amarelo
- ≥90d → vermelho + alerta no topo da Aba 05

---

## Arquivos do skill

- `build_dados.py` — pipeline: filtra escopo, cruza margens, cruza mapa produção, calcula KPIs, salva `dados_gran_mesa.json`
- `gerar_html_survey_mesa.py` — renderiza HTML 7 abas
- `conhecimento/glossario_metricas.md` — definições de share, selo, lift, quadrantes, esgotamento precoce
- `conhecimento/regras_escopo.md` — regra de atribuição em cascata, tratamento Padaria/GMPro/fornecedores/não-atribuído
- `conhecimento/identidade_visual.md` — paleta, tipografia, componentes herdados do Survey

---

## Tratamento de erros

- **base_classificada.pkl ausente** → PARAR, pedir Hugo rodar /survey primeiro.
- **base desatualizada** (última semana ≠ esperada) → PARAR, pedir Hugo atualizar.
- **gran_margens.xlsx ausente** → PARAR, pedir Hugo extrair.
- **gran_margens com >90d** → continuar mas com alerta vermelho.
- **Mapa e Producao.xlsx ausente** → continuar com bucket "Não Atribuído" 100%, alertar.
- **>5% do fat Gran Mesa sem mapping de colaborador** → bandeira amarela na Aba 07.
- **<90% do fat Gran Mesa com margem disponível** → bandeira amarela na Aba 05.

## Limites e observações

- Apontamento de produção real ainda não existe → Aba 07 Bloco B fica em modo "carteira" (alocação SKU→colaborador), não mede produtividade kg/hora ainda.
- B2B GMPro lido da planilha Omie manual. Upload automático fica para v2.
- Histórico semana a semana é compartilhado com survey-gran (não duplica).

## Quando NÃO usar este skill

- Survey global (todos os setores) → use `survey-gran`
- Análise mensal de custo de pessoal vs margem por equipe → use `produtividade-gran`
- Auditoria de caixas → use `auditoria-caixas-gran`
- CRM/régua de retenção → use `crm-proativo-gran`
- Pesquisa NPS → use `nps-gran-hortifruti`

## Histórico

- v1.0.0 — primeira versão (descontinuada). Estrutura básica com cards textuais e poucos gráficos.
- v2.0.0 — **reconstrução profunda inspirada milimetricamente no Survey global.** Identidade visual idêntica (paleta, tipografia, componentes). Adições críticas: chart-diario (semana atual + L4W + YoY), chart-evolucao com toggle KPI, tornado dual subgrupo (sem atual + 13sem acumulado), cards subgrupo com sparkline 50px, heatmap subgrupo × semana com toggle L4W/YoY, top 30 SKUs com tri-cmp completo, linha do tempo SKU com toggle qtd/fat × preço, **análise de cesta cross-sell** (lift por SKU companheiro — pergunta "quem é vendido junto com o quê"), scatter Margem × Volume com bubbles, curva intra-dia, sparklines em cards de carteira. Indicador % do fat da loja com tri-cmp (ver evolução proporcional). Escopo expandido para incluir setor GRANEL (porcionamento da equipe Mesa). 7 abas com profundidade equivalente ao Survey global.
