# Glossário de Métricas — Produtividade Gran

## KPIs principais

### Custo / Margem (KPI mãe)
**Fórmula:** `Custo Pessoal Total / Margem Total × 100`

Quanto da margem gerada pela equipe é consumido em custo de pessoal. Mais justo que custo/faturamento porque neutraliza diferença estrutural de margem entre categorias (produção própria vs revenda).

**Thresholds (editáveis em parametros.json):**
- Verde: < 30%
- Amarelo: 30-40%
- Vermelho: ≥ 40%

### Custo / Faturamento
**Fórmula:** `Custo Pessoal Total / Faturamento Total × 100`

Métrica clássica de varejo. Benchmark típico: 8-12% para varejo alimentar. KPI mais agregado, menos sensível à mistura de produtos.

### Margem / Custo (×)
**Fórmula:** `Margem Total / Custo Pessoal Total`

Quantos reais de margem cada real de custo gera. Inverso do KPI mãe. Mais visual.

### Faturamento / Funcionário
**Fórmula:** `Faturamento Total / Headcount CLT da equipe`

Produtividade bruta de venda por cabeça/mês.

### Margem / Funcionário
**Fórmula:** `Margem Total / Headcount CLT`

Produtividade líquida por cabeça/mês. Mais útil que fat/func porque considera a qualidade do mix.

## Custo Pessoal

### Custo Empresa Total
**Fórmula:** `Total Vencimentos × fator_encargos_clt (1.55)`

Cobre: salário base, DSR, adicional noturno, triênio, FGTS, INSS patronal, 13º, férias, VT, VR, plano de saúde.

### Total Vencimentos
Soma de todos os proventos brutos do mês (linha "Total de Vencimentos" do recibo).

### Diaristas
Custo fixo R$ 2.000/mês de diaristas que trabalham nas obras. 100% atribuído à Gran Mesa, fora da folha CLT.

### Rateio Retaguarda
Custo dos 4 funcionários classificados como "Retaguarda" é rateado entre Gran Mesa e Gran Horti pró-rata pelo faturamento total.

## Faturamento e Margem

### Faturamento KW
Soma do campo "Valor" do KW (sistema PDV) por SKU nos últimos 30 dias.

### Faturamento GMPro (Omie)
Soma das NFs emitidas pelo CNPJ Gran Realizacoes (39.303.338/0001-58) no Omie nos últimos 30 dias rolling. Vendas B2B de refeições coletivas.

### CMV (Custo da Mercadoria Vendida)
**Fórmula KW:** `Quantidade × P. Custo` (P. Custo de gran_margens.xlsx, coluna DADOS MARGENS / P. CUSTO)
**Fórmula GMPro:** `Faturamento × cmv_gmpro_pct (0.49)`

### Margem
**Fórmula:** `Faturamento - CMV`

### Margem %
**Fórmula:** `Margem / Faturamento × 100`

## Atribuição por Equipe

### Gran Mesa (peso 100%)
- Setor "GRAN MESA" do KW (109 SKUs: refeições, sucos, hortaliças higienizadas, frutas higienizadas, molhos, sobremesas)
- Grupo "FATIADOS" do subdept Frios & Laticínios (25 SKUs)
- Faturamento Omie GMPro (B2B refeições coletivas)

### Gran Mesa (peso 65%) / Gran Horti (peso 35%)
- 14 SKUs do grupo "PADARIA GRAN" (excluindo cód 760):
  - Cód 1 (Pão Tradicional KG)
  - Cód 589-595 (Croassants e Folhados)
  - Cód 602, 616 (Pães sem glúten)
  - Cód 759, 763 (Pão Delícia recheio + Pão Artesanal)
  - Cód 6424 (Pão Queijo Forma Minas)
  - Cód 6584 (Salgados Diversos)

### Gran Horti (peso 100%)
- Cód 760 (PAO DELICIA GRAN KG)
- Todos os demais setores e grupos

## Headcount

Headcount conta funcionários CLT no último dia do mês (decisão Hugo). Estagiários e diaristas contam separadamente.

## Período

30 dias rolling antes da `data-ref`. Se não especificado, usa último dia do mês anterior fechado.
