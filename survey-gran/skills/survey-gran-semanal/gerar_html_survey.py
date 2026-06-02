"""
Gerador HTML — Survey Semanal Gran v12
=========================================

Lê base classificada e dados pré-calculados. Renderiza HTML com 11 abas.

Uso:
    python gerar_html_survey.py

Lê:
    ~/Documents/SurveyGran/base/dados_survey.json   (gerado pelo build_dados.py)

Salva:
    ~/Documents/SurveyGran/relatorios/Survey_Gran_S{NN}_v12.html
"""
import json
import pandas as pd
from pathlib import Path

import os
# Estrutura unificada — dados ficam dentro do projeto Cowork [GRAN] Survey/
HOME = Path.home()
DEFAULT_ROOT = HOME / "Documents" / "Claude" / "Projects" / "[GRAN] Survey" / "data"
LEGACY_ROOT = HOME / "Documents" / "SurveyGran"
ENV_ROOT = os.environ.get("SURVEY_DATA_DIR")
if ENV_ROOT:
    ROOT = Path(ENV_ROOT)
elif DEFAULT_ROOT.exists() or not LEGACY_ROOT.exists():
    ROOT = DEFAULT_ROOT
else:
    ROOT = LEGACY_ROOT
DADOS_JSON = ROOT / "base" / "dados_survey.json"
RELATORIOS = ROOT / "relatorios"
RELATORIOS.mkdir(parents=True, exist_ok=True)

with open(DADOS_JSON, 'r') as f:
    D = json.load(f)

data_js = json.dumps(D, ensure_ascii=False)
kpis = D['kpis_macro']

# Helpers de formatação BR
def fmt_int_br(n):
    """Ex: 118646 -> '118.646'"""
    if n is None: return '—'
    return f"{int(n):,}".replace(',', '.')

def fmt_dec_br(n, decimals=2):
    """Ex: 52.29 -> '52,29'"""
    if n is None: return '—'
    s = f"{n:,.{decimals}f}"
    # s usa ',' milhares e '.' decimal (US). Inverter.
    return s.replace(',', '#TMP#').replace('.', ',').replace('#TMP#', '.')

def fmt_var(v, invert_sign=False):
    """Retorna string do tipo '+3.2%' ou '—' para None."""
    if v is None: return '—'
    return ('+' if v>=0 else '') + f"{v:.1f}%"

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

# Pré-calcular os comparadores pros KPIs macro
def tri_comp(lw, l4w, l8w, positivo_bom=True):
    """Retorna HTML do bloco de 3 comparadores."""
    def mini(lbl, v):
        if v is None: return f'<span class="cmp"><span class="cmp-l">{lbl}</span><span class="cmp-v mute">—</span></span>'
        col = cor_var(v, positivo_bom)
        return f'<span class="cmp"><span class="cmp-l">{lbl}</span><span class="cmp-v" style="color:{col}">{fmt_var(v)}</span></span>'
    return f'<div class="tri-cmp">{mini("LW",lw)}{mini("L4W",l4w)}{mini("L8W",l8w)}</div>'

# Calcular comparadores SKUs ativos a partir das evolucoes (a partir das 13 semanas)
import numpy as np
skus_evolucao = []
for r in D['evolucao_semanal']:
    # Aproximação: usar kpis_sem que salvei no pipeline, mas já temos em evolucao_semanal. Não tem skus lá.
    skus_evolucao.append(None)  # vou calcular direto aqui via pandas
# Infelizmente não está em evolucao_semanal. Vou extrair de novo aqui
# Ler pickle
v_pk = pd.read_pickle(ROOT / 'base' / 'base_classificada.pkl')
skus_por_sem = v_pk.groupby('sem_id_global')['cod_arius_str'].nunique().to_dict()
sem_atual_n = kpis['n_sem']
skus_atual = skus_por_sem.get(sem_atual_n, 0)
skus_lw = skus_por_sem.get(sem_atual_n-1)
l4w_vals_skus = [skus_por_sem.get(sem_atual_n-i) for i in range(1,5) if skus_por_sem.get(sem_atual_n-i) is not None]
l8w_vals_skus = [skus_por_sem.get(sem_atual_n-i) for i in range(1,9) if skus_por_sem.get(sem_atual_n-i) is not None]
skus_l4w_media = sum(l4w_vals_skus)/len(l4w_vals_skus) if l4w_vals_skus else None
skus_l8w_media = sum(l8w_vals_skus)/len(l8w_vals_skus) if l8w_vals_skus else None
skus_var_lw  = (skus_atual/skus_lw-1)*100 if skus_lw else None
skus_var_l4w = (skus_atual/skus_l4w_media-1)*100 if skus_l4w_media else None
skus_var_l8w = (skus_atual/skus_l8w_media-1)*100 if skus_l8w_media else None

fat_triplo    = tri_comp(kpis.get('fat_lw'),    kpis.get('fat_l4w'),    kpis.get('fat_l8w'))
cupons_triplo = tri_comp(kpis.get('cupons_lw'), kpis.get('cupons_l4w'), kpis.get('cupons_l8w'))
ticket_triplo = tri_comp(kpis.get('ticket_lw'), kpis.get('ticket_l4w'), kpis.get('ticket_l8w'))
itens_triplo  = tri_comp(kpis.get('itens_nf_lw'), kpis.get('itens_nf_l4w'), kpis.get('itens_nf_l8w'))
media_triplo  = tri_comp(kpis.get('media_dia_lw'), kpis.get('media_dia_l4w'), kpis.get('media_dia_l8w'))
skus_triplo   = tri_comp(skus_var_lw, skus_var_l4w, skus_var_l8w)

html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Survey Gran — {kpis['sem_label']} · {kpis['periodo']}</title>
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
  --shadow: 0 1px 2px rgba(30,77,43,0.04), 0 4px 12px rgba(30,77,43,0.06);
  --shadow-hover: 0 2px 4px rgba(30,77,43,0.06), 0 8px 20px rgba(30,77,43,0.08);
}}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; }}
body {{
  background: var(--bg); color: var(--ink);
  font-family: 'Aptos', 'Nunito Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: 15px; line-height: 1.55;
  -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale;
}}
.container {{ max-width: 1380px; margin: 0 auto; padding: 40px 32px 80px; }}

header.main-header {{
  display: flex; align-items: flex-end; justify-content: space-between;
  gap: 40px; padding: 24px 32px 28px;
  background: var(--gran-verde); color: #fff;
  border-radius: 12px; margin-bottom: 32px;
  box-shadow: var(--shadow); flex-wrap: wrap;
}}
header.main-header h1 {{
  font-family: 'Aptos', 'Nunito Sans', sans-serif;
  font-weight: 800; font-size: 44px; line-height: 1.05;
  letter-spacing: -0.02em; margin: 8px 0 4px; color: #fff;
}}
header.main-header h1 em {{ font-style: normal; color: var(--gran-dourado-2); }}
.eyebrow {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px; letter-spacing: 0.2em; text-transform: uppercase;
  color: var(--gran-dourado-2); margin: 0; font-weight: 500;
}}
.subtitle {{
  font-weight: 400; font-size: 17px;
  color: rgba(255,255,255,0.82); margin: 0 0 8px;
}}
.meta {{
  text-align: right;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px; color: rgba(255,255,255,0.7); letter-spacing: 0.05em;
}}
.meta div {{ margin-bottom: 4px; }}
.meta strong {{ color: var(--gran-dourado-2); font-weight: 600; }}

.tabs-wrap {{
  position: sticky; top: 0; z-index: 50;
  background: var(--bg); padding: 4px 0 0;
  margin-bottom: 32px; border-bottom: 1px solid var(--border);
}}
.tabs {{ display: flex; gap: 4px; overflow-x: auto; padding: 4px 0; scrollbar-width: thin; }}
.tab {{
  flex: 0 0 auto; padding: 12px 18px; border: none; background: transparent;
  cursor: pointer; font-family: 'Aptos','Nunito Sans',sans-serif;
  font-size: 14px; font-weight: 600; color: var(--ink-mute);
  border-bottom: 3px solid transparent; transition: all 0.15s ease;
  white-space: nowrap; border-radius: 6px 6px 0 0;
}}
.tab:hover {{ color: var(--gran-verde); background: var(--bg-soft); }}
.tab.active {{ color: var(--gran-verde); border-bottom-color: var(--gran-dourado); background: var(--bg-cream); }}
.tab .num {{ font-family: 'JetBrains Mono', monospace; font-size: 10px; color: var(--ink-mute); margin-right: 8px; font-weight: 500; }}
.tab.active .num {{ color: var(--gran-dourado); }}
.tab-panel {{ display: none; }}
.tab-panel.active {{ display: block; animation: fadeIn 0.25s ease; }}
@keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(4px); }} to {{ opacity: 1; transform: translateY(0); }} }}

.section-kicker {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px; letter-spacing: 0.18em; text-transform: uppercase;
  color: var(--gran-dourado); margin: 0 0 8px; font-weight: 600;
}}
.section-title {{
  font-family: 'Aptos','Nunito Sans',sans-serif;
  font-weight: 700; font-size: 32px; letter-spacing: -0.02em;
  color: var(--gran-verde); margin: 0 0 8px; line-height: 1.15;
}}
.section-desc {{ color: var(--ink-dim); font-size: 15px; margin: 0 0 32px; max-width: 760px; }}

.kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(230px,1fr)); gap: 16px; margin-bottom: 40px; }}

