# Identidade Visual · Survey Gran Mesa

O Survey Gran Mesa **herda 100% da identidade visual do Survey global** para preservar continuidade de leitura e marca. Mesma paleta, tipografia, tabs, cards, sparklines, alertas, header e rodapé. A única diferenciação é o título e um detalhe sutil de cor secundária.

## Paleta (CSS variables — copiar exatamente do gerar_html_survey.py)

```css
:root {
  /* Backgrounds */
  --bg: #ffffff;
  --bg-soft: #f6f4ee;
  --bg-cream: #faf7ef;

  /* Bordas */
  --border: #e8e3d4;
  --border-soft: #f0ebdc;

  /* Texto */
  --ink: #1a1f1a;
  --ink-dim: #4a5248;
  --ink-mute: #8b8f86;

  /* Marca Gran (verde) */
  --gran-verde: #1e4d2b;
  --gran-verde-2: #2d6a3f;
  --gran-verde-3: #3f8654;
  --gran-verde-bg: #e7f0e9;

  /* Accent dourado */
  --gran-dourado: #c9a227;
  --gran-dourado-2: #e8b93a;
  --gran-dourado-bg: #faf1d4;

  /* Status */
  --vermelho: #b8362f;
  --vermelho-bg: #f2d9d3;
  --amarelo: #d4a52e;
  --amarelo-bg: #faf1d4;
  --verde: #3f8654;
  --verde-bg: #e7f0e9;

  /* Sombras */
  --shadow: 0 1px 2px rgba(30,77,43,0.04), 0 4px 12px rgba(30,77,43,0.06);
  --shadow-hover: 0 2px 4px rgba(30,77,43,0.06), 0 8px 20px rgba(30,77,43,0.08);
}
```

**Diferenciação Survey Mesa**: o título h1 do header pode usar `<em>Mesa</em>` em dourado (`var(--gran-dourado-2)`) para distinguir visualmente sem quebrar a marca. Ex.:

```html
<h1>Survey Gran <em>Mesa</em></h1>
```

## Tipografia

```css
font-family: 'Aptos', 'Nunito Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;

/* Para números, eyebrows, labels técnicos */
font-family: 'JetBrains Mono', monospace;
```

Carregar do Google Fonts (igual Survey):

```html
<link href="https://fonts.googleapis.com/css2?family=Nunito+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;0,900;1,400&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
```

## Componentes herdados

### Header principal

```html
<header class="main-header">
  <div>
    <p class="eyebrow">SURVEY GRAN MESA · S{NN} · {periodo}</p>
    <h1>Survey Gran <em>Mesa</em></h1>
    <p class="subtitle">Foco: produtos da equipe de produção</p>
  </div>
  <div class="meta">
    <div>Gerado em <strong>{data}</strong></div>
    <div>Cobertura mapping <strong>{XX}%</strong></div>
    <div>Margens atualizadas <strong>{Xd}</strong> atrás</div>
  </div>
</header>
```

Estilização: fundo `var(--gran-verde)`, texto branco, h1 em peso 800, fontesize 44px, com `<em>` em dourado.

### Tabs sticky

```html
<div class="tabs-wrap">
  <div class="tabs">
    <button class="tab active" data-tab="01"><span class="num">01</span>Headline</button>
    <button class="tab" data-tab="02"><span class="num">02</span>Panorama</button>
    <button class="tab" data-tab="03"><span class="num">03</span>Cards & Linha do tempo</button>
    <button class="tab" data-tab="04"><span class="num">04</span>Lift por dia</button>
    <button class="tab" data-tab="05"><span class="num">05</span>Margem × Volume</button>
    <button class="tab" data-tab="06"><span class="num">06</span>Ruptura & Subprodução</button>
    <button class="tab" data-tab="07"><span class="num">07</span>Lançamentos & Carteiras</button>
  </div>
</div>
```

Active state: borda inferior dourada, background creme.

### Tri-comparador (KPIs macro)

```html
<div class="tri-cmp">
  <span class="cmp"><span class="cmp-l">LW</span><span class="cmp-v" style="color:{cor}">+3,2%</span></span>
  <span class="cmp"><span class="cmp-l">L4W</span><span class="cmp-v" style="color:{cor}">−1,1%</span></span>
  <span class="cmp"><span class="cmp-l">L8W</span><span class="cmp-v" style="color:{cor}">+0,8%</span></span>
</div>
```

Cor por threshold:

```python
def cor_var(v, positivo_bom=True):
    if v is None: return 'var(--ink-mute)'
    ok = (v >= 0) if positivo_bom else (v <= 0)
    if v == 0: return 'var(--ink-mute)'
    if ok:
        return 'var(--verde)' if abs(v) >= 3 else 'var(--ink-dim)'
    else:
        if abs(v) >= 10: return 'var(--vermelho)'
        if abs(v) >= 3:  return 'var(--amarelo)'
        return 'var(--ink-dim)'
```

