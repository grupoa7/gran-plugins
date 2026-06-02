"""
Gerar HTML · Produtividade Gran v1.3
=====================================

v1.3 — feedback Hugo:
  - Aba 1: termômetro + 2 mini-cards (% custo/fat, % margem líquida sobre fat)
  - Aba 2: barra KW segmentada por GRUPOS + treemap mostrando destino de R$
           (CMV / Custo Pessoal / Margem Líquida) com tooltip JS funcional
  - Aba 3: ordem Heróis → Menos Vendidos (com simulação 1h R$15/kg) → Vilões
  - Aba 4: data labels visíveis nos pontos dos gráficos Chart.js
"""
import json
import os
from datetime import datetime
from pathlib import Path


def get_data_dir() -> Path:
    if env := os.environ.get('SURVEY_DATA_DIR'):
        return Path(env)
    home_proj = Path.home() / 'Documents' / 'Claude' / 'Projects' / '[GRAN] Survey' / 'data'
    if home_proj.exists():
        return home_proj
    legacy = Path.home() / 'Documents' / 'SurveyGran'
    if legacy.exists():
        return legacy
    raise FileNotFoundError("Pasta data/ não encontrada.")


DATA_DIR = get_data_dir()
PROD_DIR = DATA_DIR / 'produtividade'
REL_DIR = PROD_DIR / 'relatorios'


def fmt_brl(v: float) -> str:
    s = f'{v:,.2f}'
    return 'R$ ' + s.replace(',', 'X').replace('.', ',').replace('X', '.')


def fmt_brl_short(v: float) -> str:
    if abs(v) >= 1_000_000:
        return f'R$ {v/1_000_000:.1f}M'.replace('.', ',')
    if abs(v) >= 1_000:
        return f'R$ {v/1_000:.0f}k'
    return f'R$ {v:.0f}'


def fmt_pct(v: float, casas: int = 1) -> str:
    return f'{v:.{casas}f}%'.replace('.', ',')


def cor_termometro(pct: float, crit: float, warn: float) -> str:
    if pct >= crit:
        return 'var(--vermelho)'
    if pct >= warn:
        return 'var(--amarelo)'
    return 'var(--verde)'


def cor_margem_pct(pct: float) -> str:
    if pct < 30:
        return 'var(--vermelho)'
    if pct < 50:
        return 'var(--amarelo)'
    return 'var(--verde)'


def termo_svg_compact(pct: float, crit: float, warn: float, alvo: float = None) -> str:
    cor = cor_termometro(pct, crit, warn)
    pct_clamp = min(100, max(0, pct))
    h_fill = pct_clamp * 1.4
    # Linha do benchmark (alvo)
    bench_line = ''
    if alvo and alvo > 0:
        alvo_clamp = min(100, max(0, alvo))
        y_alvo = 160 - (alvo_clamp * 1.4)
        bench_line = f'''
        <line x1="20" y1="{y_alvo}" x2="46" y2="{y_alvo}" stroke="#1a1f1a" stroke-width="2" stroke-dasharray="4,3"/>
        <text x="-2" y="{y_alvo+3}" fill="#1a1f1a" font-size="8" font-weight="700" font-family="JetBrains Mono">META</text>
        <text x="-2" y="{y_alvo+13}" fill="#1a1f1a" font-size="8" font-family="JetBrains Mono">{int(alvo)}%</text>
        '''
    return f"""
    <svg viewBox="-22 0 86 200" xmlns="http://www.w3.org/2000/svg" class="termo-compact">
      <line x1="40" y1="20" x2="40" y2="160" stroke="var(--border)" stroke-width="1"/>
      <line x1="38" y1="20" x2="46" y2="20" stroke="var(--ink-mute)" stroke-width="1"/>
      <line x1="38" y1="48" x2="46" y2="48" stroke="var(--vermelho)" stroke-width="1.5" stroke-dasharray="3,2"/>
      <line x1="38" y1="76" x2="46" y2="76" stroke="var(--amarelo)" stroke-width="1.5" stroke-dasharray="3,2"/>
      <line x1="38" y1="160" x2="46" y2="160" stroke="var(--ink-mute)" stroke-width="1"/>
      <text x="50" y="24" fill="var(--ink-mute)" font-size="8" font-family="JetBrains Mono">100%</text>
      <text x="50" y="52" fill="var(--vermelho)" font-size="8" font-weight="600" font-family="JetBrains Mono">{int(crit)}%</text>
      <text x="50" y="80" fill="var(--amarelo)" font-size="8" font-weight="600" font-family="JetBrains Mono">{int(warn)}%</text>
      <text x="50" y="164" fill="var(--ink-mute)" font-size="8" font-family="JetBrains Mono">0%</text>
      <rect x="24" y="20" width="12" height="140" rx="6" fill="var(--bg-soft)" stroke="var(--border)" stroke-width="1"/>
      <rect x="24" y="{160-h_fill}" width="12" height="{h_fill}" rx="6" fill="{cor}"/>
      <circle cx="30" cy="174" r="11" fill="{cor}" stroke="var(--ink)" stroke-opacity="0.05"/>
      {bench_line}
    </svg>
    """


def render_status_badge(status_tuple) -> str:
    """Render badge a partir do tuple (label, cor)."""
    label, cor = status_tuple
    return f'<span class="status-badge" style="background:{cor}">{label}</span>'


