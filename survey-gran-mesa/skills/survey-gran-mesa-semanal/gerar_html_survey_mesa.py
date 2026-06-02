"""
Gerar HTML · Survey Gran Mesa v2
=================================

Reconstrução com profundidade Survey-grade. 7 abas:
  01 Headline (KPI grid + chart-diario + tornado dual + 5 alertas)
  02 Panorama 13sem (chart-evolucao toggle KPI + chart-horario + faixas + tabela YoY)
  03 Subgrupos (hbars + tornado dual + cards sparkline + heatmap + tabela)
  04 Raio-X SKU + Cesta (top 30 + linha tempo + cross-sell)
  05 Margem × Volume (scatter quadrantes + drill)
  06 Ruptura + Subprodução (tabela + curva intra-dia)
  07 Lançamentos + Carteiras (90d + cards sparkline)

Lê:    data/gran-mesa/dados_gran_mesa.json
Salva: data/gran-mesa/relatorios/Survey_Gran_Mesa_S{NN}_v2.html
"""
import json
import os
from datetime import datetime
from pathlib import Path


def get_data_dir() -> Path:
    if env := os.environ.get('SURVEY_DATA_DIR'):
        return Path(env)
    p = Path.home() / 'Documents' / 'Claude' / 'Projects' / '[GRAN] Survey' / 'data'
    if p.exists(): return p
    legacy = Path.home() / 'Documents' / 'SurveyGran'
    if legacy.exists(): return legacy
    raise FileNotFoundError("Pasta data/ não encontrada.")


DATA_DIR = get_data_dir()
MESA_DIR = DATA_DIR / 'gran-mesa'
DADOS_JSON = MESA_DIR / 'dados_gran_mesa.json'
REL_DIR = MESA_DIR / 'relatorios'
REL_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────
# Helpers de formatação BR
# ─────────────────────────────────────────────────────────────────────
def fmt_int_br(n):
    if n is None or n == '': return '—'
    try: return f'{int(n):,}'.replace(',', '.')
    except Exception: return '—'

def fmt_dec_br(n, decimals=1):
    if n is None: return '—'
    try:
        s = f'{n:,.{decimals}f}'
        return s.replace(',', '#TMP#').replace('.', ',').replace('#TMP#', '.')
    except Exception: return '—'

def fmt_brl(v):
    if v is None: return '—'
    try:
        s = f'{v:,.2f}'
        return 'R$ ' + s.replace(',', 'X').replace('.', ',').replace('X', '.')
    except Exception: return '—'

def fmt_brl_full(v):
    """R$ 19.572 (sem decimais para valores inteiros)"""
    if v is None: return '—'
    try:
        s = f'{int(round(v)):,}'.replace(',', '.')
        return 'R$ ' + s
    except Exception: return '—'

def fmt_var(v):
    if v is None: return '—'
    try: return ('+' if v >= 0 else '') + f'{v:.1f}%'.replace('.', ',')
    except Exception: return '—'

def fmt_pct(v, decimals=1):
    if v is None: return '—'
    try: return f'{v:.{decimals}f}%'.replace('.', ',')
    except Exception: return '—'

def cor_var(v, positivo_bom=True):
    if v is None: return 'var(--ink-mute)'
    if v == 0: return 'var(--ink-mute)'
    ok = (v >= 0) if positivo_bom else (v <= 0)
    if ok:
        return 'var(--verde)' if abs(v) >= 3 else 'var(--ink-dim)'
    if abs(v) >= 10: return 'var(--vermelho)'
    if abs(v) >= 3: return 'var(--amarelo)'
    return 'var(--ink-dim)'

def cor_margem_pct(v):
    if v is None: return 'var(--ink-mute)'
    if v >= 50: return 'var(--verde)'
    if v >= 30: return 'var(--amarelo)'
    return 'var(--vermelho)'

def selo_html(selo):
    classe = 'verde' if selo == 'verde' else 'cinza'
    return f'<span class="selo-relev {classe}"></span>'

def share_info(share, cupons, selo):
    return f'{selo_html(selo)}<span class="mono share-text">{fmt_dec_br(share, 1)}% · {fmt_int_br(cupons)} cup</span>'

def tri_comp(lw, l4w, l8w, positivo_bom=True):
    def mini(lbl, v):
        if v is None:
            return f'<span class="cmp"><span class="cmp-l">{lbl}</span><span class="cmp-v mute">—</span></span>'
        col = cor_var(v, positivo_bom)
        return f'<span class="cmp"><span class="cmp-l">{lbl}</span><span class="cmp-v" style="color:{col}">{fmt_var(v)}</span></span>'
    return f'<div class="tri-cmp">{mini("LW",lw)}{mini("L4W",l4w)}{mini("L8W",l8w)}</div>'


# ─────────────────────────────────────────────────────────────────────
# RENDER PRINCIPAL
# ─────────────────────────────────────────────────────────────────────
def gerar_html(D):
    meta = D['meta']
    kpis = D['kpis_macro']
    skus = D['skus']
    subgrupos = D['subgrupos']
    quadrantes = D['quadrantes']
    qmeta = D['quadrantes_meta']
    carteiras = D['carteiras']
    alertas = D['alertas_top5']
    cesta = D['cesta']
    chart_diario = D['chart_diario']
    evol_13sem = D['evolucao_13sem']
    evol_yoy = D['evolucao_yoy']
    padrao_horario = D['padrao_horario']
    faixas_ticket = D['faixas_ticket']
    gmpro = D['gmpro']

    # Selo idade margens
    idade = meta.get('margens_idade_dias', 9999)
    if idade < 60:    selo_marg_classe = 'verde'; selo_marg_txt = f'{idade}d (atualizado)'
    elif idade < 90:  selo_marg_classe = 'amarelo'; selo_marg_txt = f'{idade}d (atenção)'
    else:             selo_marg_classe = 'vermelho'; selo_marg_txt = f'{idade}d (desatualizado)'

    # Tornado: top 12 ganhadores e perdedores YoY 13sem (SKUs verde)
    skus_yoy = [s for s in skus if s.get('yoy_fat_pct') is not None and s.get('selo_relevancia')=='verde']
    ganhadores_yoy = sorted(skus_yoy, key=lambda x: -(x['yoy_fat_pct'] or 0))[:12]
    perdedores_yoy = sorted(skus_yoy, key=lambda x: (x['yoy_fat_pct'] or 0))[:12]

    # Top 30 SKUs Mesa por fat
    top30 = sorted(skus, key=lambda x: -x['fat_atual'])[:30]

    # Lançamentos
    lancamentos = [s for s in skus if s['lancamento']]
    lancamentos.sort(key=lambda x: x['dias_desde_lancamento'])

    # Subgrupos para drill
    subgrupos_keys = sorted(set(s['subgrupo'] for s in skus))

    # Setores (drill em algumas abas)
    setores_keys = sorted(set(s['setor'] for s in skus if s['setor']))

    data_js = json.dumps(D, ensure_ascii=False, default=str)

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Survey Gran Mesa — {meta['sem_label']} · {meta['periodo']}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Nunito+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;0,900;1,400&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
:root {{
  --bg: #ffffff;
  --bg-soft: #f6f4ee;
  --bg-cream: #faf7ef;
  --border: #e8e3d4;
  --border-soft: #f0ebdc;
  --ink: #1a1f1a;
  --ink-dim: #4a5248;
  --ink-mute: #8b8f86;
  --gran-verde: #1e4d2b;
  --gran-verde-2: #2d6a3f;
  --gran-verde-3: #3f8654;
  --gran-verde-bg: #e7f0e9;
  --gran-dourado: #c9a227;
  --gran-dourado-2: #e8b93a;
  --gran-dourado-bg: #faf1d4;
  --vermelho: #b8362f;
  --vermelho-bg: #f2d9d3;
  --amarelo: #d4a52e;
  --amarelo-bg: #faf1d4;
  --verde: #3f8654;
  --verde-bg: #e7f0e9;
  --azul-yoy: #5b8fb8;
  --laranja-alerta: #f0a020;
  --shadow: 0 1px 2px rgba(30,77,43,0.04), 0 4px 12px rgba(30,77,43,0.06);
  --shadow-hover: 0 2px 4px rgba(30,77,43,0.06), 0 8px 20px rgba(30,77,43,0.08);
}}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; }}
body {{
  background: var(--bg); color: var(--ink);
  font-family: 'Aptos','Nunito Sans',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  font-size: 15px; line-height: 1.55;
  -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale;
  font-variant-numeric: tabular-nums;
}}
.container {{ max-width: 1380px; margin: 0 auto; padding: 40px 32px 80px; }}
.mono {{ font-family: 'JetBrains Mono', monospace; }}

/* HEADER */
header.main-header {{
  display: flex; align-items: flex-end; justify-content: space-between;
  gap: 40px; padding: 24px 32px 28px;
  background: var(--gran-verde); color: #fff;
  border-radius: 12px; margin-bottom: 32px;
  box-shadow: var(--shadow); flex-wrap: wrap;
}}
header.main-header h1 {{
  font-weight: 800; font-size: 44px; line-height: 1.05;
  letter-spacing: -0.02em; margin: 8px 0 4px; color: #fff;
}}
header.main-header h1 em {{ font-style: normal; color: var(--gran-dourado-2); }}
.eyebrow {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px; letter-spacing: 0.2em; text-transform: uppercase;
  color: var(--gran-dourado-2); margin: 0; font-weight: 500;
}}
.subtitle {{ font-weight: 400; font-size: 17px; color: rgba(255,255,255,0.82); margin: 0 0 8px; }}
.meta {{ text-align: right; font-family: 'JetBrains Mono', monospace; font-size: 11px; color: rgba(255,255,255,0.7); letter-spacing: 0.05em; }}
.meta div {{ margin-bottom: 4px; }}
.meta strong {{ color: var(--gran-dourado-2); font-weight: 600; }}

/* TABS */
.tabs-wrap {{ position: sticky; top: 0; z-index: 50; background: var(--bg); padding: 4px 0 0; margin-bottom: 32px; border-bottom: 1px solid var(--border); }}
.tabs {{ display: flex; gap: 4px; overflow-x: auto; padding: 4px 0; scrollbar-width: thin; }}
.tab {{
  flex: 0 0 auto; padding: 12px 18px; border: none; background: transparent;
  cursor: pointer; font-family: inherit; font-size: 14px; font-weight: 600;
  color: var(--ink-mute); border-bottom: 3px solid transparent;
  transition: all 0.15s ease; white-space: nowrap; border-radius: 6px 6px 0 0;
}}
.tab:hover {{ color: var(--gran-verde); background: var(--bg-soft); }}
.tab.active {{ color: var(--gran-verde); border-bottom-color: var(--gran-dourado); background: var(--bg-cream); }}
.tab .num {{ font-family: 'JetBrains Mono', monospace; font-size: 10px; color: var(--ink-mute); margin-right: 8px; font-weight: 500; }}
.tab.active .num {{ color: var(--gran-dourado); }}

/* SECTIONS */
.tab-panel {{ display: none; animation: fadeIn 0.25s; }}
.tab-panel.active {{ display: block; }}
@keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(4px); }} to {{ opacity: 1; transform: none; }} }}

.section-kicker {{ font-family: 'JetBrains Mono',monospace; font-size: 10px; letter-spacing: 0.18em; text-transform: uppercase; color: var(--gran-dourado); margin: 0; font-weight: 600; }}
.section-title {{ font-size: 32px; font-weight: 700; letter-spacing: -0.02em; color: var(--gran-verde); margin: 4px 0 8px; line-height: 1.1; }}
.section-desc {{ font-size: 14px; color: var(--ink-dim); max-width: 920px; margin: 0 0 28px; }}
.section-sub {{ font-size: 18px; font-weight: 700; color: var(--gran-verde); margin: 28px 0 12px; }}

/* CHART BOX */
.chart-box {{ background: var(--bg-cream); border: 1px solid var(--border); border-radius: 10px; padding: 24px 28px; margin-bottom: 28px; box-shadow: var(--shadow); }}
.chart-box h3 {{ font-size: 18px; color: var(--gran-verde); margin: 0 0 4px; font-weight: 700; }}
.chart-box .desc {{ font-size: 13px; color: var(--ink-dim); margin: 0 0 16px; }}
.chart-wrap {{ position: relative; height: 320px; }}
.chart-wrap.tall {{ height: 420px; }}
.chart-wrap.short {{ height: 240px; }}
.grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
@media (max-width: 1100px) {{ .grid-2 {{ grid-template-columns: 1fr; }} }}