/* === Tornado SKU (Headline · Ganhadores e Perdedores) v0.12.8 === */
.tsku-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 32px; margin-top: 8px; }}
@media (max-width: 1100px) {{ .tsku-grid {{ grid-template-columns: 1fr; }} }}
.tsku-block h4 {{ margin: 0 0 14px; font-size: 14px; color: var(--gran-verde); font-weight: 700; padding-bottom: 8px; border-bottom: 2px solid var(--gran-verde); display: flex; justify-content: space-between; align-items: center; gap: 8px; }}
.tsku-block h4 .label-A {{ color: var(--ink-mute); font-size: 11px; font-family: 'JetBrains Mono',monospace; }}
.tsku-block h4 .label-B {{ color: var(--gran-verde); font-size: 11px; font-family: 'JetBrains Mono',monospace; }}
.tsku-row {{ display: grid; grid-template-columns: 1fr 200px 1fr; gap: 0; align-items: center; margin-bottom: 6px; height: 22px; }}
.tsku-bar-A {{ display: flex; justify-content: flex-end; height: 22px; }}
.tsku-bar-A .bar {{ background: var(--ink-mute); height: 100%; border-radius: 3px 0 0 3px; display: flex; align-items: center; justify-content: flex-end; padding-right: 6px; color: #fff; font-size: 10px; font-family: 'JetBrains Mono',monospace; font-weight: 600; min-width: 6px; }}
.tsku-mid {{ text-align: center; padding: 0 8px; line-height: 1.1; }}
.tsku-mid .nome {{ font-size: 12px; font-weight: 600; color: var(--ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.tsku-mid .delta {{ font-size: 11px; font-family: 'JetBrains Mono',monospace; font-weight: 700; }}
.tsku-bar-B {{ display: flex; justify-content: flex-start; height: 22px; }}
.tsku-bar-B .bar {{ height: 100%; border-radius: 0 3px 3px 0; display: flex; align-items: center; justify-content: flex-start; padding-left: 6px; color: #fff; font-size: 10px; font-family: 'JetBrains Mono',monospace; font-weight: 600; min-width: 6px; }}
.tsku-bar-B .bar.up {{ background: var(--verde); }}
.tsku-bar-B .bar.down {{ background: var(--vermelho); }}
.tsku-bar-B .bar.flat {{ background: var(--ink-dim); }}
.tsku-section-title {{ font-family: 'Aptos','Nunito Sans',sans-serif; font-size: 14px; color: var(--gran-verde); letter-spacing: -0.01em; margin: 24px 0 10px; padding-bottom: 4px; border-bottom: 1px solid var(--ink-mute); }}
.tsku-empty {{ font-size: 12px; color: var(--ink-mute); padding: 8px 0; font-style: italic; }}
.kpi-card {{
  background: var(--bg-cream); border: 1px solid var(--border);
  border-radius: 10px; padding: 22px 24px;
  box-shadow: var(--shadow); transition: box-shadow 0.2s;
}}
.kpi-card:hover {{ box-shadow: var(--shadow-hover); }}
.kpi-card.big {{ grid-column: span 2; background: var(--gran-verde); color: #fff; border-color: var(--gran-verde); }}
.kpi-card.big .kpi-label {{ color: var(--gran-dourado-2); }}
.kpi-card.big .kpi-value {{ color: #fff; }}
.kpi-card.big .kpi-unit {{ color: var(--gran-dourado-2); }}
.kpi-card.big .kpi-sub {{ color: rgba(255,255,255,0.72); }}
.kpi-card.big .cmp-l {{ color: rgba(255,255,255,0.55); }}
.kpi-label {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px; letter-spacing: 0.15em; text-transform: uppercase;
  color: var(--ink-mute); margin: 0 0 10px; font-weight: 600;
}}
.kpi-value {{
  font-family: 'Aptos','Nunito Sans',sans-serif;
  font-weight: 800; font-size: 36px; letter-spacing: -0.03em;
  line-height: 1; color: var(--gran-verde); margin: 0;
}}
.kpi-unit {{ font-weight: 600; font-size: 17px; color: var(--gran-dourado); margin-right: 2px; }}
.kpi-sub {{ font-size: 12px; color: var(--ink-dim); margin: 10px 0 0; }}

/* Trio de comparadores (LW / L4W / L8W) */
.tri-cmp {{ display: flex; gap: 14px; margin-top: 12px; }}
.cmp {{ display: flex; flex-direction: column; gap: 1px; }}
.cmp-l {{ font-family: 'JetBrains Mono',monospace; font-size: 9px; letter-spacing: 0.12em; color: var(--ink-mute); }}
.cmp-v {{ font-family: 'Aptos','Nunito Sans',sans-serif; font-weight: 700; font-size: 13px; color: var(--ink-dim); }}
.cmp-v.mute {{ color: var(--ink-mute); }}

.alert {{
  display: flex; gap: 14px; align-items: flex-start;
  padding: 16px 20px; border-radius: 10px; margin-bottom: 12px;
  border-left: 4px solid; background: var(--bg-soft);
}}
.alert.verde    {{ background: var(--verde-bg);    border-left-color: var(--verde); }}
.alert.amarelo  {{ background: var(--amarelo-bg);  border-left-color: var(--amarelo); }}
.alert.vermelho {{ background: var(--vermelho-bg); border-left-color: var(--vermelho); }}
.alert-icon {{
  font-weight: 700; font-size: 16px; width: 32px; height: 32px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 50%; flex-shrink: 0; color: white;
}}
.alert.verde    .alert-icon {{ background: var(--verde); }}
.alert.amarelo  .alert-icon {{ background: var(--amarelo); }}
.alert.vermelho .alert-icon {{ background: var(--vermelho); }}
.alert-title {{ font-weight: 700; font-size: 14px; margin: 3px 0 4px; color: var(--ink); }}
.alert-text  {{ font-size: 13px; color: var(--ink-dim); margin: 0; }}

.chart-box {{
  background: var(--bg-cream); border: 1px solid var(--border);
  border-radius: 10px; padding: 24px 28px; margin-bottom: 24px;
  box-shadow: var(--shadow);
}}
.chart-box h3 {{
  font-family: 'Aptos','Nunito Sans',sans-serif;
  font-weight: 700; font-size: 18px; color: var(--gran-verde);
  margin: 0 0 4px; letter-spacing: -0.01em;
}}
.chart-box .desc {{ font-size: 13px; color: var(--ink-dim); margin: 0 0 22px; }}
.chart-wrap {{ position: relative; height: 320px; }}
.chart-wrap.tall {{ height: 420px; }}

table.data {{ width: 100%; border-collapse: collapse; font-size: 13px; font-variant-numeric: tabular-nums; }}
table.data th {{
  text-align: left; padding: 12px 14px;
  background: var(--gran-verde); color: var(--gran-dourado-2);
  font-family: 'JetBrains Mono',monospace; font-size: 10px;
  letter-spacing: 0.1em; text-transform: uppercase; font-weight: 600;
}}
table.data th:first-child {{ border-radius: 6px 0 0 0; }}
table.data th:last-child  {{ border-radius: 0 6px 0 0; }}
table.data th.num, table.data td.num {{ text-align: right; }}
table.data.compact {{ font-size: 12px; margin-top: 8px; }}
table.data.compact th, table.data.compact td {{ padding: 6px 10px; }}
table.data.compact tr.tem-alerta td:first-child {{
  border-left: 3px solid #f0a020;
  position: relative;
}}
table.data.compact tr.tem-alerta td:first-child::before {{
  content: '⚠ ';
  color: #f0a020;
  font-weight: 700;
}}
table.data.compact tfoot td {{
  background: var(--bg-cream);
  font-weight: 700;
  border-top: 2px solid var(--gran-verde);
  padding: 8px 10px;
}}
table.data td {{ padding: 11px 14px; border-bottom: 1px solid var(--border-soft); color: var(--ink); }}
table.data tbody tr:last-child td {{ border-bottom: none; }}
table.data tbody tr:hover td {{ background: var(--bg-soft); }}

.tag {{
  display: inline-block; padding: 3px 9px;
  font-family: 'JetBrains Mono',monospace; font-size: 10px;
  font-weight: 700; border-radius: 4px; letter-spacing: 0.05em;
}}
.tag.kvi-plus  {{ background: var(--gran-verde); color: var(--gran-dourado-2); }}
.tag.kvi       {{ background: var(--gran-verde-3); color: #fff; }}
.tag.att       {{ background: var(--border); color: var(--ink-dim); }}
.tag.A-star    {{ background: var(--gran-dourado); color: #fff; }}
.tag.curva     {{ background: var(--border); color: var(--ink-dim); }}
.tag.elast-alta    {{ background: var(--vermelho); color: #fff; }}
.tag.elast-media   {{ background: var(--amarelo); color: var(--ink); }}
.tag.elast-baixa   {{ background: var(--verde); color: #fff; }}
.tag.elast-atipico {{ background: var(--gran-dourado); color: #fff; }}
.tag.elast-sem     {{ background: var(--border); color: var(--ink-dim); }}

.grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px; }}
@media (max-width: 900px) {{
  .grid-2 {{ grid-template-columns: 1fr; }}
  header.main-header {{ flex-direction: column; align-items: flex-start; }}
  header.main-header .meta {{ text-align: left; }}
}}

.select-wrap {{ margin-bottom: 20px; display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }}
.select-wrap label {{
  font-family: 'JetBrains Mono',monospace; font-size: 11px;
  letter-spacing: 0.12em; text-transform: uppercase;
  color: var(--gran-verde); font-weight: 600;
}}
select {{
  font-family: 'Aptos','Nunito Sans',sans-serif; font-size: 14px; font-weight: 500;
  padding: 10px 16px; border: 1.5px solid var(--gran-verde);
  background: var(--bg-cream); color: var(--gran-verde);
  border-radius: 6px; cursor: pointer; min-width: 260px;
}}
select:focus {{ outline: 2px solid var(--gran-dourado); outline-offset: 1px; }}

.hbar-row {{
  display: grid; grid-template-columns: 240px 1fr 110px 80px; gap: 14px;
  align-items: center; padding: 9px 0; border-bottom: 1px solid var(--border-soft);
}}
.hbar-row:last-child {{ border-bottom: none; }}
.hbar-row .name {{ font-size: 13px; font-weight: 600; color: var(--ink); }}
.hbar-row .bar-track {{ height: 10px; background: var(--border-soft); border-radius: 5px; overflow: hidden; }}
.hbar-row .bar-fill {{ height: 100%; background: linear-gradient(90deg, var(--gran-verde) 0%, var(--gran-verde-3) 100%); border-radius: 5px; transition: width 0.8s ease; }}
.hbar-row .val {{ font-family: 'JetBrains Mono',monospace; font-size: 12px; text-align: right; color: var(--gran-verde); font-weight: 600; }}
.hbar-row .l4w {{ font-family: 'JetBrains Mono',monospace; font-size: 11px; text-align: right; font-weight: 700; }}

.callout {{
  background: var(--gran-dourado-bg); border-left: 4px solid var(--gran-dourado);
  border-radius: 8px; padding: 16px 22px; margin: 24px 0;
  font-size: 14px; color: var(--ink-dim);
}}
.callout strong {{ color: var(--gran-verde); }}

.oferta-card {{
  background: var(--bg-cream); border: 1px solid var(--border);
  border-radius: 10px; padding: 20px 22px; margin-bottom: 14px;
  display: grid; grid-template-columns: 140px 1fr auto; gap: 22px;
  align-items: center; box-shadow: var(--shadow);
}}
.oferta-card.pegou     {{ border-left: 5px solid var(--verde); }}
.oferta-card.nao-pegou {{ border-left: 5px solid var(--amarelo); }}
.oferta-card.nulo      {{ border-left: 5px solid var(--border); opacity: 0.8; }}
.oferta-dia {{ display: flex; flex-direction: column; gap: 2px; }}
.oferta-dia .dia {{ font-weight: 700; font-size: 18px; color: var(--gran-verde); }}
.oferta-dia .data {{ font-family: 'JetBrains Mono',monospace; font-size: 11px; color: var(--ink-mute); letter-spacing: 0.05em; }}
.oferta-alvo {{ font-size: 14px; color: var(--ink); font-weight: 500; }}
.oferta-alvo .label {{ font-family: 'JetBrains Mono',monospace; font-size: 10px; color: var(--ink-mute); letter-spacing: 0.1em; text-transform: uppercase; display: block; margin-bottom: 4px; }}
.oferta-metricas {{ display: flex; gap: 20px; align-items: center; }}
.oferta-metricas .metric {{ text-align: right; }}
.oferta-metricas .metric .v {{ font-family: 'Aptos','Nunito Sans',sans-serif; font-weight: 700; font-size: 18px; color: var(--gran-verde); }}
.oferta-metricas .metric .l {{ font-family: 'JetBrains Mono',monospace; font-size: 9px; color: var(--ink-mute); letter-spacing: 0.1em; text-transform: uppercase; margin-top: 2px; }}
.oferta-metricas .lift {{ padding: 6px 12px; border-radius: 6px; font-weight: 700; font-size: 15px; }}
.oferta-metricas .lift.pos {{ background: var(--verde-bg); color: var(--verde); }}
.oferta-metricas .lift.neg {{ background: var(--amarelo-bg); color: var(--amarelo); }}
.oferta-metricas .lift.nulo {{ background: var(--border); color: var(--ink-mute); }}

/* Cash&Carry resumo */
.cc-resumo {{
  display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px; margin-bottom: 22px;
  padding: 18px 20px; background: var(--gran-dourado-bg);
  border-radius: 8px; border-left: 4px solid var(--gran-dourado);
}}
.cc-resumo .box {{ }}
.cc-resumo .box .l {{
  font-family: 'JetBrains Mono',monospace; font-size: 10px;
  letter-spacing: 0.12em; text-transform: uppercase;
  color: var(--ink-mute); margin: 0 0 4px; font-weight: 600;
}}
.cc-resumo .box .v {{
  font-family: 'Aptos','Nunito Sans',sans-serif;
  font-weight: 700; font-size: 22px; color: var(--gran-verde);
}}
.cc-resumo .box .v.neg {{ color: var(--vermelho); }}
.cc-resumo .box .v.pos {{ color: var(--verde); }}

/* Alerta de desalinhamento por feriado */
.feriado-alerta {{
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 6px;
  background: #fff4d6;
  color: #8a6500;
  border: 1px solid #e0c97a;
  border-radius: 3px;
  font-size: 10px;
  font-weight: 700;
  font-family: 'JetBrains Mono', monospace;
  cursor: help;
  margin-left: 6px;
  vertical-align: middle;
}}
.feriado-alerta::before {{ content: '⚠'; font-size: 11px; }}

.yoy-toggle-row {{
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  background: var(--bg-cream);
  padding: 10px 14px;
  border-radius: 6px;
  border: 1px solid var(--border);
  margin-bottom: 14px;
}}
.yoy-toggle-row label {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-weight: 700;
  color: var(--gran-verde);
}}
.yoy-toggle-row select {{
  font-size: 13px;
  padding: 5px 10px;
  border-radius: 4px;
  border: 1px solid var(--border);
  background: white;
  font-family: 'Aptos','Nunito Sans',sans-serif;
  min-width: 280px;
}}
.yoy-info-pill {{
  font-size: 11px;
  color: var(--ink-dim);
  font-style: italic;
}}

/* Tornado/Butterfly chart */
.tornado-row {{
  display: grid;
  grid-template-columns: 1fr 200px 1fr;
  gap: 12px;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-soft);
}}
.tornado-row:last-child {{ border-bottom: none; }}
.tornado-side-left, .tornado-side-right {{
  display: flex;
  align-items: center;
  height: 28px;
  position: relative;
}}
.tornado-side-left {{ justify-content: flex-end; }}
.tornado-side-right {{ justify-content: flex-start; }}
.tornado-bar {{
  height: 22px;
  border-radius: 3px;
  transition: width 0.6s ease;
  display: flex;
  align-items: center;
  padding: 0 8px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
  font-weight: 700;
  color: white;
  white-space: nowrap;
  overflow: hidden;
}}
.tornado-bar-2025 {{
  background: var(--ink-mute);
  justify-content: flex-end;
  border-radius: 3px 0 0 3px;
}}
.tornado-bar-2026-up   {{ background: var(--verde); border-radius: 0 3px 3px 0; }}
.tornado-bar-2026-down {{ background: var(--vermelho); border-radius: 0 3px 3px 0; }}
.tornado-bar-2026-flat {{ background: var(--ink-dim); border-radius: 0 3px 3px 0; }}
.tornado-center {{
  text-align: center;
  font-family: 'Aptos','Nunito Sans',sans-serif;
  font-size: 13px;
  font-weight: 600;
  color: var(--ink);
  line-height: 1.25;
}}
.tornado-center .yoy-pct {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  font-weight: 700;
  display: block;
  margin-top: 2px;
}}
.tornado-header {{
  display: grid;
  grid-template-columns: 1fr 200px 1fr;
  gap: 12px;
  padding: 10px 0;
  margin-bottom: 6px;
  border-bottom: 2px solid var(--gran-verde);
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  font-weight: 700;
  color: var(--gran-verde);
}}
.tornado-header .h-left  {{ text-align: right; }}
.tornado-header .h-mid   {{ text-align: center; }}
.tornado-header .h-right {{ text-align: left; }}

.tornado-grid-duplo {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 32px;
}}
.tornado-grid-duplo h4 {{
  font-family: 'Aptos','Nunito Sans',sans-serif;
  font-size: 14px;
  color: var(--gran-verde);
  margin: 0 0 12px;
  padding: 6px 12px;
  background: var(--bg-cream);
  border-left: 3px solid var(--gran-dourado);
  border-radius: 4px;
}}
@media (max-width: 1100px) {{
  .tornado-grid-duplo {{ grid-template-columns: 1fr; }}
}}

/* Cards por setor */
.cards-setor {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
}}
.card-setor {{
  background: var(--bg-cream);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 18px 20px;
  box-shadow: var(--shadow);
  border-left: 4px solid var(--ink-mute);
}}
.card-setor.up   {{ border-left-color: var(--verde); }}
.card-setor.down {{ border-left-color: var(--vermelho); }}
.card-setor.flat {{ border-left-color: var(--amarelo); }}
.card-setor h4 {{
  font-family: 'Aptos','Nunito Sans',sans-serif;
  font-size: 14px;
  font-weight: 700;
  color: var(--ink);
  margin: 0 0 8px;
  letter-spacing: -0.01em;
}}
.card-yoy {{
  font-family: 'Aptos','Nunito Sans',sans-serif;
  font-weight: 800;
  font-size: 32px;
  letter-spacing: -0.03em;
  line-height: 1;
}}
.card-yoy.up   {{ color: var(--verde); }}
.card-yoy.down {{ color: var(--vermelho); }}
.card-yoy.flat {{ color: var(--amarelo); }}
.card-fats {{
  font-size: 12px;
  color: var(--ink-dim);
  margin: 8px 0 12px;
  font-family: 'JetBrains Mono', monospace;
}}
.card-spark {{
  height: 50px;
  margin-top: 8px;
}}
.card-spark-label {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 9px;
  letter-spacing: 0.1em;
  color: var(--ink-mute);
  text-transform: uppercase;
  margin-top: 4px;
}}

/* Heatmap */
.heatmap {{ overflow-x: auto; }}
.heatmap table {{ border-collapse: separate; border-spacing: 3px; width: 100%; }}
.heatmap th {{
  background: transparent; color: var(--ink-dim);
  font-family: 'JetBrains Mono',monospace; font-size: 10px;
  padding: 8px 6px; letter-spacing: 0.05em; font-weight: 600;
  text-align: center;
}}
.heatmap th.row-label {{ text-align: left; background: transparent; padding-left: 0; color: var(--ink); font-weight: 600; font-family: 'Aptos','Nunito Sans',sans-serif; font-size: 12px; }}
.heatmap td {{
  width: 60px; height: 38px; padding: 4px 6px; text-align: center;
  font-family: 'JetBrains Mono',monospace; font-size: 11px; font-weight: 600;
  border-radius: 4px; cursor: default;
}}
.heatmap td.na {{ background: #f5f5f0; color: var(--ink-mute); }}

footer {{
  margin-top: 80px; padding-top: 24px; border-top: 1px solid var(--border);
  font-family: 'JetBrains Mono',monospace; font-size: 10px;
  color: var(--ink-mute); letter-spacing: 0.1em; text-transform: uppercase;
}}
</style>
</head>
<body>
<div class="container">

<header class="main-header">
  <div class="left">
    <p class="eyebrow">Gran Hortifruti · Survey Semanal · v1</p>
    <h1>Semana <em>{kpis['sem_label']}</em></h1>
    <p class="subtitle">{kpis['periodo']} · 13 semanas de histórico</p>
  </div>
  <div class="meta">
    <div><strong>{kpis['qtd_dias']}</strong> dias · PDVs <strong>101·102</strong></div>
    <div><strong>{fmt_int_br(kpis['skus_ativos'])}</strong> SKUs ativos na semana</div>
    <div>Base hist.: <strong>{len(D['semanas_info'])}</strong> semanas em foco · <strong>19 meses</strong> totais</div>
    <div>Cobertura <strong>{kpis['cobertura_fat']:.1f}%</strong></div>
  </div>
</header>

<div class="tabs-wrap">
  <nav class="tabs">
    <button class="tab active" data-tab="headline"><span class="num">01</span>Headline</button>
    <button class="tab" data-tab="evolucao"><span class="num">02</span>Evolução 13 sem</button>
    <button class="tab" data-tab="setores"><span class="num">03</span>Setores</button>
    <button class="tab" data-tab="raiox"><span class="num">04</span>Raio-X SKU</button>
    <button class="tab" data-tab="ruptura"><span class="num">05</span>Ruptura</button>
    <button class="tab" data-tab="kvis"><span class="num">06</span>KVIs</button>
    <button class="tab" data-tab="elasticidade"><span class="num">07</span>Elasticidade</button>
    <button class="tab" data-tab="ofertas"><span class="num">08</span>Ofertas</button>
    <button class="tab" data-tab="sazonalidade"><span class="num">09</span>Sazonalidade YoY</button>
    <button class="tab" data-tab="alertas"><span class="num">10</span>Alertas</button>
  </nav>
</div>

<!-- ABA 1 HEADLINE -->
<section class="tab-panel active" id="tab-headline">
  <p class="section-kicker">01 · Headline</p>
  <h2 class="section-title">A semana em números</h2>
  <p class="section-desc">Indicadores macro da {kpis['sem_label']} ({kpis['periodo']}) com comparadores LW, L4W e L8W ativos.</p>

  <div class="kpi-grid">
    <div class="kpi-card big">
      <p class="kpi-label">Faturamento total</p>
      <p class="kpi-value"><span class="kpi-unit">R$</span> {fmt_int_br(kpis['fat_total'])}</p>
      <p class="kpi-sub">{kpis['qtd_dias']} dias · R$ {fmt_int_br(kpis['media_dia'])}/dia</p>
      {fat_triplo}
    </div>
    <div class="kpi-card">
      <p class="kpi-label">Cupons fiscais</p>
      <p class="kpi-value">{fmt_int_br(kpis['qtd_cupons'])}</p>
      <p class="kpi-sub">{kpis['qtd_cupons']/kpis['qtd_dias']:.0f}/dia em média</p>
      {cupons_triplo}
    </div>
    <div class="kpi-card">
      <p class="kpi-label">Ticket médio</p>
      <p class="kpi-value"><span class="kpi-unit">R$</span> {fmt_dec_br(kpis['ticket_medio'])}</p>
      <p class="kpi-sub">{fmt_dec_br(kpis['itens_nf'])} itens por cupom</p>
      {ticket_triplo}
    </div>
    <div class="kpi-card">
      <p class="kpi-label">SKUs ativos</p>
      <p class="kpi-value">{fmt_int_br(kpis['skus_ativos'])}</p>
      <p class="kpi-sub">distintos vendidos na semana</p>
      {skus_triplo}
    </div>
    <div class="kpi-card">
      <p class="kpi-label">Itens por NF</p>
      <p class="kpi-value">{fmt_dec_br(kpis['itens_nf'])}</p>
      <p class="kpi-sub">média de itens por cupom</p>
      {itens_triplo}
    </div>
  </div>

  <div class="chart-box">
    <h3>Ganhadores e Perdedores · Top 12 SKUs por impacto financeiro</h3>
    <p class="desc">Cada SKU classificado pelo <strong>delta R$ absoluto</strong> em três visões complementares: <strong>Semana atual vs mesma semana 2025</strong> (movimento pontual), <strong>13 semanas acumuladas 2026 vs 2025</strong> (problema crônico ou crescimento estrutural), e <strong>L4W</strong> (semana atual vs média das 4 semanas anteriores · ritmo recente). Universo: união do Top 30 da loja com Top 12 de cada setor. Filtro aplicado nas 3 visões.</p>
    <div class="select-wrap" style="margin-bottom:16px">
      <label for="sel-tsku-setor">Filtro setor:</label>
      <select id="sel-tsku-setor" style="min-width:280px">
        <option value="all">Loja toda</option>
      </select>
      <span class="info-pill" style="margin-left:8px">Top 12 ganhadores · Top 12 perdedores</span>
    </div>

    <h4 class="tsku-section-title">Semana atual · {kpis['sem_label']} vs mesma semana de 2025</h4>
    <div class="tsku-grid">
      <div class="tsku-block">
        <h4><span class="label-A">2025</span><span>↑ GANHADORES</span><span class="label-B">2026</span></h4>
        <div id="tsku-sem-ganh"></div>
      </div>
      <div class="tsku-block">
        <h4><span class="label-A">2025</span><span>↓ PERDEDORES</span><span class="label-B">2026</span></h4>
        <div id="tsku-sem-perd"></div>
      </div>
    </div>

    <h4 class="tsku-section-title">13 semanas acumuladas · 2026 vs 2025</h4>
    <div class="tsku-grid">
      <div class="tsku-block">
        <h4><span class="label-A">2025</span><span>↑ GANHADORES</span><span class="label-B">2026</span></h4>
        <div id="tsku-13s-ganh"></div>
      </div>
      <div class="tsku-block">
        <h4><span class="label-A">2025</span><span>↓ PERDEDORES</span><span class="label-B">2026</span></h4>
        <div id="tsku-13s-perd"></div>
      </div>
    </div>

    <h4 class="tsku-section-title">L4W · {kpis['sem_label']} vs média das 4 semanas anteriores</h4>
    <div class="tsku-grid">
      <div class="tsku-block">
        <h4><span class="label-A">L4W média</span><span>↑ GANHADORES</span><span class="label-B">Atual</span></h4>
        <div id="tsku-l4w-ganh"></div>
      </div>
      <div class="tsku-block">
        <h4><span class="label-A">L4W média</span><span>↓ PERDEDORES</span><span class="label-B">Atual</span></h4>
        <div id="tsku-l4w-perd"></div>
      </div>
    </div>
  </div>

  <div class="chart-box">
    <h3>Faturamento diário · vs L4W e vs 2025 <span id="alerta-feriado-aba01" style="display:none"></span></h3>
    <p class="desc">Barras: faturamento de cada dia da {kpis['sem_label']}. Linha dourada: média do mesmo dia-da-semana nas 4 semanas anteriores (L4W). Linha azul pontilhada: faturamento do mesmo dia-da-semana em {kpis['sem_label_yoy']} (YoY). Triplo comparativo permite identificar onde a semana atual ganhou ou perdeu, e se isso é diferente do ano passado.</p>
    <div class="yoy-toggle-row" id="yoy-toggle-aba01">
      <label>Comparação YoY:</label>
      <select id="sel-yoy-aba01">
        <option value="posicional">{kpis['sem_label_yoy']} (mesma posição calendária)</option>
        <option value="aligned">S14/2025 (alinhada — sem feriado)</option>
      </select>
      <span class="yoy-info-pill" id="yoy-info-aba01"></span>
    </div>
    <div class="chart-wrap tall"><canvas id="chart-diario"></canvas></div>

    <h4 style="margin-top:24px;font-family:'Aptos','Nunito Sans',sans-serif;font-size:14px;color:var(--gran-verde);letter-spacing:-0.01em">Tabela de comparação dia a dia</h4>
    <table class="data compact" id="tab-yoy-aba01">
      <thead>
        <tr>
          <th>Dia</th>
          <th class="num">Fat 2026</th>
          <th class="num">Fat L4W</th>
          <th class="num">Fat YoY</th>
          <th class="num">Δ R$ vs L4W</th>
          <th class="num">vs L4W %</th>
          <th class="num">Δ R$ YoY</th>
          <th class="num">YoY %</th>
        </tr>
      </thead>
      <tbody></tbody>
      <tfoot></tfoot>
    </table>
  </div>
</section>

<!-- ABA 2 EVOLUÇÃO 13 SEMANAS -->
<section class="tab-panel" id="tab-evolucao">
  <p class="section-kicker">02 · Evolução Semanal</p>
  <h2 class="section-title">13 semanas · o trimestre inteiro</h2>
  <p class="section-desc">Cada ponto é uma semana fechada (qua→ter). Alterne entre os KPIs para ver como cada um evoluiu.</p>

  <div class="select-wrap">
    <label for="sel-kpi-evolucao">KPI:</label>
    <select id="sel-kpi-evolucao">
      <option value="fat">Faturamento</option>
      <option value="cupons">Cupons</option>
      <option value="ticket_medio">Ticket médio</option>
      <option value="media_dia">Média dia</option>
      <option value="itens_nf">Itens/NF</option>
    </select>
  </div>

  <div class="chart-box">
    <h3 id="evol-title">Faturamento · 13 semanas (2026 vs 2025)</h3>
    <p class="desc">Linha verde: KPI escolhido em 2026. Linha azul pontilhada: mesmas semanas em 2025 (YoY). Linha dourada fina: média móvel L4W. Tooltip mostra a variação YoY de cada ponto.</p>
    <div class="yoy-toggle-row">
      <label>Comparação YoY:</label>
      <select id="sel-yoy-aba02">
        <option value="posicional">Posicional ({kpis['sem_range_label']}/{kpis['ano']-1} nas mesmas posições)</option>
        <option value="aligned">Alinhada por feriado (corrige Carnaval, Páscoa, Cinzas)</option>
      </select>
      <span class="yoy-info-pill">⚠️ 6 das 13 semanas têm desalinhamento de feriado móvel</span>
    </div>
    <div class="chart-wrap tall"><canvas id="chart-evolucao"></canvas></div>

    <h4 style="margin-top:24px;font-family:'Aptos','Nunito Sans',sans-serif;font-size:14px;color:var(--gran-verde);letter-spacing:-0.01em">Tabela de comparação semana a semana</h4>
    <table class="data compact" id="tab-yoy-evolucao">
      <thead>
        <tr>
          <th>Semana</th>
          <th>Período 2026</th>
          <th>Período 2025</th>
          <th class="num">2026</th>
          <th class="num">2025</th>
          <th class="num">Δ R$</th>
          <th class="num">YoY %</th>
        </tr>
      </thead>
      <tbody></tbody>
      <tfoot></tfoot>
    </table>
  </div>

  <div class="grid-2">
    <div class="chart-box">
      <h3>Faturamento diário (semana atual)</h3>
      <p class="desc">Dia a dia da {kpis['sem_label']}.</p>
      <div class="chart-wrap"><canvas id="chart-diario-2"></canvas></div>
    </div>
    <div class="chart-box">
      <h3>Padrão horário (semana atual)</h3>
      <p class="desc">Curva da semana atual.</p>
      <div style="margin:8px 0 12px 0">
        <label style="font-size:12px;color:var(--ink-mute);margin-right:8px">Filtrar por dia:</label>
        <select id="sel-dow-horario" style="padding:4px 8px;border:1px solid var(--border);border-radius:4px;font-size:12px">
          <option value="all">Todos os dias (consolidado)</option>
          <option value="qua">Quarta</option>
          <option value="qui">Quinta</option>
          <option value="sex">Sexta</option>
          <option value="sab">Sábado</option>
          <option value="dom">Domingo</option>
          <option value="seg">Segunda</option>
          <option value="ter">Terça</option>
        </select>
      </div>
      <div class="chart-wrap"><canvas id="chart-horario"></canvas></div>
    </div>
  </div>

  <div class="chart-box">
    <h3>Faixas de ticket (semana atual)</h3>
    <div class="chart-wrap"><canvas id="chart-faixas"></canvas></div>
  </div>
</section>

<!-- ABA 3 SETORES -->
<section class="tab-panel" id="tab-setores">
  <p class="section-kicker">03 · Setores</p>
  <h2 class="section-title">Quem puxa o faturamento</h2>
  <p class="section-desc">Os {len(D['setores'])} setores por faturamento na {kpis['sem_label']}. Heatmap 13 semanas mostra a variação vs L4W semana a semana.</p>

  <div class="chart-box">
    <h3>Faturamento por setor · {kpis['sem_label']}</h3>
    <p class="desc">Ranking + variação vs média das 4 semanas anteriores (L4W).</p>
    <div id="hbars-setor"></div>
  </div>

  <div class="chart-box">
    <h3>Comparativo visual 2026 vs 2025 · por setor</h3>
    <p class="desc">Para cada setor: barra cinza à esquerda mostra fat 2025, barra colorida à direita mostra fat 2026 (verde = cresceu, vermelho = caiu). Setores ordenados por tamanho. Permite ver instantaneamente quem cresceu, quem caiu, e a proporção do tamanho.</p>
    <div class="select-wrap" style="margin-bottom:12px">
      <label for="sel-tornado-modo">Comparação:</label>
      <select id="sel-tornado-modo" style="min-width:280px">
        <option value="13sem">13 semanas focais (2026 vs 2025)</option>
        <option value="s13">Apenas {kpis['sem_label']} (semana isolada)</option>
        <option value="duplo">Mostrar os dois lado a lado</option>
      </select>
    </div>
    <div id="tornado-wrap"></div>
  </div>

  <div class="chart-box">
    <h3>Cards por setor · YoY 13 semanas + tendência semanal</h3>
    <p class="desc">Top 8 setores. Cada card mostra: variação YoY das 13 semanas focais, fat acumulado em R$, e mini-gráfico ("sparkline") com a YoY% semana a semana. Setores que caíram todas as semanas (consistência) merecem mais atenção que setores que oscilam.</p>
    <div class="yoy-toggle-row">
      <label>Comparação YoY:</label>
      <select id="sel-yoy-cards">
        <option value="posicional">Posicional (mesma posição calendária)</option>
        <option value="aligned">Alinhada por feriado</option>
      </select>
    </div>
    <div id="cards-setor-wrap"></div>
  </div>

  <div class="chart-box">
    <h3>Heatmap setor × semana — variação <span id="hm-modo-label">vs L4W</span></h3>
    <p class="desc">Verde = crescendo · Vermelho = caindo · Cinza = sem base de comparação. Alterne entre L4W (movimento curto) e YoY (mesma semana ano anterior).</p>
    <div class="select-wrap" style="margin-bottom:12px">
      <label for="sel-heatmap-modo">Modo:</label>
      <select id="sel-heatmap-modo" style="min-width:240px">
        <option value="l4w">vs L4W (média 4 sem anteriores)</option>
        <option value="yoy">vs YoY (mesma semana 2025)</option>
      </select>
    </div>
    <div class="heatmap" id="heatmap-wrap"></div>
  </div>

  <div class="chart-box">
    <h3>Tabela completa · {kpis['sem_label']} + YoY 13 semanas</h3>
    <p class="desc">Faturamento atual + comparadores LW, L4W, L8W e YoY (1 ano). Coluna "YoY 13sem" mostra variação acumulada das 13 semanas focais 2026 vs mesmas 13 semanas em 2025.</p>
    <table class="data" id="tab-setores-full">
      <thead>
        <tr>
          <th>Setor</th>
          <th class="num">Fat {kpis['sem_label']}</th>
          <th class="num">vs LW</th>
          <th class="num">vs L4W</th>
          <th class="num">vs L8W</th>
          <th class="num">YoY {kpis['sem_label_short']}</th>
          <th class="num">YoY 13sem</th>
          <th class="num">Δ R$ YoY 13sem</th>
          <th class="num">Share</th>
        </tr>
      </thead>
      <tbody></tbody>
    </table>
  </div>
</section>

<!-- ABA 4 RAIO-X -->
<section class="tab-panel" id="tab-raiox">
  <p class="section-kicker">04 · Raio-X SKU</p>
  <h2 class="section-title">Drill-down SKU</h2>
  <p class="section-desc">Duas visões: Top 30 SKUs da loja inteira (visão macro) e Top 30 por setor (drill-down). Todos com comparadores LW, L4W e L8W.</p>

  <div class="chart-box">
    <h3>Top 30 SKUs da loja · {kpis['sem_label']}</h3>
    <p class="desc">Os 30 SKUs que mais venderam em R$ nesta semana, de todos os setores.</p>
    <table class="data" id="tab-top30-loja">
      <thead>
        <tr>
          <th class="num">#</th><th>Cód</th><th>Descrição</th><th>Setor</th>
          <th>KVI</th><th>Curva</th>
          <th class="num">Fat</th>
          <th class="num">vs LW</th><th class="num">vs L4W</th><th class="num">vs L8W</th>
          <th class="num" title="faturamento vs mesma semana 2025" style="border-left:2px solid var(--gran-dourado);padding-left:8px">YoY Fat</th>
          <th class="num" title="quantidade vs mesma semana 2025">YoY Qtd</th>
          <th class="num">Qtd</th><th class="num">Preço</th>
        </tr>
      </thead>
      <tbody></tbody>
    </table>
  </div>

  <div class="chart-box">
    <h3>Linha do tempo — evolução de SKU escolhido</h3>
    <p class="desc">Selecione qualquer SKU do Top 30 da loja para ver sua evolução nas 13 semanas. Alterne entre Quantidade ou Faturamento para ver o ângulo que importa — às vezes vendemos menos unidades mas com preço mais alto, e o faturamento compensa.</p>
    <div class="select-wrap">
      <label for="sel-sku-serie">SKU:</label>
      <select id="sel-sku-serie"></select>
      <label for="sel-sku-modo" style="margin-left:12px">Visão:</label>
      <select id="sel-sku-modo" style="min-width:200px">
        <option value="qtd">Quantidade × Preço</option>
        <option value="fat">Faturamento × Preço</option>
      </select>
    </div>
    <div id="sku-serie-meta" style="margin-bottom:16px;font-size:13px;color:var(--ink-dim)"></div>
    <div class="chart-wrap tall"><canvas id="chart-sku-serie"></canvas></div>
  </div>

  <div class="chart-box">
    <h3>Top 30 SKUs por setor</h3>
    <div class="select-wrap">
      <label for="sel-setor">Setor:</label>
      <select id="sel-setor"></select>
    </div>
    <table class="data" id="tab-skus">
      <thead>
        <tr>
          <th class="num">#</th><th>Cód</th><th>Descrição</th>
          <th>KVI</th><th>Curva</th>
          <th class="num">Fat</th>
          <th class="num">vs LW</th><th class="num">vs L4W</th><th class="num">vs L8W</th>
          <th class="num" style="border-left:2px solid var(--gran-dourado);padding-left:8px">YoY Fat</th>
          <th class="num">YoY Qtd</th>
          <th class="num">Qtd</th><th class="num">Cupons</th><th class="num">Preço</th>
        </tr>
      </thead>
      <tbody></tbody>
    </table>
  </div>
</section>

<!-- ABA 5 RUPTURA -->
<section class="tab-panel" id="tab-ruptura">
  <p class="section-kicker">05 · Ruptura</p>
  <h2 class="section-title">Itens críticos sem venda</h2>
  <p class="section-desc">Agora com 6 semanas de histórico, distinguimos ruptura pontual (1 semana) de ruptura recorrente (3+ nas últimas 6).</p>

  <div class="grid-2">
    <div class="chart-box">
      <h3>KVI+ em ruptura recorrente</h3>
      <p class="desc">3 ou mais das últimas 6 semanas sem venda. {len(D['ruptura_recorrente_kvi_plus'])} detectados.</p>
      <table class="data">
        <thead><tr><th>Cód</th><th>Descrição</th><th>Setor</th><th class="num">Sem/6</th></tr></thead>
        <tbody id="tb-rupt-rec-kviplus"></tbody>
      </table>
    </div>
    <div class="chart-box">
      <h3>KVI em ruptura recorrente</h3>
      <p class="desc">{len(D['ruptura_recorrente_kvi'])} detectados.</p>
      <table class="data">
        <thead><tr><th>Cód</th><th>Descrição</th><th>Setor</th><th class="num">Sem/6</th></tr></thead>
        <tbody id="tb-rupt-rec-kvi"></tbody>
      </table>
    </div>
  </div>

  <div class="grid-2">
    <div class="chart-box">
      <h3>KVI+ sem venda nenhuma em 6 semanas</h3>
      <p class="desc">Itens do Top 30 que zeraram totalmente. {len(D['nunca_venderam_kvi_plus'])} detectados.</p>
      <table class="data">
        <thead><tr><th>Cód</th><th>Descrição</th><th>Setor</th><th class="num">Preço</th></tr></thead>
        <tbody id="tb-nunca-kviplus"></tbody>
      </table>
    </div>
    <div class="chart-box">
      <h3>KVI sem venda nenhuma em 6 semanas</h3>
      <p class="desc">{len(D['nunca_venderam_kvi'])} detectados.</p>
      <table class="data">
        <thead><tr><th>Cód</th><th>Descrição</th><th>Setor</th><th class="num">Preço</th></tr></thead>
        <tbody id="tb-nunca-kvi"></tbody>
      </table>
    </div>
  </div>
</section>

<!-- ABA 6 KVIs -->
<section class="tab-panel" id="tab-kvis">
  <p class="section-kicker">06 · KVIs</p>
  <h2 class="section-title">Watchlist de itens críticos</h2>
  <p class="section-desc">Desempenho na {kpis['sem_label']} dos 30 KVI+ e 105 KVI do cadastro, com comparadores LW, L4W e L8W por SKU.</p>

  <div class="chart-box">
    <h3>KVI+ · Top 30</h3>
    <table class="data">
      <thead>
        <tr><th class="num">#</th><th>Cód</th><th>Descrição</th><th>Setor</th><th>Curva</th>
        <th class="num">Fat</th>
        <th class="num">vs LW</th><th class="num">vs L4W</th><th class="num">vs L8W</th>
        <th class="num">Presença</th><th class="num">Preço</th></tr>
      </thead>
      <tbody id="tb-kvisplus"></tbody>
    </table>
  </div>

  <div class="chart-box">
    <h3>KVI · 105 itens</h3>
    <table class="data">
      <thead>
        <tr><th class="num">#</th><th>Cód</th><th>Descrição</th><th>Setor</th><th>Curva</th>
        <th class="num">Fat</th>
        <th class="num">vs LW</th><th class="num">vs L4W</th><th class="num">vs L8W</th>
        <th class="num">Presença</th><th class="num">Preço</th></tr>
      </thead>
      <tbody id="tb-kvis"></tbody>
    </table>
  </div>
</section>

<!-- ABA 7 ELASTICIDADE -->
<section class="tab-panel" id="tab-elasticidade">
  <p class="section-kicker">07 · Elasticidade preço × volume</p>
  <h2 class="section-title">Como SKUs reagem a variação de preço</h2>
  <p class="section-desc">
    {len(D['elasticidade'])} SKUs analisados — KVIs + Top 50 fat + Top 20 Gran Mesa. Calculamos correlação entre preço semanal e qtd vendida semanal ao longo das 13 semanas.
    Alta elasticidade = baixar preço explode volume (KVI real). Baixa = preço não afeta volume (espaço para subir margem).
  </p>

  <div class="grid-2">
    <div class="chart-box">
      <h3>Top 10 · "espaço para subir preço" (baixa elasticidade)</h3>
      <p class="desc">Correlação perto de zero ou positiva. Volume não depende muito de preço.</p>
      <table class="data">
        <thead><tr><th>Cód</th><th>Descrição</th><th>Setor</th><th>Classe</th><th class="num">Corr</th></tr></thead>
        <tbody id="tb-elast-baixa"></tbody>
      </table>
    </div>
    <div class="chart-box">
      <h3>Top 10 · "cuidado com preço" (alta elasticidade)</h3>
      <p class="desc">Correlação fortemente negativa. Qualquer aumento pode perder volume.</p>
      <table class="data">
        <thead><tr><th>Cód</th><th>Descrição</th><th>Setor</th><th>Classe</th><th class="num">Corr</th></tr></thead>
        <tbody id="tb-elast-alta"></tbody>
      </table>
    </div>
  </div>

  <div class="chart-box">
    <h3>Tabela completa · todos os {len(D['elasticidade'])} SKUs</h3>
    <p class="desc">Filtro rápido:</p>
    <div class="select-wrap">
      <label for="sel-elast">Filtro:</label>
      <select id="sel-elast">
        <option value="all">Todos</option>
        <option value="Alta elasticidade">Só alta elasticidade</option>
        <option value="Média elasticidade">Só média elasticidade</option>
        <option value="Baixa elasticidade">Só baixa elasticidade</option>
        <option value="Atípico (preço↑ → qtd↑)">Atípicos</option>
        <option value="Sem variação de preço">Sem variação de preço</option>
      </select>
    </div>
    <table class="data">
      <thead>
        <tr><th>Cód</th><th>Descrição</th><th>Setor</th><th>KVI</th>
        <th class="num">Preço médio</th><th class="num">Variação %</th>
        <th class="num">Correlação</th><th>Classificação</th></tr>
      </thead>
      <tbody id="tb-elast-full"></tbody>
    </table>
  </div>
</section>

<!-- ABA 8 OFERTAS -->
<section class="tab-panel" id="tab-ofertas">
  <p class="section-kicker">08 · Ofertas e Cash&amp;Carry</p>
  <h2 class="section-title">Leitura das promoções · agora com L4W ativo</h2>
  <p class="section-desc">
    Lift agora é medido vs mesmo dia-da-semana nas 4 semanas anteriores (L4W), muito mais robusto que comparação intra-semana. Limiar "pegou": +15%.
  </p>

  <div class="chart-box">
    <h3>Ofertas Segunda a Quinta · {kpis['sem_label']}</h3>
    <div id="ofertas-lista"></div>
  </div>

  <div class="chart-box">
    <h3>Cash&amp;Carry Sex-Dom · 20 KVIs "leve 3"</h3>
    <p class="desc">Acompanhamento individual dos 20 KVIs da promoção "Leve 3" de fim de semana. Lift é medido comparando fat Sex/Sáb/Dom da semana atual vs média Sex/Sáb/Dom das 4 semanas anteriores. Ordenado por receita incremental em R$ (do maior para o pior).</p>

    <div class="cc-resumo" id="cc-resumo"></div>

    <table class="data" id="tab-cc">
      <thead>
        <tr>
          <th>Cód</th>
          <th>Descrição</th>
          <th class="num">Fat promo</th>
          <th class="num">Baseline L4W</th>
          <th class="num">Δ R$</th>
          <th class="num">Lift</th>
          <th class="num">Qtd</th>
          <th class="num">Leve 3+</th>
          <th class="num">Cupons</th>
          <th class="num">Preço médio</th>
        </tr>
      </thead>
      <tbody id="tb-cc"></tbody>
    </table>
  </div>
</section>

<!-- ABA 10 SAZONALIDADE YoY -->
<section class="tab-panel" id="tab-sazonalidade">
  <p class="section-kicker">09 · Sazonalidade YoY</p>
  <h2 class="section-title">2025 vs 2026 mês a mês</h2>
  <p class="section-desc">Comparação direta entre 2025 e 2026 mês a mês. Distinguir tendência real de ciclo sazonal. A base histórica vai de 09/09/2024 a 21/04/2026 (19 meses), o que permite comparações YoY a partir de Set/2025 em diante.</p>

  <div class="kpi-grid">
    <div class="kpi-card">
      <p class="kpi-label">YoY semana atual</p>
      <p class="kpi-value" id="kpi-yoy-sem">—</p>
      <p class="kpi-sub" id="kpi-yoy-sem-detail">—</p>
    </div>
    <div class="kpi-card">
      <p class="kpi-label">YoY mês de Abril (até dia 21)</p>
      <p class="kpi-value" id="kpi-yoy-mes">—</p>
      <p class="kpi-sub" id="kpi-yoy-mes-detail">—</p>
    </div>
    <div class="kpi-card big">
      <p class="kpi-label">YoY · 13 semanas focais ({kpis['sem_range_label']}/{kpis['ano']} vs {kpis['ano']-1})</p>
      <p class="kpi-value" id="kpi-yoy-13sem">—</p>
      <p class="kpi-sub" id="kpi-yoy-13sem-detail">—</p>
    </div>
  </div>

  <div class="chart-box">
    <h3>YoY semana a semana · 13 semanas focais</h3>
    <p class="desc">Comparação direta semana 2026 vs mesma semana 2025. Linha vermelha (zero) = sem variação. Acima = crescendo · abaixo = caindo.</p>
    <div class="chart-wrap tall"><canvas id="chart-yoy-semanal"></canvas></div>
  </div>

  <div class="chart-box">
    <h3>Faturamento mensal · 2025 vs 2026</h3>
    <p class="desc">Linha azul: 2025. Linha dourada: 2026. Pontos onde só uma linha aparece = ainda sem comparação possível.</p>
    <div class="chart-wrap tall"><canvas id="chart-sazonalidade"></canvas></div>
  </div>

  <div class="chart-box">
    <h3>Tabela detalhada YoY</h3>
    <table class="data" id="tabela-sazonalidade">
      <thead>
        <tr>
          <th>Mês</th>
          <th class="num">Fat 2025</th>
          <th class="num">Fat 2026</th>
          <th class="num">Δ R$</th>
          <th class="num">YoY %</th>
        </tr>
      </thead>
      <tbody></tbody>
    </table>
  </div>

  <div class="chart-box">
    <h3>YoY por setor (semana atual)</h3>
    <p class="desc">Variação de cada setor entre {kpis['sem_label']} e {kpis['sem_label_yoy']}. Verde forte = setor crescendo. Vermelho = setor sangrando.</p>
    <div class="chart-wrap tall"><canvas id="chart-setor-yoy"></canvas></div>
  </div>
</section>

<!-- ABA 11 ALERTAS -->
<section class="tab-panel" id="tab-alertas">
  <p class="section-kicker">10 · Alertas Priorizados</p>
  <h2 class="section-title">O que exige atenção</h2>
  <p class="section-desc">Lista curta priorizada por severidade. Vermelho = crítico · Amarelo = atenção · Verde = positivo/estável.</p>

  <div id="alertas-list"></div>

  <div class="chart-box" style="margin-top:40px;">
    <h3>Exceções · itens sem classificação automática</h3>
    <p class="desc">{len(D['excecoes'])} descrições únicas do KW com prefixo ambíguo no cadastro ARIUS. Total R$ {fmt_int_br(sum(x['fat'] for x in D['excecoes']))} da semana atual.</p>
    <table class="data">
      <thead><tr><th>Descrição KW</th><th class="num">Linhas</th><th class="num">Fat</th></tr></thead>
      <tbody id="tb-excecoes"></tbody>
    </table>
  </div>
</section>

<footer>
  <p>Survey Semanal Gran · v1.0 · 13 semanas de histórico real · cobertura {kpis['cobertura_fat']:.1f}%</p>
</footer>

</div>

<script>
const D = {data_js};
const kpis = D.kpis_macro;
// alias retrocompat para acesso direto a campos da semana atual
window._sem_label = kpis.sem_label;
window._sem_label_yoy = kpis.sem_label_yoy;
window._sem_label_short = kpis.sem_label_short;

const fmtR  = n => 'R$ ' + (n||0).toLocaleString('pt-BR', {{maximumFractionDigits:0}});
const fmtR2 = n => 'R$ ' + (n||0).toLocaleString('pt-BR', {{minimumFractionDigits:2, maximumFractionDigits:2}});
const fmtN  = n => (n||0).toLocaleString('pt-BR', {{maximumFractionDigits:0}});
const fmtP  = n => (n||0).toFixed(1) + '%';
const fmtSignP = n => n==null ? '—' : ((n>=0?'+':'') + n.toFixed(1) + '%');

const css = getComputedStyle(document.documentElement);
const C = {{
  verde:   css.getPropertyValue('--gran-verde').trim(),
  verde2:  css.getPropertyValue('--gran-verde-2').trim(),
  verde3:  css.getPropertyValue('--gran-verde-3').trim(),
  dourado: css.getPropertyValue('--gran-dourado').trim(),
  dourado2:css.getPropertyValue('--gran-dourado-2').trim(),
  vermelho:css.getPropertyValue('--vermelho').trim(),
  amarelo: css.getPropertyValue('--amarelo').trim(),
  verdeAlert: css.getPropertyValue('--verde').trim(),
  ink:     css.getPropertyValue('--ink').trim(),
  inkDim:  css.getPropertyValue('--ink-dim').trim(),
  inkMute: css.getPropertyValue('--ink-mute').trim(),
  border:  css.getPropertyValue('--border').trim(),
  bgSoft:  css.getPropertyValue('--bg-soft').trim(),
}};

Chart.defaults.font.family = "'Aptos','Nunito Sans',sans-serif";
Chart.defaults.font.size = 12;
Chart.defaults.color = C.inkDim;
Chart.defaults.borderColor = C.border;
Chart.defaults.plugins.legend.labels.boxWidth = 12;
Chart.defaults.plugins.legend.labels.boxHeight = 12;
Chart.defaults.plugins.legend.labels.font = {{ weight: 600, size: 12 }};

document.querySelectorAll('.tab').forEach(btn => {{
  btn.addEventListener('click', () => {{
    document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
    window.scrollTo({{top:0, behavior:'smooth'}});
  }});
}});

// ABA 1: Diário com baseline L4W e YoY 2025 (3 elementos) + toggle YoY
let diarioCharts = {{}};

function renderChartDiarioL4W(canvasId, modoYoY) {{
  if (diarioCharts[canvasId]) diarioCharts[canvasId].destroy();
  const dados = D.evol_diaria_l4w;
  const usarAligned = modoYoY === 'aligned';
  const baselineYoYKey = usarAligned ? 'baseline_yoy_aligned' : 'baseline_yoy';
  const liftYoYKey     = usarAligned ? 'lift_yoy_aligned_pct' : 'lift_yoy_pct';
  const labelYoY = usarAligned ? 'S14/2025 (alinhada · pós-Páscoa)' : '{kpis['sem_label_yoy']} (mesmo dia-semana)';

  // Renderizar tabela apenas uma vez (canvas chart-diario, não chart-diario-2)
  if (canvasId === 'chart-diario') {{
    const tbody = document.querySelector('#tab-yoy-aba01 tbody');
    const tfoot = document.querySelector('#tab-yoy-aba01 tfoot');
    if (tbody) {{
      tbody.innerHTML = '';
      tfoot.innerHTML = '';

      // Atualizar header da coluna Fat YoY com o label
      const ths = document.querySelectorAll('#tab-yoy-aba01 thead th');
      ths[3].textContent = 'Fat ' + (usarAligned ? 'S14/25' : '{kpis['sem_label_short']}/{str(kpis['ano']-1)[2:]}');

      let tot_2026 = 0, tot_l4w = 0, tot_yoy = 0;
      dados.forEach(d => {{
        const v_2026 = d.fat;
        const v_l4w = d.baseline_l4w;
        const v_yoy = d[baselineYoYKey];
        const dR_l4w = (v_2026 != null && v_l4w != null) ? (v_2026 - v_l4w) : null;
        const dR_yoy = (v_2026 != null && v_yoy != null) ? (v_2026 - v_yoy) : null;
        const lift_l4w = d.lift_pct;
        const lift_yoy = d[liftYoYKey];

        if (v_2026 != null) tot_2026 += v_2026;
        if (v_l4w  != null) tot_l4w  += v_l4w;
        if (v_yoy  != null) tot_yoy  += v_yoy;

        const corL4W = lift_l4w == null ? 'var(--ink-mute)' : (lift_l4w >= 5 ? 'var(--verde)' : lift_l4w <= -5 ? 'var(--vermelho)' : 'var(--amarelo)');
        const corYoY = lift_yoy == null ? 'var(--ink-mute)' : (lift_yoy >= 5 ? 'var(--verde)' : lift_yoy <= -5 ? 'var(--vermelho)' : 'var(--amarelo)');
        const corDL4W = dR_l4w == null ? 'var(--ink-mute)' : (dR_l4w >= 0 ? 'var(--verde)' : 'var(--vermelho)');
        const corDYoY = dR_yoy == null ? 'var(--ink-mute)' : (dR_yoy >= 0 ? 'var(--verde)' : 'var(--vermelho)');

        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td><strong>${{d.dia_label}}</strong></td>
          <td class="num">${{fmtR(v_2026)}}</td>
          <td class="num">${{v_l4w == null ? '—' : fmtR(v_l4w)}}</td>
          <td class="num">${{v_yoy == null ? '—' : fmtR(v_yoy)}}</td>
          <td class="num" style="color:${{corDL4W}}">${{dR_l4w == null ? '—' : (dR_l4w>=0?'+':'') + fmtR(dR_l4w)}}</td>
          <td class="num" style="color:${{corL4W}};font-weight:700">${{lift_l4w == null ? '—' : fmtSignP(lift_l4w)}}</td>
          <td class="num" style="color:${{corDYoY}}">${{dR_yoy == null ? '—' : (dR_yoy>=0?'+':'') + fmtR(dR_yoy)}}</td>
          <td class="num" style="color:${{corYoY}};font-weight:700">${{lift_yoy == null ? '—' : fmtSignP(lift_yoy)}}</td>
        `;
        tbody.appendChild(tr);
      }});

      const dT_l4w = tot_2026 - tot_l4w;
      const dT_yoy = tot_2026 - tot_yoy;
      const yoyT_l4w = tot_l4w > 0 ? (tot_2026/tot_l4w - 1)*100 : null;
      const yoyT_yoy = tot_yoy > 0 ? (tot_2026/tot_yoy - 1)*100 : null;
      const corTl4w = yoyT_l4w == null ? 'var(--ink-mute)' : (yoyT_l4w >= 5 ? 'var(--verde)' : yoyT_l4w <= -5 ? 'var(--vermelho)' : 'var(--amarelo)');
      const corTyoy = yoyT_yoy == null ? 'var(--ink-mute)' : (yoyT_yoy >= 5 ? 'var(--verde)' : yoyT_yoy <= -5 ? 'var(--vermelho)' : 'var(--amarelo)');
      tfoot.innerHTML = `
        <tr>
          <td><strong>TOTAL ${{kpis.sem_label_short}}</strong></td>
          <td class="num">${{fmtR(tot_2026)}}</td>
          <td class="num">${{fmtR(tot_l4w)}}</td>
          <td class="num">${{fmtR(tot_yoy)}}</td>
          <td class="num" style="color:${{dT_l4w>=0?'var(--verde)':'var(--vermelho)'}}">${{(dT_l4w>=0?'+':'') + fmtR(dT_l4w)}}</td>
          <td class="num" style="color:${{corTl4w}}">${{yoyT_l4w==null?'—':fmtSignP(yoyT_l4w)}}</td>
          <td class="num" style="color:${{dT_yoy>=0?'var(--verde)':'var(--vermelho)'}}">${{(dT_yoy>=0?'+':'') + fmtR(dT_yoy)}}</td>
          <td class="num" style="color:${{corTyoy}}">${{yoyT_yoy==null?'—':fmtSignP(yoyT_yoy)}}</td>
        </tr>
      `;
    }}
  }}

  diarioCharts[canvasId] = new Chart(document.getElementById(canvasId), {{
    type: 'bar',
    data: {{
      labels: dados.map(r => r.dia_label),
      datasets: [
        {{
          type: 'bar',
          label: 'Fat. {kpis['sem_label']}',
          data: dados.map(r => r.fat),
          backgroundColor: C.verde,
          hoverBackgroundColor: C.verde2,
          borderRadius: 6, borderSkipped: false,
          datalabels: {{ display: true }},
          order: 3,
        }},
        {{
          type: 'line',
          label: 'Média L4W (4 sem anteriores)',
          data: dados.map(r => r.baseline_l4w),
          borderColor: C.dourado,
          backgroundColor: 'transparent',
          borderDash: [6,4], borderWidth: 2.5,
          pointRadius: 5, pointBackgroundColor: C.dourado, pointBorderColor:'#fff', pointBorderWidth: 2,
          tension: 0, fill: false,
          order: 2,
        }},
        {{
          type: 'line',
          label: labelYoY,
          data: dados.map(r => r[baselineYoYKey]),
          borderColor: '#5b8fb8',
          backgroundColor: 'transparent',
          borderDash: [3,3], borderWidth: 2,
          pointRadius: 4, pointBackgroundColor: '#5b8fb8', pointBorderColor:'#fff', pointBorderWidth: 1.5,
          tension: 0, fill: false,
          order: 1,
        }}
      ]
    }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      plugins: {{
        legend: {{ display: true, position: 'top' }},
        tooltip: {{
          callbacks: {{
            label: c => {{
              const row = dados[c.dataIndex];
              if (c.dataset.type === 'bar') {{
                let txt = ' Fat: ' + fmtR(c.raw);
                if (row.lift_pct !== null) txt += '  ·  vs L4W: ' + fmtSignP(row.lift_pct);
                if (row[liftYoYKey] !== null) txt += '  ·  YoY: ' + fmtSignP(row[liftYoYKey]);
                return txt;
              }} else if (c.dataset.label.startsWith('Média L4W')) {{
                return ' Média L4W: ' + fmtR(c.raw);
              }} else {{
                return ' ' + labelYoY + ': ' + (c.raw==null?'—':fmtR(c.raw));
              }}
            }}
          }}
        }}
      }},
      scales: {{
        y: {{ ticks: {{ callback: v => fmtR(v) }}, grid: {{ color: C.border }}, beginAtZero: true }},
        x: {{ grid: {{ display: false }} }}
      }},
      animation: {{
        onComplete: function() {{
          const ctx = this.ctx;
          ctx.font = '600 11px Aptos, "Nunito Sans", sans-serif';
          ctx.fillStyle = C.verde;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'bottom';
          this.data.datasets.forEach((ds, i) => {{
            if (ds.type !== 'bar') return;
            const meta = this.getDatasetMeta(i);
            meta.data.forEach((bar, j) => {{
              const val = ds.data[j];
              const row = dados[j];
              let label = fmtR(val);
              if (row.lift_pct !== null && Math.abs(row.lift_pct) >= 3) {{
                label += ' ' + fmtSignP(row.lift_pct);
              }}
              ctx.fillStyle = row.lift_pct !== null && row.lift_pct >= 3 ? C.verdeAlert : (row.lift_pct !== null && row.lift_pct < -10 ? C.vermelho : row.lift_pct !== null && row.lift_pct < -3 ? C.amarelo : C.verde);
              ctx.fillText(label, bar.x, bar.y - 6);
            }});
          }});
        }}
      }}
    }}
  }});
}}

// Mostrar alerta de feriado se a semana atual tiver desalinhamento
const semAtualInfo = D.yoy_dados_completo[D.yoy_dados_completo.length - 1];
if (semAtualInfo && semAtualInfo.tem_alerta) {{
  const alertaEl = document.getElementById('alerta-feriado-aba01');
  const fer26 = semAtualInfo.feriados_2026.map(f => f.nome).join(', ') || '—';
  const fer25 = semAtualInfo.feriados_2025_posicional.map(f => f.nome).join(', ') || '—';
  alertaEl.style.display = 'inline-flex';
  alertaEl.className = 'feriado-alerta';
  alertaEl.title = 'Feriados 2026: ' + fer26 + '\\nFeriados 2025 (mesma posição): ' + fer25 + '\\n\\nUse o seletor abaixo para mudar a comparação.';
  alertaEl.textContent = 'desalinhamento de feriado';

  document.getElementById('yoy-info-aba01').textContent = '⚠️ {kpis['sem_label_yoy']} tinha Páscoa+Sex Santa+Tiradentes — comparação posicional infla os números.';
}}

document.getElementById('sel-yoy-aba01').addEventListener('change', e => {{
  renderChartDiarioL4W('chart-diario', e.target.value);
  renderChartDiarioL4W('chart-diario-2', e.target.value);
}});

renderChartDiarioL4W('chart-diario', 'posicional');
renderChartDiarioL4W('chart-diario-2', 'posicional');

// ============================================================
// ABA 1 (Headline): Tornado SKU — Ganhadores e Perdedores · 3 visões (v0.12.8)
// ============================================================
(function() {{
  const tskuData = D.skus_tornado || [];
  if (!tskuData.length) return;

  // Popula dropdown de setores
  const setSel = document.getElementById('sel-tsku-setor');
  const setores = [...new Set(tskuData.map(s => s.setor))].sort();
  setores.forEach(setor => {{
    const opt = document.createElement('option');
    opt.value = `setor:${{setor}}`;
    opt.textContent = setor;
    setSel.appendChild(opt);
  }});

  // Top 12 ganhadores e perdedores por delta R$ (uma visão)
  function topByDelta(arr, deltaKey, n) {{
    const valid = arr.filter(s => s[deltaKey] != null && isFinite(s[deltaKey]));
    const ganh = [...valid].sort((a,b) => b[deltaKey] - a[deltaKey]).slice(0, n).filter(s => s[deltaKey] > 0);
    const perd = [...valid].sort((a,b) => a[deltaKey] - b[deltaKey]).slice(0, n).filter(s => s[deltaKey] < 0);
    return {{ganh, perd}};
  }}

  // Renderiza linhas do tornado para uma lista de SKUs e visão
  function renderTskuRows(skus, visao) {{
    if (!skus.length) return '<div class="tsku-empty">Sem SKUs nesse filtro/visão.</div>';
    let kA, kB, kDelta, kPct, periodoLabel;
    if (visao === 'sem') {{
      kA='fat_yoy_rs'; kB='fat_atual'; kDelta='delta_yoy_sem_rs'; kPct='var_yoy_fat_pct'; periodoLabel='sem 2025 vs 2026';
    }} else if (visao === '13s') {{
      kA='fat_13sem_2025'; kB='fat_13sem_2026'; kDelta='delta_yoy_13sem_rs'; kPct='var_yoy_13sem_pct'; periodoLabel='13 sem';
    }} else {{ // l4w
      kA='fat_l4w_media'; kB='fat_atual'; kDelta='delta_l4w_rs'; kPct='var_l4w_pct'; periodoLabel='L4W vs atual';
    }}
    const maxV = Math.max(...skus.map(s => Math.max(s[kA]||0, s[kB]||0))) || 1;
    return skus.map(s => {{
      const fA = s[kA] || 0;
      const fB = s[kB] || 0;
      const delta = s[kDelta] || 0;
      const pct = s[kPct];
      const wA = Math.abs(fA) / maxV * 100;
      const wB = Math.abs(fB) / maxV * 100;
      const cls = (pct != null && pct > 5) ? 'up' : (pct != null && pct < -5 ? 'down' : 'flat');
      const colDelta = delta >= 0 ? 'var(--verde)' : 'var(--vermelho)';
      const sinalDelta = delta >= 0 ? '+' : '';
      const showA = wA > 25 ? fmtR(fA) : '';
      const showB = wB > 25 ? fmtR(fB) : '';
      const pctTxt = pct == null ? '—' : fmtSignP(pct);
      const labelA = visao === 'l4w' ? 'L4W média' : '2025';
      const labelB = visao === 'l4w' ? 'Atual' : '2026';
      const tipA = `${{s.desc}} · cód ${{s.cod}} · ${{s.setor}} · ${{labelA}}: ${{fmtR(fA)}}`;
      const tipB = `${{s.desc}} · cód ${{s.cod}} · ${{s.setor}} · ${{labelB}}: ${{fmtR(fB)}} · Δ ${{sinalDelta}}${{fmtR(delta)}} (${{pctTxt}})`;
      const tipRow = `${{s.desc}} · cód ${{s.cod}} · ${{s.setor}} · ${{labelA}}=${{fmtR(fA)}} → ${{labelB}}=${{fmtR(fB)}} · Δ ${{sinalDelta}}${{fmtR(delta)}} (${{pctTxt}})`;
      return `<div class="tsku-row" title="${{tipRow}}">
        <div class="tsku-bar-A" title="${{tipA}}"><div class="bar" style="width:${{wA}}%" title="${{tipA}}">${{showA}}</div></div>
        <div class="tsku-mid">
          <div class="nome" title="${{s.desc}} · ${{s.setor}}">${{s.desc}}</div>
          <div class="delta" style="color:${{colDelta}}">${{sinalDelta}}${{fmtR(delta)}}</div>
        </div>
        <div class="tsku-bar-B" title="${{tipB}}"><div class="bar ${{cls}}" style="width:${{wB}}%" title="${{tipB}}">${{showB}}</div></div>
      </div>`;
    }}).join('');
  }}

  function applyFiltro(filtro) {{
    let skus = tskuData.slice();
    if (filtro && filtro.startsWith('setor:')) {{
      const s = filtro.slice(6);
      skus = skus.filter(x => x.setor === s);
    }}
    // Visão Semana
    const sem = topByDelta(skus, 'delta_yoy_sem_rs', 12);
    document.getElementById('tsku-sem-ganh').innerHTML = renderTskuRows(sem.ganh, 'sem');
    document.getElementById('tsku-sem-perd').innerHTML = renderTskuRows(sem.perd, 'sem');
    // Visão 13 Sem
    const s13 = topByDelta(skus, 'delta_yoy_13sem_rs', 12);
    document.getElementById('tsku-13s-ganh').innerHTML = renderTskuRows(s13.ganh, '13s');
    document.getElementById('tsku-13s-perd').innerHTML = renderTskuRows(s13.perd, '13s');
    // Visão L4W
    const l4w = topByDelta(skus, 'delta_l4w_rs', 12);
    document.getElementById('tsku-l4w-ganh').innerHTML = renderTskuRows(l4w.ganh, 'l4w');
    document.getElementById('tsku-l4w-perd').innerHTML = renderTskuRows(l4w.perd, 'l4w');
  }}

  setSel.addEventListener('change', e => applyFiltro(e.target.value));
  applyFiltro('all');
}})();

// ABA 2: Evolução 13 semanas com seletor de KPI + YoY 2025 + toggle alinhado
const kpiLabels = {{ 'fat': 'Faturamento', 'cupons': 'Cupons', 'ticket_medio': 'Ticket médio', 'media_dia': 'Média dia', 'itens_nf': 'Itens/NF' }};
const fmtMap    = {{ 'fat': fmtR, 'cupons': fmtN, 'ticket_medio': fmtR2, 'media_dia': fmtR, 'itens_nf': v => v.toFixed(2) }};
let evolChart = null;
let evolKpiAtual = 'fat';
let evolYoYModo = 'posicional';

// Identificar quais semanas têm alerta de feriado
const semsComAlerta = D.yoy_dados_completo.map((d,i) => d.tem_alerta ? i : -1).filter(i => i>=0);

function renderEvolucao(kpi, modoYoY) {{
  if (evolChart) evolChart.destroy();
  // v12.7: labels com período (29/04-05/05) abaixo do label da semana (S05)
  const labels = D.evolucao_semanal.map(r => {{
    const info = (D.semanas_info || []).find(s => s.label === r.label);
    return info && info.periodo ? [r.label, info.periodo] : r.label;
  }});
  const vals = D.evolucao_semanal.map(r => r[kpi]);
  const mm = (arr, n) => arr.map((_, i) => i<n ? null : arr.slice(i-n,i).reduce((a,b)=>a+b,0)/n);
  const l4w = mm(vals, 4);
  const yoy_serie = modoYoY === 'aligned'
    ? (D.evolucao_yoy_kpis_aligned[kpi] || [])
    : (D.evolucao_yoy_kpis[kpi] || []);
  const yoyLabel = modoYoY === 'aligned'
    ? 'Mesmas semanas em 2025 (alinhada por feriado)'
    : 'Mesmas semanas em 2025 (posicional)';

  // Marcar pontos com alerta usando pointStyle/borderColor
  const pointBgVerde = labels.map((_, i) => semsComAlerta.includes(i) ? '#f0a020' : C.dourado);
  const pointBgAzul  = labels.map((_, i) => semsComAlerta.includes(i) ? '#f0a020' : '#5b8fb8');

  evolChart = new Chart(document.getElementById('chart-evolucao'), {{
    type: 'line',
    data: {{
      labels,
      datasets: [
        {{ label: kpiLabels[kpi] + ' · 2026', data: vals, borderColor: C.verde, backgroundColor: C.verde+'22',
           fill: true, tension: 0.3, pointRadius: 5, pointBackgroundColor: pointBgVerde, pointBorderColor: '#fff', pointBorderWidth: 2, borderWidth: 2.5, order: 1 }},
        {{ label: yoyLabel, data: yoy_serie, borderColor: '#5b8fb8', backgroundColor: 'transparent',
           borderDash: [4,4], pointRadius: 4, pointBackgroundColor: pointBgAzul, pointBorderColor: '#fff', pointBorderWidth: 1.5, borderWidth: 2, fill: false, tension: 0.3, order: 2 }},
        {{ label: 'Média móvel L4W', data: l4w, borderColor: C.dourado, borderDash: [2,4], pointRadius: 0, borderWidth: 1.5, fill: false, tension: 0, order: 3 }},
      ]
    }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      plugins: {{
        legend: {{ position: 'top' }},
        tooltip: {{
          callbacks: {{
            title: ctx => {{
              const idx = ctx[0].dataIndex;
              const info = D.yoy_dados_completo[idx];
              let t = labels[idx];
              if (info && info.tem_alerta) t += ' ⚠ desalinhamento de feriado';
              return t;
            }},
            label: c => {{
              const v = c.raw;
              const txt = c.dataset.label + ': ' + (v==null ? '—' : fmtMap[kpi](v));
              if (c.datasetIndex === 0 && yoy_serie[c.dataIndex] != null && yoy_serie[c.dataIndex] > 0) {{
                const yoy = (v / yoy_serie[c.dataIndex] - 1) * 100;
                return ' ' + txt + '  ·  YoY: ' + fmtSignP(yoy);
              }}
              return ' ' + txt;
            }},
            afterBody: ctx => {{
              const idx = ctx[0].dataIndex;
              const info = D.yoy_dados_completo[idx];
              if (info && info.tem_alerta) {{
                const fer = info.feriados_2026.map(f => f.nome).join(', ') || '—';
                const fer25 = info.feriados_2025_posicional.map(f => f.nome).join(', ') || '—';
                return ['', '⚠ Atenção:', '2026: ' + fer, '2025 (mesma posição): ' + fer25];
              }}
              return [];
            }}
          }}
        }}
      }},
      scales: {{ y: {{ ticks: {{ callback: v => fmtMap[kpi](v) }}, grid: {{ color: C.border }} }}, x: {{ grid: {{ display: false }} }} }}
    }}
  }});
  document.getElementById('evol-title').textContent = kpiLabels[kpi] + ' · 13 semanas (2026 vs 2025' + (modoYoY==='aligned'?' alinhada':'') + ')';

  // Renderizar tabela compacta abaixo do gráfico
  const tbody = document.querySelector('#tab-yoy-evolucao tbody');
  const tfoot = document.querySelector('#tab-yoy-evolucao tfoot');
  tbody.innerHTML = '';
  tfoot.innerHTML = '';

  // Atualizar headers da tabela conforme KPI escolhido
  const ths = document.querySelectorAll('#tab-yoy-evolucao thead th');
  ths[3].textContent = '2026';
  ths[4].textContent = '2025';
  ths[5].textContent = kpi === 'fat' ? 'Δ R$' : 'Δ';
  ths[6].textContent = 'YoY %';

  let tot_2026 = 0, tot_2025 = 0, n_validos = 0;
  D.yoy_dados_completo.forEach((info, idx) => {{
    const v_2026 = vals[idx];
    const v_2025 = yoy_serie[idx];
    const delta = (v_2026 != null && v_2025 != null) ? (v_2026 - v_2025) : null;
    const yoy = (v_2026 != null && v_2025 != null && v_2025 > 0) ? (v_2026/v_2025 - 1)*100 : null;

    // Período 2025 escolhido depende do modo
    let periodo_2025 = '—';
    if (modoYoY === 'aligned' && info.tem_alerta && info.opcoes_2025.length >= 2) {{
      periodo_2025 = info.opcoes_2025[1].periodo;
    }} else if (info.opcoes_2025.length >= 1) {{
      periodo_2025 = info.opcoes_2025[0].periodo;
    }}

    if (v_2026 != null) tot_2026 += v_2026;
    if (v_2025 != null) {{ tot_2025 += v_2025; n_validos++; }}

    const corYoY = yoy == null ? 'var(--ink-mute)' : (yoy >= 5 ? 'var(--verde)' : yoy <= -5 ? 'var(--vermelho)' : 'var(--amarelo)');
    const corDelta = delta == null ? 'var(--ink-mute)' : (delta >= 0 ? 'var(--verde)' : 'var(--vermelho)');
    const tr = document.createElement('tr');
    if (info.tem_alerta) tr.className = 'tem-alerta';
    tr.innerHTML = `
      <td><strong>${{info.sem_label}}</strong></td>
      <td>${{info.periodo_2026}}</td>
      <td>${{periodo_2025}}</td>
      <td class="num">${{v_2026 == null ? '—' : fmtMap[kpi](v_2026)}}</td>
      <td class="num">${{v_2025 == null ? '—' : fmtMap[kpi](v_2025)}}</td>
      <td class="num" style="color:${{corDelta}};font-weight:700">${{delta == null ? '—' : (delta>=0?'+':'') + fmtMap[kpi](delta)}}</td>
      <td class="num" style="color:${{corYoY}};font-weight:700">${{yoy == null ? '—' : fmtSignP(yoy)}}</td>
    `;
    tbody.appendChild(tr);
  }});

  // Linha de total (footer)
  const delta_tot = tot_2026 - tot_2025;
  const yoy_tot = tot_2025 > 0 ? (tot_2026/tot_2025 - 1)*100 : null;
  const corYoYtot = yoy_tot == null ? 'var(--ink-mute)' : (yoy_tot >= 5 ? 'var(--verde)' : yoy_tot <= -5 ? 'var(--vermelho)' : 'var(--amarelo)');
  const corDeltaTot = delta_tot >= 0 ? 'var(--verde)' : 'var(--vermelho)';
  tfoot.innerHTML = `
    <tr>
      <td><strong>TOTAL 13sem</strong></td>
      <td>—</td>
      <td>—</td>
      <td class="num">${{fmtMap[kpi](tot_2026)}}</td>
      <td class="num">${{fmtMap[kpi](tot_2025)}}</td>
      <td class="num" style="color:${{corDeltaTot}}">${{(delta_tot>=0?'+':'') + fmtMap[kpi](delta_tot)}}</td>
      <td class="num" style="color:${{corYoYtot}}">${{yoy_tot==null?'—':fmtSignP(yoy_tot)}}</td>
    </tr>
  `;
}}
document.getElementById('sel-kpi-evolucao').addEventListener('change', e => {{
  evolKpiAtual = e.target.value;
  renderEvolucao(evolKpiAtual, evolYoYModo);
}});
document.getElementById('sel-yoy-aba02').addEventListener('change', e => {{
  evolYoYModo = e.target.value;
  renderEvolucao(evolKpiAtual, evolYoYModo);
}});
renderEvolucao('fat', 'posicional');

// Padrão horário (v12.7: filtro por dia da semana)
let chartHorario = null;
function renderHorario(dow) {{
  if (chartHorario) chartHorario.destroy();
  const cupData = D.padrao_horario.map(r => {{
    if (dow === 'all' || !r.by_dow) return r.cupons;
    return (r.by_dow[dow] || {{}}).cupons || 0;
  }});
  const fatData = D.padrao_horario.map(r => {{
    if (dow === 'all' || !r.by_dow) return r.fat;
    return (r.by_dow[dow] || {{}}).fat || 0;
  }});
  chartHorario = new Chart(document.getElementById('chart-horario'), {{
    type: 'bar',
    data: {{
      labels: D.padrao_horario.map(r => r.hora_int + 'h'),
      datasets: [
        {{ label: 'Cupons', data: cupData, backgroundColor: C.verde, borderRadius: 4, yAxisID: 'y' }},
        {{ label: 'Faturamento', data: fatData, type: 'line', borderColor: C.dourado, backgroundColor: C.dourado + '33', yAxisID: 'y1', tension: 0.35, pointRadius: 4, borderWidth: 2.5 }}
      ]
    }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      scales: {{
        y: {{ position: 'left', grid: {{ color: C.border }}, title: {{ display: true, text: 'Cupons', color: C.verde, font: {{ weight: 600 }} }} }},
        y1: {{ position: 'right', grid: {{ display: false }}, ticks: {{ callback: v => fmtR(v) }}, title: {{ display: true, text: 'Fat (R$)', color: C.dourado, font: {{ weight: 600 }} }} }},
        x: {{ grid: {{ display: false }} }}
      }}
    }}
  }});
}}
const selDowHorario = document.getElementById('sel-dow-horario');
if (selDowHorario) selDowHorario.addEventListener('change', e => renderHorario(e.target.value));
renderHorario('all');

// Faixas ticket
new Chart(document.getElementById('chart-faixas'), {{
  type: 'bar',
  data: {{
    labels: D.faixas_ticket.map(r => r.faixa),
    datasets: [
      {{ label: 'Qtd cupons', data: D.faixas_ticket.map(r => r.qtd), backgroundColor: C.verde, yAxisID: 'y', borderRadius: 4 }},
      {{ label: 'Faturamento', data: D.faixas_ticket.map(r => r.fat), backgroundColor: C.dourado, yAxisID: 'y1', borderRadius: 4 }}
    ]
  }},
  options: {{
    responsive: true, maintainAspectRatio: false,
    scales: {{
      y: {{ position: 'left', grid: {{ color: C.border }}, title: {{ display: true, text: 'Qtd', color: C.verde, font: {{ weight: 600 }} }} }},
      y1: {{ position: 'right', grid: {{ display: false }}, ticks: {{ callback: v => fmtR(v) }}, title: {{ display: true, text: 'Fat', color: C.dourado, font: {{ weight: 600 }} }} }},
      x: {{ grid: {{ display: false }} }}
    }}
  }}
}});

// ABA 3: Setores hbars
const hbarsCont = document.getElementById('hbars-setor');
const maxFatSet = Math.max(...D.setores.map(s => s.fat));
D.setores.forEach(s => {{
  const l4w = s.var_l4w;
  const l4wTxt = l4w==null ? '—' : fmtSignP(l4w);
  const l4wColor = l4w==null ? C.inkMute : (l4w >= 3 ? C.verdeAlert : l4w <= -10 ? C.vermelho : l4w < -3 ? C.amarelo : C.inkDim);
  const div = document.createElement('div');
  div.className = 'hbar-row';
  div.innerHTML = `
    <div class="name">${{s.setor}}</div>
    <div class="bar-track"><div class="bar-fill" style="width:${{(s.fat/maxFatSet*100).toFixed(1)}}%"></div></div>
    <div class="val">${{fmtR(s.fat)}}</div>
    <div class="l4w" style="color:${{l4wColor}}">${{l4wTxt}}</div>
  `;
  hbarsCont.appendChild(div);
}});

// ABA 3: Tornado chart (2026 vs 2025)
function renderTornado(modo) {{
  const wrap = document.getElementById('tornado-wrap');
  wrap.innerHTML = '';

  function buildTornado(setores, fatKeyA, fatKeyY, yoyKey, label_2025, label_2026) {{
    // Filtra setores que têm dado nos dois lados
    const valid = setores.filter(s => (s[fatKeyA] || 0) > 0 || (s[fatKeyY] || 0) > 0);
    // Ordenar por fat 2026 desc
    valid.sort((a,b) => (b[fatKeyA]||0) - (a[fatKeyA]||0));
    // Escala: maior valor entre 2025 e 2026 vira o 100%
    const maxVal = Math.max(...valid.map(s => Math.max(s[fatKeyA]||0, s[fatKeyY]||0)));

    let html = '<div class="tornado-header"><span class="h-left">2025</span><span class="h-mid">SETOR</span><span class="h-right">2026</span></div>';
    valid.forEach(s => {{
      const fa = s[fatKeyA] || 0;
      const fy = s[fatKeyY] || 0;
      const yoy = s[yoyKey];
      const wA = (fa / maxVal) * 100;
      const wY = (fy / maxVal) * 100;
      let cls26;
      if (yoy == null) cls26 = 'tornado-bar-2026-flat';
      else if (yoy >= 5) cls26 = 'tornado-bar-2026-up';
      else if (yoy <= -5) cls26 = 'tornado-bar-2026-down';
      else cls26 = 'tornado-bar-2026-flat';
      const yoyTxt = yoy==null ? '—' : fmtSignP(yoy);
      const yoyColor = yoy == null ? 'var(--ink-mute)' : (yoy >= 5 ? 'var(--verde)' : yoy <= -5 ? 'var(--vermelho)' : 'var(--amarelo)');
      // Apenas mostrar valor dentro da barra se > 30% pra não estourar
      const showValY = wY > 25;
      const showValA = wA > 25;
      html += `
        <div class="tornado-row">
          <div class="tornado-side-left">
            <div class="tornado-bar tornado-bar-2025" style="width:${{wY}}%">
              ${{showValY ? fmtR(fy) : ''}}
            </div>
          </div>
          <div class="tornado-center">
            <div>${{s.setor}}</div>
            <span class="yoy-pct" style="color:${{yoyColor}}">${{yoyTxt}}</span>
          </div>
          <div class="tornado-side-right">
            <div class="tornado-bar ${{cls26}}" style="width:${{wA}}%">
              ${{showValA ? fmtR(fa) : ''}}
            </div>
          </div>
        </div>`;
    }});
    return html;
  }}

  const setoresData = D.setores_expand.filter(s => s.setor !== 'SEM CLASSIFICAÇÃO');

  if (modo === '13sem') {{
    wrap.innerHTML = buildTornado(setoresData, 'fat_2026_13sem', 'fat_2025_13sem', 'yoy_13sem_pct', '2025', '2026');
  }} else if (modo === 's13') {{
    wrap.innerHTML = buildTornado(setoresData, 'fat_atual', 'fat_yoy', 'var_yoy_pct', '{kpis['sem_label_yoy']}', '{kpis['sem_label']}');
  }} else if (modo === 'duplo') {{
    wrap.innerHTML = `
      <div class="tornado-grid-duplo">
        <div>
          <h4>13 semanas focais (2026 vs 2025)</h4>
          ${{buildTornado(setoresData, 'fat_2026_13sem', 'fat_2025_13sem', 'yoy_13sem_pct', '2025', '2026')}}
        </div>
        <div>
          <h4>{kpis['sem_label']} isolada (vs {kpis['sem_label_yoy']})</h4>
          ${{buildTornado(setoresData, 'fat_atual', 'fat_yoy', 'var_yoy_pct', '{kpis['sem_label_short']}/{str(kpis['ano']-1)[2:]}', '{kpis['sem_label_short']}/{str(kpis['ano'])[2:]}')}}
        </div>
      </div>
    `;
  }}
}}
document.getElementById('sel-tornado-modo').addEventListener('change', e => renderTornado(e.target.value));
renderTornado('duplo');  // default duplo conforme escolha do usuário

// Cards por setor com sparkline YoY + toggle posicional/aligned
const cardsWrap = document.getElementById('cards-setor-wrap');
let sparkCharts = [];

function renderCardsSetor(modoYoY) {{
  // Limpar charts antigas
  sparkCharts.forEach(c => c.destroy());
  sparkCharts = [];
  cardsWrap.innerHTML = '';
  const cardsContainer = document.createElement('div');
  cardsContainer.className = 'cards-setor';
  cardsWrap.appendChild(cardsContainer);

  // Pra modo aligned, recalcular yoy_13sem_pct usando série aligned
  D.setor_yoy_sparkline.forEach((s, idx) => {{
    const serie = modoYoY === 'aligned' ? s.yoy_serie_aligned : s.yoy_serie;
    // YoY consolidado também muda quando aligned: média ponderada das séries
    let yoy;
    if (modoYoY === 'aligned') {{
      // Média simples das semanas (com peso, ideal, mas vamos simplificar)
      const valid = serie.filter(v => v !== null);
      if (valid.length > 0) {{
        yoy = valid.reduce((a,b) => a+b, 0) / valid.length;
      }} else yoy = null;
    }} else {{
      yoy = s.yoy_13sem_pct;
    }}

    let cls;
    if (yoy == null) cls = 'flat';
    else if (yoy >= 5) cls = 'up';
    else if (yoy <= -5) cls = 'down';
    else cls = 'flat';

    const card = document.createElement('div');
    card.className = 'card-setor ' + cls;
    const yoyTxt = yoy == null ? '—' : fmtSignP(yoy);

    card.innerHTML = `
      <h4>${{s.setor}}</h4>
      <div class="card-yoy ${{cls}}">${{yoyTxt}}</div>
      <div class="card-fats">
        2026: ${{fmtR(s.fat_2026_13sem)}}<br>
        2025: ${{fmtR(s.fat_2025_13sem)}}
      </div>
      <div class="card-spark"><canvas id="spark-${{idx}}"></canvas></div>
      <div class="card-spark-label">YoY % por semana ({kpis['sem_range_label']}) ${{modoYoY==='aligned'?'· alinhada':''}}</div>
    `;
    cardsContainer.appendChild(card);
  }});

  // Renderizar sparklines
  D.setor_yoy_sparkline.forEach((s, idx) => {{
    const serie = modoYoY === 'aligned' ? s.yoy_serie_aligned : s.yoy_serie;
    const ctxEl = document.getElementById('spark-' + idx);
    if (!ctxEl) return;
    const labels = D.semanas_info.map(x => x.label);
    const colors = serie.map(v => v == null ? '#ccc' : v >= 5 ? C.verdeAlert : v <= -5 ? C.vermelho : C.amarelo);
    const chart = new Chart(ctxEl, {{
      type: 'bar',
      data: {{
        labels,
        datasets: [{{
          data: serie,
          backgroundColor: colors,
          borderRadius: 2,
        }}]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
          legend: {{ display: false }},
          tooltip: {{
            callbacks: {{
              label: ctx => ' ' + (ctx.raw==null ? '—' : fmtSignP(ctx.raw))
            }}
          }}
        }},
        scales: {{
          x: {{ display: false, grid: {{ display: false }} }},
          y: {{ display: false, grid: {{ display: false }}, beginAtZero: true }}
        }}
      }}
    }});
    sparkCharts.push(chart);
  }});
}}

document.getElementById('sel-yoy-cards').addEventListener('change', e => {{
  renderCardsSetor(e.target.value);
}});
renderCardsSetor('posicional');

// ABA 3: Heatmap com toggle L4W/YoY
const hmWrap = document.getElementById('heatmap-wrap');
const semanas = D.semanas_info;

function cellColor(v) {{
  if (v==null) return '#f5f5f0';
  if (v >= 15)  return '#3f8654';
  if (v >= 5)   return '#7fb07d';
  if (v >= 0)   return '#c8dcc0';
  if (v > -5)   return '#f0e4c0';
  if (v > -15)  return '#e8b5a0';
  return '#b8362f';
}}
function cellTextColor(v) {{
  if (v==null) return '#8b8f86';
  if (v >= 15 || v <= -15) return '#fff';
  return '#1a1f1a';
}}

let heatmapModo = 'l4w';

function renderHeatmap() {{
  const dataset = heatmapModo === 'yoy' ? D.heatmap_yoy : D.heatmap_l4w;
  const sufixo = heatmapModo === 'yoy' ? '_yoy' : '_l4w';
  const idCampo = heatmapModo === 'yoy' ? 'sem_X_yoy' : 'sem_X_l4w';

  let tbl = '<table><thead><tr><th class="row-label">Setor</th>';
  semanas.forEach(s => tbl += `<th>${{s.label}}</th>`);
  tbl += '</tr></thead><tbody>';

  dataset.forEach(row => {{
    tbl += `<tr><th class="row-label">${{row.setor}}</th>`;
    semanas.forEach(s => {{
      let v;
      if (heatmapModo === 'yoy') {{
        // dataset yoy usa sem_id_focal (1-13)
        v = row['sem_' + s.sem_id + '_yoy'];
      }} else {{
        v = row['sem_' + s.sem_id + '_l4w'];
      }}
      const bg = cellColor(v);
      const fg = cellTextColor(v);
      const txt = v==null ? '—' : fmtSignP(v);
      tbl += `<td style="background:${{bg}};color:${{fg}}">${{txt}}</td>`;
    }});
    tbl += '</tr>';
  }});
  tbl += '</tbody></table>';
  hmWrap.innerHTML = tbl;

  document.getElementById('hm-modo-label').textContent = heatmapModo === 'yoy' ? 'vs YoY (mesma semana 2025)' : 'vs L4W';
}}
document.getElementById('sel-heatmap-modo').addEventListener('change', e => {{
  heatmapModo = e.target.value;
  renderHeatmap();
}});
renderHeatmap();

// ABA 3: Tabela setores — versão expandida com LW, L4W, L8W, YoY S13 e YoY 13sem
const tbSet = document.querySelector('#tab-setores-full tbody');
const set_map_share = {{}};
D.setores.forEach(s => {{
  set_map_share[s.setor] = {{
    share: s.share, cupons: s.cupons, ticket_medio: s.ticket_medio,
    presenca_cupom: s.presenca_cupom
  }};
}});
function colorPct(v) {{
  if (v == null) return 'var(--ink-mute)';
  if (v >= 10)  return 'var(--verde)';
  if (v >= 3)   return 'var(--verde)';
  if (v > -3)   return 'var(--ink-dim)';
  if (v > -10)  return 'var(--amarelo)';
  return 'var(--vermelho)';
}}
D.setores_expand.forEach(s => {{
  const extra = set_map_share[s.setor] || {{}};
  const tr = document.createElement('tr');
  const rsSignal = rs => rs==null ? '—' : (rs>=0?'+':'') + fmtR(rs);
  tr.innerHTML = `
    <td><strong>${{s.setor}}</strong></td>
    <td class="num">${{fmtR(s.fat_atual)}}</td>
    <td class="num" style="color:${{colorPct(s.var_lw_pct)}};font-weight:700">${{fmtSignP(s.var_lw_pct)}}</td>
    <td class="num" style="color:${{colorPct(s.var_l4w_pct)}};font-weight:700">${{fmtSignP(s.var_l4w_pct)}}</td>
    <td class="num" style="color:${{colorPct(s.var_l8w_pct)}};font-weight:700">${{fmtSignP(s.var_l8w_pct)}}</td>
    <td class="num" style="color:${{colorPct(s.var_yoy_pct)}};font-weight:700">${{fmtSignP(s.var_yoy_pct)}}</td>
    <td class="num" style="color:${{colorPct(s.yoy_13sem_pct)}};font-weight:700;border-left:2px solid var(--gran-dourado);padding-left:10px">${{fmtSignP(s.yoy_13sem_pct)}}</td>
    <td class="num" style="color:${{colorPct(s.yoy_13sem_pct)}};font-size:12px">${{rsSignal(s.yoy_13sem_rs)}}</td>
    <td class="num">${{fmtP(extra.share||0)}}</td>
  `;
  tbSet.appendChild(tr);
}});

// ABA 4: Top 30 SKUs da loja (v12.7: + YoY fat e YoY qtd)
const tbTop30 = document.querySelector('#tab-top30-loja tbody');
D.top30_loja.forEach((s, i) => {{
  const kviTag = s.KVI && s.KVI !== '-' ? `<span class="tag ${{s.KVI==='KVI+'?'kvi-plus':s.KVI==='KVI'?'kvi':'att'}}">${{s.KVI}}</span>` : '';
  const curvaTag = s.CURVA && s.CURVA !== '-' ? `<span class="tag ${{s.CURVA==='A*'?'A-star':'curva'}}">${{s.CURVA}}</span>` : '';
  const tr = document.createElement('tr');
  tr.innerHTML = `
    <td class="num">${{i+1}}</td>
    <td><code style="font-size:11px;color:var(--ink-dim)">${{s.cod||'—'}}</code></td>
    <td>${{s.desc}}</td>
    <td style="font-size:11px;color:var(--ink-dim)">${{s.setor}}</td>
    <td>${{kviTag}}</td>
    <td>${{curvaTag}}</td>
    <td class="num">${{fmtR(s.fat)}}</td>
    <td class="num" style="color:${{colorPct(s.var_lw_pct)}};font-weight:700">${{fmtSignP(s.var_lw_pct)}}</td>
    <td class="num" style="color:${{colorPct(s.var_l4w_pct)}};font-weight:700">${{fmtSignP(s.var_l4w_pct)}}</td>
    <td class="num" style="color:${{colorPct(s.var_l8w_pct)}};font-weight:700">${{fmtSignP(s.var_l8w_pct)}}</td>
    <td class="num" style="color:${{colorPct(s.var_yoy_fat_pct)}};font-weight:700;border-left:2px solid var(--gran-dourado);padding-left:8px" title="comparado a S${{(D.kpis_macro.sem_gran_no_ano-1)||'?'}}/2025">${{fmtSignP(s.var_yoy_fat_pct)}}</td>
    <td class="num" style="color:${{colorPct(s.var_yoy_qtd_pct)}};font-weight:700" title="qtd vs mesma sem 2025">${{fmtSignP(s.var_yoy_qtd_pct)}}</td>
    <td class="num">${{fmtN(s.qtd)}}</td>
    <td class="num">${{fmtR2(s.preco_medio)}}</td>
  `;
  tbTop30.appendChild(tr);
}});

// ABA 4: Raio-X por setor
const selSetor = document.getElementById('sel-setor');

// ABA 4: Linha do tempo do SKU (qualquer do Top 30 loja)
const selSkuSerie = document.getElementById('sel-sku-serie');
const semanasLabels = D.semanas_info.map(s => s.label);
const semanasPeriodos = D.semanas_info.map(s => s.periodo);

Object.keys(D.serie_top30).forEach(cod => {{
  const info = D.serie_top30[cod].info;
  const opt = document.createElement('option');
  opt.value = cod;
  opt.textContent = info.desc + '  (' + info.setor + ')';
  selSkuSerie.appendChild(opt);
}});

let skuSerieChart = null;
let skuSerieModo = 'qtd';  // ou 'fat'
let skuSerieCodAtual = null;

function renderSkuSerie(cod) {{
  skuSerieCodAtual = cod;
  const entry = D.serie_top30[cod];
  if (!entry) return;
  const info = entry.info;
  const series = entry.series;

  // Arrays 13 semanas
  const semIds = D.semanas_info.map(s => s.sem_id);
  const precos = semIds.map(sid => series[sid] ? series[sid].preco_medio : null);
  const qtds   = semIds.map(sid => series[sid] ? series[sid].qtd : null);
  const fats   = semIds.map(sid => series[sid] ? series[sid].fat : null);
  // v12.7: série YoY (mesma semana ano anterior)
  const fatsYoY = semIds.map(sid => series[sid] && series[sid].fat_yoy != null ? series[sid].fat_yoy : null);
  const qtdsYoY = semIds.map(sid => series[sid] && series[sid].qtd_yoy != null ? series[sid].qtd_yoy : null);
  const precosYoY = semIds.map(sid => series[sid] && series[sid].preco_medio_yoy != null ? series[sid].preco_medio_yoy : null);

  // Meta info
  const kviTag = info.KVI && info.KVI !== '-' ? ` <span class="tag ${{info.KVI==='KVI+'?'kvi-plus':info.KVI==='KVI'?'kvi':'att'}}">${{info.KVI}}</span>` : '';
  const curvaTag = info.CURVA && info.CURVA !== '-' ? ` <span class="tag ${{info.CURVA==='A*'?'A-star':'curva'}}">${{info.CURVA}}</span>` : '';
  document.getElementById('sku-serie-meta').innerHTML = `<strong>${{info.desc}}</strong> · ${{info.setor}}${{kviTag}}${{curvaTag}} · cód <code style="font-size:11px">${{cod}}</code>`;

  // Dados conforme modo
  const modo = skuSerieModo;
  const barData  = modo === 'qtd' ? qtds : fats;
  const barDataYoY = modo === 'qtd' ? qtdsYoY : fatsYoY;
  const barLabel = modo === 'qtd' ? 'Quantidade vendida (2026)' : 'Faturamento 2026 (R$)';
  const barLabelYoY = modo === 'qtd' ? 'Quantidade vendida (2025)' : 'Faturamento 2025 (R$)';
  const barAxisTitle = modo === 'qtd' ? 'Quantidade' : 'Faturamento (R$)';
  const barTickCb = modo === 'qtd' ? (v => fmtN(v)) : (v => fmtR(v));
  const barTooltipFmt = modo === 'qtd'
    ? (raw, i) => ' Qtd 2026: ' + (raw==null ? '—' : fmtN(raw)) + '  |  Qtd 2025: ' + (qtdsYoY[i]==null ? '—' : fmtN(qtdsYoY[i])) + '  |  Fat: ' + (fats[i]==null ? '—' : fmtR(fats[i]))
    : (raw, i) => ' Fat 2026: ' + (raw==null ? '—' : fmtR(raw)) + '  |  Fat 2025: ' + (fatsYoY[i]==null ? '—' : fmtR(fatsYoY[i])) + '  |  Qtd: ' + (qtds[i]==null ? '—' : fmtN(qtds[i]));

  if (skuSerieChart) skuSerieChart.destroy();
  skuSerieChart = new Chart(document.getElementById('chart-sku-serie'), {{
    type: 'bar',
    data: {{
      labels: semanasLabels,
      datasets: [
        {{
          type: 'bar',
          label: barLabel,
          data: barData,
          backgroundColor: C.verde,
          hoverBackgroundColor: C.verde2,
          borderRadius: 4,
          yAxisID: 'yBar',
          order: 3,
        }},
        // v12.7: série YoY (2025) sobreposta
        {{
          type: 'bar',
          label: barLabelYoY,
          data: barDataYoY,
          backgroundColor: '#5b8fb822',
          borderColor: '#5b8fb8',
          borderWidth: 1.5,
          borderRadius: 4,
          yAxisID: 'yBar',
          order: 2,
        }},
        {{
          type: 'line',
          label: 'Preço médio 2026 (R$)',
          data: precos,
          borderColor: C.dourado,
          backgroundColor: 'transparent',
          borderWidth: 3,
          pointRadius: 6,
          pointBackgroundColor: C.dourado,
          pointBorderColor: '#fff',
          pointBorderWidth: 2,
          tension: 0.3,
          yAxisID: 'yPreco',
          order: 1,
        }},
        {{
          type: 'line',
          label: 'Preço médio 2025 (R$)',
          data: precosYoY,
          borderColor: '#999',
          borderDash: [4, 3],
          backgroundColor: 'transparent',
          borderWidth: 2,
          pointRadius: 3,
          pointBackgroundColor: '#999',
          tension: 0.3,
          yAxisID: 'yPreco',
          order: 0,
        }}
      ]
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      plugins: {{
        legend: {{ position: 'top' }},
        tooltip: {{
          callbacks: {{
            title: ctx => {{
              const i = ctx[0].dataIndex;
              return semanasLabels[i] + ' · ' + semanasPeriodos[i];
            }},
            label: ctx => {{
              const i = ctx.dataIndex;
              if (ctx.dataset.type === 'line') {{
                return ' Preço médio: ' + (ctx.raw==null ? '—' : fmtR2(ctx.raw));
              }} else {{
                return barTooltipFmt(ctx.raw, i);
              }}
            }}
          }}
        }}
      }},
      scales: {{
        x: {{ grid: {{ display: false }} }},
        yBar: {{
          type: 'linear', position: 'left',
          title: {{ display: true, text: barAxisTitle, color: C.verde, font: {{ weight: 600 }} }},
          grid: {{ color: C.border }},
          beginAtZero: true,
          ticks: {{ callback: barTickCb }},
        }},
        yPreco: {{
          type: 'linear', position: 'right',
          title: {{ display: true, text: 'Preço médio (R$)', color: C.dourado, font: {{ weight: 600 }} }},
          grid: {{ display: false }},
          ticks: {{ callback: v => fmtR2(v) }},
        }}
      }}
    }}
  }});
}}
selSkuSerie.addEventListener('change', e => renderSkuSerie(e.target.value));
document.getElementById('sel-sku-modo').addEventListener('change', e => {{
  skuSerieModo = e.target.value;
  if (skuSerieCodAtual) renderSkuSerie(skuSerieCodAtual);
}});
if (Object.keys(D.serie_top30).length > 0) {{
  renderSkuSerie(Object.keys(D.serie_top30)[0]);
}}
Object.keys(D.sku_por_setor).forEach(s => {{
  const opt = document.createElement('option');
  opt.value = s; opt.textContent = s;
  selSetor.appendChild(opt);
}});
function renderSkus(setor) {{
  const tb = document.querySelector('#tab-skus tbody');
  tb.innerHTML = '';
  (D.sku_por_setor[setor] || []).forEach((s, i) => {{
    const kviTag = s.KVI && s.KVI !== '-' ? `<span class="tag ${{s.KVI==='KVI+'?'kvi-plus':s.KVI==='KVI'?'kvi':'att'}}">${{s.KVI}}</span>` : '';
    const curvaTag = s.CURVA && s.CURVA !== '-' ? `<span class="tag ${{s.CURVA==='A*'?'A-star':'curva'}}">${{s.CURVA}}</span>` : '';
    const tr = document.createElement('tr');
    // v12.7: comparadores LW/L4W/L8W/YoY (mesmo padrão da top30 loja)
    tr.innerHTML = `
      <td class="num">${{i+1}}</td>
      <td><code style="font-size:11px;color:var(--ink-dim)">${{s.cod||'—'}}</code></td>
      <td>${{s.desc}}</td>
      <td>${{kviTag}}</td>
      <td>${{curvaTag}}</td>
      <td class="num">${{fmtR(s.fat)}}</td>
      <td class="num" style="color:${{colorPct(s.var_lw_pct)}};font-weight:700">${{fmtSignP(s.var_lw_pct)}}</td>
      <td class="num" style="color:${{colorPct(s.var_l4w_pct)}};font-weight:700">${{fmtSignP(s.var_l4w_pct)}}</td>
      <td class="num" style="color:${{colorPct(s.var_l8w_pct)}};font-weight:700">${{fmtSignP(s.var_l8w_pct)}}</td>
      <td class="num" style="color:${{colorPct(s.var_yoy_fat_pct)}};font-weight:700;border-left:2px solid var(--gran-dourado);padding-left:8px" title="vs mesma sem 2025">${{fmtSignP(s.var_yoy_fat_pct)}}</td>
      <td class="num" style="color:${{colorPct(s.var_yoy_qtd_pct)}};font-weight:700" title="qtd vs mesma sem 2025">${{fmtSignP(s.var_yoy_qtd_pct)}}</td>
      <td class="num">${{fmtN(s.qtd)}}</td>
      <td class="num">${{fmtN(s.cupons)}}</td>
      <td class="num">${{fmtR2(s.preco_medio)}}</td>
    `;
    tb.appendChild(tr);
  }});
}}
selSetor.addEventListener('change', e => renderSkus(e.target.value));
renderSkus(Object.keys(D.sku_por_setor)[0]);

// ABA 5: Ruptura recorrente
function renderRuptRec(tbId, items) {{
  const tb = document.getElementById(tbId);
  if (items.length === 0) {{
    tb.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--verde);padding:20px;font-weight:600;">✓ Nenhuma ruptura recorrente detectada.</td></tr>';
    return;
  }}
  items.forEach(x => {{
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><code style="font-size:11px;color:var(--ink-dim)">${{x.cod}}</code></td>
      <td>${{x.desc}}</td>
      <td>${{(x.departamento||'').split('/')[0].trim()}}</td>
      <td class="num" style="color:var(--vermelho);font-weight:700">${{x.sem_venda_em}}/6</td>
    `;
    tb.appendChild(tr);
  }});
}}
renderRuptRec('tb-rupt-rec-kviplus', D.ruptura_recorrente_kvi_plus);
renderRuptRec('tb-rupt-rec-kvi',     D.ruptura_recorrente_kvi);

function renderNunca(tbId, items) {{
  const tb = document.getElementById(tbId);
  if (items.length === 0) {{
    tb.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--verde);padding:20px;font-weight:600;">✓ Todos venderam em pelo menos 1 das últimas 6 semanas.</td></tr>';
    return;
  }}
  items.forEach(x => {{
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><code style="font-size:11px;color:var(--ink-dim)">${{x.cod}}</code></td>
      <td>${{x.desc}}</td>
      <td>${{(x.departamento||'').split('/')[0].trim()}}</td>
      <td class="num">${{fmtR2(x.preco_atual)}}</td>
    `;
    tb.appendChild(tr);
  }});
}}
renderNunca('tb-nunca-kviplus', D.nunca_venderam_kvi_plus);
renderNunca('tb-nunca-kvi',     D.nunca_venderam_kvi);

// ABA 6: KVIs com comparadores LW, L4W, L8W
function renderKvisExpand(tbId, items) {{
  const tb = document.getElementById(tbId);
  items.forEach((s, i) => {{
    const curvaTag = s.CURVA && s.CURVA !== '-' ? `<span class="tag ${{s.CURVA==='A*'?'A-star':'curva'}}">${{s.CURVA}}</span>` : '';
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td class="num">${{i+1}}</td>
      <td><code style="font-size:11px;color:var(--ink-dim)">${{s.cod}}</code></td>
      <td>${{s.desc}}</td>
      <td style="font-size:11px;color:var(--ink-dim)">${{s.setor}}</td>
      <td>${{curvaTag}}</td>
      <td class="num">${{fmtR(s.fat_atual)}}</td>
      <td class="num" style="color:${{colorPct(s.var_lw_pct)}};font-weight:700">${{fmtSignP(s.var_lw_pct)}}</td>
      <td class="num" style="color:${{colorPct(s.var_l4w_pct)}};font-weight:700">${{fmtSignP(s.var_l4w_pct)}}</td>
      <td class="num" style="color:${{colorPct(s.var_l8w_pct)}};font-weight:700">${{fmtSignP(s.var_l8w_pct)}}</td>
      <td class="num">${{fmtP(s.presenca||0)}}</td>
      <td class="num">${{fmtR2(s.preco_medio||0)}}</td>
    `;
    tb.appendChild(tr);
  }});
}}
renderKvisExpand('tb-kvisplus', D.kvi_plus_expand);
renderKvisExpand('tb-kvis',     D.kvi_norm_expand);

// ABA 7: Elasticidade
function classElast(c) {{
  if (c === 'Alta elasticidade')    return 'elast-alta';
  if (c === 'Média elasticidade')   return 'elast-media';
  if (c === 'Baixa elasticidade')   return 'elast-baixa';
  if (c === 'Atípico (preço↑ → qtd↑)') return 'elast-atipico';
  return 'elast-sem';
}}

// Top 10 baixa elasticidade (correlação alta positiva ou perto de zero, desde que tenha variação)
const elastComVar = D.elasticidade.filter(e => e.classificacao !== 'Sem variação de preço' && e.corr !== null);
const elastBaixaOrdem = elastComVar.filter(e => e.classificacao === 'Baixa elasticidade' || e.classificacao === 'Atípico (preço↑ → qtd↑)').sort((a,b) => b.corr - a.corr).slice(0,10);
const elastAltaOrdem = elastComVar.filter(e => e.classificacao === 'Alta elasticidade').sort((a,b) => a.corr - b.corr).slice(0,10);

function renderElastTopo(tbId, items) {{
  const tb = document.getElementById(tbId);
  if (items.length === 0) {{
    tb.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--ink-mute);padding:20px;">Sem SKUs nesta classificação ainda.</td></tr>';
    return;
  }}
  items.forEach(x => {{
    const cls = classElast(x.classificacao);
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><code style="font-size:11px;color:var(--ink-dim)">${{x.cod}}</code></td>
      <td>${{x.desc}}</td>
      <td>${{x.setor}}</td>
      <td><span class="tag ${{cls}}">${{x.classificacao}}</span></td>
      <td class="num">${{x.corr==null?'—':x.corr.toFixed(2)}}</td>
    `;
    tb.appendChild(tr);
  }});
}}
renderElastTopo('tb-elast-baixa', elastBaixaOrdem);
renderElastTopo('tb-elast-alta',  elastAltaOrdem);

function renderElastFull(filtro) {{
  const tb = document.getElementById('tb-elast-full');
  tb.innerHTML = '';
  let list = D.elasticidade;
  if (filtro !== 'all') list = list.filter(e => e.classificacao === filtro);
  list.forEach(x => {{
    const cls = classElast(x.classificacao);
    const kviTag = x.kvi && x.kvi !== '-' ? `<span class="tag ${{x.kvi==='KVI+'?'kvi-plus':'kvi'}}">${{x.kvi}}</span>` : '';
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><code style="font-size:11px;color:var(--ink-dim)">${{x.cod}}</code></td>
      <td>${{x.desc}}</td>
      <td>${{x.setor}}</td>
      <td>${{kviTag}}</td>
      <td class="num">${{fmtR2(x.preco_medio)}}</td>
      <td class="num">${{x.preco_range_pct.toFixed(1)}}%</td>
      <td class="num">${{x.corr==null?'—':x.corr.toFixed(2)}}</td>
      <td><span class="tag ${{cls}}">${{x.classificacao}}</span></td>
    `;
    tb.appendChild(tr);
  }});
}}
document.getElementById('sel-elast').addEventListener('change', e => renderElastFull(e.target.value));
renderElastFull('all');

// ABA 8: Ofertas com dois lifts (L4W + intra-semana)
const ofCont = document.getElementById('ofertas-lista');
D.ofertas_full.forEach(o => {{
  const liftL4W   = o.lift_l4w;
  const liftIntra = o.lift_intra;
  // Status: verde só se AMBOS positivos e >=15%; vermelho se ambos negativos; amarelo misto/baixo
  let cls, descStatus;
  if (liftL4W == null && liftIntra == null) {{ cls = 'nulo'; descStatus = 'Sem baseline'; }}
  else if ((liftL4W||-999) >= 15 && (liftIntra||-999) >= 15) {{ cls = 'pegou'; descStatus = 'Oferta pegou nos 2 ângulos'; }}
  else if ((liftL4W||999) < 0 && (liftIntra||999) < 0) {{ cls = 'nao-pegou'; descStatus = 'Oferta não pegou'; }}
  else {{ cls = 'nao-pegou'; descStatus = 'Oferta parcial'; }}
  const liftCls = v => v==null ? 'nulo' : (v>=15 ? 'pos' : 'neg');
  const liftTxt = v => v==null ? '—' : ((v>=15 ? '✓ ' : '! ') + fmtSignP(v));
  const div = document.createElement('div');
  div.className = 'oferta-card ' + cls;
  div.innerHTML = `
    <div class="oferta-dia">
      <span class="dia">${{o.dia_pt}}</span>
      <span class="data">${{o.data_br}}</span>
    </div>
    <div class="oferta-alvo">
      <span class="label">Alvo da oferta</span>
      ${{o.alvo}}
      <div style="font-size:11px;color:var(--ink-mute);margin-top:4px">${{descStatus}}</div>
    </div>
    <div class="oferta-metricas">
      <div class="metric"><div class="v">${{fmtR(o.fat_dia)}}</div><div class="l">Fat dia</div></div>
      <div class="metric"><div class="v">${{fmtR(o.fat_base_l4w)}}</div><div class="l">Baseline L4W (${{o.n_weeks_base}} sem)</div></div>
      <div class="lift ${{liftCls(liftL4W)}}" title="Lift vs mesmo dia-da-semana em L4W">${{liftTxt(liftL4W)}}<div style="font-size:9px;font-weight:400;opacity:0.8;margin-top:2px">vs L4W</div></div>
      <div class="metric"><div class="v">${{fmtR(o.fat_base_intra)}}</div><div class="l">Baseline outros dias</div></div>
      <div class="lift ${{liftCls(liftIntra)}}" title="Lift vs média dos outros dias da mesma semana">${{liftTxt(liftIntra)}}<div style="font-size:9px;font-weight:400;opacity:0.8;margin-top:2px">vs intra-sem</div></div>
    </div>
  `;
  ofCont.appendChild(div);
}});

// ABA 8: Cash&Carry
const ccResumo = D.cash_carry_resumo;
const ccCont = document.getElementById('cc-resumo');
const liftStr = ccResumo.lift_total==null ? '—' : fmtSignP(ccResumo.lift_total);
const liftCls = ccResumo.lift_total==null ? '' : (ccResumo.lift_total >= 15 ? 'pos' : ccResumo.lift_total < 0 ? 'neg' : '');
const incrStr = (ccResumo.total_incremental>=0 ? '+' : '') + fmtR(ccResumo.total_incremental);
const incrCls = ccResumo.total_incremental>=0 ? 'pos' : 'neg';
ccCont.innerHTML = `
  <div class="box"><div class="l">Fat promo S${{D.kpis_macro.n_sem}}</div><div class="v">${{fmtR(ccResumo.total_promo)}}</div></div>
  <div class="box"><div class="l">Baseline L4W</div><div class="v">${{fmtR(ccResumo.total_baseline)}}</div></div>
  <div class="box"><div class="l">Incremental</div><div class="v ${{incrCls}}">${{incrStr}}</div></div>
  <div class="box"><div class="l">Lift total</div><div class="v ${{liftCls}}">${{liftStr}}</div></div>
  <div class="box"><div class="l">SKUs que pegaram</div><div class="v">${{ccResumo.n_pegou}}/${{ccResumo.n_itens}}</div></div>
  <div class="box"><div class="l">SKUs que não pegaram</div><div class="v ${{ccResumo.n_nao_pegou>0?'neg':''}}">${{ccResumo.n_nao_pegou}}/${{ccResumo.n_itens}}</div></div>
`;

const tbCC = document.getElementById('tb-cc');
D.cash_carry_itens.forEach(it => {{
  const liftCell = it.lift_fat==null ? '—' : fmtSignP(it.lift_fat);
  const liftColor = colorPct(it.lift_fat);
  const deltaStr = (it.fat_incremental>=0 ? '+' : '') + fmtR(it.fat_incremental);
  const deltaColor = it.fat_incremental>=0 ? 'var(--verde)' : 'var(--vermelho)';
  const tr = document.createElement('tr');
  tr.innerHTML = `
    <td><code style="font-size:11px;color:var(--ink-dim)">${{it.cod}}</code></td>
    <td>${{it.desc}}</td>
    <td class="num">${{fmtR2(it.fat_promo)}}</td>
    <td class="num">${{fmtR2(it.fat_baseline_l4w)}}</td>
    <td class="num" style="color:${{deltaColor}};font-weight:700">${{deltaStr}}</td>
    <td class="num" style="color:${{liftColor}};font-weight:700">${{liftCell}}</td>
    <td class="num">${{fmtN(it.qtd_promo)}}</td>
    <td class="num">${{fmtN(it.cupons_leve3)}}</td>
    <td class="num">${{fmtN(it.cupons_promo)}}</td>
    <td class="num">${{it.preco_medio>0 ? fmtR2(it.preco_medio) : '—'}}</td>
  `;
  tbCC.appendChild(tr);
}});
// ABA 10: Sazonalidade YoY
const kpis_d = D.kpis_macro;

// KPI YoY semana
const yoy_sem_el = document.getElementById('kpi-yoy-sem');
const yoy_sem_detail = document.getElementById('kpi-yoy-sem-detail');
if (kpis_d.fat_yoy_pct !== null && kpis_d.fat_yoy_pct !== undefined) {{
  const pct = kpis_d.fat_yoy_pct;
  const col = pct >= 5 ? 'var(--verde)' : pct <= -5 ? 'var(--vermelho)' : 'var(--amarelo)';
  yoy_sem_el.innerHTML = `<span style="color:${{col}}">${{fmtSignP(pct)}}</span>`;
  yoy_sem_detail.textContent = `R$ ${{fmtR(kpis_d.fat_total).replace('R$ ','')}} · {kpis['sem_label_yoy']} era R$ ${{fmtR(kpis_d.fat_yoy_valor).replace('R$ ','')}}`;
}}

// KPI YoY mês
const yoy_mes_el = document.getElementById('kpi-yoy-mes');
const yoy_mes_detail = document.getElementById('kpi-yoy-mes-detail');
if (kpis_d.mes_yoy_pct !== null && kpis_d.mes_yoy_pct !== undefined) {{
  const pct = kpis_d.mes_yoy_pct;
  const col = pct >= 5 ? 'var(--verde)' : pct <= -5 ? 'var(--vermelho)' : 'var(--amarelo)';
  yoy_mes_el.innerHTML = `<span style="color:${{col}}">${{fmtSignP(pct)}}</span>`;
  yoy_mes_detail.textContent = `Variação: ${{fmtR(kpis_d.mes_yoy_rs)}} (parcial 1-21 abril)`;
}}

// KPI YoY 13 sem (NOVO destaque)
const yoy13 = D.yoy_13sem_total;
if (yoy13) {{
  const yoy13_el = document.getElementById('kpi-yoy-13sem');
  const yoy13_detail = document.getElementById('kpi-yoy-13sem-detail');
  const pct = yoy13.yoy_pct;
  // KPI big tem fundo verde, o destaque vai por intensidade
  let txt;
  if (pct >= 5) txt = `✓ ${{fmtSignP(pct)}}`;
  else if (pct <= -5) txt = `✕ ${{fmtSignP(pct)}}`;
  else txt = fmtSignP(pct);
  yoy13_el.textContent = txt;
  yoy13_detail.textContent = `2026: ${{fmtR(yoy13.fat_2026)}} · 2025: ${{fmtR(yoy13.fat_2025)}} · Δ: ${{(yoy13.yoy_rs>=0?'+':'') + fmtR(yoy13.yoy_rs)}}`;
}}

// Gráfico YoY semanal
const yoy_sem = D.yoy_por_semana;
new Chart(document.getElementById('chart-yoy-semanal'), {{
  type: 'bar',
  data: {{
    labels: yoy_sem.map(s => s.sem_label),
    datasets: [{{
      label: 'YoY %',
      data: yoy_sem.map(s => s.yoy_pct),
      backgroundColor: yoy_sem.map(s => s.yoy_pct >= 5 ? C.verdeAlert : s.yoy_pct >= 0 ? '#7fb07d' : s.yoy_pct >= -10 ? C.amarelo : C.vermelho),
      borderRadius: 4,
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{
      legend: {{ display: false }},
      tooltip: {{
        callbacks: {{
          title: ctx => yoy_sem[ctx[0].dataIndex].sem_label + ' · ' + yoy_sem[ctx[0].dataIndex].periodo_2026,
          label: ctx => {{
            const s = yoy_sem[ctx.dataIndex];
            return [
              ' YoY: ' + fmtSignP(s.yoy_pct),
              ' 2026: ' + fmtR(s.fat_2026),
              ' 2025: ' + fmtR(s.fat_2025) + ' (' + s.periodo_2025 + ')',
              ' Δ: ' + (s.yoy_rs>=0?'+':'') + fmtR(s.yoy_rs),
            ];
          }}
        }}
      }}
    }},
    scales: {{
      y: {{ ticks: {{ callback: v => v + '%' }}, grid: {{ color: C.border }} }},
      x: {{ grid: {{ display: false }} }}
    }}
  }}
}});

// Chart Sazonalidade mensal
const sazon = D.sazonalidade;
new Chart(document.getElementById('chart-sazonalidade'), {{
  type: 'line',
  data: {{
    labels: sazon.map(s => s.mes),
    datasets: [
      {{
        label: '2025',
        data: sazon.map(s => s.fat_2025),
        borderColor: '#5b8fb8',
        backgroundColor: '#5b8fb822',
        borderWidth: 3,
        pointRadius: 5,
        pointBackgroundColor: '#5b8fb8',
        pointBorderColor: '#fff',
        pointBorderWidth: 2,
        tension: 0.3,
        fill: false,
        spanGaps: true,
      }},
      {{
        label: '2026',
        data: sazon.map(s => s.fat_2026),
        borderColor: C.dourado,
        backgroundColor: C.dourado + '22',
        borderWidth: 3,
        pointRadius: 5,
        pointBackgroundColor: C.dourado,
        pointBorderColor: '#fff',
        pointBorderWidth: 2,
        tension: 0.3,
        fill: false,
        spanGaps: true,
      }}
    ]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{
      legend: {{ position: 'top' }},
      tooltip: {{
        callbacks: {{
          label: ctx => ' ' + ctx.dataset.label + ': ' + (ctx.raw==null ? '—' : fmtR(ctx.raw))
        }}
      }}
    }},
    scales: {{
      y: {{ ticks: {{ callback: v => fmtR(v) }}, grid: {{ color: C.border }} }},
      x: {{ grid: {{ display: false }} }}
    }}
  }}
}});

// Tabela Sazonalidade
const tbSazon = document.querySelector('#tabela-sazonalidade tbody');
sazon.forEach(s => {{
  const delta = (s.fat_2025 != null && s.fat_2026 != null) ? (s.fat_2026 - s.fat_2025) : null;
  const yoy = s.yoy_pct;
  const colYoY = yoy == null ? 'var(--ink-mute)' : (yoy >= 5 ? 'var(--verde)' : yoy <= -5 ? 'var(--vermelho)' : 'var(--amarelo)');
  const tr = document.createElement('tr');
  tr.innerHTML = `
    <td><strong>${{s.mes}}</strong></td>
    <td class="num">${{s.fat_2025==null ? '—' : fmtR(s.fat_2025)}}</td>
    <td class="num">${{s.fat_2026==null ? '—' : fmtR(s.fat_2026)}}</td>
    <td class="num">${{delta==null ? '—' : (delta>=0?'+':'') + fmtR(delta)}}</td>
    <td class="num" style="color:${{colYoY}};font-weight:700">${{yoy==null ? '—' : fmtSignP(yoy)}}</td>
  `;
  tbSazon.appendChild(tr);
}});

// Chart Setor YoY
const setoresYoY = D.setores_expand.filter(s => s.var_yoy_pct != null).slice(0, 12);
new Chart(document.getElementById('chart-setor-yoy'), {{
  type: 'bar',
  data: {{
    labels: setoresYoY.map(s => s.setor.length > 25 ? s.setor.substring(0,25)+'…' : s.setor),
    datasets: [{{
      label: 'YoY %',
      data: setoresYoY.map(s => s.var_yoy_pct),
      backgroundColor: setoresYoY.map(s => s.var_yoy_pct >= 5 ? C.verdeAlert : s.var_yoy_pct <= -10 ? C.vermelho : s.var_yoy_pct <= -3 ? C.amarelo : C.inkDim),
      borderRadius: 4,
    }}]
  }},
  options: {{
    indexAxis: 'y',
    responsive: true,
    maintainAspectRatio: false,
    plugins: {{
      legend: {{ display: false }},
      tooltip: {{
        callbacks: {{
          label: ctx => {{
            const s = setoresYoY[ctx.dataIndex];
            return [
              ' YoY: ' + fmtSignP(s.var_yoy_pct),
              ' Atual: ' + fmtR(s.fat_atual),
              ' 2025: ' + fmtR(s.fat_yoy),
              ' Δ: ' + (s.var_yoy_rs>=0?'+':'') + fmtR(s.var_yoy_rs),
            ];
          }}
        }}
      }}
    }},
    scales: {{
      x: {{ ticks: {{ callback: v => v + '%' }}, grid: {{ color: C.border }} }},
      y: {{ grid: {{ display: false }} }}
    }}
  }}
}});

// ABA 9: Alertas
const alList = document.getElementById('alertas-list');
const ord = {{ vermelho: 0, amarelo: 1, verde: 2 }};
const sorted = [...D.alertas_v2].sort((a,b) => ord[a.cor] - ord[b.cor]);
sorted.forEach(a => {{
  const div = document.createElement('div');
  div.className = 'alert ' + a.cor;
  div.innerHTML = `
    <div class="alert-icon">${{a.icone}}</div>
    <div>
      <div class="alert-title">${{a.titulo}}</div>
      <div class="alert-text">${{a.texto}}</div>
    </div>
  `;
  alList.appendChild(div);
}});

// Exceções
const tbEx = document.getElementById('tb-excecoes');
D.excecoes.forEach(e => {{
  const tr = document.createElement('tr');
  tr.innerHTML = `<td>${{e.DESCRICAO}}</td><td class="num">${{e.linhas}}</td><td class="num">${{fmtR2(e.fat)}}</td>`;
  tbEx.appendChild(tr);
}});
</script>
</body>
</html>
"""

# sem_label pode conter '/' (ex: 'S17/2026') que não é safe pra path
sem_label_file = str(kpis['sem_label']).replace('/', '_').replace(' ', '_')
out_path = RELATORIOS / f"Survey_Gran_{sem_label_file}_v12.html"
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"HTML gerado: {out_path}")
print(f"Tamanho: {out_path.stat().st_size / 1024:.1f} KB")

# v0.12.8: smoke test pós-build (impede regressão tipo fmtBRL)
try:
    import subprocess as _sp
    from pathlib import Path as _P
    _validate = _P(__file__).parent / 'validate_publicado.py'
    if _validate.exists():
        print()
        _r = _sp.run(['python3', str(_validate), str(out_path)], capture_output=True, text=True)
        print(_r.stdout, end='')
        if _r.returncode != 0:
            print(_r.stderr, end='')
            print("⛔ Build gerado MAS smoke test FALHOU. NÃO publique sem corrigir.")
except Exception as _e:
    print(f"⚠️  Smoke test não rodou: {_e}")


# v12.7: main() para compatibilidade de chamada uniforme (import + sys.exit(main()))
# A geração já aconteceu em import-time; main() apenas confirma sucesso.
def main():
    """Compat: a geração roda no import. main() retorna 0 se chegou até aqui."""
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