def gerar_html(d: dict) -> str:
    meta = d['meta']
    p = d['parametros']
    kpis = d['kpis']
    gm = kpis['gran_mesa']
    gh = kpis['gran_horti']
    tot = kpis['total']
    qd = d['qualidade_dado']
    nivel = d['nivel_alerta']
    crit = p['alerta_custo_margem_critico_pct']
    warn = p['alerta_custo_margem_warning_pct']

    mes_ref = meta['mes_referencia']
    periodo = f"{datetime.fromisoformat(meta['periodo_inicio']).strftime('%d/%m')} a {datetime.fromisoformat(meta['periodo_fim']).strftime('%d/%m/%Y')}"

    fat_total_geral = gm['fat_total'] + gh['fat_total']
    pct_fat_gm = (gm['fat_total'] / fat_total_geral * 100) if fat_total_geral else 0
    pct_fat_gh = (gh['fat_total'] / fat_total_geral * 100) if fat_total_geral else 0
    margem_total_geral = gm['margem_total'] + gh['margem_total']
    pct_mar_gm = (gm['margem_total'] / margem_total_geral * 100) if margem_total_geral else 0
    pct_mar_gh = (gh['margem_total'] / margem_total_geral * 100) if margem_total_geral else 0
    custo_total_geral = gm['custo_total'] + gh['custo_total']
    pct_custo_gm = (gm['custo_total'] / custo_total_geral * 100) if custo_total_geral else 0
    pct_custo_gh = (gh['custo_total'] / custo_total_geral * 100) if custo_total_geral else 0

    def render_top(skus):
        if not skus:
            return '<tr><td colspan="5" style="text-align:center;color:var(--ink-mute);padding:20px">Sem dados</td></tr>'
        rows = []
        for s in skus:
            cor = cor_margem_pct(s['margem_pct'])
            rows.append(f"""
                <tr>
                    <td class="cod">{s['cod']}</td>
                    <td class="desc">{s['descricao']}</td>
                    <td class="num">{fmt_brl_short(s['fat'])}</td>
                    <td class="num"><strong>{fmt_brl_short(s['margem'])}</strong></td>
                    <td class="num pct" style="color:{cor}">{fmt_pct(s['margem_pct'], 0)}</td>
                </tr>
            """)
        return ''.join(rows)

    def render_viloes(viloes):
        if not viloes:
            return '<div class="empty-state">✅ Nenhum vilão crítico identificado.</div>'
        cards = []
        for v in viloes:
            cor_acao = {'DESCONTINUAR': 'var(--vermelho)', 'REVISAR PREÇO': 'var(--vermelho)',
                       'AVALIAR': 'var(--amarelo)', 'OTIMIZAR': 'var(--amarelo)',
                       'ACOMPANHAR': 'var(--ink-mute)'}.get(v['acao_sugerida'], 'var(--ink-mute)')
            cor_marg = cor_margem_pct(v['margem_pct'])
            cards.append(f"""
                <div class="vilao-card">
                  <div class="vilao-acao" style="background:{cor_acao}">{v['acao_sugerida']}</div>
                  <div class="vilao-cod">cód {v['cod']}</div>
                  <div class="vilao-desc">{v['descricao']}</div>
                  <div class="vilao-grupo">{v['grupo']} · {v['setor']}</div>
                  <div class="vilao-stats">
                    <div class="vilao-stat">
                      <div class="stat-label">Margem atual</div>
                      <div class="stat-value" style="color:{cor_marg}">{fmt_pct(v['margem_pct'])}</div>
                    </div>
                    <div class="vilao-stat">
                      <div class="stat-label">Margem ref. (média GM)</div>
                      <div class="stat-value">{fmt_pct(v['margem_pct_ref'])}</div>
                    </div>
                    <div class="vilao-stat">
                      <div class="stat-label">Faturamento 30d</div>
                      <div class="stat-value">{fmt_brl_short(v['fat'])}</div>
                    </div>
                    <div class="vilao-stat highlight">
                      <div class="stat-label">Margem perdida</div>
                      <div class="stat-value" style="color:var(--vermelho)">{fmt_brl(v['score'])}</div>
                    </div>
                  </div>
                  <div class="vilao-diag">{v['diagnostico']}</div>
                </div>
            """)
        return f'<div class="viloes-grid">{"".join(cards)}</div>'

    def render_menos_vendidos(items):
        if not items:
            return '<div class="empty-state">✅ Nenhum produto com baixo giro detectado.</div>'
        rows = []
        for m in items:
            margem_pos = m.get('sim_margem_apos_horas', 0)
            cor_pos = 'var(--vermelho)' if margem_pos < 0 else ('var(--amarelo)' if margem_pos < m.get('sim_custo_horas', 0) else 'var(--verde)')
            rows.append(f"""
                <tr>
                    <td class="cod">{m['cod']}</td>
                    <td class="desc">{m['descricao']}</td>
                    <td class="num">{m['qtd']:.1f} {m['unidade'][:5]}</td>
                    <td class="num">{fmt_brl_short(m['fat'])}</td>
                    <td class="num"><strong>{fmt_brl_short(m['margem'])}</strong></td>
                    <td class="num sim-col">{m.get('sim_horas_estim', 0):.1f}h</td>
                    <td class="num sim-col">−{fmt_brl_short(m.get('sim_custo_horas', 0))}</td>
                    <td class="num sim-col" style="color:{cor_pos};font-weight:700">{fmt_brl_short(margem_pos)}</td>
                </tr>
            """)
        return ''.join(rows)

    funcs_data = json.dumps([
        {
            'name': f['nome'].split()[0] + ' ' + (f['nome'].split()[-1] if len(f['nome'].split()) > 1 else ''),
            'fullname': f['nome'],
            'value': f['custo_total'],
            'equipe': f['equipe'],
            'funcao': f['funcao'],
        }
        for f in d['funcionarios']
    ], ensure_ascii=False)

    # Dados pro treemap "destino do faturamento"
    destino_fat = {
        'fat_total': tot['fat_total'],
        'cmv_total': tot['cmv_total'],
        'custo_pessoal': tot['custo_total'],
        'margem_liquida': tot['margem_liquida'],
        'cmv_por_equipe': {
            'gran_mesa': gm['cmv_total'],
            'gran_horti': gh['cmv_total'],
        },
        'pessoal_por_equipe': {
            'gran_mesa': gm['custo_total'],
            'gran_horti': gh['custo_total'],
        },
        'margem_liquida_por_equipe': {
            'gran_mesa': gm['margem_liquida'],
            'gran_horti': gh['margem_liquida'],
        },
    }
    destino_fat_json = json.dumps(destino_fat)

    sens = d['sensibilidade']
    chart_sens_a = json.dumps({
        'labels': [fmt_brl_short(s['fat_gmpro']) for s in sens['eixo_a_gmpro']],
        'data': [round(s['custo_sobre_margem_pct'], 1) for s in sens['eixo_a_gmpro']],
    })
    chart_sens_b = json.dumps({
        'labels': [f"{s['n_funcionarios']} func" for s in sens['eixo_b_quadro_gm']],
        'data': [round(s['custo_sobre_margem_pct'], 1) for s in sens['eixo_b_quadro_gm']],
    })
    chart_sens_c = json.dumps({
        'labels': [f"{s['pct_realocado']}%" for s in sens['eixo_c_realocacao']],
        'data': [round(s['custo_sobre_margem_pct'], 1) for s in sens['eixo_c_realocacao']],
    })
    chart_sens_d = json.dumps({
        'labels': [f"{s['pct_migracao']}%" for s in sens['eixo_d_migracao']],
        'data_gm': [round(s['custo_sobre_margem_pct_gm'], 1) for s in sens['eixo_d_migracao']],
        'data_gh': [round(s['custo_sobre_margem_pct_gh'], 1) for s in sens['eixo_d_migracao']],
    })
    referencia_gh = round(gh['custo_sobre_margem_pct'], 1)

    # Lista nominal por equipe + alfabética + subtotais
    def lista_nominal_por_equipe():
        grupos = {}
        for f in d['funcionarios']:
            grupos.setdefault(f['equipe'], []).append(f)
        ordem_equipes = ['Gran Mesa', 'Gran Horti', 'Retaguarda']
        html_blocks = []
        for eq in ordem_equipes:
            funcs_eq = sorted(grupos.get(eq, []), key=lambda x: x['nome'].upper())
            if not funcs_eq:
                continue
            total_venc = sum(f['vencimentos'] for f in funcs_eq)
            total_custo = sum(f['custo_total'] for f in funcs_eq)
            eq_class = {'Gran Mesa': 'gm', 'Gran Horti': 'gh', 'Retaguarda': 'retag'}.get(eq, 'retag')
            rows = []
            for f in funcs_eq:
                rows.append(f"""
                    <tr>
                        <td class="cod">{f['matricula']}</td>
                        <td>{f['nome']}</td>
                        <td class="desc">{f['funcao']}</td>
                        <td class="num">{fmt_brl(f['vencimentos'])}</td>
                        <td class="num"><strong>{fmt_brl(f['custo_total'])}</strong></td>
                    </tr>
                """)
            html_blocks.append(f"""
                <div class="equipe-block">
                  <div class="equipe-header equipe-{eq_class}">
                    <span class="equipe-titulo">{eq}</span>
                    <span class="equipe-count">{len(funcs_eq)} pessoas</span>
                  </div>
                  <table class="lista-table">
                    <thead><tr><th>Matrícula</th><th>Nome</th><th>Função</th><th class="num">Vencimentos</th><th class="num">Custo Empresa</th></tr></thead>
                    <tbody>
                      {''.join(rows)}
                      <tr class="subtotal-row">
                        <td colspan="3"><strong>Subtotal {eq}</strong></td>
                        <td class="num"><strong>{fmt_brl(total_venc)}</strong></td>
                        <td class="num"><strong>{fmt_brl(total_custo)}</strong></td>
                      </tr>
                    </tbody>
                  </table>
                </div>
            """)
        return ''.join(html_blocks)

    # Render de barra KW segmentada por grupos
    def render_grupos_bar(grupos, equipe_label, cor_base):
        # Cores progressivamente mais claras pra cada grupo
        paleta = ['var(--gran-verde)', 'var(--gran-verde-2)', 'var(--gran-verde-3)',
                  'var(--gran-dourado)', 'var(--gran-dourado-2)',
                  '#5b8fb8', '#8b8f86', '#a8a298'] if cor_base == 'gm' else \
                 ['var(--gran-dourado)', '#e0c97a', 'var(--gran-verde-3)',
                  '#5b8fb8', '#7fb07d', '#c9a227', '#e8b5a0', '#a8a298']
        total = sum(g['fat'] for g in grupos)
        if total == 0:
            return '<div class="empty-state">Sem grupos no período</div>'
        segs = []
        for i, g in enumerate(grupos):
            pct = g['fat'] / total * 100
            cor = paleta[i % len(paleta)]
            label = g['grupo']
            text_in = f"{label[:14]} {pct:.0f}%" if pct >= 8 else f"{pct:.0f}%"
            segs.append(f"""
                <div class="seg-grupo" style="background:{cor}; width:{pct}%" data-grupo="{label}" data-fat="{fmt_brl(g['fat'])}" data-pct="{pct:.1f}%">
                  <span class="seg-label">{text_in}</span>
                </div>
            """)
        return f'<div class="grupos-bar">{"".join(segs)}</div>'

    qd_warn = ''
    if qd['flag_cobertura']:
        qd_warn = f'<div class="warn-pill">⚠️ {fmt_pct(qd["fat_sem_pcusto_pct"])} do faturamento sem custo cadastrado.</div>'

    fonte_kw_label = {'pkl': 'KW base classificada', 'csv_fallback': 'CSV processado',
                      'margens': 'gran_margens (modo demo)'}.get(qd['fonte_kw'], qd['fonte_kw'])

    if nivel == 'vermelho':
        alerta_class = 'alerta-vermelho'; alerta_icone = '🚨'; alerta_titulo = 'Equipe acima do limite crítico'
    elif nivel == 'amarelo':
        alerta_class = 'alerta-amarelo'; alerta_icone = '⚠️'; alerta_titulo = 'Equipe em zona de atenção'
    else:
        alerta_class = 'alerta-verde'; alerta_icone = '✅'; alerta_titulo = 'Ambas equipes dentro do esperado'

    razao = gm['custo_sobre_margem_pct'] / max(0.01, gh['custo_sobre_margem_pct'])
    leitura_txt = (
        f"A equipe <strong>Gran Mesa</strong> ({gm['n_funcionarios_clt']} pessoas + diaristas) gera "
        f"<strong>{fmt_brl(gm['margem_total'])}</strong> de margem por mês e custa "
        f"<strong>{fmt_brl(gm['custo_total'])}</strong> em pessoal — <strong>{fmt_pct(gm['custo_sobre_margem_pct'])}</strong>. "
        f"A <strong>Gran Horti</strong> ({gh['n_funcionarios_clt']} pessoas) gera "
        f"<strong>{fmt_brl(gh['margem_total'])}</strong> e custa "
        f"<strong>{fmt_brl(gh['custo_total'])}</strong> — <strong>{fmt_pct(gh['custo_sobre_margem_pct'])}</strong>. "
        f"Por real de margem produzida, a Gran Mesa custa <strong>{razao:.1f}× mais</strong> que a Gran Horti."
    )

    top_resumo = d.get('top_resumo', {})
    pct_top_gm = top_resumo.get('gran_mesa', {}).get('pct_sobre_margem_total', 0)
    pct_top_gh = top_resumo.get('gran_horti', {}).get('pct_sobre_margem_total', 0)
    soma_top_gm = top_resumo.get('gran_mesa', {}).get('soma_top10', 0)
    soma_top_gh = top_resumo.get('gran_horti', {}).get('soma_top10', 0)

    # Benchmarks
    bm = d.get('benchmarks', {})
    bm_gm = bm.get('gran_mesa', {})
    bm_gh = bm.get('gran_horti', {})
    alvo_cm_gm = bm_gm.get('alvo_custo_sobre_margem_pct', 0)
    alvo_cm_gh = bm_gh.get('alvo_custo_sobre_margem_pct', 0)
    alvo_cf_gm = bm_gm.get('alvo_custo_sobre_fat_pct', 0)
    alvo_cf_gh = bm_gh.get('alvo_custo_sobre_fat_pct', 0)
    alvo_mb_gm = bm_gm.get('alvo_margem_bruta_pct', 0)
    alvo_mb_gh = bm_gh.get('alvo_margem_bruta_pct', 0)

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Produtividade Gran — {mes_ref}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0"></script>
<style>
:root {{
  --bg: #ffffff; --bg-soft: #f6f4ee; --bg-cream: #faf7ef;
  --border: #e8e3d4; --border-soft: #f0ebdc;
  --ink: #1a1f1a; --ink-dim: #4a5248; --ink-mute: #8b8f86;
  --gran-verde: #1e4d2b; --gran-verde-2: #2d6a3f; --gran-verde-3: #3f8654; --gran-verde-bg: #e7f0e9;
  --gran-dourado: #c9a227; --gran-dourado-2: #e8b93a; --gran-dourado-bg: #faf1d4;
  --vermelho: #b8362f; --vermelho-bg: #f2d9d3;
  --amarelo: #d4a52e; --amarelo-bg: #faf1d4;
  --verde: #3f8654; --verde-bg: #e7f0e9;
  --shadow: 0 1px 2px rgba(30,77,43,0.04), 0 4px 12px rgba(30,77,43,0.06);
}}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; }}
body {{ background: var(--bg); color: var(--ink); font-family: 'Aptos', 'Nunito Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 15px; line-height: 1.55; -webkit-font-smoothing: antialiased; }}
.container {{ max-width: 1380px; margin: 0 auto; padding: 32px 32px 80px; }}

header.main-header {{ display: flex; align-items: flex-end; justify-content: space-between; gap: 40px; padding: 24px 32px 28px; background: var(--gran-verde); color: #fff; border-radius: 12px; margin-bottom: 28px; box-shadow: var(--shadow); flex-wrap: wrap; }}
header.main-header h1 {{ font-weight: 800; font-size: 40px; line-height: 1.05; letter-spacing: -0.02em; margin: 8px 0 4px; color: #fff; }}
header.main-header h1 em {{ font-style: normal; color: var(--gran-dourado-2); }}
.eyebrow {{ font-family: 'JetBrains Mono', monospace; font-size: 11px; letter-spacing: 0.2em; text-transform: uppercase; color: var(--gran-dourado-2); margin: 0; font-weight: 500; }}
.subtitle {{ font-weight: 400; font-size: 16px; color: rgba(255,255,255,0.82); margin: 0 0 8px; }}
.meta {{ text-align: right; font-family: 'JetBrains Mono', monospace; font-size: 11px; color: rgba(255,255,255,0.7); letter-spacing: 0.05em; }}
.meta div {{ margin-bottom: 4px; }}
.meta strong {{ color: var(--gran-dourado-2); font-weight: 600; }}

.tabs-wrap {{ position: sticky; top: 0; z-index: 50; background: var(--bg); padding: 4px 0 0; margin-bottom: 28px; border-bottom: 1px solid var(--border); }}
.tabs {{ display: flex; gap: 4px; overflow-x: auto; padding: 4px 0; }}
.tab {{ flex: 0 0 auto; padding: 12px 18px; border: none; background: transparent; cursor: pointer; font-family: 'Aptos','Nunito Sans',sans-serif; font-size: 14px; font-weight: 600; color: var(--ink-mute); border-bottom: 3px solid transparent; transition: all 0.15s ease; white-space: nowrap; border-radius: 6px 6px 0 0; }}
.tab:hover {{ color: var(--gran-verde); background: var(--bg-soft); }}
.tab.active {{ color: var(--gran-verde); border-bottom-color: var(--gran-dourado); background: var(--bg-cream); }}
.tab .num {{ font-family: 'JetBrains Mono', monospace; font-size: 10px; color: var(--ink-mute); margin-right: 8px; font-weight: 500; }}
.tab.active .num {{ color: var(--gran-dourado); }}
.tab-panel {{ display: none; }}
.tab-panel.active {{ display: block; animation: fadeIn 0.25s ease; }}
@keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(4px); }} to {{ opacity: 1; transform: translateY(0); }} }}

.section-kicker {{ font-family: 'JetBrains Mono', monospace; font-size: 10px; letter-spacing: 0.18em; text-transform: uppercase; color: var(--gran-dourado); margin: 0 0 6px; font-weight: 600; }}
.section-title {{ font-weight: 700; font-size: 26px; letter-spacing: -0.02em; color: var(--gran-verde); margin: 0 0 6px; line-height: 1.2; }}
.section-desc {{ color: var(--ink-dim); font-size: 14px; margin: 0 0 20px; max-width: 760px; }}

.alerta {{ padding: 14px 20px; border-radius: 10px; margin-bottom: 24px; display: flex; align-items: center; gap: 14px; }}
.alerta-vermelho {{ background: var(--vermelho-bg); border-left: 4px solid var(--vermelho); }}
.alerta-amarelo {{ background: var(--amarelo-bg); border-left: 4px solid var(--amarelo); }}
.alerta-verde {{ background: var(--verde-bg); border-left: 4px solid var(--verde); }}
.alerta-icone {{ font-size: 28px; }}
.alerta-titulo {{ font-weight: 700; font-size: 15px; color: var(--ink); }}
.alerta-sub {{ font-size: 13px; color: var(--ink-dim); margin-top: 2px; }}

/* ─── ABA 1 ─── */
.equipe-row {{ display: grid; grid-template-columns: 380px 1fr; gap: 18px; background: var(--bg-cream); border: 1px solid var(--border); border-radius: 12px; padding: 18px 20px; margin-bottom: 14px; box-shadow: var(--shadow); align-items: stretch; }}
.termo-area {{ display: flex; gap: 12px; padding: 4px; border-right: 1px solid var(--border-soft); padding-right: 16px; }}
.equipe-termo {{ display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 4px; min-width: 130px; }}
.equipe-termo .termo-compact {{ height: 200px; width: 64px; }}
.termo-num-big {{ font-size: 30px; font-weight: 800; line-height: 1; letter-spacing: -0.02em; margin-top: 4px; }}
.termo-num-label {{ font-size: 11px; color: var(--ink-mute); text-align: center; margin-top: 2px; max-width: 130px; line-height: 1.3; }}

.termo-extras {{ display: flex; flex-direction: column; justify-content: center; gap: 8px; flex: 1; }}
.extra-card {{ background: white; border: 1px solid var(--border-soft); border-radius: 8px; padding: 10px 12px; position: relative; }}
.extra-card.highlight {{ border: 1px solid var(--gran-dourado); background: var(--gran-dourado-bg); }}
.extra-label {{ font-size: 9px; color: var(--ink-mute); text-transform: uppercase; letter-spacing: 0.1em; font-weight: 700; }}
.extra-value {{ font-size: 22px; font-weight: 800; color: var(--gran-verde); margin-top: 2px; line-height: 1.05; letter-spacing: -0.02em; }}
.extra-sub {{ font-size: 11px; color: var(--ink-dim); margin-top: 1px; line-height: 1.3; }}
.extra-status {{ margin-top: 6px; }}
.status-badge {{ display: inline-block; padding: 3px 9px; border-radius: 999px; color: white; font-size: 9px; font-weight: 800; letter-spacing: 0.08em; text-transform: uppercase; line-height: 1.3; }}
.bench-meta {{ font-size: 10px; color: var(--ink-mute); font-family: 'JetBrains Mono', monospace; margin-top: 3px; letter-spacing: 0.05em; }}

.equipe-info {{ display: flex; flex-direction: column; padding: 4px 4px 4px 8px; }}
.equipe-nome {{ font-size: 22px; font-weight: 700; color: var(--gran-verde); margin: 0 0 2px; }}
.equipe-sub {{ font-size: 12px; color: var(--ink-mute); margin-bottom: 14px; font-family: 'JetBrains Mono', monospace; letter-spacing: 0.05em; }}
.equipe-kpis {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; flex: 1; align-content: center; }}
.equipe-kpi {{ background: white; border: 1px solid var(--border-soft); border-radius: 8px; padding: 10px 12px; }}
.kpi-label {{ font-size: 10px; color: var(--ink-mute); text-transform: uppercase; letter-spacing: 0.1em; font-weight: 600; }}
.kpi-value {{ font-size: 19px; font-weight: 700; color: var(--gran-verde); margin-top: 2px; line-height: 1.1; letter-spacing: -0.01em; }}
.kpi-pct {{ font-size: 11px; color: var(--ink-mute); margin-top: 2px; font-family: 'JetBrains Mono', monospace; }}

.kpi-row {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px; margin: 22px 0; }}
.kpi-big {{ background: white; border: 1px solid var(--border); border-radius: 10px; padding: 16px 18px; box-shadow: var(--shadow); }}
.kpi-big-label {{ font-family: 'JetBrains Mono', monospace; font-size: 10px; letter-spacing: 0.15em; text-transform: uppercase; color: var(--ink-mute); font-weight: 600; }}
.kpi-big-value {{ font-size: 26px; font-weight: 800; color: var(--gran-verde); margin-top: 6px; line-height: 1.1; letter-spacing: -0.02em; }}
.kpi-big-sub {{ font-size: 12px; color: var(--ink-dim); margin-top: 3px; }}