/* KPI GRID */
.kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 16px; margin-bottom: 36px; }}
.kpi-card {{
  padding: 22px 24px; border-radius: 10px; background: var(--bg-cream);
  border: 1px solid var(--border); box-shadow: var(--shadow);
  transition: box-shadow 0.2s ease;
}}
.kpi-card:hover {{ box-shadow: var(--shadow-hover); }}
.kpi-card.big {{
  grid-column: span 2; background: var(--gran-verde); color: #fff;
}}
.kpi-card.big .kpi-label, .kpi-card.big .cmp-l {{ color: var(--gran-dourado-2) !important; }}
.kpi-card.big .kpi-value {{ color: #fff !important; }}
.kpi-card.big .cmp-v.mute {{ color: rgba(255,255,255,0.5); }}
.kpi-label {{ font-family: 'JetBrains Mono',monospace; font-size: 10px; letter-spacing: 0.15em; text-transform: uppercase; color: var(--ink-mute); margin-bottom: 8px; font-weight: 600; }}
.kpi-value {{ font-size: 36px; font-weight: 800; color: var(--gran-verde); margin: 0 0 6px; line-height: 1.0; letter-spacing: -0.03em; }}
.kpi-value .unit {{ font-size: 17px; font-weight: 600; color: var(--gran-dourado); margin-right: 4px; }}
.kpi-card.big .kpi-value .unit {{ color: var(--gran-dourado-2); }}
.kpi-sub {{ font-size: 12px; color: var(--ink-dim); margin: 4px 0 8px; }}
.kpi-card.big .kpi-sub {{ color: rgba(255,255,255,0.7); }}

.tri-cmp {{ display: flex; gap: 14px; margin-top: 10px; }}
.cmp {{ display: flex; flex-direction: column; gap: 2px; min-width: 44px; }}
.cmp-l {{ font-family: 'JetBrains Mono',monospace; font-size: 9px; color: var(--ink-mute); letter-spacing: 0.1em; }}
.cmp-v {{ font-size: 13px; font-weight: 700; }}
.cmp-v.mute {{ color: var(--ink-mute); }}

/* GMPRO BLOCK */
.gmpro-block {{
  background: linear-gradient(135deg, var(--gran-dourado-bg) 0%, var(--bg-cream) 100%);
  border: 1px solid var(--gran-dourado); border-radius: 10px;
  padding: 18px 24px; margin-bottom: 28px;
}}
.gmpro-block .label {{ font-family: 'JetBrains Mono',monospace; font-size: 10px; letter-spacing: 0.18em; color: var(--gran-dourado); font-weight: 700; }}
.gmpro-block h3 {{ margin: 4px 0 14px; color: var(--gran-verde); font-size: 18px; }}
.gmpro-stats {{ display: flex; gap: 36px; flex-wrap: wrap; }}
.gmpro-stats > div {{ display: flex; flex-direction: column; gap: 3px; }}
.gmpro-stats .v {{ font-size: 22px; font-weight: 700; color: var(--gran-verde); }}
.gmpro-stats .l {{ font-family: 'JetBrains Mono',monospace; font-size: 10px; color: var(--ink-mute); letter-spacing: 0.05em; }}

/* ALERTAS */
.alertas-wrap {{ margin-bottom: 28px; }}
.alerta {{
  display: grid; grid-template-columns: 28px 130px 80px 1fr auto 110px;
  gap: 14px; align-items: center;
  background: var(--bg-cream); border-left: 4px solid var(--vermelho);
  border-radius: 4px; padding: 12px 16px; margin-bottom: 8px;
}}
.alerta.queda_macro    {{ border-left-color: var(--vermelho); }}
.alerta.queda_subgrupo {{ border-left-color: var(--vermelho); }}
.alerta.queda_yoy_sku  {{ border-left-color: var(--vermelho); }}
.alerta.subproducao    {{ border-left-color: var(--gran-dourado); }}
.alerta.ruptura        {{ border-left-color: var(--amarelo); }}
.alerta.lancamento     {{ border-left-color: var(--ink-mute); }}
.alerta-rank {{ font-family: 'JetBrains Mono',monospace; font-weight: 700; color: var(--gran-verde); font-size: 14px; }}
.alerta-tipo {{ font-family: 'JetBrains Mono',monospace; font-size: 10px; letter-spacing: 0.15em; text-transform: uppercase; color: var(--ink-mute); font-weight: 600; }}
.alerta-cod {{ font-family: 'JetBrains Mono',monospace; color: var(--ink-mute); font-size: 12px; }}
.alerta-desc {{ font-weight: 700; color: var(--ink); }}
.alerta-detalhe {{ color: var(--ink-dim); font-size: 13px; }}
.alerta-impacto {{ font-weight: 800; color: var(--vermelho); font-family: 'JetBrains Mono',monospace; text-align: right; font-size: 14px; }}

/* TORNADO */
.tornado-grid-duplo {{ display: grid; grid-template-columns: 1fr 1fr; gap: 32px; margin-top: 16px; }}
@media (max-width: 1100px) {{ .tornado-grid-duplo {{ grid-template-columns: 1fr; }} }}
.tornado-block h4 {{ margin: 0 0 14px; font-size: 14px; color: var(--gran-verde); font-weight: 700; padding-bottom: 8px; border-bottom: 2px solid var(--gran-verde); display: flex; justify-content: space-between; }}
.tornado-block h4 .label-2025 {{ color: var(--azul-yoy); font-size: 11px; font-family: 'JetBrains Mono',monospace; }}
.tornado-block h4 .label-2026 {{ color: var(--gran-verde); font-size: 11px; font-family: 'JetBrains Mono',monospace; }}
.tornado-row {{ display: grid; grid-template-columns: 1fr 200px 1fr; gap: 0; align-items: center; margin-bottom: 6px; height: 22px; }}
.tornado-bar-2025 {{ display: flex; justify-content: flex-end; height: 22px; }}
.tornado-bar-2025 .bar {{ background: var(--ink-mute); height: 100%; border-radius: 3px 0 0 3px; display: flex; align-items: center; justify-content: flex-end; padding-right: 6px; color: #fff; font-size: 10px; font-family: 'JetBrains Mono',monospace; font-weight: 600; }}
.tornado-mid {{ text-align: center; padding: 0 8px; }}
.tornado-mid .nome {{ font-size: 12px; font-weight: 600; color: var(--ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.tornado-mid .yoy {{ font-size: 11px; font-family: 'JetBrains Mono',monospace; font-weight: 700; }}
.tornado-bar-2026 {{ display: flex; justify-content: flex-start; height: 22px; }}
.tornado-bar-2026 .bar {{ height: 100%; border-radius: 0 3px 3px 0; display: flex; align-items: center; justify-content: flex-start; padding-left: 6px; color: #fff; font-size: 10px; font-family: 'JetBrains Mono',monospace; font-weight: 600; }}
.tornado-bar-2026 .bar.up {{ background: var(--gran-verde-3); }}
.tornado-bar-2026 .bar.down {{ background: var(--vermelho); }}
.tornado-bar-2026 .bar.flat {{ background: var(--ink-dim); }}

/* TABELAS */
table {{ width: 100%; border-collapse: collapse; font-size: 13px; font-variant-numeric: tabular-nums; }}
th, td {{ padding: 8px 10px; text-align: left; border-bottom: 1px solid var(--border-soft); }}
th {{ font-family: 'JetBrains Mono',monospace; font-size: 10px; letter-spacing: 0.1em; text-transform: uppercase; color: var(--gran-dourado-2); font-weight: 600; background: var(--gran-verde); }}
th.right, td.num {{ text-align: right; }}
td.cod {{ font-family: 'JetBrains Mono',monospace; color: var(--ink-mute); font-size: 11px; }}
td.num {{ font-family: 'JetBrains Mono',monospace; }}
td.yoy-13sem {{ border-left: 2px solid var(--gran-dourado); padding-left: 12px; font-weight: 700; }}
.table-wrap {{ overflow-x: auto; }}
tr:hover {{ background: var(--bg-soft); }}

/* TAGS */
.tag {{ display: inline-block; padding: 3px 8px; border-radius: 4px; font-family: 'JetBrains Mono',monospace; font-size: 10px; font-weight: 700; letter-spacing: 0.05em; }}
.tag.kvi-plus {{ background: var(--gran-verde); color: var(--gran-dourado-2); }}
.tag.kvi {{ background: var(--gran-verde-3); color: #fff; }}
.tag.A-star {{ background: var(--gran-dourado); color: #fff; }}
.tag.curva {{ background: transparent; border: 1px solid var(--border); color: var(--ink-dim); }}
.tag.elast-alta {{ background: var(--vermelho); color: #fff; }}
.tag.elast-media {{ background: var(--amarelo); color: #fff; }}
.tag.elast-baixa {{ background: var(--verde); color: #fff; }}
.tag.elast-atipico {{ background: var(--gran-dourado); color: #fff; }}
.tag.elast-sem-var {{ background: var(--ink-mute); color: #fff; }}
.tag.estrela {{ background: var(--verde); color: #fff; }}
.tag.vaca {{ background: var(--gran-dourado); color: #fff; }}
.tag.interrogacao {{ background: var(--ink-dim); color: #fff; }}
.tag.abacaxi {{ background: var(--vermelho); color: #fff; }}

/* SELO */
.selo-relev {{ display: inline-block; width: 8px; height: 8px; border-radius: 50%; vertical-align: middle; margin-right: 4px; }}
.selo-relev.verde {{ background: var(--verde); }}
.selo-relev.cinza {{ background: var(--ink-mute); }}
.share-text {{ font-size: 11px; color: var(--ink-mute); }}

/* HBARS SUBGRUPO */
.hbar-row {{ display: grid; grid-template-columns: 240px 1fr 110px 80px; gap: 14px; align-items: center; margin-bottom: 4px; height: 28px; padding: 0 4px; }}
.hbar-row:hover {{ background: var(--bg-soft); border-radius: 4px; }}
.hbar-name {{ font-size: 13px; color: var(--ink); font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.hbar-track {{ background: var(--bg-soft); height: 10px; border-radius: 5px; position: relative; overflow: hidden; }}
.hbar-fill {{ height: 100%; background: linear-gradient(90deg, var(--gran-verde), var(--gran-verde-3)); border-radius: 5px; transition: width 0.3s; }}
.hbar-val {{ font-family: 'JetBrains Mono',monospace; font-size: 12px; font-weight: 700; color: var(--gran-verde); text-align: right; }}
.hbar-var {{ font-family: 'JetBrains Mono',monospace; font-size: 12px; font-weight: 600; text-align: right; }}

/* CARDS SUBGRUPO COM SPARKLINE */
.cards-setor-wrap {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; margin-top: 16px; }}
.card-setor {{ padding: 18px 20px; border-radius: 10px; background: var(--bg-cream); border: 1px solid var(--border); border-left: 4px solid var(--ink-mute); box-shadow: var(--shadow); transition: box-shadow 0.2s; }}
.card-setor:hover {{ box-shadow: var(--shadow-hover); }}
.card-setor.up {{ border-left-color: var(--verde); }}
.card-setor.down {{ border-left-color: var(--vermelho); }}
.card-setor.flat {{ border-left-color: var(--amarelo); }}
.card-setor h4 {{ margin: 0 0 4px; font-size: 15px; color: var(--gran-verde); font-weight: 700; }}
.card-setor .meta-mini {{ font-family: 'JetBrains Mono',monospace; font-size: 10px; color: var(--ink-mute); letter-spacing: 0.05em; margin-bottom: 10px; }}
.card-setor .card-yoy {{ font-size: 32px; font-weight: 800; line-height: 1; letter-spacing: -0.02em; margin: 4px 0 6px; }}
.card-setor .card-yoy.up {{ color: var(--verde); }}
.card-setor .card-yoy.down {{ color: var(--vermelho); }}
.card-setor .card-yoy.flat {{ color: var(--amarelo); }}
.card-setor .card-yoy.null {{ color: var(--ink-mute); }}
.card-setor .card-fats {{ font-family: 'JetBrains Mono',monospace; font-size: 11px; color: var(--ink-dim); margin-bottom: 8px; }}
.card-setor .card-fats .v2025 {{ color: var(--azul-yoy); }}
.card-setor .card-fats .v2026 {{ color: var(--gran-verde); font-weight: 700; }}
.card-setor canvas {{ height: 50px !important; max-height: 50px; }}
.card-setor .card-margin {{ font-size: 11px; color: var(--ink-mute); margin-top: 8px; }}
.card-setor .card-margin strong {{ font-family: 'JetBrains Mono',monospace; }}

/* HEATMAP */
.heatmap-wrap {{ overflow-x: auto; }}
.heatmap {{ border-collapse: separate; border-spacing: 3px; }}
.heatmap th, .heatmap td {{ background: var(--bg); border: none; }}
.heatmap th {{ background: var(--gran-verde); color: var(--gran-dourado-2); padding: 6px 10px; font-size: 10px; }}
.heatmap td.row-label {{ background: var(--bg-cream); color: var(--ink); font-weight: 600; padding: 8px 12px; min-width: 200px; font-size: 13px; }}
.heatmap td.cell {{ width: 60px; height: 38px; padding: 4px 6px; font-family: 'JetBrains Mono',monospace; font-size: 11px; font-weight: 600; border-radius: 4px; text-align: center; }}

.toggle-row {{ background: var(--bg-cream); padding: 10px 14px; border-radius: 6px; margin-bottom: 16px; display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }}
.toggle-row label {{ font-family: 'JetBrains Mono',monospace; font-size: 10px; letter-spacing: 0.15em; color: var(--gran-verde); font-weight: 600; text-transform: uppercase; }}
.toggle-row select {{ font-family: inherit; font-size: 13px; padding: 6px 10px; border: 1.5px solid var(--gran-verde); border-radius: 5px; background: #fff; color: var(--gran-verde); font-weight: 600; cursor: pointer; }}
.toggle-row .info-pill {{ font-style: italic; color: var(--ink-dim); font-size: 12px; }}

/* LINHA DO TEMPO */
.linha-tempo-wrap {{ background: var(--bg-cream); border: 1px solid var(--border); border-radius: 10px; padding: 24px 28px; margin-top: 24px; }}
.linha-tempo-header {{ display: flex; gap: 24px; align-items: center; flex-wrap: wrap; margin-bottom: 16px; padding: 10px 14px; background: var(--bg); border-radius: 6px; }}
.linha-tempo-header label {{ font-family: 'JetBrains Mono',monospace; font-size: 10px; letter-spacing: 0.15em; color: var(--gran-verde); margin-right: 8px; font-weight: 700; }}
.linha-tempo-header select {{ font-family: inherit; font-size: 14px; padding: 8px 12px; border: 1.5px solid var(--gran-verde); border-radius: 6px; background: var(--bg); color: var(--gran-verde); font-weight: 500; min-width: 280px; cursor: pointer; }}
.linha-tempo-info {{ display: flex; align-items: center; gap: 10px; flex-wrap: wrap; font-weight: 700; font-size: 16px; color: var(--gran-verde); margin: 12px 0; }}
.linha-tempo-info .badge-mono {{ font-family: 'JetBrains Mono',monospace; font-size: 11px; padding: 3px 8px; background: var(--bg); border: 1px solid var(--border); border-radius: 4px; color: var(--ink-dim); font-weight: 600; }}

/* CESTA / CROSS-SELL */
.cesta-wrap {{ background: var(--bg-cream); border: 1px solid var(--border); border-radius: 10px; padding: 24px 28px; margin-top: 24px; }}
.cesta-header {{ display: flex; gap: 16px; align-items: center; flex-wrap: wrap; margin-bottom: 18px; }}
.cesta-stats {{ display: flex; gap: 18px; padding: 10px 14px; background: var(--gran-verde-bg); border-radius: 6px; font-size: 12px; }}
.cesta-stats .stat .l {{ font-family: 'JetBrains Mono',monospace; font-size: 10px; color: var(--ink-mute); letter-spacing: 0.05em; }}
.cesta-stats .stat .v {{ font-weight: 700; color: var(--gran-verde); font-size: 14px; }}
.cesta-companheiros .lift-bar {{ display: inline-block; height: 6px; background: var(--gran-verde-3); border-radius: 3px; vertical-align: middle; margin-right: 8px; }}

/* MATRIZ MARGEM x VOLUME */
.q-summary {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 18px; }}
.q-card {{ padding: 16px 18px; border-radius: 8px; }}
.q-card.estrela {{ background: var(--verde-bg); border-left: 4px solid var(--verde); }}
.q-card.vaca {{ background: var(--gran-dourado-bg); border-left: 4px solid var(--gran-dourado); }}
.q-card.interrogacao {{ background: var(--bg-soft); border-left: 4px solid var(--ink-mute); }}
.q-card.abacaxi {{ background: var(--vermelho-bg); border-left: 4px solid var(--vermelho); }}
.q-card .q-nome {{ font-family: 'JetBrains Mono',monospace; font-size: 11px; letter-spacing: 0.1em; text-transform: uppercase; font-weight: 700; }}
.q-card .q-n {{ font-size: 28px; font-weight: 800; color: var(--gran-verde); margin: 4px 0; }}
.q-card .q-acao {{ font-size: 11px; color: var(--ink-dim); }}

/* CARTEIRAS */
.carteira-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(290px, 1fr)); gap: 16px; margin-top: 20px; }}
.carteira-card {{ padding: 18px 20px; border-radius: 10px; background: var(--bg-cream); border: 1px solid var(--border); box-shadow: var(--shadow); border-left: 4px solid var(--gran-verde); }}
.carteira-card.fornecedor {{ background: var(--gran-dourado-bg); border-left-color: var(--gran-dourado); }}
.carteira-card.nao-atribuido {{ background: var(--vermelho-bg); border-left-color: var(--vermelho); }}
.carteira-card h4 {{ margin: 0 0 4px; font-size: 18px; color: var(--gran-verde); font-weight: 700; }}
.carteira-card .meta-mini {{ font-family: 'JetBrains Mono',monospace; font-size: 10px; color: var(--ink-mute); letter-spacing: 0.1em; margin-bottom: 12px; }}
.carteira-stats {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 12px; }}
.carteira-stats > div {{ display: flex; flex-direction: column; gap: 2px; }}
.carteira-stats label {{ font-family: 'JetBrains Mono',monospace; font-size: 9px; color: var(--ink-mute); letter-spacing: 0.1em; }}
.carteira-stats .v {{ font-size: 16px; font-weight: 800; color: var(--ink); font-family: 'JetBrains Mono',monospace; }}
.carteira-stats .v.alerta {{ color: var(--vermelho); }}
.carteira-card canvas {{ height: 50px !important; max-height: 50px; }}
.carteira-top {{ border-top: 1px dashed var(--border); padding-top: 8px; margin-top: 8px; font-size: 11px; }}
.carteira-top div {{ padding: 2px 0; color: var(--ink-dim); display: flex; justify-content: space-between; }}

/* PÓDIO */
.podio-grid {{ display: grid; grid-template-columns: 1fr 1.2fr 1fr; gap: 16px; margin: 24px 0; align-items: end; }}
.podio-card {{ background: var(--bg-cream); border: 2px solid var(--border); border-radius: 12px; padding: 20px 22px; text-align: center; box-shadow: var(--shadow); position: relative; overflow: hidden; }}
.podio-card.podio-1 {{ background: linear-gradient(180deg, #fff8dc 0%, var(--bg-cream) 100%); border-color: var(--gran-dourado); border-width: 3px; transform: scale(1.06); padding-top: 28px; padding-bottom: 28px; }}
.podio-card.podio-2 {{ background: linear-gradient(180deg, #f5f5f0 0%, var(--bg-cream) 100%); border-color: #c0c0c0; }}
.podio-card.podio-3 {{ background: linear-gradient(180deg, #f7e8d8 0%, var(--bg-cream) 100%); border-color: #cd7f32; }}
.podio-medal {{ font-size: 38px; line-height: 1; margin-bottom: 4px; }}
.podio-rank {{ font-family: 'JetBrains Mono', monospace; font-size: 14px; color: var(--ink-mute); font-weight: 700; }}
.podio-nome {{ font-size: 22px; font-weight: 800; color: var(--gran-verde); margin: 6px 0 4px; }}
.podio-score {{ font-size: 36px; font-weight: 800; color: var(--gran-verde); font-family: 'JetBrains Mono', monospace; line-height: 1; margin: 6px 0; letter-spacing: -0.03em; }}
.podio-fat {{ font-size: 12px; color: var(--ink-dim); font-family: 'JetBrains Mono', monospace; margin-bottom: 10px; }}
.podio-badges {{ display: flex; flex-wrap: wrap; gap: 4px; justify-content: center; }}

/* BADGES PILL */
.badges-row {{ display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 10px; }}
.badge-pill {{ font-family: 'JetBrains Mono',monospace; font-size: 9px; letter-spacing: 0.05em; padding: 3px 7px; background: var(--gran-verde); color: var(--gran-dourado-2); border-radius: 10px; font-weight: 700; }}

/* BARRA RANKING */
.barra-rank {{ background: var(--bg-soft); height: 6px; border-radius: 3px; margin-bottom: 4px; overflow: hidden; }}
.barra-fill {{ height: 100%; border-radius: 3px; transition: width 0.3s; }}
.rank-table td {{ padding: 12px 10px; }}

/* LANÇAMENTOS */
.lancamento-status {{ font-family: 'JetBrains Mono',monospace; font-size: 11px; padding: 3px 8px; border-radius: 3px; font-weight: 700; letter-spacing: 0.05em; }}
.lancamento-status.decolando {{ background: var(--verde-bg); color: var(--verde); }}
.lancamento-status.mediano {{ background: var(--gran-dourado-bg); color: var(--gran-dourado); }}
.lancamento-status.naopegou {{ background: var(--vermelho-bg); color: var(--vermelho); }}

/* CALLOUT / AVISO */
.callout {{ background: var(--gran-dourado-bg); border-left: 4px solid var(--gran-dourado); border-radius: 4px; padding: 12px 16px; font-size: 13px; margin: 16px 0; color: var(--ink-dim); }}
.aviso-painel {{ background: var(--bg-soft); border: 1px dashed var(--ink-mute); border-radius: 6px; padding: 8px 14px; margin: 16px 0; font-size: 12px; color: var(--ink-mute); }}

/* RUPTURA TR */
tr.ruptura td {{ background: var(--vermelho-bg) !important; }}

/* FOOTER */
.footer {{ margin-top: 60px; padding: 20px 0; border-top: 1px solid var(--border); display: flex; justify-content: space-between; flex-wrap: wrap; gap: 16px; font-family: 'JetBrains Mono',monospace; font-size: 11px; color: var(--ink-mute); }}
.footer .selo-marg {{ display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; vertical-align: middle; }}
.footer .selo-marg.verde {{ background: var(--verde); }}
.footer .selo-marg.amarelo {{ background: var(--amarelo); }}
.footer .selo-marg.vermelho {{ background: var(--vermelho); }}
</style>
</head>
<body>
<div class="container">
  <header class="main-header">
    <div>
      <p class="eyebrow">GRAN HORTIFRUTI · SURVEY GRAN MESA · v2</p>
      <h1>Semana <em>{meta['sem_label']}</em></h1>
      <p class="subtitle">{meta['periodo']} · 13 semanas de histórico · escopo equipe de produção</p>
    </div>
    <div class="meta">
      <div>Gerado em <strong>{datetime.now().strftime('%d/%m/%Y %H:%M')}</strong></div>
      <div>Cobertura mapping <strong>{meta['cobertura_mapping_pct']}%</strong></div>
      <div>Cobertura margem <strong>{meta['cobertura_margem_pct']}%</strong></div>
      <div>Margens há <strong>{idade}d</strong></div>
    </div>
  </header>

  <div class="tabs-wrap">
    <div class="tabs">
      <button class="tab active" data-tab="01"><span class="num">01</span>Headline</button>
      <button class="tab" data-tab="02"><span class="num">02</span>Panorama 13 sem</button>
      <button class="tab" data-tab="03"><span class="num">03</span>Subgrupos</button>
      <button class="tab" data-tab="04"><span class="num">04</span>Raio-X SKU + Cesta</button>
      <button class="tab" data-tab="05"><span class="num">05</span>Margem × Volume</button>
      <button class="tab" data-tab="06"><span class="num">06</span>Ruptura & Subprodução</button>
      <button class="tab" data-tab="07"><span class="num">07</span>Lançamentos & Carteiras</button>
    </div>
  </div>

{render_aba_01(D, kpis, alertas, ganhadores_yoy, perdedores_yoy, gmpro)}
{render_aba_02(D, evol_13sem, evol_yoy, padrao_horario, faixas_ticket, kpis)}
{render_aba_03(D, subgrupos, sids_focais=meta['sids_focais'])}
{render_aba_04(D, top30, skus, cesta, subgrupos_keys)}
{render_aba_05(D, quadrantes, qmeta, subgrupos_keys)}
{render_aba_06(D, skus, subgrupos_keys)}
{render_aba_07(D, lancamentos, carteiras)}

  <footer class="footer">
    <div>
      <span class="selo-marg {selo_marg_classe}"></span>
      Margens atualizadas em {meta['margens_data_atualizacao']} ({selo_marg_txt})
    </div>
    <div>Survey Gran Mesa v2 · escopo {len(skus)} SKUs · cobertura mapping {meta['cobertura_mapping_pct']}%</div>
  </footer>
</div>

<script>
const D = {data_js};

// Constantes de cores
const C = {{}};
const css = getComputedStyle(document.documentElement);
['--gran-verde','--gran-verde-2','--gran-verde-3','--gran-dourado','--gran-dourado-2',
 '--vermelho','--amarelo','--verde','--ink','--ink-dim','--ink-mute','--bg-cream','--border',
 '--azul-yoy','--bg-soft'].forEach(v => C[v.replace('--','')] = css.getPropertyValue(v).trim());

// Chart.js defaults
Chart.defaults.font.family = "Aptos, 'Nunito Sans', sans-serif";
Chart.defaults.font.size = 12;
Chart.defaults.color = C['ink-dim'];
Chart.defaults.borderColor = C['border'];
Chart.defaults.plugins.legend.labels.boxWidth = 12;

// Helpers
function fmtR(n) {{ return 'R$ ' + (n||0).toLocaleString('pt-BR',{{maximumFractionDigits:0}}); }}
function fmtR2(n) {{ return 'R$ ' + (n||0).toLocaleString('pt-BR',{{maximumFractionDigits:2,minimumFractionDigits:2}}); }}
function fmtN(n) {{ return (n||0).toLocaleString('pt-BR',{{maximumFractionDigits:0}}); }}
function fmtP(n,d=1) {{ if(n==null) return '—'; return n.toFixed(d).replace('.',',')+'%'; }}
function fmtSignP(n) {{ if(n==null) return '—'; return (n>=0?'+':'')+n.toFixed(1).replace('.',',')+'%'; }}
function corVar(v, posBom=true) {{
  if (v==null||v===0) return C['ink-mute'];
  const ok = posBom ? v>=0 : v<=0;
  if (ok) return Math.abs(v)>=3 ? C['verde'] : C['ink-dim'];
  if (Math.abs(v)>=10) return C['vermelho'];
  if (Math.abs(v)>=3) return C['amarelo'];
  return C['ink-dim'];
}}
function corMarg(v) {{ if(v==null) return C['ink-mute']; if(v>=50) return C['verde']; if(v>=30) return C['amarelo']; return C['vermelho']; }}
function cellColor(v) {{
  if (v==null) return '#f5f5f0';
  if (v>=15) return '#3f8654';
  if (v>=5) return '#7fb07d';
  if (v>=0) return '#c8dcc0';
  if (v>-5) return '#f0e4c0';
  if (v>-15) return '#e8b5a0';
  return '#b8362f';
}}
function cellTextColor(v) {{
  if (v==null) return C['ink-mute'];
  if (Math.abs(v)>=15) return '#fff';
  return C['ink'];
}}

// Tabs
document.querySelectorAll('.tab').forEach(btn => {{
  btn.addEventListener('click', () => {{
    document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
    window.scrollTo({{top:0, behavior:'smooth'}});
  }});
}});

{render_scripts(D)}

</script>
</body>
</html>"""
    return html


# ─────────────────────────────────────────────────────────────────────
# RENDER ABA 01 — HEADLINE
# ─────────────────────────────────────────────────────────────────────
def render_aba_01(D, kpis, alertas, ganhadores_yoy, perdedores_yoy, gmpro):
    fat_tri = tri_comp(kpis.get('fat_lw'), kpis.get('fat_l4w'), kpis.get('fat_l8w'))
    cup_tri = tri_comp(kpis.get('cupons_lw'), kpis.get('cupons_l4w'), kpis.get('cupons_l8w'))
    tic_tri = tri_comp(kpis.get('ticket_lw'), kpis.get('ticket_l4w'), kpis.get('ticket_l8w'))
    itn_tri = tri_comp(kpis.get('itens_lw'), kpis.get('itens_l4w'), kpis.get('itens_l8w'))
    sku_tri = tri_comp(kpis.get('skus_lw'), kpis.get('skus_l4w'), kpis.get('skus_l8w'))
    pct_tri = tri_comp(kpis.get('pct_loja_lw'), kpis.get('pct_loja_l4w'), kpis.get('pct_loja_l8w'))
    mar_tri = tri_comp(kpis.get('margem_pct_lw'), kpis.get('margem_pct_l4w'), kpis.get('margem_pct_l8w'))

    yoy_marker = ''
    if kpis.get('fat_yoy') is not None:
        col = cor_var(kpis['fat_yoy'])
        yoy_marker = f'<div class="kpi-sub">YoY <strong style="color:{col}">{fmt_var(kpis["fat_yoy"])}</strong></div>'

    return f"""
<section class="tab-panel active" id="tab-01">
  <p class="section-kicker">01 · Headline</p>
  <h2 class="section-title">A semana em números</h2>
  <p class="section-desc">Fechamento de {kpis['sem_label']} ({kpis['periodo']}) — escopo Gran Mesa: {meta_n_skus(D)} SKUs (Gran Mesa + Granel + Padaria Gran). Comparativo com semana anterior, média 4 sem, média 8 sem, e mesma semana ano anterior. Indicador % do fat da loja com triplo comparador para isolar evolução proporcional.</p>

  <div class="kpi-grid">
    <div class="kpi-card big">
      <div class="kpi-label">Faturamento Gran Mesa</div>
      <div class="kpi-value"><span class="unit">R$</span>{fmt_int_br(kpis['fat'])}</div>
      <div class="kpi-sub">{fmt_int_br(kpis['cupons'])} cupons · {fmt_brl(kpis['ticket'])} ticket médio</div>
      {yoy_marker}
      {fat_tri}
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Margem R$</div>
      <div class="kpi-value">{fmt_brl_full(kpis['margem_rs'])}</div>
      <div class="kpi-sub" style="color:{cor_margem_pct(kpis['margem_pct'])}">{fmt_pct(kpis['margem_pct'])} sobre fat</div>
      {mar_tri}
    </div>
    <div class="kpi-card">
      <div class="kpi-label">% do fat da loja</div>
      <div class="kpi-value" style="color:{cor_margem_pct(kpis['pct_loja']) if kpis['pct_loja']>=15 else 'var(--gran-verde)'}">{fmt_pct(kpis['pct_loja'])}</div>
      <div class="kpi-sub">loja toda fez {fmt_brl_full(kpis['fat_loja_atual'])}</div>
      {pct_tri}
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Cupons Gran Mesa</div>
      <div class="kpi-value">{fmt_int_br(kpis['cupons'])}</div>
      <div class="kpi-sub">{fmt_dec_br(kpis['itens_nf'],2)} itens/NF</div>
      {cup_tri}
    </div>
    <div class="kpi-card">
      <div class="kpi-label">Ticket médio Mesa</div>
      <div class="kpi-value">{fmt_brl(kpis['ticket'])}</div>
      <div class="kpi-sub">{fmt_dec_br(kpis['itens_nf'],2)} itens · NF</div>
      {tic_tri}
    </div>
    <div class="kpi-card">
      <div class="kpi-label">SKUs ativos</div>
      <div class="kpi-value">{fmt_int_br(kpis['skus'])}</div>
      <div class="kpi-sub">distintos vendidos na semana</div>
      {sku_tri}
    </div>
  </div>

  {render_gmpro_block(gmpro)}

  <div class="chart-box">
    <h3>Movimento dia a dia · semana atual vs L4W vs YoY</h3>
    <p class="desc">Barras = faturamento Gran Mesa de cada dia. Linha dourada = média do mesmo dia da semana nas 4 semanas anteriores. Linha azul = mesmo dia em S{kpis['sem_label'].split('/')[0].replace('S','')}/2025.</p>
    <div class="chart-wrap"><canvas id="chart-diario-01"></canvas></div>
  </div>

  <div class="chart-box">
    <h3>5 alertas com maior impacto absoluto em R$</h3>
    <p class="desc">Ordenados por impacto financeiro estimado, não por % de desvio. Um SKU com share &lt; 0,5% nunca vira alerta de capa.</p>
    <div class="alertas-wrap">
      {render_alertas(alertas)}
    </div>
  </div>

  <div class="chart-box">
    <h3>Tornado YoY · ganhadores e perdedores entre os SKUs Mesa</h3>
    <p class="desc">Visão dupla: <strong>semana atual</strong> mostra dinâmica pontual (o que está acontecendo agora), <strong>13 sem acumulado</strong> mostra problemas crônicos (o que está estruturalmente errado). Filtro por departamento ou subgrupo aplica nos dois.</p>
    <div class="toggle-row">
      <label>Filtro:</label>
      <select id="sel-tornado-cat">
        <option value="all">Todos os SKUs Mesa</option>
        <option value="cat:gran_mesa">Departamento · Gran Mesa</option>
        <option value="cat:granel">Departamento · Granel</option>
        <option value="cat:padaria_gran">Departamento · Padaria Gran</option>
        {render_options_subgrupos(D)}
      </select>
      <span class="info-pill">Comparação 2026 vs 2025</span>
    </div>

    <h4 class="section-sub" style="font-size:14px;margin:24px 0 8px">Semana atual · S{D['meta']['sem_label'].replace('S','').replace('/','-')}</h4>
    <div class="tornado-grid-duplo" id="tornado-skus-wrap">
      <div class="tornado-block">
        <h4><span class="label-2025">2025</span><span>↑ GANHADORES SEMANA</span><span class="label-2026">2026</span></h4>
        <div id="tornado-ganhadores"></div>
      </div>
      <div class="tornado-block">
        <h4><span class="label-2025">2025</span><span>↓ PERDEDORES SEMANA</span><span class="label-2026">2026</span></h4>
        <div id="tornado-perdedores"></div>
      </div>
    </div>

    <h4 class="section-sub" style="font-size:14px;margin:24px 0 8px">13 semanas acumuladas · problemas crônicos</h4>
    <div class="tornado-grid-duplo">
      <div class="tornado-block">
        <h4><span class="label-2025">2025</span><span>↑ GANHADORES 13SEM</span><span class="label-2026">2026</span></h4>
        <div id="tornado-13sem-ganhadores"></div>
      </div>
      <div class="tornado-block">
        <h4><span class="label-2025">2025</span><span>↓ PERDEDORES 13SEM</span><span class="label-2026">2026</span></h4>
        <div id="tornado-13sem-perdedores"></div>
      </div>
    </div>
  </div>
</section>
"""


def render_options_subgrupos(D):
    sgs = sorted(set(s['subgrupo'] for s in D['skus']))
    return ''.join(f'<option value="sg:{sg}">Subgrupo · {sg}</option>' for sg in sgs)


def render_gmpro_block(g):
    if not g or g.get('fat', 0) == 0:
        return '<div class="aviso-painel">⚠️ GMPro Omie sem dados (verifique data/produtividade/inputs/omie_gmpro.xlsx).</div>'
    return f"""
    <div class="gmpro-block">
      <div class="label">B2B · GRAN MESA PRO (OMIE) · refeições coletivas · 30d</div>
      <h3>Bloco segregado — não mistura em ticket / heatmap / cupons varejo</h3>
      <div class="gmpro-stats">
        <div><span class="v">{fmt_brl_full(g['fat'])}</span><span class="l">FATURAMENTO 30D</span></div>
        <div><span class="v" style="color:{cor_margem_pct(100-g['cmv_pct'])}">{fmt_pct(100-g['cmv_pct'])}</span><span class="l">MARGEM (CMV {g['cmv_pct']}%)</span></div>
        <div><span class="v">{fmt_brl_full(g['margem_rs'])}</span><span class="l">MARGEM R$</span></div>
        <div><span class="v">{fmt_int_br(g['clientes'])}</span><span class="l">CLIENTES ATIVOS</span></div>
        <div><span class="v">{fmt_int_br(g['cupons'])}</span><span class="l">NFs / CUPONS</span></div>
      </div>
    </div>
    """


def render_alertas(alertas):
    if not alertas:
        return '<div class="aviso-painel">✅ Nenhum alerta crítico esta semana.</div>'
    tipos_lbl = {
        'queda_macro':'QUEDA MACRO',
        'queda_subgrupo':'QUEDA SUBGRUPO',
        'queda_yoy_sku':'QUEDA YOY',
        'subproducao':'SUBPRODUÇÃO',
        'margem_baixa':'MARGEM BAIXA',
        'ruptura':'RUPTURA',
        'lancamento':'LANÇAMENTO',
    }
    out = []
    for i, a in enumerate(alertas, 1):
        out.append(f"""
        <div class="alerta {a['tipo']}">
          <div class="alerta-rank">#{i}</div>
          <div class="alerta-tipo">{tipos_lbl.get(a['tipo'], a['tipo'].upper())}</div>
          <div class="alerta-cod">{('cód '+a['cod']) if a['cod']!='—' else '—'}</div>
          <div class="alerta-desc">{a['desc']}</div>
          <div class="alerta-detalhe">{a['detalhe']}</div>
          <div class="alerta-impacto">{fmt_brl_full(a['impacto_rs'])}</div>
        </div>""")
    return ''.join(out)


def render_tornado_skus(skus, direcao):
    if not skus:
        return '<div class="aviso-painel">Sem dados YoY suficientes.</div>'
    max_v = max(max(s['fat_atual'], s['fat_yoy_rs']) for s in skus) or 1
    rows = []
    for s in skus:
        f_2025 = s['fat_yoy_rs']
        f_2026 = s['fat_atual']
        yoy = s['yoy_fat_pct']
        w_25 = abs(f_2025) / max_v * 100
        w_26 = abs(f_2026) / max_v * 100
        cls = 'up' if yoy and yoy > 5 else ('down' if yoy and yoy < -5 else 'flat')
        col_yoy = 'var(--verde)' if yoy and yoy >= 5 else ('var(--vermelho)' if yoy and yoy <= -5 else 'var(--ink-dim)')
        val_25 = fmt_brl_full(f_2025) if w_25 > 25 else ''
        val_26 = fmt_brl_full(f_2026) if w_26 > 25 else ''
        rows.append(f"""
        <div class="tornado-row">
          <div class="tornado-bar-2025"><div class="bar" style="width:{w_25}%">{val_25}</div></div>
          <div class="tornado-mid">
            <div class="nome">{s['descricao']}</div>
            <div class="yoy" style="color:{col_yoy}">{fmt_var(yoy)}</div>
          </div>
          <div class="tornado-bar-2026"><div class="bar {cls}" style="width:{w_26}%">{val_26}</div></div>
        </div>""")
    return ''.join(rows)


def meta_n_skus(D):
    return len(D.get('skus', []))


# ─────────────────────────────────────────────────────────────────────
# RENDER ABA 02 — PANORAMA 13 SEM
# ─────────────────────────────────────────────────────────────────────
def render_aba_02(D, evol_13sem, evol_yoy, padrao_horario, faixas_ticket, kpis):
    rows_yoy = []
    total_2026 = total_2025 = 0
    for r in evol_yoy:
        total_2026 += r['fat_2026']
        total_2025 += r['fat_2025']
        col = cor_var(r['yoy_pct'])
        col_dr = 'var(--verde)' if (r['delta_rs'] or 0) > 0 else ('var(--vermelho)' if (r['delta_rs'] or 0) < 0 else 'var(--ink-mute)')
        rows_yoy.append(f"""
        <tr>
          <td class="mono">{r['label']}</td>
          <td class="mono">{r['periodo_2026']}</td>
          <td class="mono" style="color:var(--azul-yoy)">{r['periodo_2025']}</td>
          <td class="num">{fmt_brl_full(r['fat_2026'])}</td>
          <td class="num" style="color:var(--azul-yoy)">{fmt_brl_full(r['fat_2025'])}</td>
          <td class="num" style="color:{col_dr}">{fmt_brl_full(r['delta_rs'])}</td>
          <td class="num" style="color:{col};font-weight:700">{fmt_var(r['yoy_pct'])}</td>
        </tr>""")
    yoy_total = ((total_2026/total_2025-1)*100) if total_2025 else None
    delta_total = total_2026 - total_2025
    col_tot = cor_var(yoy_total)

    return f"""
<section class="tab-panel" id="tab-02">
  <p class="section-kicker">02 · Panorama</p>
  <h2 class="section-title">13 semanas — o trimestre inteiro</h2>
  <p class="section-desc">Evolução completa do escopo Gran Mesa nas últimas 13 semanas focais. Toggle entre KPIs (Faturamento, Cupons, Ticket, Margem%) sem recarregar página. Comparação YoY linha 2026 vs 2025, com média móvel L4W como referência.</p>

  <div class="chart-box">
    <h3>Evolução semanal (toggle KPI)</h3>
    <div class="toggle-row">
      <label>KPI:</label>
      <select id="sel-kpi-evolucao">
        <option value="fat">Faturamento</option>
        <option value="cupons">Cupons</option>
        <option value="ticket">Ticket médio</option>
        <option value="media_dia">Média/dia</option>
        <option value="margem_pct">Margem %</option>
        <option value="pct_loja">% do fat da loja</option>
      </select>
      <span class="info-pill">Linha verde = 2026 · Linha azul = 2025 · Linha dourada = L4W (média móvel)</span>
    </div>
    <div class="chart-wrap tall"><canvas id="chart-evolucao"></canvas></div>
  </div>

  <div class="chart-box">
    <h3>Tabela YoY 13 sem · linha por linha</h3>
    <p class="desc">Faturamento Gran Mesa por semana 2026 vs mesma semana 2025. Total das 13 semanas no rodapé.</p>
    <div class="table-wrap">
      <table>
        <thead><tr>
          <th>Sem</th><th>Período 2026</th><th style="color:var(--gran-dourado-2)">Período 2025</th>
          <th class="right">Fat 2026</th><th class="right" style="color:var(--gran-dourado-2)">Fat 2025</th>
          <th class="right">Δ R$</th><th class="right">YoY %</th>
        </tr></thead>
        <tbody>{''.join(rows_yoy)}</tbody>
        <tfoot><tr style="border-top:2px solid var(--gran-verde);font-weight:700">
          <td colspan="3" class="mono">TOTAL 13 SEM</td>
          <td class="num">{fmt_brl_full(total_2026)}</td>
          <td class="num">{fmt_brl_full(total_2025)}</td>
          <td class="num" style="color:{cor_var((delta_total or 0))}">{fmt_brl_full(delta_total)}</td>
          <td class="num" style="color:{col_tot}">{fmt_var(yoy_total)}</td>
        </tr></tfoot>
      </table>
    </div>
  </div>

  <div class="grid-2">
    <div class="chart-box">
      <h3>Padrão horário · semana atual</h3>
      <p class="desc">Distribuição de cupons (verde) e faturamento (dourado) por hora do dia. Filtre por dia da semana ou agregação (úteis vs fim de semana) para entender quando produzir.</p>
      <div class="toggle-row">
        <label>Filtro:</label>
        <select id="sel-horario-dia">
          <option value="all">Toda a semana</option>
          <option value="uteis">Dias úteis (qua a sex + seg/ter)</option>
          <option value="fds">Fim de semana (sáb + dom)</option>
          <option value="2">Quarta</option>
          <option value="3">Quinta</option>
          <option value="4">Sexta</option>
          <option value="5">Sábado</option>
          <option value="6">Domingo</option>
          <option value="0">Segunda</option>
          <option value="1">Terça</option>
        </select>
      </div>
      <div class="chart-wrap"><canvas id="chart-horario"></canvas></div>
    </div>
    <div class="chart-box">
      <h3>Faixas de ticket · semana atual</h3>
      <p class="desc">Quantos cupons em cada faixa de valor e quanto cada faixa contribui no faturamento total.</p>
      <div class="chart-wrap"><canvas id="chart-faixas"></canvas></div>
    </div>
  </div>

  <div class="chart-box">
    <h3>Movimento dia a dia · semana atual vs L4W vs YoY</h3>
    <p class="desc">Mesmo gráfico da Aba 01, replicado para análise contextual junto à evolução 13 semanas.</p>
    <div class="chart-wrap"><canvas id="chart-diario-02"></canvas></div>
  </div>
</section>
"""


# ─────────────────────────────────────────────────────────────────────
# RENDER ABA 03 — SUBGRUPOS
# ─────────────────────────────────────────────────────────────────────
def render_aba_03(D, subgrupos, sids_focais):
    # Hbars
    fat_max = max(s['fat_atual'] for s in subgrupos) or 1
    hbars = []
    for s in subgrupos:
        w = s['fat_atual']/fat_max*100
        col_var = cor_var(s['var_l4w_pct'])
        hbars.append(f"""
        <div class="hbar-row">
          <div class="hbar-name">{s['subgrupo']}</div>
          <div class="hbar-track"><div class="hbar-fill" style="width:{w}%"></div></div>
          <div class="hbar-val">{fmt_brl_full(s['fat_atual'])}</div>
          <div class="hbar-var" style="color:{col_var}">{fmt_var(s['var_l4w_pct'])}</div>
        </div>""")

    # Cards subgrupos
    cards = []
    for s in subgrupos:
        yoy = s['yoy_13sem_pct']
        cls = 'up' if yoy and yoy > 5 else ('down' if yoy and yoy < -5 else ('flat' if yoy is not None else 'null'))
        cards.append(f"""
        <div class="card-setor {cls}">
          <h4>{s['subgrupo']}</h4>
          <div class="meta-mini">{s['n_skus']} SKUs · {fmt_dec_br(s['share_pct'],1)}% DO FAT MESA</div>
          <div class="card-yoy {cls}">{fmt_var(yoy)}</div>
          <div class="card-fats"><span class="v2026">{fmt_brl_full(s['fat_2026_13sem'])}</span> · <span class="v2025">{fmt_brl_full(s['fat_2025_13sem'])}</span> em 13 sem</div>
          <canvas id="spark-sg-{slugify(s['subgrupo'])}" data-spark='{json.dumps(s["sparkline"])}'></canvas>
          <div class="card-margin">Margem: <strong style="color:{cor_margem_pct(s['margem_pct'])}">{fmt_pct(s['margem_pct'])}</strong></div>
        </div>""")

    # Tornado dual subgrupos
    sgs_yoy = sorted(subgrupos, key=lambda x: -(x['fat_2026_13sem'] or 0))[:12]
    tornado_atual = render_tornado_subgrupos(sgs_yoy, modo='atual')
    tornado_13sem = render_tornado_subgrupos(sgs_yoy, modo='13sem')

    # Heatmap
    sids_focais_list = sids_focais
    sgs_top = sorted(subgrupos, key=lambda x: -(x['fat_atual'] or 0))
    heatmap_rows_l4w = []
    heatmap_rows_yoy = []
    sem_labels = [f'S{i}' for i in range(1, len(sids_focais_list)+1)]
    for sg in sgs_top:
        cells_l4w = ''.join(
            f'<td class="cell" data-v="{v if v is not None else ""}">{fmt_var(v)}</td>'
            for v in sg['heatmap_l4w']
        )
        cells_yoy = ''.join(
            f'<td class="cell" data-v="{v if v is not None else ""}">{fmt_var(v)}</td>'
            for v in sg['heatmap_yoy']
        )
        heatmap_rows_l4w.append(f'<tr><td class="row-label">{sg["subgrupo"]}</td>{cells_l4w}</tr>')
        heatmap_rows_yoy.append(f'<tr><td class="row-label">{sg["subgrupo"]}</td>{cells_yoy}</tr>')

    head_cells = ''.join(f'<th>{lbl}</th>' for lbl in sem_labels)

    # Tabela completa
    rows_tab = []
    for s in subgrupos:
        rows_tab.append(f"""
        <tr>
          <td>{s['subgrupo']}</td>
          <td class="num">{fmt_int_br(s['n_skus'])}</td>
          <td class="num">{fmt_brl_full(s['fat_atual'])}</td>
          <td class="num" style="color:{cor_var(s['var_lw_pct'])}">{fmt_var(s['var_lw_pct'])}</td>
          <td class="num" style="color:{cor_var(s['var_l4w_pct'])}">{fmt_var(s['var_l4w_pct'])}</td>
          <td class="num" style="color:{cor_var(s['var_l8w_pct'])}">{fmt_var(s['var_l8w_pct'])}</td>
          <td class="num" style="color:{cor_var(s['var_yoy_pct'])}">{fmt_var(s['var_yoy_pct'])}</td>
          <td class="num yoy-13sem" style="color:{cor_var(s['yoy_13sem_pct'])}">{fmt_var(s['yoy_13sem_pct'])}</td>
          <td class="num">{fmt_brl_full((s['fat_2026_13sem'] or 0)-(s['fat_2025_13sem'] or 0))}</td>
          <td class="num">{fmt_dec_br(s['share_pct'],1)}%</td>
          <td class="num" style="color:{cor_margem_pct(s['margem_pct'])}">{fmt_pct(s['margem_pct'])}</td>
        </tr>""")

    return f"""
<section class="tab-panel" id="tab-03">
  <p class="section-kicker">03 · Subgrupos</p>
  <h2 class="section-title">Quem puxa, quem cresce, quem afunda</h2>
  <p class="section-desc">Os 11 subgrupos do escopo Gran Mesa, com tornado YoY duplo (semana atual + 13 sem acumulado), heatmap visual, cards detalhados com sparkline e tabela completa para drill.</p>

  <div class="chart-box">
    <h3>Faturamento por subgrupo · semana atual</h3>
    <p class="desc">Variação à direita = vs L4W (média 4 sem anteriores).</p>
    {''.join(hbars)}
  </div>

  <div class="chart-box">
    <h3>Tornado YoY · semana atual e 13 sem acumulado</h3>
    <p class="desc">Subgrupos lado a lado: 2025 à esquerda (cinza), 2026 à direita (verde se cresceu, vermelho se caiu). Mesma escala visual entre os dois lados.</p>
    <div class="tornado-grid-duplo">
      <div class="tornado-block">
        <h4><span class="label-2025">2025</span><span>SEMANA ATUAL</span><span class="label-2026">2026</span></h4>
        {tornado_atual}
      </div>
      <div class="tornado-block">
        <h4><span class="label-2025">2025</span><span>13 SEMANAS</span><span class="label-2026">2026</span></h4>
        {tornado_13sem}
      </div>
    </div>
  </div>

  <div class="chart-box">
    <h3>Cards por subgrupo · YoY 13 semanas + sparkline</h3>
    <p class="desc">Border-left colorido por desempenho. Sparkline mostra evolução semana a semana 2026 (barras verdes) com cor por intensidade.</p>
    <div class="cards-setor-wrap">{''.join(cards)}</div>
  </div>

  <div class="chart-box">
    <h3>Heatmap subgrupo × semana</h3>
    <div class="toggle-row">
      <label>Modo:</label>
      <select id="sel-heatmap-modo">
        <option value="l4w">vs L4W (média 4 sem)</option>
        <option value="yoy">vs YoY (mesma sem 2025)</option>
      </select>
      <span class="info-pill">Verde = cresceu · Vermelho = caiu · Mais escuro = variação maior</span>
    </div>
    <div class="heatmap-wrap">
      <table class="heatmap" id="heatmap-table">
        <thead><tr><th class="row-label">Subgrupo</th>{head_cells}</tr></thead>
        <tbody id="heatmap-body-l4w" style="">{''.join(heatmap_rows_l4w)}</tbody>
        <tbody id="heatmap-body-yoy" style="display:none">{''.join(heatmap_rows_yoy)}</tbody>
      </table>
    </div>
  </div>

  <div class="chart-box">
    <h3>Tabela completa · subgrupos com todos os comparadores</h3>
    <p class="desc">Coluna YoY 13 sem destacada com borda dourada — é o indicador de tendência mais robusto.</p>
    <div class="table-wrap">
      <table>
        <thead><tr>
          <th>Subgrupo</th><th class="right">SKUs</th><th class="right">Fat sem</th>
          <th class="right">vs LW</th><th class="right">vs L4W</th><th class="right">vs L8W</th>
          <th class="right">YoY sem</th><th class="right" style="color:var(--gran-dourado-2)">YoY 13sem</th>
          <th class="right">Δ R$ 13sem</th><th class="right">Share %</th><th class="right">Margem %</th>
        </tr></thead>
        <tbody>{''.join(rows_tab)}</tbody>
      </table>
    </div>
  </div>
</section>
"""


def render_tornado_subgrupos(subgrupos, modo):
    if modo == 'atual':
        # fat_atual vs fat_yoy
        skus = [(s['subgrupo'], s['fat_yoy'], s['fat_atual'], s['var_yoy_pct']) for s in subgrupos]
    else:
        skus = [(s['subgrupo'], s['fat_2025_13sem'], s['fat_2026_13sem'], s['yoy_13sem_pct']) for s in subgrupos]
    if not skus: return '<div class="aviso-painel">Sem dados.</div>'
    skus = [t for t in skus if (t[1] or 0) + (t[2] or 0) > 0]
    if not skus: return '<div class="aviso-painel">Sem dados.</div>'
    max_v = max(max(t[1] or 0, t[2] or 0) for t in skus) or 1
    rows = []
    for nome, f25, f26, yoy in skus:
        w_25 = abs(f25 or 0)/max_v*100
        w_26 = abs(f26 or 0)/max_v*100
        cls = 'up' if yoy and yoy > 5 else ('down' if yoy and yoy < -5 else 'flat')
        col_yoy = 'var(--verde)' if yoy and yoy >= 5 else ('var(--vermelho)' if yoy and yoy <= -5 else 'var(--ink-dim)')
        val_25 = fmt_brl_full(f25) if w_25 > 25 else ''
        val_26 = fmt_brl_full(f26) if w_26 > 25 else ''
        rows.append(f"""
        <div class="tornado-row">
          <div class="tornado-bar-2025"><div class="bar" style="width:{w_25}%">{val_25}</div></div>
          <div class="tornado-mid">
            <div class="nome">{nome}</div>
            <div class="yoy" style="color:{col_yoy}">{fmt_var(yoy)}</div>
          </div>
          <div class="tornado-bar-2026"><div class="bar {cls}" style="width:{w_26}%">{val_26}</div></div>
        </div>""")
    return ''.join(rows)


def slugify(s):
    return ''.join(c if c.isalnum() else '-' for c in s.lower())[:30]


# ─────────────────────────────────────────────────────────────────────
# RENDER ABA 04 — RAIO-X SKU + CESTA
# ─────────────────────────────────────────────────────────────────────
def render_aba_04(D, top30, skus, cesta, subgrupos_keys):
    # Top 30 (com data-cat para filtro JS)
    rows_top = []
    for i, s in enumerate(top30, 1):
        kvi_tag = f'<span class="tag kvi-plus">{s["kvi"]}</span>' if s['kvi'] == 'KVI+' else (f'<span class="tag kvi">{s["kvi"]}</span>' if s['kvi']=='KVI' else '')
        curva_tag = f'<span class="tag A-star">{s["curva"]}</span>' if s['curva']=='A*' else (f'<span class="tag curva">{s["curva"]}</span>' if s['curva'] not in (None,'-','') else '')
        cat_lbl = {'gran_mesa':'Gran Mesa','granel':'Granel','padaria_gran':'Padaria'}.get(s['categoria_mesa'],s['categoria_mesa'])
        rows_top.append(f"""
        <tr data-cat="{s['categoria_mesa']}">
          <td class="num">{i}</td>
          <td>{share_info(s['share_fat_mesa'], s['cupons_atual'], s['selo_relevancia'])}</td>
          <td class="cod">{s['cod']}</td>
          <td>{s['descricao']}</td>
          <td style="font-size:11px;color:var(--ink-mute)">{cat_lbl}</td>
          <td style="font-size:11px;color:var(--ink-mute)">{s['subgrupo']}</td>
          <td>{kvi_tag} {curva_tag}</td>
          <td class="num">{fmt_brl_full(s['fat_atual'])}</td>
          <td class="num" style="color:{cor_var(s['var_lw_pct'])}">{fmt_var(s['var_lw_pct'])}</td>
          <td class="num" style="color:{cor_var(s['var_l4w_pct'])}">{fmt_var(s['var_l4w_pct'])}</td>
          <td class="num" style="color:{cor_var(s['var_l8w_pct'])}">{fmt_var(s['var_l8w_pct'])}</td>
          <td class="num" style="color:{cor_var(s['yoy_fat_pct'])};border-left:2px solid var(--gran-dourado);padding-left:8px" title="fat vs mesma sem 2025">{fmt_var(s['yoy_fat_pct'])}</td>
          <td class="num" style="color:{cor_var(s.get('yoy_qtd_pct'))}" title="qtd vs mesma sem 2025">{fmt_var(s.get('yoy_qtd_pct'))}</td>
          <td class="num">{fmt_dec_br(s['qtd_atual'],1)}</td>
          <td class="num">{fmt_brl(s['preco_medio'])}</td>
          <td class="num" style="color:{cor_margem_pct(s['margem_pct'])}">{fmt_pct(s['margem_pct'])}</td>
        </tr>""")

    return f"""
<section class="tab-panel" id="tab-04">
  <p class="section-kicker">04 · Raio-X SKU + Cesta</p>
  <h2 class="section-title">SKU a SKU — desempenho e venda casada</h2>
  <p class="section-desc">Top 30 SKUs Mesa por faturamento na semana atual com triplo comparador, linha do tempo individual com toggle quantidade/faturamento × preço, e <strong>análise de cesta</strong>: para cada SKU Mesa relevante, os top 8 SKUs companheiros ranqueados por lift (probabilidade de aparecer no mesmo cupom).</p>

  <div class="chart-box">
    <h3>Top 30 SKUs Mesa · semana atual</h3>
    <p class="desc">Ordenado por faturamento. Filtre por departamento (Gran Mesa / Granel / Padaria) — visualização mais ampla com menos cliques.</p>
    <div class="toggle-row">
      <label>Filtro departamento:</label>
      <select id="sel-cat-top30">
        <option value="all">Todos</option>
        <option value="gran_mesa">Gran Mesa</option>
        <option value="granel">Granel</option>
        <option value="padaria_gran">Padaria Gran</option>
      </select>
    </div>
    <div class="table-wrap">
      <table id="tab-top30">
        <thead><tr>
          <th>#</th><th>Relev.</th><th>Cód</th><th>Descrição</th><th>Depto</th><th>Subgrupo</th><th>Tags</th>
          <th class="right">Fat sem</th><th class="right">vs LW</th><th class="right">vs L4W</th>
          <th class="right">vs L8W</th>
          <th class="right" title="fat vs mesma sem 2025" style="border-left:2px solid var(--gran-dourado);padding-left:8px">YoY Fat</th>
          <th class="right" title="qtd vs mesma sem 2025">YoY Qtd</th>
          <th class="right">Qtd</th>
          <th class="right">Preço</th><th class="right">Margem %</th>
        </tr></thead>
        <tbody id="tbody-top30">{''.join(rows_top)}</tbody>
      </table>
    </div>
  </div>

  <div class="linha-tempo-wrap">
    <h3 class="section-sub" style="margin-top:0">Linha do tempo · evolução de SKU escolhido</h3>
    <p class="section-desc">Selecione qualquer SKU do top 30 para ver suas 13 semanas. Toggle entre Quantidade × Preço ou Faturamento × Preço.</p>
    <div class="linha-tempo-header">
      <div><label>SKU:</label><select id="sku-select"></select></div>
      <div><label>VISÃO:</label><select id="visao-select">
        <option value="qtd">Quantidade × Preço</option>
        <option value="fat">Faturamento × Preço</option>
      </select></div>
    </div>
    <div class="linha-tempo-info" id="sku-info">—</div>
    <div class="chart-wrap tall"><canvas id="linha-tempo-chart"></canvas></div>
  </div>

  <div class="cesta-wrap">
    <h3 class="section-sub" style="margin-top:0">Análise de cesta · venda casada</h3>
    <p class="section-desc">Para cada SKU Gran Mesa relevante, os top 10 produtos da loja que mais aparecem no mesmo cupom.</p>
    <div class="callout" style="background:var(--gran-dourado-bg);border-color:var(--gran-dourado);margin:12px 0">
      <strong>Critério atual de ordenamento (v2.1.4):</strong>
      <ol style="margin:6px 0 0 20px;font-size:13px;line-height:1.6">
        <li><strong>Filtro de ruído:</strong> SKU Mesa precisa estar em ≥5 cupons das 13 sem; companheiro precisa ter ≥3 cupons compartilhados.</li>
        <li><strong>Ordenação default:</strong> <code>Lift</code> decrescente. Lift = P(B|A) ÷ P(B). Mede "quantas vezes mais" o companheiro aparece junto vs sozinho.</li>
        <li><strong>Ordenações alternativas</strong> (use o seletor abaixo): <code>Score</code> (lift × √suporte — equilibra força da associação com volume), <code>Suporte</code> (% dos cupons da loja que têm ambos — mede tamanho do mercado), <code>Cupons juntos</code> (volume bruto), <code>Fat companheiro</code> (R$ que o companheiro gera).</li>
      </ol>
      <p style="margin:8px 0 0 0;font-size:12px;color:var(--ink-mute)">⚠ <strong>Lift puro tem um viés conhecido:</strong> companheiros raros (vendidos em poucos cupons) podem ter lift altíssimo sem relevância de negócio (ex: produto vendido em 3 cupons total, todos junto com o SKU Mesa = lift gigante mas vende quase nada). Use <code>Score</code> ou cruze com <code>Suporte</code> para filtrar esse tipo de falso positivo.</p>
    </div>
    <div class="linha-tempo-header">
      <div><label>SKU MESA:</label><select id="cesta-select"></select></div>
      <div><label>Ordenar por:</label>
        <select id="cesta-sort">
          <option value="lift">Lift (default)</option>
          <option value="score">Score combinado (lift × √suporte)</option>
          <option value="suporte">Suporte (% cupons loja)</option>
          <option value="cupons">Cupons juntos</option>
          <option value="fat">Faturamento companheiro</option>
        </select>
      </div>
    </div>
    <div class="cesta-stats" id="cesta-stats">
      <div class="stat"><div class="l">CUPONS COM SKU</div><div class="v" id="cesta-n-cupons">—</div></div>
      <div class="stat"><div class="l">COMPANHEIROS</div><div class="v" id="cesta-n-comp">—</div></div>
    </div>
    <div class="table-wrap">
      <table id="cesta-tabela">
        <thead><tr>
          <th>#</th><th>Cód</th><th>Descrição companheira</th><th>Setor</th>
          <th class="right" title="P(B|A) ÷ P(B) — quantas vezes mais aparece junto vs sozinho">Lift</th>
          <th class="right" title="lift × √suporte — equilibra força e volume">Score</th>
          <th class="right">Cupons juntos</th>
          <th class="right" title="P(B|A) — chance de levar o companheiro dado que o SKU Mesa está no cupom">P(B|A)</th>
          <th class="right" title="% de TODOS os cupons da loja que têm AMBOS — tamanho do mercado">Suporte</th>
          <th class="right">Fat companheiro</th>
        </tr></thead>
        <tbody id="cesta-body"></tbody>
      </table>
    </div>
    <div class="callout">
      <strong>Como ler em 3 segundos:</strong> Lift 5 = aparece 5× mais junto que sozinho. P(B|A) 40% = 4 em 10 cupons do SKU Mesa têm o companheiro. Suporte 2% = 2% dos cupons da loja inteira têm ambos. <strong>Score</strong> = melhor número único — alto Score significa associação forte E volume relevante.
    </div>
  </div>
</section>
"""


# ─────────────────────────────────────────────────────────────────────
# RENDER ABA 05 — MARGEM × VOLUME
# ─────────────────────────────────────────────────────────────────────
def render_aba_05(D, quadrantes, qmeta, subgrupos_keys):
    # Contagem por quadrante
    counts = {'Estrela':0,'Vaca':0,'Interrogação':0,'Abacaxi':0}
    for q in quadrantes: counts[q['quadrante']] += 1
    # v2.1.4: custo hora-homem para mostrar no header explicativo
    custo_hr_label = '15.00'
    if D.get('skus'):
        custo_hr_label = f"{D['skus'][0].get('custo_hora_homem_rs', 15.0):.2f}"

    def row(s):
        cls_q = {'Estrela':'estrela','Vaca':'vaca','Interrogação':'interrogacao','Abacaxi':'abacaxi'}[s['quadrante']]
        cat_lbl = {'gran_mesa':'Gran Mesa','granel':'Granel','padaria_gran':'Padaria'}.get(s['categoria_mesa'], s['categoria_mesa'])
        marg_h = s.get('margem_rs_por_hora_est')
        marg_h_str = fmt_brl_full(marg_h) + '/h' if marg_h is not None else '—'
        cor_h = 'var(--verde)' if (marg_h is not None and marg_h>=80) else ('var(--amarelo)' if (marg_h is not None and marg_h>=30) else 'var(--vermelho)' if marg_h is not None else 'var(--ink-mute)')
        # v2.1.4: novas colunas — custo das horas + margem líquida pós-custo
        custo_h_rs = s.get('custo_horas_rs')
        marg_liq_rs = s.get('margem_liquida_rs')
        marg_liq_pct = s.get('margem_liquida_pct')
        custo_h_str = fmt_brl_full(custo_h_rs) if custo_h_rs is not None else '—'
        marg_liq_rs_str = fmt_brl_full(marg_liq_rs) if marg_liq_rs is not None else '—'
        marg_liq_pct_str = fmt_pct(marg_liq_pct) if marg_liq_pct is not None else '—'
        cor_liq = ('var(--vermelho)' if (marg_liq_rs is not None and marg_liq_rs < 0)
                   else 'var(--amarelo)' if (marg_liq_pct is not None and marg_liq_pct < 30)
                   else 'var(--verde)' if marg_liq_rs is not None else 'var(--ink-mute)')
        custo_hr_ref = s.get('custo_hora_homem_rs', 15.0)
        horas_est = s.get('horas_estim_sem', 0)
        return f"""
        <tr data-cat="{s['categoria_mesa']}" data-sg="{s['subgrupo']}">
          <td>{share_info(s['share_fat_mesa'], s['cupons_atual'], s['selo_relevancia'])}</td>
          <td class="cod">{s['cod']}</td>
          <td>{s['descricao']}</td>
          <td style="font-size:11px;color:var(--ink-mute)">{cat_lbl}</td>
          <td style="font-size:11px;color:var(--ink-mute)">{s['subgrupo']}</td>
          <td class="num">{fmt_brl_full(s['fat_atual'])}</td>
          <td class="num" style="color:{cor_margem_pct(s['margem_pct'])}">{fmt_pct(s['margem_pct'])}</td>
          <td class="num">{fmt_brl_full(s['margem_rs'])}</td>
          <td class="num" title="{horas_est:.1f}h × R$ {custo_hr_ref:.2f}/h">{custo_h_str}</td>
          <td class="num" style="color:{cor_liq};font-weight:700" title="margem bruta − custo das horas">{marg_liq_rs_str}<br><span style="font-size:10px;font-weight:400">{marg_liq_pct_str}</span></td>
          <td class="num" style="color:{cor_h}" title="rendimento de margem POR hora trabalhada (eficiência operacional, não é margem líquida)"><em>{marg_h_str}</em></td>
          <td><span class="tag {cls_q}">{s['quadrante']}</span></td>
        </tr>"""

    # Top 30 (vai filtrar via JS)
    interr_all = sorted([q for q in quadrantes if q['quadrante']=='Interrogação' and q['selo_relevancia']=='verde'],
                        key=lambda x: -x['margem_pct'])
    abac_all = sorted([q for q in quadrantes if q['quadrante']=='Abacaxi'], key=lambda x: -x['fat_atual'])

    return f"""
<section class="tab-panel" id="tab-05">
  <p class="section-kicker">05 · Margem × Volume</p>
  <h2 class="section-title">A matriz de decisão</h2>
  <p class="section-desc">Cada SKU Mesa classificado em quadrante baseado em volume (fat semana) × margem %. <strong>Crítério v4:</strong> a mediana de comparação é <strong>POR SUBGRUPO</strong> (Refeições competem entre Refeições, Sucos entre Sucos, Granel entre Granel). Resolve a distorção de SKUs Granel parecerem "Estrelas" só porque a mediana global era puxada pra baixo. Subgrupos com menos de 3 SKUs caem na mediana global como fallback. Mediana global para referência: <strong>{fmt_brl_full(qmeta['mediana_fat'])}</strong> de fat e <strong>{fmt_pct(qmeta['mediana_margem_pct'])}</strong> de margem.</p>

  <div class="q-summary">
    <div class="q-card estrela"><div class="q-nome">⭐ Estrelas</div><div class="q-n">{counts['Estrela']}</div><div class="q-acao">Alta venda + alta margem · proteger preço</div></div>
    <div class="q-card vaca"><div class="q-nome">🐄 Vacas</div><div class="q-n">{counts['Vaca']}</div><div class="q-acao">Alta venda + margem média · tentar +5% sem perder volume</div></div>
    <div class="q-card interrogacao"><div class="q-nome">❓ Interrogação</div><div class="q-n">{counts['Interrogação']}</div><div class="q-acao">Baixa venda + alta margem · puxar exposição/promo</div></div>
    <div class="q-card abacaxi"><div class="q-nome">🍍 Abacaxis</div><div class="q-n">{counts['Abacaxi']}</div><div class="q-acao">Baixa venda + baixa margem · candidatos a corte/repricing</div></div>
  </div>

  <div class="chart-box">
    <h3>Scatter Margem × Volume · {qmeta['n_skus']} SKUs com margem disponível</h3>
    <div class="toggle-row">
      <label>Filtro departamento:</label>
      <select id="sel-cat-matriz">
        <option value="all">Todos</option>
        <option value="gran_mesa">Gran Mesa</option>
        <option value="granel">Granel</option>
        <option value="padaria_gran">Padaria Gran</option>
      </select>
      <span class="info-pill">Cada bolha = 1 SKU. Tamanho proporcional ao fat. Hover mostra detalhes.</span>
    </div>
    <div class="chart-wrap tall"><canvas id="chart-matriz"></canvas></div>
  </div>

  <div class="chart-box" style="background:var(--gran-dourado-bg);border:1px solid var(--gran-dourado)">
    <h3 style="color:var(--gran-dourado)">⏱️ Margem com e sem custo de hora-homem · proxy de produtividade financeira</h3>
    <p class="desc"><strong>3 métricas distintas para não confundir:</strong></p>
    <ul style="margin:8px 0 0 20px;font-size:13px;line-height:1.6">
      <li><strong>Margem R$ (bruta):</strong> faturamento − CMV. <em>Não inclui</em> custo de mão de obra.</li>
      <li><strong>Custo Horas R$:</strong> horas estimadas × <code>R$ {custo_hr_label}/h</code> (parâmetro <code>custo_hora_homem_rs</code> em <code>parametros.json</code>).</li>
      <li><strong>Margem Líquida R$:</strong> margem bruta − custo das horas. <strong>É o que efetivamente sobra após pagar o trabalho.</strong> Negativa = SKU dá prejuízo operacional.</li>
      <li><em>Eficiência R$/h:</em> margem bruta ÷ horas. Métrica de RENDIMENTO da hora trabalhada — <em>não é margem líquida.</em> Use para comparar SKUs entre si.</li>
    </ul>
    <p class="desc" style="margin-top:12px"><strong>Como ler:</strong> SKU com margem líquida vermelha (negativa) está consumindo mais em horas do que devolve em margem — candidato a corte ou repricing. SKU com eficiência alta (verde, R$ ≥ 80/h) gera caixa rápido por hora produzida.</p>
    <p class="desc" style="margin-top:8px;color:var(--ink-mute);font-size:12px">⚠ Tempos estimados editáveis em <code>data/gran-mesa/inputs/tempos_producao_estimados.json</code>. Custo da hora-homem em <code>data/produtividade/inputs/parametros.json</code> (chave <code>custo_hora_homem_rs</code>). Quando o apontamento real existir (kg produzidos × hora trabalhada), substitui automaticamente.</p>
  </div>

  <div class="chart-box">
    <h3>Alavancas de decisão · Interrogação + Abacaxi</h3>
    <p class="desc">Tabelas mostram TODOS os SKUs do quadrante. Filtre por departamento — quando você seleciona Gran Mesa, vê todos os Interrogação/Abacaxi daquele departamento (não restringe a top 15).</p>
    <div class="toggle-row">
      <label>Filtro departamento:</label>
      <select id="sel-alavancas">
        <option value="all">Todos</option>
        <option value="cat:gran_mesa">Gran Mesa</option>
        <option value="cat:granel">Granel</option>
        <option value="cat:padaria_gran">Padaria Gran</option>
      </select>
      <span class="info-pill">{len(interr_all)} Interrogação · {len(abac_all)} Abacaxi no total</span>
    </div>
  </div>

  <div class="grid-2">
    <div class="chart-box">
      <h3>Interrogação · puxar exposição</h3>
      <p class="desc">Margem alta mas volume baixo. Ordenados por margem.</p>
      <div class="table-wrap">
        <table id="tab-interrog">
          <thead><tr><th>Relev.</th><th>Cód</th><th>Descrição</th><th>Depto</th><th>Subgrupo</th>
            <th class="right">Fat</th>
            <th class="right" title="margem bruta sobre fat antes de qualquer custo">Margem %</th>
            <th class="right" title="margem bruta em reais (fat - CMV)">Margem R$<br><span style="font-size:10px;font-weight:400">bruta</span></th>
            <th class="right" title="custo total das horas-homem (estim h × custo/h)">Custo Horas R$</th>
            <th class="right" title="margem bruta menos custo das horas — quanto realmente sobra">Margem Líq R$<br><span style="font-size:10px;font-weight:400">pós-custo</span></th>
            <th class="right" title="rendimento de margem por hora trabalhada (eficiência operacional)"><em>Eficiência R$/h</em></th>
            <th>Quad.</th></tr></thead>
          <tbody>{''.join(row(s) for s in interr_all)}</tbody>
        </table>
      </div>
    </div>
    <div class="chart-box">
      <h3>Abacaxi · candidatos a corte</h3>
      <p class="desc">Volume e margem baixos. Ordenados por fat (impacto de remoção).</p>
      <div class="table-wrap">
        <table id="tab-abacaxi">
          <thead><tr><th>Relev.</th><th>Cód</th><th>Descrição</th><th>Depto</th><th>Subgrupo</th>
            <th class="right">Fat</th>
            <th class="right" title="margem bruta sobre fat antes de qualquer custo">Margem %</th>
            <th class="right" title="margem bruta em reais (fat - CMV)">Margem R$<br><span style="font-size:10px;font-weight:400">bruta</span></th>
            <th class="right" title="custo total das horas-homem (estim h × custo/h)">Custo Horas R$</th>
            <th class="right" title="margem bruta menos custo das horas — quanto realmente sobra">Margem Líq R$<br><span style="font-size:10px;font-weight:400">pós-custo</span></th>
            <th class="right" title="rendimento de margem por hora trabalhada (eficiência operacional)"><em>Eficiência R$/h</em></th>
            <th>Quad.</th></tr></thead>
          <tbody>{''.join(row(s) for s in abac_all)}</tbody>
        </table>
      </div>
    </div>
  </div>
</section>
"""


# ─────────────────────────────────────────────────────────────────────
# RENDER ABA 06 — RUPTURA + SUBPRODUÇÃO
# ─────────────────────────────────────────────────────────────────────
def render_aba_06(D, skus, subgrupos_keys):
    rupt = [s for s in skus if s['ruptura_recorrente'] and s['selo_relevancia']=='verde']
    rupt = sorted(rupt, key=lambda x: -x['fat_atual'])
    aba06 = D.get('aba06_extras', {})
    sub_top = aba06.get('subproducao_top', [])
    tend_queda = aba06.get('tendencia_queda', [])
    evol_rupt = aba06.get('evolucao_ruptura', [])

    def row_rupt(s):
        ult6 = s['evolucao_13sem'][-6:]
        sem_v = sum(1 for e in ult6 if e['fat']>0)
        return f"""<tr class="ruptura">
          <td>{share_info(s['share_fat_mesa'], s['cupons_atual'], s['selo_relevancia'])}</td>
          <td class="cod">{s['cod']}</td>
          <td>{s['descricao']}</td>
          <td style="font-size:11px;color:var(--ink-mute)">{s['subgrupo']}</td>
          <td>{s['colaborador']}</td>
          <td class="num"><strong style="color:var(--vermelho)">{sem_v}/6</strong></td>
          <td class="num">{fmt_brl_full(s['fat_atual'])}</td>
        </tr>"""

    def row_sub(s):
        h = s['hora_ultimo_cupom_med']
        pot = s.get('potencial_perdido', 0)
        return f"""<tr>
          <td>{share_info(s['share_fat_mesa'], s['cupons_atual'], s['selo_relevancia'])}</td>
          <td class="cod">{s['cod']}</td>
          <td>{s['descricao']}</td>
          <td style="font-size:11px;color:var(--ink-mute)">{s['subgrupo']}</td>
          <td>{s['colaborador']}</td>
          <td class="num">{f'{int(h)}h' if h else '—'}</td>
          <td class="num" style="color:var(--vermelho);font-weight:700">{fmt_pct(s['dias_esgotamento_precoce_pct'])}</td>
          <td class="num">{fmt_brl_full(s['fat_atual'])}</td>
          <td class="num" style="color:var(--gran-dourado);font-weight:700">{fmt_brl_full(pot)}</td>
        </tr>"""

    def row_tend(s):
        return f"""<tr>
          <td>{share_info(s['share_fat_mesa'], s['cupons_atual'], s['selo_relevancia'])}</td>
          <td class="cod">{s['cod']}</td>
          <td>{s['descricao']}</td>
          <td style="font-size:11px;color:var(--ink-mute)">{s['subgrupo']}</td>
          <td>{s['colaborador']}</td>
          <td class="num">{fmt_brl_full(s['fat_atual'])}</td>
          <td class="num" style="color:{cor_var(s.get('var_l4w_pct'))}">{fmt_var(s.get('var_l4w_pct'))}</td>
          <td class="num" style="color:{cor_var(s.get('yoy_fat_pct'))}">{fmt_var(s.get('yoy_fat_pct'))}</td>
        </tr>"""

    return f"""
<section class="tab-panel" id="tab-06">
  <p class="section-kicker">06 · Ruptura + Subprodução</p>
  <h2 class="section-title">O que está deixando faturamento na mesa</h2>
  <p class="section-desc">Dois sintomas distintos: <strong>ruptura</strong> (faltou na gôndola, vendeu em &lt;4 das últimas 6 semanas) e <strong>subprodução defensiva</strong> (esgotou cedo demais, antes das 17h em ≥40% dos dias). A segunda é a hipótese H3 — produzir menos por medo de perda termina cortando o teto de venda.</p>

  <div class="chart-box">
    <h3>Ruptura recorrente · vendeu em menos de 4 das últimas 6 semanas focais</h3>
    <p class="desc">Apenas SKUs com selo verde (peso real no fat Mesa).</p>
    <div class="table-wrap">
      <table>
        <thead><tr>
          <th>Relev.</th><th>Cód</th><th>Descrição</th><th>Subgrupo</th><th>Colaborador</th>
          <th class="right">Sem c/ venda</th><th class="right">Fat sem</th>
        </tr></thead>
        <tbody>{''.join(row_rupt(s) for s in rupt) if rupt else '<tr><td colspan="7" style="text-align:center;color:var(--ink-mute);padding:20px">✅ Sem ruptura recorrente esta semana.</td></tr>'}</tbody>
      </table>
    </div>
  </div>

  <div class="chart-box">
    <h3>Subprodução defensiva · esgotamento precoce (≥30% dos dias antes 17h)</h3>
    <div class="callout">
      ⚠️ <strong>Hipótese H3 em ação:</strong> SKUs que estão vendendo todo o estoque cedo demais. Coluna <strong>"Pot. perdido"</strong> estima o faturamento que poderia ser capturado se a produção acompanhasse a demanda dos horários de pico (17h–20h).
    </div>
    <div class="table-wrap">
      <table>
        <thead><tr>
          <th>Relev.</th><th>Cód</th><th>Descrição</th><th>Subgrupo</th><th>Colaborador</th>
          <th class="right">Hora últ. cupom</th><th class="right">% dias ≤17h</th><th class="right">Fat sem</th><th class="right">Pot. perdido</th>
        </tr></thead>
        <tbody>{''.join(row_sub(s) for s in sub_top) if sub_top else '<tr><td colspan="9" style="text-align:center;color:var(--ink-mute);padding:20px">✅ Nenhum SKU com sinal forte de subprodução.</td></tr>'}</tbody>
      </table>
    </div>
  </div>

  <div class="chart-box">
    <h3>Tendência de queda estrutural · SKUs com L4W &lt;-20% OU YoY &lt;-25%</h3>
    <p class="desc">SKUs relevantes (selo verde) que estão em deterioração tanto recente (L4W) quanto histórica (YoY). Atenção especial: estes podem ser os próximos a entrar em ruptura.</p>
    <div class="table-wrap">
      <table>
        <thead><tr>
          <th>Relev.</th><th>Cód</th><th>Descrição</th><th>Subgrupo</th><th>Colaborador</th>
          <th class="right">Fat sem</th><th class="right">L4W</th><th class="right">YoY</th>
        </tr></thead>
        <tbody>{''.join(row_tend(s) for s in tend_queda) if tend_queda else '<tr><td colspan="8" style="text-align:center;color:var(--ink-mute);padding:20px">✅ Nenhuma tendência crítica de queda detectada.</td></tr>'}</tbody>
      </table>
    </div>
  </div>

  <div class="grid-2">
    <div class="chart-box">
      <h3>Evolução semanal de SKUs em ruptura</h3>
      <p class="desc">Quantos SKUs Mesa estiveram em ruptura recorrente (vendendo em &lt;4 das últimas 6 sem) em cada semana focal.</p>
      <div class="chart-wrap"><canvas id="chart-evol-ruptura"></canvas></div>
    </div>
    <div class="chart-box">
      <h3>Curva intra-dia · cupons Mesa por hora</h3>
      <p class="desc">Distribuição horária consolidada da semana atual. Identifique os horários onde a produção precisa estar pronta.</p>
      <div class="chart-wrap"><canvas id="chart-intradia"></canvas></div>
    </div>
  </div>
</section>
"""


# ─────────────────────────────────────────────────────────────────────
# RENDER ABA 07 — LANÇAMENTOS + CARTEIRAS
# ─────────────────────────────────────────────────────────────────────
def render_aba_07(D, lancamentos, carteiras):
    # Lançamentos
    rows_lanc = []
    for s in lancamentos:
        if s['fat_atual'] >= 1000: cl, lbl = 'decolando', '🟢 DECOLANDO'
        elif s['fat_atual'] >= 300: cl, lbl = 'mediano', '🟡 MEDIANO'
        else: cl, lbl = 'naopegou', '🔴 NÃO PEGOU'
        rows_lanc.append(f"""
        <tr>
          <td>{share_info(s['share_fat_mesa'], s['cupons_atual'], s['selo_relevancia'])}</td>
          <td class="cod">{s['cod']}</td>
          <td>{s['descricao']}</td>
          <td style="font-size:11px;color:var(--ink-mute)">{s['subgrupo']}</td>
          <td>{s['colaborador']}</td>
          <td class="num">{s['dias_desde_lancamento']}d</td>
          <td class="num">{fmt_brl_full(s['fat_atual'])}</td>
          <td class="num" style="color:{cor_margem_pct(s['margem_pct'])}">{fmt_pct(s['margem_pct'])}</td>
          <td><span class="lancamento-status {cl}">{lbl}</span></td>
        </tr>""")

    # Carteiras — internos com ranking + fornecedores + não atribuído
    internos = [c for c in carteiras if c['tipo_pessoa']=='colaborador_interno']
    internos.sort(key=lambda x: x.get('rank', 99))

    # Pódio top 3
    podio_html = ''
    if len(internos) >= 1:
        medals = ['🥇','🥈','🥉']
        cards_podio = []
        for i, c in enumerate(internos[:3]):
            cards_podio.append(f"""
            <div class="podio-card podio-{i+1}">
              <div class="podio-medal">{medals[i]}</div>
              <div class="podio-rank">#{i+1}</div>
              <div class="podio-nome">{c['colaborador']}</div>
              <div class="podio-score">{fmt_dec_br(c.get('score',0),1)} <span class="mono" style="font-size:10px">/ 100</span></div>
              <div class="podio-fat">{fmt_brl_full(c['fat'])} · {fmt_pct(c['margem_pct'])} margem</div>
              <div class="podio-badges">{' '.join(c.get('badges_extra',[]) or [c.get('badge','')])}</div>
            </div>""")
        podio_html = f'<div class="podio-grid">{"".join(cards_podio)}</div>'

    # Tabela ranking completa com barras visuais
    max_fat = max((c['fat'] for c in internos), default=1)
    max_score = max((c.get('score',0) for c in internos), default=100)
    rows_rank = []
    for c in internos:
        score = c.get('score', 0)
        score_w = (score / max_score * 100) if max_score else 0
        fat_w = (c['fat'] / max_fat * 100) if max_fat else 0
        col_yoy = cor_var(c.get('yoy_13sem_pct'))
        col_marg = cor_margem_pct(c['margem_pct'])
        col_sc = 'var(--verde)' if score >= 60 else ('var(--amarelo)' if score >= 40 else 'var(--vermelho)')
        badges_inline = ' '.join(c.get('badges_extra',[]))
        rows_rank.append(f"""
        <tr>
          <td class="num"><strong>#{c.get('rank','?')}</strong></td>
          <td><strong>{c['colaborador']}</strong> <span style="font-size:10px">{badges_inline}</span></td>
          <td class="num"><div class="barra-rank"><div class="barra-fill" style="width:{score_w}%;background:{col_sc}"></div></div><strong style="color:{col_sc}">{fmt_dec_br(score,1)}</strong></td>
          <td class="num"><div class="barra-rank"><div class="barra-fill" style="width:{fat_w}%;background:var(--gran-verde)"></div></div>{fmt_brl_full(c['fat'])}</td>
          <td class="num" style="color:{col_marg}">{fmt_pct(c['margem_pct'])}</td>
          <td class="num" style="color:{col_yoy}">{fmt_var(c.get('yoy_13sem_pct'))}</td>
          <td class="num">{c['n_skus']}</td>
          <td class="num" style="color:{'var(--vermelho)' if c['n_skus_alerta']>0 else 'var(--ink-dim)'}">{c['n_skus_alerta']} ({fmt_pct(c['pct_alerta'],0)})</td>
          <td class="num">{fmt_brl_full(c.get('fat_por_sku',0))}</td>
        </tr>""")

    # Cards detalhados (todos)
    cards_cart = []
    for c in carteiras:
        cls = ''
        if c['tipo_pessoa']=='fornecedor_externo': cls='fornecedor'
        elif c['colaborador']=='Não Atribuído': cls='nao-atribuido'
        tipo_lbl = {'colaborador_interno':f"COLABORADOR · #{c.get('rank','?')}",'fornecedor_externo':'FORNECEDOR EXTERNO',
                    'nao_atribuido':'SEM MAPPING'}.get(c['tipo_pessoa'],'COLABORADOR')
        col_yoy = cor_var(c.get('yoy_13sem_pct'))
        top_html = ''.join(
            f'<div><span>↑ {t["desc"][:32]}</span><span class="mono" style="color:{cor_var(t["yoy_pct"])}">{fmt_var(t["yoy_pct"])}</span></div>'
            for t in c['top_skus'][:5]
        )
        score_lbl = ''
        if c['tipo_pessoa']=='colaborador_interno':
            score = c.get('score', 0)
            col_sc = 'var(--verde)' if score >= 60 else ('var(--amarelo)' if score >= 40 else 'var(--vermelho)')
            score_lbl = f'<div style="margin-bottom:8px;font-family:JetBrains Mono,monospace;font-size:11px;color:var(--ink-mute)">SCORE <strong style="color:{col_sc};font-size:18px">{fmt_dec_br(score,1)}</strong> / 100</div>'
        badges_html = ''
        if c.get('badge') or c.get('badges_extra'):
            all_b = []
            if c.get('badge'): all_b.append(c['badge'])
            all_b.extend(c.get('badges_extra',[]))
            if all_b:
                badges_html = '<div class="badges-row">' + ''.join(f'<span class="badge-pill">{b}</span>' for b in all_b) + '</div>'

        cards_cart.append(f"""
        <div class="carteira-card {cls}">
          <h4>{c['colaborador']}</h4>
          <div class="meta-mini">{tipo_lbl} · {fmt_dec_br(c['share_fat_mesa'],1)}% DO FAT MESA · {c['n_skus']} SKUs</div>
          {score_lbl}
          {badges_html}
          <div class="carteira-stats">
            <div><label>FAT SEMANA</label><span class="v">{fmt_brl_full(c['fat'])}</span></div>
            <div><label>MARGEM</label><span class="v" style="color:{cor_margem_pct(c['margem_pct'])}">{fmt_pct(c['margem_pct'])}</span></div>
            <div><label>YOY 13 SEM</label><span class="v" style="color:{col_yoy}">{fmt_var(c.get('yoy_13sem_pct'))}</span></div>
            <div><label>EM ALERTA</label><span class="v {'alerta' if c['n_skus_alerta']>0 else ''}">{c['n_skus_alerta']}</span></div>
            <div><label>FAT/SKU</label><span class="v">{fmt_brl_full(c.get('fat_por_sku',0))}</span></div>
            <div><label>MARG/SKU</label><span class="v">{fmt_brl_full(c.get('margem_por_sku',0))}</span></div>
          </div>
          <canvas id="spark-cart-{slugify(c['colaborador'])}" data-spark='{json.dumps(c["sparkline"])}'></canvas>
          <div class="carteira-top">{top_html}</div>
        </div>""")

    return f"""
<section class="tab-panel" id="tab-07">
  <p class="section-kicker">07 · Lançamentos + Carteiras</p>
  <h2 class="section-title">Novidades e responsabilidades</h2>
  <p class="section-desc">Bloco A: SKUs lançados nos últimos 90 dias com status de adoção. Bloco B: alocação de SKU por colaborador (modo proxy — até planilha de produção real existir, mostra carteira de responsabilidade, não produtividade kg/hora).</p>

  <h3 class="section-sub">Bloco A · Lançamentos últimos 90 dias</h3>
  <div class="chart-box">
    {f'''<div class="table-wrap"><table>
      <thead><tr><th>Relev.</th><th>Cód</th><th>Descrição</th><th>Subgrupo</th><th>Colaborador</th>
        <th class="right">Idade</th><th class="right">Fat sem</th><th class="right">Margem %</th><th>Status</th></tr></thead>
      <tbody>{''.join(rows_lanc)}</tbody>
    </table></div>''' if rows_lanc else '<div class="aviso-painel">Nenhum SKU lançado nos últimos 90 dias.</div>'}
  </div>

  <h3 class="section-sub">Bloco B · Pódio · Top 3 colaboradores da semana</h3>

  <div class="callout" style="background:var(--bg-cream);border-left:4px solid var(--gran-verde);margin-bottom:24px">
    <strong style="color:var(--gran-verde)">Como o Score é calculado (v4 — calibrado com Hugo)</strong><br>
    Score 0-100 = soma ponderada normalizada (cada métrica é convertida pra escala 0-100 entre o pior e melhor da turma):
    <ul style="margin:8px 0 0 20px;color:var(--ink-dim);font-size:13px;line-height:1.6">
      <li><strong>60% Faturamento da carteira</strong> — peso dominante: volume entregue é o que mais reflete capacidade produtiva no turno. Margem alta com baixo volume rende pouco dinheiro absoluto pra empresa.</li>
      <li><strong>25% Margem R$ absoluta</strong> — quanto de margem em reais cada carteira gerou. É o "dinheiro que sobrou" depois do CMV. Premia eficiência financeira sem cair na armadilha do %.</li>
      <li><strong>10% Margem %</strong> — eficiência relativa. Importante mas não decisivo isolado.</li>
      <li><strong>5% Saúde da carteira</strong> — % de SKUs em alerta (ruptura ou queda forte). Tie-breaker que premia consistência.</li>
    </ul>
    <div style="margin-top:10px;font-size:12px;color:var(--ink-mute)">
      💡 <em>Próximos passos:</em> quando a planilha de produção real existir (kg produzidos/hora trabalhada por colaborador), entra como 5ª métrica e pesos se redistribuem. Aí o score vira "produtividade real" em vez de proxy de carteira.
    </div>
  </div>

  {podio_html}

  <div class="chart-box">
    <h3>Ranking completo · comparação justa por indicador</h3>
    <p class="desc">Barras visuais facilitam comparação. Cada métrica isolada permite ver onde cada colaborador é forte/fraco.</p>
    <div class="table-wrap">
      <table class="rank-table">
        <thead><tr><th>Pos.</th><th>Colaborador</th><th class="right">Score</th><th class="right">Fat sem</th>
          <th class="right">Margem %</th><th class="right">YoY 13sem</th><th class="right">SKUs</th><th class="right">Em alerta</th><th class="right">Fat/SKU</th></tr></thead>
        <tbody>{''.join(rows_rank)}</tbody>
      </table>
    </div>
  </div>

  <h3 class="section-sub">Bloco C · Cards detalhados de cada carteira</h3>
  <div class="callout">
    ⚠️ <strong>Modo proxy:</strong> estes números mostram o que cada colaborador é responsável por <em>produzir</em>, não a produtividade real (kg/hora). Quando a planilha de produção diária existir, esta aba evolui pra v3 com sell-through e perdas físicas.
  </div>
  <div class="carteira-grid">{''.join(cards_cart)}</div>
</section>
"""


# ─────────────────────────────────────────────────────────────────────
# RENDER SCRIPTS — toda a interatividade JS
# ─────────────────────────────────────────────────────────────────────
def render_scripts(D):
    return r"""
// ============== ABA 01: tornado SKU dual (semana + 13sem) — ordenação por DELTA R$ ==============
function renderTornadoSkus(filtro) {
  let skus = D.skus.filter(s => s.yoy_fat_pct != null || s.yoy_13sem_pct != null);
  if (filtro && filtro !== 'all') {
    if (filtro.startsWith('cat:')) skus = skus.filter(s => s.categoria_mesa === filtro.slice(4));
    else if (filtro.startsWith('sg:')) skus = skus.filter(s => s.subgrupo === filtro.slice(3));
  }
  // Helpers
  const deltaSem = s => (s.fat_atual||0) - (s.fat_yoy_rs||0);
  const delta13 = s => (s.fat_13sem_2026||0) - (s.fat_13sem_2025||0);

  // Semana atual — ordenado por DELTA R$ (impacto financeiro absoluto)
  const skusSem = skus.filter(s => s.yoy_fat_pct != null);
  const ganh = [...skusSem].sort((a,b) => deltaSem(b) - deltaSem(a)).slice(0,12);
  const perd = [...skusSem].sort((a,b) => deltaSem(a) - deltaSem(b)).slice(0,12);
  document.getElementById('tornado-ganhadores').innerHTML = renderTornadoRows(ganh, 'sem');
  document.getElementById('tornado-perdedores').innerHTML = renderTornadoRows(perd, 'sem');

  // 13 sem acumulado — ordenado por DELTA R$ acumulado
  const skus13 = skus.filter(s => s.yoy_13sem_pct != null);
  const ganh13 = [...skus13].sort((a,b) => delta13(b) - delta13(a)).slice(0,12);
  const perd13 = [...skus13].sort((a,b) => delta13(a) - delta13(b)).slice(0,12);
  document.getElementById('tornado-13sem-ganhadores').innerHTML = renderTornadoRows(ganh13, '13sem');
  document.getElementById('tornado-13sem-perdedores').innerHTML = renderTornadoRows(perd13, '13sem');
}
function renderTornadoRows(skus, modo) {
  if (!skus.length) return '<div class="aviso-painel">Sem dados suficientes nesse filtro.</div>';
  const fa = modo==='13sem' ? 'fat_13sem_2026' : 'fat_atual';
  const fy = modo==='13sem' ? 'fat_13sem_2025' : 'fat_yoy_rs';
  const yoyKey = modo==='13sem' ? 'yoy_13sem_pct' : 'yoy_fat_pct';
  const periodo = modo==='13sem' ? '13 sem' : 'sem atual';
  const maxV = Math.max(...skus.map(s => Math.max(s[fa]||0, s[fy]||0))) || 1;
  return skus.map(s => {
    const f25 = s[fy]||0, f26 = s[fa]||0, yoy = s[yoyKey];
    const w25 = Math.abs(f25) / maxV * 100;
    const w26 = Math.abs(f26) / maxV * 100;
    const cls = (yoy && yoy > 5) ? 'up' : (yoy && yoy < -5 ? 'down' : 'flat');
    const colYoy = (yoy && yoy >= 5) ? C['verde'] : (yoy && yoy <= -5 ? C['vermelho'] : C['ink-dim']);
    const v25 = w25 > 25 ? fmtR(f25) : '';
    const v26 = w26 > 25 ? fmtR(f26) : '';
    // Tooltip nativo (title) com valor sempre visível ao hover, mesmo barras pequenas
    const delta = f26 - f25;
    const sinalDelta = delta >= 0 ? '+' : '';
    const tipBar25 = `${s.descricao} · 2025 ${periodo}: ${fmtR(f25)}`;
    const tipBar26 = `${s.descricao} · 2026 ${periodo}: ${fmtR(f26)} · Δ ${sinalDelta}${fmtR(delta)} · YoY ${fmtSignP(yoy)}`;
    return `<div class="tornado-row" title="${s.descricao} · cód ${s.cod} · 2026 ${fmtR(f26)} vs 2025 ${fmtR(f25)} · Δ ${sinalDelta}${fmtR(delta)} · YoY ${fmtSignP(yoy)}">
      <div class="tornado-bar-2025"><div class="bar" style="width:${w25}%" title="${tipBar25}">${v25}</div></div>
      <div class="tornado-mid">
        <div class="nome">${s.descricao}</div>
        <div class="yoy" style="color:${colYoy}">${sinalDelta}${fmtR(delta)}</div>
      </div>
      <div class="tornado-bar-2026"><div class="bar ${cls}" style="width:${w26}%" title="${tipBar26}">${v26}</div></div>
    </div>`;
  }).join('');
}
document.getElementById('sel-tornado-cat').addEventListener('change', e => renderTornadoSkus(e.target.value));
renderTornadoSkus('all');

// ============== ABA 01: chart-diario ==============
function renderDiario(canvasId) {
  const dados = D.chart_diario;
  const labels = dados.map(d => d.dia_short + '\n' + d.data_iso.split('-').slice(1).reverse().join('/'));
  const fat = dados.map(d => d.fat);
  const l4w = dados.map(d => d.baseline_l4w);
  const yoy = dados.map(d => d.baseline_yoy);
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  return new Chart(ctx.getContext('2d'), {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [
        { label: 'Fat semana atual', data: fat, backgroundColor: C['gran-verde'], borderRadius: 6, order: 3 },
        { label: 'Média L4W (mesmo dia)', data: l4w, type: 'line', borderColor: C['gran-dourado'], borderWidth: 2.5, borderDash: [6,4], pointBackgroundColor: C['gran-dourado'], pointBorderColor:'#fff', pointBorderWidth:2, pointRadius: 5, fill: false, tension: 0.2, order: 1 },
        { label: 'YoY mesma sem 2025', data: yoy, type: 'line', borderColor: C['azul-yoy'], borderWidth: 1.5, borderDash:[2,3], pointBackgroundColor: C['azul-yoy'], pointRadius: 4, fill: false, tension: 0.2, order: 2 }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      scales: {
        y: { beginAtZero: true, ticks: { callback: v => fmtR(v) } }
      },
      plugins: {
        legend: { position: 'top' },
        tooltip: {
          callbacks: {
            label: function(ctx) {
              const d = dados[ctx.dataIndex];
              if (ctx.dataset.label.includes('Fat semana')) {
                let s = `Fat: ${fmtR(d.fat)}`;
                if (d.lift_l4w_pct != null) s += ` · vs L4W ${fmtSignP(d.lift_l4w_pct)}`;
                if (d.lift_yoy_pct != null) s += ` · YoY ${fmtSignP(d.lift_yoy_pct)}`;
                return s;
              }
              return `${ctx.dataset.label}: ${fmtR(ctx.parsed.y)}`;
            }
          }
        }
      }
    }
  });
}
renderDiario('chart-diario-01');

// ============== ABA 02: chart-evolucao toggle KPI ==============
let evolChart = null;
function renderEvolucao() {
  const kpi = document.getElementById('sel-kpi-evolucao').value;
  const ev = D.evolucao_13sem;
  const yoy = D.evolucao_yoy;
  // v2.1.4: labels com período (29/04-05/05) abaixo do label da semana
  const labels = ev.map(e => {
    if (e.periodo) return [e.label, e.periodo];
    if (e.iso_label) return [e.label, e.iso_label];
    return e.label;
  });
  const data2026 = ev.map(e => e[kpi]);
  // Construir 2025: pega yoy_13sem (mesma sem ano anterior)
  const data2025 = yoy.map(e => kpi==='fat' ? e.fat_2025 : null);
  // Média móvel L4W
  const l4w = ev.map((e,i) => {
    if (i < 3) return null;
    let s = 0, n = 0;
    for (let j=Math.max(0,i-3); j<=i; j++) { if (ev[j][kpi]) { s += ev[j][kpi]; n++; }}
    return n ? s/n : null;
  });
  const ctx = document.getElementById('chart-evolucao').getContext('2d');
  if (evolChart) evolChart.destroy();
  const isPct = (kpi === 'margem_pct' || kpi === 'pct_loja');
  const fmt = isPct ? fmtP : (kpi==='cupons' ? fmtN : fmtR);
  const dsets = [
    { label: '2026', data: data2026, borderColor: C['gran-verde'], backgroundColor: C['gran-verde']+'22',
      pointBackgroundColor: C['gran-dourado'], pointBorderColor:'#fff', pointBorderWidth:2, pointRadius: 5,
      tension: 0.3, fill: true, borderWidth: 2.5, order: 1 }
  ];
  if (kpi === 'fat') {
    dsets.push({ label: '2025', data: data2025, borderColor: C['azul-yoy'], borderWidth: 1.5,
      borderDash: [3,3], pointRadius: 3, fill: false, tension: 0.3, order: 2, spanGaps: true });
  }
  dsets.push({ label: 'L4W (média móvel)', data: l4w, borderColor: C['gran-dourado'], borderWidth: 1.5,
    borderDash:[6,4], pointRadius: 0, fill: false, tension: 0.3, order: 3 });
  evolChart = new Chart(ctx, {
    type: 'line',
    data: { labels: labels, datasets: dsets },
    options: {
      responsive: true, maintainAspectRatio: false,
      scales: { y: { beginAtZero: false, ticks: { callback: v => fmt(v) } }},
      plugins: { tooltip: { callbacks: { label: c => `${c.dataset.label}: ${fmt(c.parsed.y)}` }}}
    }
  });
}
document.getElementById('sel-kpi-evolucao').addEventListener('change', renderEvolucao);
renderEvolucao();

// ============== ABA 02: chart-horario com filtro dia ==============
let chartHorario = null;
function filtrarPorDia(filtro) {
  const ph = D.padrao_horario;
  if (!ph || !ph.length) return [];
  let dows;
  if (filtro === 'all') dows = [0,1,2,3,4,5,6];
  else if (filtro === 'uteis') dows = [0,1,2,3,4];  // seg-sex
  else if (filtro === 'fds') dows = [5,6];  // sáb-dom
  else dows = [parseInt(filtro)];
  // Agregação por hora
  const agg = {};
  ph.forEach(e => {
    if (!dows.includes(e.dow)) return;
    if (!agg[e.hora_int]) agg[e.hora_int] = { hora: e.hora_int, cupons: 0, fat: 0 };
    agg[e.hora_int].cupons += e.cupons;
    agg[e.hora_int].fat += e.fat;
  });
  return Object.values(agg).sort((a,b) => a.hora - b.hora).filter(x => x.cupons > 0 || x.fat > 0);
}
function renderHorario() {
  const filtro = document.getElementById('sel-horario-dia').value;
  const data = filtrarPorDia(filtro);
  if (!data.length) return;
  const labels = data.map(h => h.hora + 'h');
  const cupons = data.map(h => h.cupons);
  const fats = data.map(h => h.fat);
  if (chartHorario) chartHorario.destroy();
  chartHorario = new Chart(document.getElementById('chart-horario').getContext('2d'), {
    data: {
      labels: labels,
      datasets: [
        { type:'bar', label:'Cupons', data: cupons, backgroundColor: C['gran-verde'], yAxisID:'y', borderRadius: 4 },
        { type:'line', label:'Fat (R$)', data: fats, borderColor: C['gran-dourado'], yAxisID:'y1', tension:0.3, pointRadius:4, pointBackgroundColor: C['gran-dourado'], pointBorderColor: '#fff', pointBorderWidth: 2, borderWidth: 2.5 }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      scales: { y:{position:'left',beginAtZero:true,title:{display:true,text:'Cupons'}}, y1:{position:'right',beginAtZero:true,title:{display:true,text:'Fat R$'},grid:{display:false},ticks:{callback:v=>fmtR(v)}}}
    }
  });
}
document.getElementById('sel-horario-dia').addEventListener('change', renderHorario);
renderHorario();

// ============== ABA 02: chart-faixas ==============
(function() {
  const f = D.faixas_ticket;
  new Chart(document.getElementById('chart-faixas').getContext('2d'), {
    data: {
      labels: f.map(x=>x.faixa),
      datasets: [
        { type:'bar', label:'Cupons', data: f.map(x=>x.cupons), backgroundColor: C['gran-verde'], yAxisID:'y' },
        { type:'bar', label:'Fat (R$)', data: f.map(x=>x.fat), backgroundColor: C['gran-dourado'], yAxisID:'y1' }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      scales: { y:{position:'left',title:{display:true,text:'Cupons'}}, y1:{position:'right',title:{display:true,text:'Fat R$'},grid:{display:false},ticks:{callback:v=>fmtR(v)}}}
    }
  });
})();

renderDiario('chart-diario-02');

// ============== ABA 03: heatmap toggle ==============
document.getElementById('sel-heatmap-modo').addEventListener('change', e => {
  const m = e.target.value;
  document.getElementById('heatmap-body-l4w').style.display = m==='l4w' ? '' : 'none';
  document.getElementById('heatmap-body-yoy').style.display = m==='yoy' ? '' : 'none';
});
// Aplica cores nos heatmaps
document.querySelectorAll('.heatmap td.cell').forEach(td => {
  const v = parseFloat(td.dataset.v);
  if (!isNaN(v)) {
    td.style.background = cellColor(v);
    td.style.color = cellTextColor(v);
  } else {
    td.style.background = '#f5f5f0';
    td.style.color = C['ink-mute'];
  }
});

// ============== ABA 03: sparklines subgrupo ==============
document.querySelectorAll('canvas[id^="spark-sg-"]').forEach(canvas => {
  const data = JSON.parse(canvas.dataset.spark);
  const labels = data.map(d=>'S'+(d.sid%52));
  const yoyVals = data.map(d => d.yoy_pct);
  new Chart(canvas.getContext('2d'), {
    type:'bar',
    data: { labels: labels, datasets: [{ data: data.map(d=>d.fat_2026),
      backgroundColor: yoyVals.map(v=>cellColor(v||0)), borderRadius:2 }]},
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend:{display:false}, tooltip:{callbacks:{label: c => fmtR(c.parsed.y) + ' · YoY ' + fmtSignP(yoyVals[c.dataIndex])}}},
      scales: { x:{display:false}, y:{display:false}}
    }
  });
});

// ============== ABA 04: filtro top30 por departamento ==============
document.getElementById('sel-cat-top30').addEventListener('change', e => {
  const cat = e.target.value;
  const tbody = document.getElementById('tbody-top30');
  tbody.querySelectorAll('tr').forEach(tr => {
    if (cat === 'all') tr.style.display = '';
    else tr.style.display = (tr.dataset.cat === cat) ? '' : 'none';
  });
});

// ============== ABA 04: linha do tempo SKU ==============
const top30Skus = [...D.skus].sort((a,b)=>b.fat_atual-a.fat_atual).slice(0,30);
const skuSelect = document.getElementById('sku-select');
top30Skus.forEach(s => {
  const opt = document.createElement('option');
  opt.value = s.cod;
  const seloIcon = s.selo_relevancia === 'verde' ? '🟢' : '⚪';
  opt.textContent = `${seloIcon} ${s.descricao}`;
  skuSelect.appendChild(opt);
});

let chartLT = null;
function renderLinhaTempo() {
  const cod = skuSelect.value;
  const visao = document.getElementById('visao-select').value;
  const sku = D.skus.find(s => s.cod === cod);
  if (!sku) return;
  const info = document.getElementById('sku-info');
  const seloHtml = `<span class="selo-relev ${sku.selo_relevancia}"></span>`;
  const kviTag = sku.kvi==='KVI+' ? `<span class="tag kvi-plus">${sku.kvi}</span>` : (sku.kvi==='KVI' ? `<span class="tag kvi">${sku.kvi}</span>` : '');
  const curvaTag = sku.curva==='A*' ? `<span class="tag A-star">${sku.curva}</span>` : (sku.curva!=='-'&&sku.curva ? `<span class="tag curva">${sku.curva}</span>` : '');
  info.innerHTML = `${sku.descricao.toUpperCase()} ${kviTag} ${curvaTag} <span class="badge-mono">cód ${sku.cod}</span> ${seloHtml} <span class="mono share-text">${sku.share_fat_mesa.toFixed(1).replace('.',',')}% · ${sku.cupons_atual} cup · margem ${(sku.margem_pct||0).toFixed(1).replace('.',',')}%</span> <span class="badge-mono">${sku.subgrupo}</span> <span class="badge-mono">${sku.colaborador}</span>`;
  // Labels ISO reais (S{NN}/26)
  const labels = sku.evolucao_13sem.map(e => e.iso_label || ('S'+String(e.sid).padStart(2,'0')));
  const valores2026 = sku.evolucao_13sem.map(e => visao==='qtd' ? e.qtd : e.fat);
  const valores2025 = sku.evolucao_13sem.map(e => visao==='qtd' ? e.qtd_yoy : e.fat_yoy);
  const precos2026 = sku.evolucao_13sem.map(e => e.preco_medio);
  const precos2025 = sku.evolucao_13sem.map(e => e.preco_medio_yoy);
  const ctx = document.getElementById('linha-tempo-chart').getContext('2d');
  if (chartLT) chartLT.destroy();
  chartLT = new Chart(ctx, {
    data: {
      labels: labels,
      datasets: [
        { type:'bar', label: (visao==='qtd' ? 'Quantidade' : 'Faturamento') + ' 2026', data: valores2026, backgroundColor: C['gran-verde'], yAxisID: 'y', borderRadius: 4, order: 3 },
        { type:'bar', label: (visao==='qtd' ? 'Quantidade' : 'Faturamento') + ' 2025', data: valores2025, backgroundColor: C['azul-yoy']+'88', yAxisID: 'y', borderRadius: 4, order: 4 },
        { type:'line', label: 'Preço médio 2026', data: precos2026, borderColor: C['gran-dourado'], backgroundColor: 'transparent', tension: 0.3, yAxisID: 'y1', borderWidth: 2.5, pointBackgroundColor: C['gran-dourado'], pointBorderColor: '#fff', pointBorderWidth: 2, pointRadius: 5, order: 1 },
        { type:'line', label: 'Preço médio 2025', data: precos2025, borderColor: C['gran-dourado']+'66', backgroundColor: 'transparent', tension: 0.3, yAxisID: 'y1', borderWidth: 1.5, borderDash: [4,3], pointRadius: 0, spanGaps: true, order: 2 }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      scales: {
        y: { position: 'left', title: { display: true, text: visao==='qtd' ? 'Quantidade' : 'Faturamento (R$)' }, ticks: { callback: v => visao==='qtd' ? fmtN(v) : fmtR(v) }},
        y1: { position: 'right', title: { display: true, text: 'Preço médio (R$)' }, grid: { display: false }, ticks: { callback: v => fmtR2(v) }}
      },
      plugins: { legend: { position: 'top' }, tooltip: { callbacks: { label: c => `${c.dataset.label}: ${c.dataset.yAxisID==='y1' ? fmtR2(c.parsed.y) : (visao==='qtd' ? fmtN(c.parsed.y) : fmtR(c.parsed.y))}`}}}
    }
  });
}
skuSelect.addEventListener('change', renderLinhaTempo);
document.getElementById('visao-select').addEventListener('change', renderLinhaTempo);
if (top30Skus.length) renderLinhaTempo();

// ============== ABA 04: cesta cross-sell — TODOS Mesa, alfabética ==============
const cestaSelect = document.getElementById('cesta-select');
const skusComCesta = Object.keys(D.cesta).map(cod => D.skus.find(s => s.cod === cod)).filter(Boolean);
skusComCesta.sort((a,b) => a.descricao.localeCompare(b.descricao, 'pt-BR'));
skusComCesta.forEach(s => {
  const opt = document.createElement('option');
  opt.value = s.cod;
  const sel = s.selo_relevancia === 'verde' ? '🟢 ' : '⚪ ';
  opt.textContent = `${sel}${s.descricao}`;
  cestaSelect.appendChild(opt);
});

function renderCesta() {
  const cod = cestaSelect.value;
  const c = D.cesta[cod];
  const sku = D.skus.find(s => s.cod === cod);
  if (!c || !sku) return;
  document.getElementById('cesta-n-cupons').textContent = fmtN(c.n_cupons_com_sku);
  document.getElementById('cesta-n-comp').textContent = c.companheiros.length;
  const tbody = document.getElementById('cesta-body');
  // v2.1.4: Score combinado = lift × √suporte (equilibra força e volume)
  const enriched = c.companheiros.map(co => ({
    ...co,
    score: co.lift * Math.sqrt(Math.max(0, co.suporte_pct))
  }));
  // Ordenação dinâmica
  const sortBy = document.getElementById('cesta-sort').value;
  const keyMap = {
    lift: 'lift', score: 'score', suporte: 'suporte_pct',
    cupons: 'cupons_juntos', fat: 'fat_total_companheiro'
  };
  const k = keyMap[sortBy] || 'lift';
  enriched.sort((a, b) => (b[k] || 0) - (a[k] || 0));
  const top10 = enriched.slice(0, 10);
  const maxLift = Math.max(...top10.map(x => x.lift));
  tbody.innerHTML = top10.map((co, i) => {
    const liftBarW = (co.lift / maxLift * 60).toFixed(0);
    return `<tr>
      <td class="num">${i+1}</td>
      <td class="cod">${co.cod}</td>
      <td>${co.desc}</td>
      <td style="font-size:11px;color:var(--ink-mute)">${co.setor}</td>
      <td class="num"><span class="lift-bar" style="width:${liftBarW}px"></span><strong>${co.lift.toFixed(2).replace('.',',')}×</strong></td>
      <td class="num"><strong>${co.score.toFixed(2).replace('.',',')}</strong></td>
      <td class="num">${co.cupons_juntos}</td>
      <td class="num">${(co.p_b_dado_a_pct).toFixed(1).replace('.',',')}%</td>
      <td class="num">${(co.suporte_pct).toFixed(2).replace('.',',')}%</td>
      <td class="num">${fmtR(co.fat_total_companheiro || 0)}</td>
    </tr>`;
  }).join('');
}
cestaSelect.addEventListener('change', renderCesta);
document.getElementById('cesta-sort').addEventListener('change', renderCesta);
if (skusComCesta.length) renderCesta();

// ============== ABA 05: chart matriz Margem × Volume ==============
let chartMatriz = null;
function renderMatriz() {
  const catFiltro = document.getElementById('sel-cat-matriz').value;
  const items = D.quadrantes.filter(q => catFiltro==='all' || q.categoria_mesa === catFiltro);
  const dataPoints = items.map(q => ({
    x: q.fat_atual,
    y: q.margem_pct,
    r: Math.min(20, Math.max(4, Math.sqrt(q.fat_atual)/3)),
    cod: q.cod,
    desc: q.descricao,
    quad: q.quadrante,
    selo: q.selo_relevancia,
    subgrupo: q.subgrupo,
    margem_rs: q.margem_rs,
  }));
  const colorMap = { 'Estrela': C['verde'], 'Vaca': C['gran-dourado'], 'Interrogação': C['ink-dim'], 'Abacaxi': C['vermelho'] };
  const ctx = document.getElementById('chart-matriz').getContext('2d');
  if (chartMatriz) chartMatriz.destroy();
  chartMatriz = new Chart(ctx, {
    type: 'bubble',
    data: {
      datasets: ['Estrela','Vaca','Interrogação','Abacaxi'].map(q => ({
        label: q,
        data: dataPoints.filter(d => d.quad === q),
        backgroundColor: colorMap[q] + 'aa',
        borderColor: colorMap[q],
        borderWidth: 1.5,
      }))
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      scales: {
        x: { type: 'logarithmic', title: { display:true, text:'Fat semana (R$, log scale)' }, ticks: { callback: v => fmtR(v) }},
        y: { title: { display: true, text: 'Margem %' }, ticks: { callback: v => fmtP(v,0) }}
      },
      plugins: {
        legend: { position: 'top' },
        tooltip: { callbacks: { label: c => {
          const d = c.raw;
          return [`${d.desc}`, `cód ${d.cod} · ${d.subgrupo}`, `Fat: ${fmtR(d.x)} · Margem: ${fmtP(d.y)} · R$ ${fmtR(d.margem_rs)}`];
        }}},
        annotation: {
          annotations: {
            medFat: { type: 'line', xMin: D.quadrantes_meta.mediana_fat, xMax: D.quadrantes_meta.mediana_fat,
              borderColor: C['ink-mute'], borderWidth: 1, borderDash: [4,4] },
            medMarg: { type: 'line', yMin: D.quadrantes_meta.mediana_margem_pct, yMax: D.quadrantes_meta.mediana_margem_pct,
              borderColor: C['ink-mute'], borderWidth: 1, borderDash: [4,4] }
          }
        }
      }
    }
  });
}
document.getElementById('sel-cat-matriz').addEventListener('change', renderMatriz);
renderMatriz();

// ============== ABA 05: filtro Categoria/Subgrupo nos top 15 ==============
document.getElementById('sel-alavancas').addEventListener('change', e => {
  const v = e.target.value;
  ['tab-interrog','tab-abacaxi'].forEach(tid => {
    const tbody = document.querySelector(`#${tid} tbody`);
    if (!tbody) return;
    tbody.querySelectorAll('tr').forEach(tr => {
      if (v === 'all') { tr.style.display = ''; return; }
      const cat = tr.dataset.cat;
      const sg = tr.dataset.sg;
      let show = false;
      if (v.startsWith('cat:')) show = (cat === v.slice(4));
      else if (v.startsWith('sg:')) show = (sg === v.slice(3));
      tr.style.display = show ? '' : 'none';
    });
  });
});

// ============== ABA 06: evolução semanal de SKUs em ruptura ==============
(function() {
  const evol = D.aba06_extras && D.aba06_extras.evolucao_ruptura;
  if (!evol || !evol.length) return;
  const ctx = document.getElementById('chart-evol-ruptura');
  if (!ctx) return;
  const labels = evol.map(e => e.iso_label);
  const nrupt = evol.map(e => e.n_ruptura);
  const pct = evol.map(e => e.pct_ruptura);
  new Chart(ctx.getContext('2d'), {
    data: {
      labels: labels,
      datasets: [
        { type:'bar', label:'SKUs em ruptura', data: nrupt, backgroundColor: C['vermelho']+'aa', yAxisID:'y', borderRadius: 4, order: 2 },
        { type:'line', label:'% sobre ativos', data: pct, borderColor: C['gran-dourado'], backgroundColor: 'transparent', tension: 0.3, yAxisID:'y1', borderWidth: 2.5, pointBackgroundColor: C['gran-dourado'], pointBorderColor: '#fff', pointBorderWidth: 2, pointRadius: 5, order: 1 }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      scales: {
        y: { beginAtZero: true, position: 'left', title: { display: true, text: 'SKUs em ruptura' }},
        y1: { beginAtZero: true, position: 'right', title: { display: true, text: '% sobre ativos' }, grid: { display: false }, ticks: { callback: v => fmtP(v,0) }}
      }
    }
  });
})();

// ============== ABA 06: curva intra-dia ==============
(function() {
  const ph = D.padrao_horario;
  if (!ph || !ph.length) return;
  // Prepara série completa 6h-23h com null nos vazios
  const horas = Array.from({length:18}, (_,i) => i+6);
  const cupporhora = horas.map(h => {
    const ent = ph.find(x => x.hora_int === h);
    return ent ? ent.cupons : 0;
  });
  new Chart(document.getElementById('chart-intradia').getContext('2d'), {
    type: 'line',
    data: {
      labels: horas.map(h => h+'h'),
      datasets: [{ label:'Cupons Mesa por hora', data: cupporhora, borderColor: C['gran-verde'], backgroundColor: C['gran-verde']+'33', tension: 0.3, fill: true, pointRadius: 4, pointBackgroundColor: C['gran-dourado'], borderWidth: 2.5 }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      scales: { y: { beginAtZero: true, title: { display: true, text:'Cupons Mesa' }}}
    }
  });
})();

// ============== ABA 07: sparklines carteira ==============
document.querySelectorAll('canvas[id^="spark-cart-"]').forEach(canvas => {
  const data = JSON.parse(canvas.dataset.spark);
  const labels = data.map(d=>'S'+(d.sid%52));
  const yoyVals = data.map(d => d.yoy_pct);
  new Chart(canvas.getContext('2d'), {
    type:'bar',
    data: { labels: labels, datasets: [{ data: data.map(d=>d.fat_2026),
      backgroundColor: yoyVals.map(v=>cellColor(v||0)), borderRadius:2 }]},
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend:{display:false}, tooltip:{callbacks:{label: c => fmtR(c.parsed.y) + ' · YoY ' + fmtSignP(yoyVals[c.dataIndex])}}},
      scales: { x:{display:false}, y:{display:false}}
    }
  });
});
"""


# ─────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────
def main():
    if not DADOS_JSON.exists():
        print(f"❌ {DADOS_JSON} não encontrado. Rode build_dados.py primeiro.")
        return
    with open(DADOS_JSON, encoding='utf-8') as f:
        D = json.load(f)
    html = gerar_html(D)
    safe_label = D['meta']['sem_label'].replace('/', '_')
    out = REL_DIR / f'Survey_Gran_Mesa_{safe_label}_v2.html'
    out.write_text(html, encoding='utf-8')
    print(f"✅ HTML gerado: {out}")
    print(f"   Tamanho: {out.stat().st_size:,} bytes")

    # Smoke test pós-build (v2.1.5): impede regressão do tipo fmtBRL.
    try:
        import subprocess
        validate_script = Path(__file__).parent / 'validate_publicado.py'
        if validate_script.exists():
            print()
            r = subprocess.run(
                ['python3', str(validate_script), str(out)],
                capture_output=True, text=True
            )
            print(r.stdout, end='')
            if r.returncode != 0:
                print(r.stderr, end='')
                print("⛔ Build gerado MAS smoke test FALHOU. NÃO publique sem corrigir.")
    except Exception as e:
        print(f"⚠️  Smoke test não rodou: {e}")
    return out


if __name__ == '__main__':
    main()