### Selo de relevância

Componente novo do Survey Mesa, presente em **todas as abas que mostram SKU**:

```html
<span class="selo-relev verde">●</span>  <!-- ou cinza -->
```

```css
.selo-relev {
  display: inline-block; width: 8px; height: 8px;
  border-radius: 50%; vertical-align: middle;
  margin-right: 4px;
}
.selo-relev.verde { background: var(--verde); }
.selo-relev.cinza { background: var(--ink-mute); }
```

Ao lado do selo, mostrar share e cupons na fonte mono:

```html
<span class="share-info">
  <span class="selo-relev verde"></span>
  <span class="mono">3,2% · 142 cup/sem</span>
</span>
```

### Linha do tempo SKU (componente principal Aba 03)

Replicar fielmente o componente do print que Hugo anexou:

- Container creme `var(--bg-soft)` ou `var(--bg-cream)`
- Header verde escuro (`var(--gran-verde)`)
- Dropdown SKU no canto esquerdo
- Dropdown Visão no canto direito (Quantidade × Preço / Faturamento × Preço)
- Badge KVI+ em verde com texto branco, badge A* em dourado
- Eixo Y esquerdo (verde): Quantidade ou Faturamento
- Eixo Y direito (dourado): Preço médio
- Barras verde-escuro
- Linha dourada com pontos para o eixo direito
- 13 semanas no eixo X (S01...S13)

Implementar com Chart.js 4.4.1 (já carregado pelo Survey).

### Tornado chart (Aba 01)

Ganhadores em verde, perdedores em vermelho, ordenados por |valor|. Top 10 cada lado.

### Quadrantes Margem × Volume (Aba 05)

Plot scatter com:
- Eixo X: Volume (qtd × preco_medio normalizado, log scale se necessário)
- Eixo Y: Margem %
- Cada bolha proporcional a √(fat) para legibilidade
- Linhas de mediana dividindo em 4 quadrantes
- Quadrantes coloridos com transparência:
  - Estrelas (top-direito): `var(--verde-bg)`
  - Vacas (top-esquerdo): `var(--gran-dourado-bg)`
  - Interrogação (bottom-direito): `var(--bg-soft)`
  - Abacaxis (bottom-esquerdo): `var(--vermelho-bg)`

### Heatmap Lift por dia (Aba 04)

Grid 10 subgrupos × 7 dias com cores:

```python
def cor_heatmap_lift(lift_pct):
    if lift_pct is None: return 'var(--ink-mute)'
    if lift_pct >= 30: return 'var(--gran-verde-2)'
    if lift_pct >= 10: return 'var(--gran-verde-3)'
    if lift_pct >= -10: return 'var(--bg-soft)'
    if lift_pct >= -30: return '#e8b9b3'
    return 'var(--vermelho)'
```

### Cards de carteira (Aba 07 Bloco B)

5 cards por colaborador interno + 1 card "Não Atribuído" (vermelho borda) + sub-bloco "Fornecedores":

```html
<div class="carteira-card">
  <div class="carteira-nome">Solange</div>
  <div class="carteira-stats">
    <div><label>Fat carteira</label><value>R$ 28,4k</value></div>
    <div><label>Margem</label><value style="color:var(--verde)">42%</value></div>
    <div><label>SKUs</label><value>19</value></div>
    <div><label>Em alerta</label><value class="alerta">3</value></div>
  </div>
  <div class="carteira-top">
    <div>Top 1: SALADA CAPRESE · 8% do fat</div>
    <div>Top 2: ARROZ GRAN MESA · 6% do fat</div>
    <div>Top 3: MAMAO PCS KG · 4% do fat</div>
  </div>
</div>
```

### Rodapé (selo última atualização)

```html
<footer class="footer">
  <div class="footer-meta">
    <span class="selo-margem {classe}">●</span>
    Margens atualizadas em {data} ({Xd} atrás)
  </div>
  <div class="footer-attrs">
    Survey Gran Mesa v1 · gerado em {timestamp} · escopo {N} SKUs · cobertura mapping {XX}%
  </div>
</footer>
```

Onde `{classe}` é `verde` se <60d, `amarelo` se 60-90d, `vermelho` se ≥90d.

## Regra de leitura

Sempre que mostrar um número ou percentual de variação isoladamente, perguntar:
- Qual é o peso desse SKU/subgrupo no Gran Mesa? (selo + share)
- Quantos cupons únicos? (penetração)

Se as duas respostas forem baixas, o número não merece destaque visual. Vai pra painel secundário.

Esta regra é o que diferencia o Survey Mesa de um relatório técnico genérico — protege a leitura da sócia contra ruído estatístico.