.compara-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; margin: 24px 0; }}
.compara-card {{ background: white; border: 1px solid var(--border); border-radius: 10px; padding: 14px 18px; box-shadow: var(--shadow); }}
.compara-titulo {{ font-size: 11px; color: var(--ink-mute); text-transform: uppercase; letter-spacing: 0.1em; font-weight: 600; margin-bottom: 10px; }}
.compara-bar-wrap {{ display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }}
.compara-eq {{ width: 80px; font-size: 12px; color: var(--ink-dim); font-weight: 600; }}
.compara-bar {{ flex: 1; height: 24px; background: var(--bg-soft); border-radius: 4px; overflow: hidden; }}
.compara-bar-fill {{ height: 100%; border-radius: 4px; display: flex; align-items: center; justify-content: flex-end; padding-right: 8px; color: white; font-weight: 700; font-size: 12px; }}

.leitura-final {{ background: var(--bg-cream); border-left: 3px solid var(--gran-dourado); padding: 16px 20px; border-radius: 6px; margin: 24px 0; line-height: 1.7; font-size: 14px; }}
.leitura-final p {{ margin: 0; color: var(--ink); }}
.hipoteses-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; margin-top: 14px; }}
.hipotese {{ background: var(--bg); border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; box-shadow: var(--shadow); }}
.hipotese-titulo {{ font-weight: 700; font-size: 14px; color: var(--gran-verde); margin-bottom: 6px; display: flex; align-items: center; gap: 6px; }}
.hipotese-letra {{ display: inline-block; width: 22px; height: 22px; background: var(--gran-dourado); color: white; border-radius: 50%; text-align: center; line-height: 22px; font-size: 12px; font-weight: 800; }}
.hipotese-texto {{ font-size: 13px; color: var(--ink-dim); line-height: 1.5; }}

/* ─── ABA 2 ─── */
.composicao-section {{ background: white; border: 1px solid var(--border); border-radius: 12px; padding: 24px; margin-bottom: 20px; box-shadow: var(--shadow); }}
.composicao-section h3 {{ color: var(--gran-verde); font-size: 20px; margin: 0 0 4px; font-weight: 700; }}
.composicao-section .sub-desc {{ color: var(--ink-dim); font-size: 13px; margin-bottom: 18px; }}

.equipe-grupos-bloco {{ margin-bottom: 18px; }}
.equipe-grupos-titulo {{ font-size: 13px; font-weight: 700; color: var(--ink); margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; }}
.equipe-grupos-total {{ font-family: 'JetBrains Mono', monospace; font-size: 13px; color: var(--gran-verde); font-weight: 700; }}
.grupos-bar {{ display: flex; height: 38px; background: var(--bg-soft); border-radius: 8px; overflow: hidden; gap: 1px; }}
.seg-grupo {{ height: 100%; display: flex; align-items: center; justify-content: center; color: white; font-size: 11px; font-weight: 600; padding: 0 6px; min-width: 0; cursor: default; transition: filter 0.15s; overflow: hidden; }}
.seg-grupo:hover {{ filter: brightness(1.15); }}
.seg-label {{ white-space: nowrap; overflow: hidden; text-overflow: ellipsis; pointer-events: none; }}
.grupos-omie {{ margin-top: 6px; padding: 8px 12px; background: var(--gran-dourado-bg); border-radius: 6px; font-size: 12px; color: var(--ink); }}
.grupos-omie strong {{ color: var(--gran-verde); }}

.stacked-row {{ display: flex; align-items: center; margin: 12px 0; gap: 14px; }}
.stacked-label {{ width: 110px; font-weight: 600; font-size: 14px; color: var(--ink); }}
.stacked-bar {{ flex: 1; height: 34px; background: var(--bg-soft); border-radius: 6px; overflow: hidden; display: flex; }}
.stacked-seg {{ height: 100%; display: flex; align-items: center; justify-content: center; color: white; font-size: 12px; font-weight: 600; padding: 0 10px; min-width: 0; overflow: hidden; white-space: nowrap; }}
.stacked-total {{ width: 130px; text-align: right; font-weight: 700; font-variant-numeric: tabular-nums; color: var(--gran-verde); }}
.legenda {{ display: flex; gap: 16px; flex-wrap: wrap; margin-top: 12px; font-size: 12px; color: var(--ink-mute); }}
.leg-item {{ display: flex; align-items: center; gap: 6px; }}
.leg-dot {{ width: 12px; height: 12px; border-radius: 3px; }}

#destino-fat {{ width: 100%; height: 280px; min-height: 280px; position: relative; }}
.destino-tooltip {{ position: absolute; background: var(--gran-verde); color: white; padding: 8px 12px; border-radius: 6px; font-size: 12px; pointer-events: none; opacity: 0; transition: opacity 0.15s; z-index: 100; box-shadow: 0 4px 12px rgba(0,0,0,0.2); }}
.destino-tooltip strong {{ display: block; margin-bottom: 4px; font-size: 13px; }}

#treemap-funcs {{ width: 100%; height: 480px; min-height: 480px; position: relative; }}
.treemap-tooltip {{ position: absolute; background: var(--gran-verde); color: white; padding: 8px 12px; border-radius: 6px; font-size: 12px; pointer-events: none; opacity: 0; transition: opacity 0.15s; z-index: 100; box-shadow: 0 4px 12px rgba(0,0,0,0.2); }}

.equipe-block {{ margin-bottom: 24px; border: 1px solid var(--border); border-radius: 10px; overflow: hidden; }}
.equipe-header {{ padding: 12px 18px; display: flex; justify-content: space-between; align-items: center; color: white; }}
.equipe-header.equipe-gm {{ background: var(--gran-verde); }}
.equipe-header.equipe-gh {{ background: var(--gran-dourado); }}
.equipe-header.equipe-retag {{ background: var(--ink-mute); }}
.equipe-titulo {{ font-size: 16px; font-weight: 700; }}
.equipe-count {{ font-size: 12px; font-family: 'JetBrains Mono', monospace; opacity: 0.85; letter-spacing: 0.05em; }}
.lista-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
.lista-table th {{ background: var(--bg-cream); padding: 8px 12px; text-align: left; font-weight: 600; color: var(--ink-dim); border-bottom: 1px solid var(--border); font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; }}
.lista-table td {{ padding: 8px 12px; border-bottom: 1px solid var(--border-soft); }}
.lista-table tr:hover {{ background: var(--bg-cream); }}
.subtotal-row {{ background: var(--bg-soft) !important; border-top: 2px solid var(--gran-dourado); }}
.subtotal-row td {{ padding: 10px 12px !important; }}

table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
th {{ background: var(--bg-cream); padding: 9px 12px; text-align: left; font-weight: 600; color: var(--ink-dim); border-bottom: 2px solid var(--border); font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; }}
td {{ padding: 8px 12px; border-bottom: 1px solid var(--border-soft); }}
td.cod {{ font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--ink-mute); }}
td.desc {{ font-size: 13px; }}
td.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
td.pct {{ font-weight: 700; }}
td.sim-col {{ background: var(--gran-dourado-bg); }}
tr:hover {{ background: var(--bg-cream); }}

/* ─── ABA 3 ─── */
.heroes-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin-bottom: 20px; }}
.heroes-section {{ background: white; border: 1px solid var(--border); border-radius: 10px; padding: 20px; box-shadow: var(--shadow); }}
.heroes-section h3 {{ color: var(--gran-verde); font-size: 17px; margin: 0 0 4px; display: flex; align-items: center; gap: 8px; font-weight: 700; }}
.heroes-icone {{ font-size: 20px; }}
.heroes-resumo {{ font-size: 12px; color: var(--ink-dim); margin-bottom: 12px; padding: 8px 12px; background: var(--gran-verde-bg); border-radius: 6px; }}
.heroes-resumo strong {{ color: var(--gran-verde); }}

.menos-vendidos-section {{ background: white; border: 1px solid var(--amarelo); border-radius: 12px; padding: 24px; margin-bottom: 20px; box-shadow: var(--shadow); }}
.menos-vendidos-section h3 {{ color: var(--amarelo); font-size: 18px; margin: 0 0 4px; display: flex; align-items: center; gap: 8px; font-weight: 700; }}
.menos-vendidos-section .sub-desc {{ color: var(--ink-dim); font-size: 13px; margin-bottom: 14px; }}
.sim-pill {{ display: inline-block; padding: 4px 10px; background: var(--gran-dourado); color: white; border-radius: 4px; font-size: 10px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 12px; }}

.viloes-section {{ background: var(--vermelho-bg); border: 1px solid var(--vermelho); border-radius: 12px; padding: 24px; }}
.viloes-section h3 {{ color: var(--vermelho); font-size: 20px; margin: 0 0 4px; display: flex; align-items: center; gap: 10px; font-weight: 700; }}
.viloes-section .sub-desc {{ color: var(--ink-dim); font-size: 13px; margin-bottom: 16px; }}
.viloes-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; }}
.vilao-card {{ background: white; border: 1px solid var(--border); border-radius: 10px; padding: 14px; position: relative; box-shadow: var(--shadow); }}
.vilao-acao {{ position: absolute; top: 0; right: 0; background: var(--vermelho); color: white; padding: 4px 10px; font-size: 10px; font-weight: 800; letter-spacing: 0.06em; text-transform: uppercase; border-radius: 0 10px 0 10px; }}
.vilao-cod {{ font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--ink-mute); }}
.vilao-desc {{ font-weight: 700; font-size: 14px; color: var(--ink); margin: 4px 0 2px; padding-right: 90px; }}
.vilao-grupo {{ font-size: 11px; color: var(--ink-mute); margin-bottom: 12px; }}
.vilao-stats {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 12px; }}
.vilao-stat {{ background: var(--bg-soft); padding: 8px 10px; border-radius: 6px; }}
.vilao-stat.highlight {{ background: var(--vermelho-bg); border: 1px solid var(--vermelho); }}
.stat-label {{ font-size: 10px; color: var(--ink-mute); text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; }}
.stat-value {{ font-size: 14px; font-weight: 700; color: var(--ink); margin-top: 2px; }}
.vilao-diag {{ font-size: 12px; color: var(--ink-dim); padding-top: 10px; border-top: 1px solid var(--border-soft); }}
.empty-state {{ text-align: center; padding: 30px; color: var(--ink-dim); background: white; border-radius: 10px; }}

/* ─── ABA 4 ─── */
.sens-intro {{ background: var(--bg-cream); border: 1px solid var(--border); border-radius: 10px; padding: 16px 20px; margin-bottom: 22px; font-size: 14px; }}
.sens-charts {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 18px; }}
.sens-chart-card {{ background: white; border: 1px solid var(--border); border-radius: 12px; padding: 20px; box-shadow: var(--shadow); }}
.sens-chart-card h4 {{ color: var(--gran-verde); font-size: 16px; margin: 0 0 4px; font-weight: 700; }}
.sens-chart-card .sens-sub {{ font-size: 12px; color: var(--ink-mute); margin-bottom: 12px; }}
.sens-chart-canvas {{ height: 240px; }}
.sens-chart-card .sens-leitura {{ font-size: 12px; color: var(--ink-dim); margin-top: 12px; padding: 10px 12px; background: var(--bg-soft); border-radius: 6px; line-height: 1.5; }}

footer {{ margin-top: 40px; padding: 24px 28px; background: var(--bg-soft); border-radius: 10px; font-size: 12px; color: var(--ink-mute); line-height: 1.7; }}
footer strong {{ color: var(--ink); }}
footer .footer-cols {{ display: grid; grid-template-columns: 2fr 1fr; gap: 28px; }}
.warn-pill {{ display: inline-block; padding: 6px 12px; background: var(--amarelo-bg); color: #8a6500; border-radius: 6px; font-size: 12px; margin-top: 12px; font-weight: 600; }}

@media (max-width: 1100px) {{
  .equipe-row {{ grid-template-columns: 1fr; }}
  .termo-area {{ border-right: none; border-bottom: 1px solid var(--border-soft); padding-right: 0; padding-bottom: 16px; }}
  .equipe-kpis {{ grid-template-columns: repeat(2, 1fr); }}
}}
</style>
</head>
<body>
<div class="container">

<header class="main-header">
  <div>
    <p class="eyebrow">📊 Produtividade Gran · Mensal</p>
    <h1>Custo da equipe <em>vs</em> margem produzida</h1>
    <p class="subtitle">Análise comparativa Gran Mesa × Gran Horti — referência {mes_ref}</p>
  </div>
  <div class="meta">
    <div>Período: <strong>{periodo}</strong></div>
    <div>Janela: <strong>{p['periodo_analise_dias']} dias</strong></div>
    <div>Gerado em: <strong>{datetime.fromisoformat(meta['gerado_em']).strftime('%d/%m %H:%M')}</strong></div>
  </div>
</header>

<div class="tabs-wrap">
  <div class="tabs">
    <button class="tab active" onclick="showTab(event, 'tab-1')"><span class="num">01</span>Diagnóstico</button>
    <button class="tab" onclick="showTab(event, 'tab-2')"><span class="num">02</span>Composição por Equipe</button>
    <button class="tab" onclick="showTab(event, 'tab-3')"><span class="num">03</span>Heróis &amp; Vilões</button>
    <button class="tab" onclick="showTab(event, 'tab-4')"><span class="num">04</span>Cenários</button>
  </div>
</div>

<!-- ═══════════════════ ABA 1: DIAGNÓSTICO ═══════════════════ -->
<div id="tab-1" class="tab-panel active">
  <p class="section-kicker">📌 Diagnóstico do Mês</p>
  <h2 class="section-title">% da margem que vira pessoal</h2>
  <p class="section-desc">Quanto do que cada equipe produz de margem é consumido em pagamento de pessoal. Quanto menor, melhor — sobra mais pra reinvestir.</p>

  <div class="alerta {alerta_class}">
    <div class="alerta-icone">{alerta_icone}</div>
    <div>
      <div class="alerta-titulo">{alerta_titulo}</div>
      <div class="alerta-sub">Alerta vermelho ≥ {fmt_pct(crit, 0)} · amarelo ≥ {fmt_pct(warn, 0)} · verde abaixo</div>
    </div>
  </div>

  <!-- Gran Mesa -->
  <div class="equipe-row">
    <div class="termo-area">
      <div class="equipe-termo">
        {termo_svg_compact(gm['custo_sobre_margem_pct'], crit, warn, alvo_cm_gm)}
        <div class="termo-num-big" style="color:{cor_termometro(gm['custo_sobre_margem_pct'], crit, warn)}">{fmt_pct(gm['custo_sobre_margem_pct'])}</div>
        <div class="termo-num-label">do margem vai pra pessoal</div>
        {render_status_badge(bm_gm.get('status_custo_sobre_margem', ('-', 'var(--ink-mute)')))}
        <div class="bench-meta">vs meta {fmt_pct(alvo_cm_gm, 0)}*</div>
      </div>
      <div class="termo-extras">
        <div class="extra-card">
          <div class="extra-label">Custo sobre faturamento</div>
          <div class="extra-value">{fmt_pct(gm['custo_sobre_fat_pct'])}</div>
          <div class="extra-sub">vs meta {fmt_pct(alvo_cf_gm, 0)}* · {fmt_brl_short(gm['custo_total'])} de {fmt_brl_short(gm['fat_total'])}</div>
          <div class="extra-status">{render_status_badge(bm_gm.get('status_custo_sobre_fat', ('-', 'var(--ink-mute)')))}</div>
        </div>
        <div class="extra-card">
          <div class="extra-label">Margem bruta %</div>
          <div class="extra-value">{fmt_pct(gm['margem_pct'])}</div>
          <div class="extra-sub">vs meta {fmt_pct(alvo_mb_gm, 0)}* · {fmt_brl_short(gm['margem_total'])} de margem</div>
          <div class="extra-status">{render_status_badge(bm_gm.get('status_margem_bruta', ('-', 'var(--ink-mute)')))}</div>
        </div>
        <div class="extra-card highlight">
          <div class="extra-label">⭐ Margem líquida sobre fat</div>
          <div class="extra-value" style="color:var(--gran-dourado)">{fmt_pct(gm['margem_liquida_pct_sobre_fat'])}</div>
          <div class="extra-sub">{fmt_brl_short(gm['margem_liquida'])} sobra após mercadoria + pessoal</div>
        </div>
      </div>
    </div>
    <div class="equipe-info">
      <div class="equipe-nome">Gran Mesa</div>
      <div class="equipe-sub">{gm['n_funcionarios_clt']} func + diaristas · produção própria + GMPro · benchmark: cozinha industrial top quartil</div>
      <div class="equipe-kpis">
        <div class="equipe-kpi"><div class="kpi-label">Faturamento</div><div class="kpi-value">{fmt_brl_short(gm['fat_total'])}</div><div class="kpi-pct">{fmt_pct(pct_fat_gm, 0)} do total</div></div>
        <div class="equipe-kpi"><div class="kpi-label">Margem R$</div><div class="kpi-value">{fmt_brl_short(gm['margem_total'])}</div><div class="kpi-pct">{fmt_pct(pct_mar_gm, 0)} da margem</div></div>
        <div class="equipe-kpi"><div class="kpi-label">Margem %</div><div class="kpi-value" style="color:var(--verde)">{fmt_pct(gm['margem_pct'])}</div><div class="kpi-pct">sobre faturamento</div></div>
        <div class="equipe-kpi"><div class="kpi-label">Custo Pessoal</div><div class="kpi-value">{fmt_brl_short(gm['custo_total'])}</div><div class="kpi-pct">{fmt_pct(pct_custo_gm, 0)} do total</div></div>
      </div>
    </div>
  </div>

  <!-- Gran Horti -->
  <div class="equipe-row">
    <div class="termo-area">
      <div class="equipe-termo">
        {termo_svg_compact(gh['custo_sobre_margem_pct'], crit, warn, alvo_cm_gh)}
        <div class="termo-num-big" style="color:{cor_termometro(gh['custo_sobre_margem_pct'], crit, warn)}">{fmt_pct(gh['custo_sobre_margem_pct'])}</div>
        <div class="termo-num-label">do margem vai pra pessoal</div>
        {render_status_badge(bm_gh.get('status_custo_sobre_margem', ('-', 'var(--ink-mute)')))}
        <div class="bench-meta">vs meta {fmt_pct(alvo_cm_gh, 0)}*</div>
      </div>
      <div class="termo-extras">
        <div class="extra-card">
          <div class="extra-label">Custo sobre faturamento</div>
          <div class="extra-value">{fmt_pct(gh['custo_sobre_fat_pct'])}</div>
          <div class="extra-sub">vs meta {fmt_pct(alvo_cf_gh, 0)}* · {fmt_brl_short(gh['custo_total'])} de {fmt_brl_short(gh['fat_total'])}</div>
          <div class="extra-status">{render_status_badge(bm_gh.get('status_custo_sobre_fat', ('-', 'var(--ink-mute)')))}</div>
        </div>
        <div class="extra-card">
          <div class="extra-label">Margem bruta %</div>
          <div class="extra-value">{fmt_pct(gh['margem_pct'])}</div>
          <div class="extra-sub">vs meta {fmt_pct(alvo_mb_gh, 0)}* · {fmt_brl_short(gh['margem_total'])} de margem</div>
          <div class="extra-status">{render_status_badge(bm_gh.get('status_margem_bruta', ('-', 'var(--ink-mute)')))}</div>
        </div>
        <div class="extra-card highlight">
          <div class="extra-label">⭐ Margem líquida sobre fat</div>
          <div class="extra-value" style="color:var(--gran-dourado)">{fmt_pct(gh['margem_liquida_pct_sobre_fat'])}</div>
          <div class="extra-sub">{fmt_brl_short(gh['margem_liquida'])} sobra após mercadoria + pessoal</div>
        </div>
      </div>
    </div>
    <div class="equipe-info">
      <div class="equipe-nome">Gran Horti</div>
      <div class="equipe-sub">{gh['n_funcionarios_clt']} func · operação de varejo geral · benchmark: varejo alimentar premium top quartil</div>
      <div class="equipe-kpis">
        <div class="equipe-kpi"><div class="kpi-label">Faturamento</div><div class="kpi-value">{fmt_brl_short(gh['fat_total'])}</div><div class="kpi-pct">{fmt_pct(pct_fat_gh, 0)} do total</div></div>
        <div class="equipe-kpi"><div class="kpi-label">Margem R$</div><div class="kpi-value">{fmt_brl_short(gh['margem_total'])}</div><div class="kpi-pct">{fmt_pct(pct_mar_gh, 0)} da margem</div></div>
        <div class="equipe-kpi"><div class="kpi-label">Margem %</div><div class="kpi-value" style="color:var(--amarelo)">{fmt_pct(gh['margem_pct'])}</div><div class="kpi-pct">sobre faturamento</div></div>
        <div class="equipe-kpi"><div class="kpi-label">Custo Pessoal</div><div class="kpi-value">{fmt_brl_short(gh['custo_total'])}</div><div class="kpi-pct">{fmt_pct(pct_custo_gh, 0)} do total</div></div>
      </div>
    </div>
  </div>

  <div class="kpi-row">
    <div class="kpi-big">
      <div class="kpi-big-label">Faturamento total · {p['periodo_analise_dias']}d</div>
      <div class="kpi-big-value">{fmt_brl(tot['fat_total'])}</div>
      <div class="kpi-big-sub">KW + Omie</div>
    </div>
    <div class="kpi-big">
      <div class="kpi-big-label">Margem total · {p['periodo_analise_dias']}d</div>
      <div class="kpi-big-value">{fmt_brl(tot['margem_total'])}</div>
      <div class="kpi-big-sub">{fmt_pct(tot['margem_pct'])} sobre faturamento</div>
    </div>
    <div class="kpi-big">
      <div class="kpi-big-label">Margem líquida (após pessoal)</div>
      <div class="kpi-big-value" style="color:var(--gran-dourado)">{fmt_brl(tot['margem_liquida'])}</div>
      <div class="kpi-big-sub">{fmt_pct(tot['margem_liquida_pct_sobre_fat'])} sobre faturamento</div>
    </div>
    <div class="kpi-big">
      <div class="kpi-big-label">Total Gran · % margem → pessoal</div>
      <div class="kpi-big-value" style="color:{cor_termometro(tot['custo_sobre_margem_pct'], crit, warn)}">{fmt_pct(tot['custo_sobre_margem_pct'])}</div>
      <div class="kpi-big-sub">média ponderada da loja</div>
    </div>
  </div>

  <div class="compara-grid">
    <div class="compara-card">
      <div class="compara-titulo">Margem gerada por funcionário</div>
      <div class="compara-bar-wrap">
        <div class="compara-eq">Gran Mesa</div>
        <div class="compara-bar"><div class="compara-bar-fill" style="background:var(--gran-verde-3); width:{gm['margem_por_func']/max(gm['margem_por_func'],gh['margem_por_func'])*100:.0f}%">{fmt_brl_short(gm['margem_por_func'])}</div></div>
      </div>
      <div class="compara-bar-wrap">
        <div class="compara-eq">Gran Horti</div>
        <div class="compara-bar"><div class="compara-bar-fill" style="background:var(--gran-dourado); width:{gh['margem_por_func']/max(gm['margem_por_func'],gh['margem_por_func'])*100:.0f}%">{fmt_brl_short(gh['margem_por_func'])}</div></div>
      </div>
    </div>
    <div class="compara-card">
      <div class="compara-titulo">Margem gerada por R$ 1 de pessoal</div>
      <div class="compara-bar-wrap">
        <div class="compara-eq">Gran Mesa</div>
        <div class="compara-bar"><div class="compara-bar-fill" style="background:var(--gran-verde-3); width:{gm['margem_sobre_custo_x']/max(gm['margem_sobre_custo_x'],gh['margem_sobre_custo_x'])*100:.0f}%">R$ {gm['margem_sobre_custo_x']:.2f}</div></div>
      </div>
      <div class="compara-bar-wrap">
        <div class="compara-eq">Gran Horti</div>
        <div class="compara-bar"><div class="compara-bar-fill" style="background:var(--gran-dourado); width:{gh['margem_sobre_custo_x']/max(gm['margem_sobre_custo_x'],gh['margem_sobre_custo_x'])*100:.0f}%">R$ {gh['margem_sobre_custo_x']:.2f}</div></div>
      </div>
    </div>
  </div>

  <div class="leitura-final">
    <p>{leitura_txt}</p>
  </div>

  <p class="section-kicker" style="margin-top:28px">🤔 Hipóteses para investigação</p>
  <h3 class="section-title" style="font-size:18px">Por que essa diferença?</h3>
  <div class="hipoteses-grid">
    <div class="hipotese"><div class="hipotese-titulo"><span class="hipotese-letra">A</span> Sub-escala</div><div class="hipotese-texto">Gran Mesa Pro cresceu de R$ 32k → R$ 70k em 4 meses. Se chegar a R$ 130k/mês, KPI da Gran Mesa cai pra ~30%.</div></div>
    <div class="hipotese"><div class="hipotese-titulo"><span class="hipotese-letra">B</span> Quadro inflado</div><div class="hipotese-texto">{gm['n_funcionarios_clt']} pessoas pra operação atual pode ser excessivo. Veja Cenário B na aba 04.</div></div>
    <div class="hipotese"><div class="hipotese-titulo"><span class="hipotese-letra">C</span> Mistura de funções</div><div class="hipotese-texto">Parte da Gran Mesa pode estar tocando atividade da Gran Horti. Custo mal alocado.</div></div>
    <div class="hipotese"><div class="hipotese-titulo"><span class="hipotese-letra">D</span> SKUs alocados errado</div><div class="hipotese-texto">Produtos lucrativos hoje contabilizados na Gran Horti que vieram da Gran Mesa. Veja Cenário D.</div></div>
  </div>

  {qd_warn}
</div>

<!-- ═══════════════════ ABA 2: COMPOSIÇÃO ═══════════════════ -->
<div id="tab-2" class="tab-panel">
  <p class="section-kicker">📊 Composição por Equipe</p>
  <h2 class="section-title">De onde vem o dinheiro e pra onde vai</h2>
  <p class="section-desc">Quebra detalhada do faturamento por grupo, custo, e o destino de cada R$ que entra na loja.</p>

  <div class="composicao-section">
    <h3>① Faturamento — De onde vem (por grupo do KW)</h3>
    <div class="sub-desc">Cada barra mostra os principais grupos que compõem o faturamento KW de cada equipe. Passe o mouse pra ver detalhes.</div>

    <div class="equipe-grupos-bloco">
      <div class="equipe-grupos-titulo">
        <span>🍽️ Gran Mesa — KW (loja)</span>
        <span class="equipe-grupos-total">{fmt_brl(gm['fat_kw'])}</span>
      </div>
      {render_grupos_bar(d['grupos_fat']['gran_mesa'], 'gm', 'gm')}
      <div class="grupos-omie">
        + <strong>Omie Gran Mesa Pro</strong> (B2B refeições coletivas) = {fmt_brl(gm['fat_gmpro'])} fora do KW
      </div>
    </div>

    <div class="equipe-grupos-bloco">
      <div class="equipe-grupos-titulo">
        <span>🥬 Gran Horti — KW (loja)</span>
        <span class="equipe-grupos-total">{fmt_brl(gh['fat_kw'])}</span>
      </div>
      {render_grupos_bar(d['grupos_fat']['gran_horti'], 'gh', 'gh')}
    </div>
  </div>

  <div class="composicao-section">
    <h3>② Margem — Quanto sobra após pagar mercadoria</h3>
    <div class="sub-desc">Margem = Faturamento − CMV. Gran Mesa tem margem maior (produção própria). Gran Horti tem volume maior.</div>
    <div class="stacked-row">
      <div class="stacked-label">Gran Mesa</div>
      <div class="stacked-bar">
        <div class="stacked-seg" style="background:var(--gran-verde); width:{gm['margem_total']/gm['fat_total']*100:.1f}%">Margem {fmt_brl_short(gm['margem_total'])} ({fmt_pct(gm['margem_pct'])})</div>
        <div class="stacked-seg" style="background:var(--ink-mute); width:{(1-gm['margem_total']/gm['fat_total'])*100:.1f}%">CMV {fmt_brl_short(gm['fat_total']-gm['margem_total'])}</div>
      </div>
      <div class="stacked-total">{fmt_brl(gm['fat_total'])}</div>
    </div>
    <div class="stacked-row">
      <div class="stacked-label">Gran Horti</div>
      <div class="stacked-bar">
        <div class="stacked-seg" style="background:var(--gran-verde-3); width:{gh['margem_total']/gh['fat_total']*100:.1f}%">Margem {fmt_brl_short(gh['margem_total'])} ({fmt_pct(gh['margem_pct'])})</div>
        <div class="stacked-seg" style="background:var(--ink-mute); width:{(1-gh['margem_total']/gh['fat_total'])*100:.1f}%">CMV {fmt_brl_short(gh['fat_total']-gh['margem_total'])}</div>
      </div>
      <div class="stacked-total">{fmt_brl(gh['fat_total'])}</div>
    </div>
  </div>

  <div class="composicao-section">
    <h3>③ Destino do faturamento total — Pra onde vai cada R$</h3>
    <div class="sub-desc">Visualização do faturamento total de <strong>{fmt_brl(tot['fat_total'])}</strong> dividido em CMV (mercadoria), Custo Pessoal e Margem Líquida que sobra. Passe o mouse pra ver cada bloco.</div>
    <div id="destino-fat"></div>
    <div id="destino-tooltip" class="destino-tooltip"></div>
    <div class="legenda" style="margin-top:14px">
      <div class="leg-item"><div class="leg-dot" style="background:var(--ink-mute)"></div>CMV — pra fornecedores ({fmt_pct(tot['cmv_total']/tot['fat_total']*100)})</div>
      <div class="leg-item"><div class="leg-dot" style="background:var(--vermelho)"></div>Custo Pessoal — folha + diaristas + retag ({fmt_pct(tot['custo_total']/tot['fat_total']*100)})</div>
      <div class="leg-item"><div class="leg-dot" style="background:var(--gran-dourado)"></div>Margem Líquida — sobra ({fmt_pct(tot['margem_liquida']/tot['fat_total']*100)})</div>
    </div>
  </div>

  <div class="composicao-section">
    <h3>④ Custo Pessoal — Composição</h3>
    <div class="sub-desc">Salário × {p['fator_encargos_clt']} (encargos). Diaristas R$ {p['custo_diaristas_gran_mesa']:.0f} fixo na GM. Retaguarda rateada pró-rata por faturamento.</div>
    <div class="stacked-row">
      <div class="stacked-label">Gran Mesa</div>
      <div class="stacked-bar">
        <div class="stacked-seg" style="background:var(--gran-verde); width:{gm['custo_folha']/gm['custo_total']*100:.1f}%">CLT {fmt_brl_short(gm['custo_folha'])}</div>
        <div class="stacked-seg" style="background:var(--gran-dourado); width:{gm['custo_diaristas']/gm['custo_total']*100:.1f}%">Diar {fmt_brl_short(gm['custo_diaristas'])}</div>
        <div class="stacked-seg" style="background:var(--ink-mute); width:{gm['custo_retag_rateio']/gm['custo_total']*100:.1f}%">Retag {fmt_brl_short(gm['custo_retag_rateio'])}</div>
      </div>
      <div class="stacked-total">{fmt_brl(gm['custo_total'])}</div>
    </div>
    <div class="stacked-row">
      <div class="stacked-label">Gran Horti</div>
      <div class="stacked-bar">
        <div class="stacked-seg" style="background:var(--gran-verde-3); width:{gh['custo_folha']/gh['custo_total']*100:.1f}%">CLT {fmt_brl_short(gh['custo_folha'])}</div>
        <div class="stacked-seg" style="background:var(--ink-mute); width:{gh['custo_retag_rateio']/gh['custo_total']*100:.1f}%">Retag {fmt_brl_short(gh['custo_retag_rateio'])}</div>
      </div>
      <div class="stacked-total">{fmt_brl(gh['custo_total'])}</div>
    </div>
  </div>

  <div class="composicao-section">
    <h3>⑤ Mapa da Equipe — Quem pesa mais no orçamento</h3>
    <div class="sub-desc">Cada retângulo é uma pessoa. Tamanho proporcional ao custo total empresa. Cor identifica a equipe. Passe o mouse pra detalhes.</div>
    <div id="treemap-funcs"></div>
    <div id="treemap-tooltip" class="treemap-tooltip"></div>
    <div class="legenda" style="margin-top:18px">
      <div class="leg-item"><div class="leg-dot" style="background:var(--gran-verde)"></div>Gran Mesa</div>
      <div class="leg-item"><div class="leg-dot" style="background:var(--gran-dourado)"></div>Gran Horti</div>
      <div class="leg-item"><div class="leg-dot" style="background:var(--ink-mute)"></div>Retaguarda (rateada)</div>
    </div>
  </div>

  <div class="composicao-section">
    <h3>⑥ Lista Nominal · {len(d['funcionarios'])} pessoas</h3>
    <div class="sub-desc">Funcionários separados por equipe e ordem alfabética. Subtotais ao final de cada bloco.</div>
    {lista_nominal_por_equipe()}
  </div>
</div>

<!-- ═══════════════════ ABA 3: HERÓIS, MENOS VENDIDOS, VILÕES ═══════════════════ -->
<div id="tab-3" class="tab-panel">
  <p class="section-kicker">⚔️ Heróis e Vilões</p>
  <h2 class="section-title">Quem puxa, quem ocupa, quem atrapalha</h2>
  <p class="section-desc">Heróis (mais margem), Menos Vendidos (baixo giro com simulação de hora) e Vilões (margem perdida vs média da equipe).</p>

  <div class="heroes-grid">
    <div class="heroes-section">
      <h3><span class="heroes-icone">🍽️</span> Top 10 Heróis · Gran Mesa</h3>
      <div class="heroes-resumo">Os 10 puxam <strong>{fmt_brl_short(soma_top_gm)}</strong> em margem — <strong>{fmt_pct(pct_top_gm)}</strong> da margem total da Gran Mesa</div>
      <table>
        <thead><tr><th>Cód</th><th>Descrição</th><th class="num">Fat</th><th class="num">Margem</th><th class="num">Marg %</th></tr></thead>
        <tbody>{render_top(d['top_skus']['gran_mesa'])}</tbody>
      </table>
    </div>
    <div class="heroes-section">
      <h3><span class="heroes-icone">🥬</span> Top 10 Heróis · Gran Horti</h3>
      <div class="heroes-resumo">Os 10 puxam <strong>{fmt_brl_short(soma_top_gh)}</strong> em margem — <strong>{fmt_pct(pct_top_gh)}</strong> da margem total da Gran Horti</div>
      <table>
        <thead><tr><th>Cód</th><th>Descrição</th><th class="num">Fat</th><th class="num">Margem</th><th class="num">Marg %</th></tr></thead>
        <tbody>{render_top(d['top_skus']['gran_horti'])}</tbody>
      </table>
    </div>
  </div>

  <div class="menos-vendidos-section">
    <h3>📉 Menos Vendidos · Candidatos a tirar do mix</h3>
    <div class="sub-desc">Produtos da Gran Mesa com baixíssimo giro (&lt; {p.get('limite_baixo_giro_kg_30d', 5)}kg em 30d). Ocupam capacidade da equipe sem contribuir.</div>
    <div class="sim-pill">⚠️ SIMULAÇÃO — 1h × R$ 15 / kg vendido (apenas nesta tabela)</div>
    <table>
      <thead>
        <tr><th>Cód</th><th>Descrição</th><th class="num">Qtd 30d</th><th class="num">Fat</th><th class="num">Margem</th><th class="num">Horas est.</th><th class="num">Custo da hora</th><th class="num">Margem após hora</th></tr>
      </thead>
      <tbody>{render_menos_vendidos(d.get('menos_vendidos_gran_mesa', []))}</tbody>
    </table>
  </div>

  <div class="viloes-section">
    <h3>🎯 Vilões da Gran Mesa · Margem perdida vs média da equipe</h3>
    <div class="sub-desc">Produtos cuja margem está abaixo da média da equipe ({fmt_pct(d['viloes_gran_mesa'][0]['margem_pct_ref']) if d['viloes_gran_mesa'] else 'n/a'}). Score = potencial de margem perdida em R$.</div>
    {render_viloes(d['viloes_gran_mesa'])}
  </div>
</div>

<!-- ═══════════════════ ABA 4: SENSIBILIDADE ═══════════════════ -->
<div id="tab-4" class="tab-panel">
  <p class="section-kicker">🎚️ Análise de Cenários</p>
  <h2 class="section-title">O que precisa acontecer pra equilibrar?</h2>
  <p class="section-desc">Como o KPI principal muda em diferentes cenários. Linha tracejada dourada = Gran Horti (alvo). Números visíveis nos pontos.</p>

  <div class="sens-intro">
    <strong>Hoje:</strong> Gran Mesa em <strong style="color:{cor_termometro(gm['custo_sobre_margem_pct'], crit, warn)}">{fmt_pct(gm['custo_sobre_margem_pct'])}</strong>
    · Gran Horti em <strong style="color:{cor_termometro(gh['custo_sobre_margem_pct'], crit, warn)}">{fmt_pct(gh['custo_sobre_margem_pct'])}</strong>
    · Diferença <strong>{abs(gm['custo_sobre_margem_pct']-gh['custo_sobre_margem_pct']):.1f}pp</strong>
  </div>

  <div class="sens-charts">
    <div class="sens-chart-card">
      <h4>📈 Cenário A · Crescimento Gran Mesa Pro</h4>
      <div class="sens-sub">Faturamento Omie aumenta — KPI Gran Mesa cai</div>
      <div class="sens-chart-canvas"><canvas id="chart-sens-a"></canvas></div>
      <div class="sens-leitura">Hipótese de <strong>sub-escala</strong>: GMPro a <strong>~R$ 130k/mês</strong> equilibra com Gran Horti.</div>
    </div>
    <div class="sens-chart-card">
      <h4>👥 Cenário B · Redução de Quadro</h4>
      <div class="sens-sub">Cada funcionário a menos derruba o KPI</div>
      <div class="sens-chart-canvas"><canvas id="chart-sens-b"></canvas></div>
      <div class="sens-leitura">Hipótese de <strong>quadro inflado</strong>: corte de 1 cabeça leva o KPI pra ~36-38%.</div>
    </div>
    <div class="sens-chart-card">
      <h4>🔀 Cenário C · Realocação de Funções</h4>
      <div class="sens-sub">% custo Gran Mesa que efetivamente trabalha pra Gran Horti</div>
      <div class="sens-chart-canvas"><canvas id="chart-sens-c"></canvas></div>
      <div class="sens-leitura">Hipótese de <strong>mistura</strong>: 30% do tempo da GM beneficiando GH derruba o KPI.</div>
    </div>
    <div class="sens-chart-card">
      <h4>↩️ Cenário D · Migração de SKUs lucrativos</h4>
      <div class="sens-sub">% do fat Gran Horti que volta pra Gran Mesa</div>
      <div class="sens-chart-canvas"><canvas id="chart-sens-d"></canvas></div>
      <div class="sens-leitura">Hipótese de <strong>SKUs alocados errado</strong>: 15% migrado equilibra os dois KPIs.</div>
    </div>
  </div>
</div>

<footer>
  <div class="footer-cols">
    <div>
      <strong>Premissas usadas (editáveis em parametros.json):</strong><br>
      • Custo total empresa = Total Vencimentos × {p['fator_encargos_clt']}<br>
      • CMV Gran Mesa Pro = {fmt_pct(p['cmv_gmpro_pct']*100)} → margem {fmt_pct((1-p['cmv_gmpro_pct'])*100)}<br>
      • Diaristas Gran Mesa = R$ {p['custo_diaristas_gran_mesa']:.0f}/mês<br>
      • Rateio Retaguarda = pró-rata por faturamento<br>
      • Padaria Gran (14 itens, exceto cód 760) = 65% Gran Mesa / 35% Gran Horti<br>
      • Cód 760 (PAO DELICIA GRAN KG) = 100% Gran Horti<br>
      • Período = {p['periodo_analise_dias']} dias rolling
    </div>
    <div>
      <strong>Qualidade do dado:</strong><br>
      • Cobertura P. Custo: {fmt_pct(qd['cobertura_pcusto_pct'])}<br>
      • Fat sem custo: {fmt_pct(qd['fat_sem_pcusto_pct'])}<br>
      • Fonte KW: {fonte_kw_label}<br><br>
      Plugin <strong>produtividade-gran v1.4.0</strong><br>
      Grupo A7 / Gran Hortifruti
    </div>
  </div>
  <div style="margin-top: 18px; padding-top: 14px; border-top: 1px solid var(--border); font-size: 11px;">
    <strong>* Sobre os benchmarks:</strong> os alvos marcados com asterisco são referências <strong>aspiracionais (top quartil)</strong>, não médias do setor. Servem como meta a perseguir, não como linha mínima.
    Para Gran Horti uso ABRAS Ranking 2025 (top performers do varejo alimentar brasileiro) e SEBRAE Guia de Indicadores para Varejo.
    Para Gran Mesa, dado público brasileiro de cozinha industrial é escasso — uso ABERC 2023 (estrutura típica de custos) cruzado com benchmarks de foodservice top quartil de mercados emergentes (catering full-service Latam/global).
    Como toda referência cruzada, os números são <strong>indicativos</strong> e devem ser revisados anualmente em parametros.json.
  </div>
</footer>

</div>

<script>
const FUNCS_DATA = {funcs_data};
const DESTINO_FAT = {destino_fat_json};

function showTab(evt, tabId) {{
  document.querySelectorAll('.tab-panel').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.getElementById(tabId).classList.add('active');
  evt.target.closest('.tab').classList.add('active');
  if (tabId === 'tab-2') {{ setTimeout(() => {{ renderDestinoFat(); renderTreemap(); }}, 50); }}
  if (tabId === 'tab-4') {{ setTimeout(renderSensCharts, 50); }}
}}

// Tooltip helper
function setupTooltip(container, tooltip) {{
  container.addEventListener('mouseleave', () => {{ tooltip.style.opacity = 0; }});
}}

// ─── Destino do Faturamento (3 grandes blocos: CMV / Pessoal / Margem) ───
function renderDestinoFat() {{
  const container = document.getElementById('destino-fat');
  if (!container) return;
  const tooltip = document.getElementById('destino-tooltip');
  const W = container.clientWidth || 1200;
  const H = 280;
  const total = DESTINO_FAT.fat_total;
  const wCMV = (DESTINO_FAT.cmv_total / total) * W;
  const wPess = (DESTINO_FAT.custo_pessoal / total) * W;
  const wMarg = (DESTINO_FAT.margem_liquida / total) * W;

  let svg = `<svg width="${{W}}" height="${{H}}" xmlns="http://www.w3.org/2000/svg" style="display:block;border-radius:8px;overflow:hidden;background:var(--bg-soft)">`;
  // Header com total
  svg += `<rect x="0" y="0" width="${{W}}" height="36" fill="var(--gran-verde)"/>`;
  svg += `<text x="${{W/2}}" y="23" fill="white" font-size="14" font-weight="700" text-anchor="middle" font-family="Aptos,sans-serif">FATURAMENTO TOTAL · R$ ${{total.toLocaleString('pt-BR',{{minimumFractionDigits:2,maximumFractionDigits:2}})}}</text>`;

  const yBase = 36;
  const innerH = H - yBase;

  // Bloco CMV (cinza)
  svg += `<g class="destino-bloco" data-titulo="CMV (mercadoria)" data-valor="${{DESTINO_FAT.cmv_total}}" data-total="${{total}}" data-detalhe="GM: R$ ${{DESTINO_FAT.cmv_por_equipe.gran_mesa.toLocaleString('pt-BR',{{minimumFractionDigits:2,maximumFractionDigits:2}})}} · GH: R$ ${{DESTINO_FAT.cmv_por_equipe.gran_horti.toLocaleString('pt-BR',{{minimumFractionDigits:2,maximumFractionDigits:2}})}}">`;
  svg += `<rect x="0" y="${{yBase}}" width="${{wCMV-1}}" height="${{innerH}}" fill="#8b8f86" opacity="0.85"/>`;
  if (wCMV > 100) {{
    svg += `<text x="${{wCMV/2}}" y="${{yBase + innerH/2 - 8}}" fill="white" font-size="14" font-weight="700" text-anchor="middle" font-family="Aptos,sans-serif">CMV (mercadoria)</text>`;
    svg += `<text x="${{wCMV/2}}" y="${{yBase + innerH/2 + 14}}" fill="white" font-size="20" font-weight="800" text-anchor="middle" font-family="Aptos,sans-serif">R$ ${{(DESTINO_FAT.cmv_total/1000).toFixed(0)}}k</text>`;
    svg += `<text x="${{wCMV/2}}" y="${{yBase + innerH/2 + 36}}" fill="white" opacity="0.85" font-size="12" text-anchor="middle" font-family="JetBrains Mono,monospace">${{(DESTINO_FAT.cmv_total/total*100).toFixed(1).replace('.',',')}}% do faturamento</text>`;
  }}
  svg += `</g>`;

  // Bloco Custo Pessoal (vermelho)
  svg += `<g class="destino-bloco" data-titulo="Custo Pessoal" data-valor="${{DESTINO_FAT.custo_pessoal}}" data-total="${{total}}" data-detalhe="GM: R$ ${{DESTINO_FAT.pessoal_por_equipe.gran_mesa.toLocaleString('pt-BR',{{minimumFractionDigits:2,maximumFractionDigits:2}})}} · GH: R$ ${{DESTINO_FAT.pessoal_por_equipe.gran_horti.toLocaleString('pt-BR',{{minimumFractionDigits:2,maximumFractionDigits:2}})}}">`;
  svg += `<rect x="${{wCMV}}" y="${{yBase}}" width="${{wPess-1}}" height="${{innerH}}" fill="#b8362f" opacity="0.85"/>`;
  if (wPess > 80) {{
    svg += `<text x="${{wCMV + wPess/2}}" y="${{yBase + innerH/2 - 8}}" fill="white" font-size="13" font-weight="700" text-anchor="middle" font-family="Aptos,sans-serif">Custo Pessoal</text>`;
    svg += `<text x="${{wCMV + wPess/2}}" y="${{yBase + innerH/2 + 14}}" fill="white" font-size="18" font-weight="800" text-anchor="middle" font-family="Aptos,sans-serif">R$ ${{(DESTINO_FAT.custo_pessoal/1000).toFixed(0)}}k</text>`;
    svg += `<text x="${{wCMV + wPess/2}}" y="${{yBase + innerH/2 + 34}}" fill="white" opacity="0.85" font-size="11" text-anchor="middle" font-family="JetBrains Mono,monospace">${{(DESTINO_FAT.custo_pessoal/total*100).toFixed(1).replace('.',',')}}%</text>`;
  }}
  svg += `</g>`;

  // Bloco Margem Líquida (dourado)
  svg += `<g class="destino-bloco" data-titulo="Margem Líquida (sobra)" data-valor="${{DESTINO_FAT.margem_liquida}}" data-total="${{total}}" data-detalhe="GM: R$ ${{DESTINO_FAT.margem_liquida_por_equipe.gran_mesa.toLocaleString('pt-BR',{{minimumFractionDigits:2,maximumFractionDigits:2}})}} · GH: R$ ${{DESTINO_FAT.margem_liquida_por_equipe.gran_horti.toLocaleString('pt-BR',{{minimumFractionDigits:2,maximumFractionDigits:2}})}}">`;
  svg += `<rect x="${{wCMV+wPess}}" y="${{yBase}}" width="${{wMarg}}" height="${{innerH}}" fill="#c9a227"/>`;
  if (wMarg > 100) {{
    svg += `<text x="${{wCMV + wPess + wMarg/2}}" y="${{yBase + innerH/2 - 8}}" fill="white" font-size="14" font-weight="700" text-anchor="middle" font-family="Aptos,sans-serif">⭐ Margem Líquida</text>`;
    svg += `<text x="${{wCMV + wPess + wMarg/2}}" y="${{yBase + innerH/2 + 14}}" fill="white" font-size="20" font-weight="800" text-anchor="middle" font-family="Aptos,sans-serif">R$ ${{(DESTINO_FAT.margem_liquida/1000).toFixed(0)}}k</text>`;
    svg += `<text x="${{wCMV + wPess + wMarg/2}}" y="${{yBase + innerH/2 + 36}}" fill="white" opacity="0.9" font-size="12" text-anchor="middle" font-family="JetBrains Mono,monospace">${{(DESTINO_FAT.margem_liquida/total*100).toFixed(1).replace('.',',')}}% do faturamento</text>`;
  }}
  svg += `</g>`;

  svg += `</svg>`;
  container.innerHTML = svg;

  // Bind tooltips
  container.querySelectorAll('.destino-bloco').forEach(el => {{
    el.addEventListener('mousemove', e => {{
      const rect = container.getBoundingClientRect();
      const t = el.dataset.titulo;
      const v = parseFloat(el.dataset.valor);
      const total = parseFloat(el.dataset.total);
      const det = el.dataset.detalhe;
      tooltip.innerHTML = `<strong>${{t}}</strong>R$ ${{v.toLocaleString('pt-BR',{{minimumFractionDigits:2,maximumFractionDigits:2}})}} · ${{(v/total*100).toFixed(1).replace('.',',')}}% do total<br>${{det}}`;
      tooltip.style.left = (e.clientX - rect.left + 14) + 'px';
      tooltip.style.top = (e.clientY - rect.top - 36) + 'px';
      tooltip.style.opacity = 1;
    }});
    el.addEventListener('mouseleave', () => {{ tooltip.style.opacity = 0; }});
  }});
}}

// ─── Treemap de Funcionários ───
function renderTreemap() {{
  const container = document.getElementById('treemap-funcs');
  if (!container) return;
  const tooltip = document.getElementById('treemap-tooltip');
  const W = container.clientWidth || 1200;
  const H = 480;
  const corMap = {{ 'Gran Mesa': '#1e4d2b', 'Gran Horti': '#c9a227', 'Retaguarda': '#8b8f86' }};
  const byEq = {{ 'Gran Mesa': [], 'Gran Horti': [], 'Retaguarda': [] }};
  FUNCS_DATA.forEach(d => {{ if (byEq[d.equipe]) byEq[d.equipe].push(d); }});
  const totGM = byEq['Gran Mesa'].reduce((s,d)=>s+d.value,0);
  const totGH = byEq['Gran Horti'].reduce((s,d)=>s+d.value,0);
  const totRT = byEq['Retaguarda'].reduce((s,d)=>s+d.value,0);
  const total3 = totGM + totGH + totRT;
  if (total3 === 0) return;
  const wGM = (totGM/total3) * W;
  const wGH = (totGH/total3) * W;
  const wRT = (totRT/total3) * W;
  let svg = `<svg width="${{W}}" height="${{H}}" xmlns="http://www.w3.org/2000/svg" style="display:block;border-radius:8px;overflow:hidden;background:var(--bg-soft)">`;
  function renderColumn(arr, eqName, x, w) {{
    const tot = arr.reduce((s,d)=>s+d.value,0);
    if (tot === 0 || arr.length === 0) return;
    let y = 0;
    svg += `<rect x="${{x}}" y="0" width="${{w}}" height="34" fill="${{corMap[eqName]}}"/>`;
    svg += `<text x="${{x+w/2}}" y="22" fill="white" font-size="13" font-weight="700" text-anchor="middle" font-family="Aptos,sans-serif">${{eqName}} · ${{arr.length}} pessoas · R$ ${{(tot/1000).toFixed(1).replace('.',',')}}k</text>`;
    y = 34;
    const innerH = H - 34;
    arr.sort((a,b) => b.value - a.value).forEach((d, i) => {{
      const h = (d.value / tot) * innerH;
      const opacity = 0.55 + (0.45 * (1 - i/Math.max(1,arr.length-1)));
      const dataAttrs = `data-fullname="${{d.fullname.replace(/"/g, '&quot;')}}" data-funcao="${{d.funcao.replace(/"/g, '&quot;')}}" data-valor="${{d.value}}" data-equipe="${{eqName}}"`;
      svg += `<rect class="func-rect" x="${{x+1}}" y="${{y}}" width="${{w-2}}" height="${{h-1}}" fill="${{corMap[eqName]}}" opacity="${{opacity}}" stroke="white" stroke-width="1" ${{dataAttrs}}/>`;
      if (h > 26 && w > 80) {{
        const fontSize = h > 60 ? 13 : (h > 40 ? 11 : 10);
        const txtCor = opacity > 0.7 ? 'white' : '#1a1f1a';
        const nome = d.name.substring(0,20);
        svg += `<text x="${{x+8}}" y="${{y+fontSize+4}}" fill="${{txtCor}}" font-size="${{fontSize}}" font-weight="600" font-family="Aptos,sans-serif" pointer-events="none">${{nome}}</text>`;
        if (h > 50) {{
          svg += `<text x="${{x+8}}" y="${{y+fontSize+18}}" fill="${{txtCor}}" font-size="10" font-family="JetBrains Mono,monospace" opacity="0.85" pointer-events="none">R$ ${{(d.value/1000).toFixed(1).replace('.',',')}}k</text>`;
        }}
      }}
      y += h;
    }});
  }}
  if (totGM > 0) renderColumn(byEq['Gran Mesa'], 'Gran Mesa', 0, wGM);
  if (totGH > 0) renderColumn(byEq['Gran Horti'], 'Gran Horti', wGM, wGH);
  if (totRT > 0) renderColumn(byEq['Retaguarda'], 'Retaguarda', wGM+wGH, wRT);
  svg += `</svg>`;
  container.innerHTML = svg;

  // Bind tooltip via JS (em vez de <title> nativo)
  container.querySelectorAll('.func-rect').forEach(el => {{
    el.style.cursor = 'pointer';
    el.addEventListener('mousemove', e => {{
      const rect = container.getBoundingClientRect();
      const fname = el.dataset.fullname;
      const fn = el.dataset.funcao;
      const v = parseFloat(el.dataset.valor);
      const eq = el.dataset.equipe;
      tooltip.innerHTML = `<strong>${{fname}}</strong>${{fn}}<br>${{eq}} · R$ ${{v.toLocaleString('pt-BR',{{minimumFractionDigits:2,maximumFractionDigits:2}})}}`;
      tooltip.style.left = (e.clientX - rect.left + 14) + 'px';
      tooltip.style.top = (e.clientY - rect.top - 50) + 'px';
      tooltip.style.opacity = 1;
    }});
    el.addEventListener('mouseleave', () => {{ tooltip.style.opacity = 0; }});
  }});
}}

let sensChartsRendered = false;
function renderSensCharts() {{
  if (sensChartsRendered) return;
  sensChartsRendered = true;
  // Registrar plugin globalmente
  if (window.ChartDataLabels) {{ Chart.register(window.ChartDataLabels); }}
  const dataA = {chart_sens_a};
  const dataB = {chart_sens_b};
  const dataC = {chart_sens_c};
  const dataD = {chart_sens_d};
  const refGH = {referencia_gh};

  function makeChart(canvasId, dataObj, xLabel, yLabel, secondLine = null) {{
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    const datasets = [
      {{
        label: 'KPI Gran Mesa',
        data: dataObj.data || dataObj.data_gm,
        borderColor: '#1e4d2b',
        backgroundColor: 'rgba(30,77,43,0.08)',
        borderWidth: 3, pointRadius: 7, pointBackgroundColor: '#1e4d2b',
        pointBorderColor: 'white', pointBorderWidth: 2, tension: 0.3, fill: true,
        datalabels: {{
          align: 'top', anchor: 'end', offset: 4,
          color: '#1e4d2b', font: {{ family: 'Aptos, sans-serif', size: 11, weight: 700 }},
          formatter: (v) => v.toFixed(1).replace('.',',') + '%',
          backgroundColor: 'rgba(255,255,255,0.85)', borderRadius: 4, padding: {{top:2,bottom:2,left:5,right:5}}
        }}
      }},
      {{
        label: 'Gran Horti (referência)',
        data: dataObj.labels.map(() => refGH),
        borderColor: '#c9a227', borderDash: [6, 4],
        borderWidth: 2, pointRadius: 0, fill: false,
        datalabels: {{ display: false }}
      }}
    ];
    if (secondLine) {{
      datasets.splice(1, 0, {{
        label: 'KPI Gran Horti (cenário)',
        data: secondLine,
        borderColor: '#c9a227', backgroundColor: 'rgba(201,162,39,0.08)',
        borderWidth: 2, pointRadius: 5, pointBackgroundColor: '#c9a227',
        pointBorderColor: 'white', pointBorderWidth: 1, tension: 0.3, fill: false,
        datalabels: {{
          align: 'bottom', anchor: 'start', offset: 4,
          color: '#8a6500', font: {{ family: 'Aptos, sans-serif', size: 10, weight: 600 }},
          formatter: (v) => v.toFixed(1).replace('.',',') + '%',
          backgroundColor: 'rgba(250,241,212,0.9)', borderRadius: 4, padding: {{top:2,bottom:2,left:5,right:5}}
        }}
      }});
    }}
    new Chart(ctx, {{
      type: 'line',
      data: {{ labels: dataObj.labels, datasets: datasets }},
      options: {{
        responsive: true, maintainAspectRatio: false,
        layout: {{ padding: {{ top: 18, bottom: 4, left: 4, right: 8 }} }},
        plugins: {{
          legend: {{ position: 'top', labels: {{ font: {{family: 'Aptos, sans-serif', size: 11}}, usePointStyle: true, padding: 12 }} }},
          tooltip: {{ callbacks: {{ label: ctx => `${{ctx.dataset.label}}: ${{ctx.parsed.y.toFixed(1).replace('.',',')}}%` }} }}
        }},
        scales: {{
          x: {{
            title: {{ display: true, text: xLabel, color: '#8b8f86', font: {{size: 11}} }},
            grid: {{ display: false }},
            ticks: {{ color: '#4a5248', font: {{family: 'JetBrains Mono', size: 10}} }}
          }},
          y: {{
            title: {{ display: true, text: yLabel, color: '#8b8f86', font: {{size: 11}} }},
            ticks: {{ color: '#4a5248', font: {{family: 'JetBrains Mono', size: 10}}, callback: v => v.toFixed(1).replace('.',',') + '%' }},
            grid: {{ color: '#f0ebdc' }}
          }}
        }}
      }}
    }});
  }}

  makeChart('chart-sens-a', dataA, 'Faturamento GMPro (R$)', '% margem → pessoal');
  makeChart('chart-sens-b', dataB, 'Tamanho do quadro Gran Mesa', '% margem → pessoal');
  makeChart('chart-sens-c', dataC, '% custo realocado', '% margem → pessoal');
  makeChart('chart-sens-d', dataD, '% migrado de GH→GM', '% margem → pessoal', dataD.data_gh);
}}

window.addEventListener('resize', () => {{
  if (document.getElementById('tab-2').classList.contains('active')) {{
    renderDestinoFat(); renderTreemap();
  }}
}});
</script>

</body>
</html>"""
    return html


def main():
    json_path = PROD_DIR / 'dados_produtividade.json'
    if not json_path.exists():
        print(f"❌ {json_path} não encontrado. Rode build_dados.py primeiro.")
        return
    with open(json_path, encoding='utf-8') as f:
        d = json.load(f)
    html = gerar_html(d)
    REL_DIR.mkdir(parents=True, exist_ok=True)
    mes = d['meta']['mes_referencia'].replace('/', '_')
    out_path = REL_DIR / f'Produtividade_{mes}.html'
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"\n✓ Relatório gerado: {out_path}")
    print(f"  Tamanho: {out_path.stat().st_size / 1024:.1f} KB")


if __name__ == '__main__':
    main()
