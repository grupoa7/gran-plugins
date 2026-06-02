#!/usr/bin/env python3
"""HTML v3.2: Aba 01 promovida ao formato Consolidado (KPIs cumulativos + tendência + heatmap multi-semana + tornado + reincidentes)."""
import json, sys, html, os
from datetime import datetime
from collections import defaultdict

import os as _os
# v3.3: auto-detecta HIST e semana atual ao invés de hardcoded
HIST = _os.environ.get("JORNADA_HIST_DIR")
if not HIST:
    # Procurar dir 'historico' no projeto
    for candidate in [
        _os.environ.get("JORNADA_PROJECT_DIR", "") + "/historico",
        "/sessions/magical-wizardly-mayer/mnt/[GRAN RH] Monitoramento de jornada/historico",
        "/Users/hugogusmao/Documents/Claude/Projects/[GRAN RH] Monitoramento de jornada/historico",
    ]:
        if candidate and _os.path.isdir(candidate):
            HIST = candidate
            break
    if not HIST:
        raise RuntimeError("HIST não encontrado. Setar JORNADA_HIST_DIR ou JORNADA_PROJECT_DIR.")

# Auto-detectar semana mais recente
def _detect_semana_atual():
    arquivos = sorted([f for f in _os.listdir(HIST) if f.startswith("2026-") and f.endswith(".json")])
    if not arquivos:
        raise RuntimeError(f"Sem JSONs em {HIST}")
    return arquivos[-1]

SEMANA_ATUAL_ARQUIVO = _os.environ.get("JORNADA_SEMANA_ARQUIVO") or _detect_semana_atual()
import json as _json
_d = _json.load(open(f"{HIST}/{SEMANA_ATUAL_ARQUIVO}"))
SEMANA_ATUAL_ID = _d.get("semana", "?").split("/")[0]

# Auto-gerar DIAS_LABELS a partir do período da semana atual
from datetime import datetime as _dt, timedelta as _td
_ini = _dt.strptime(_d["periodo_iso"]["ini"], "%Y-%m-%d")
_dias_semana_pt = {0: "SEG", 1: "TER", 2: "QUA", 3: "QUI", 4: "SEX", 5: "SÁB", 6: "DOM"}
DIAS_LABELS = []
for _i in range(7):
    _dt_atual = _ini + _td(days=_i)
    DIAS_LABELS.append((_dt_atual.strftime("%Y-%m-%d"), _dias_semana_pt[_dt_atual.weekday()], _dt_atual.strftime("%d/%m")))

SETOR_DISPLAY = {"ENCARREGADOS":"Encarregados","OPERADOR DE LOJA":"Op. Loja","OPERADOR DE CAIXAS":"Op. Caixas","ASG":"Asg","COZINHA":"Cozinha","SUPRIMENTOS":"Suprimentos","MANOBRISTA":"Manobrista","LOGÍSTICA":"Logística","ESTAGIÁRIAS":"Estagiárias"}
SETOR_DISPLAY_LONG = {"ENCARREGADOS":"Encarregados","OPERADOR DE LOJA":"Operador de Loja","OPERADOR DE CAIXAS":"Operador de Caixas","ASG":"Asg","COZINHA":"Cozinha","SUPRIMENTOS":"Suprimentos","MANOBRISTA":"Manobrista","LOGÍSTICA":"Logística","ESTAGIÁRIAS":"Estagiárias"}
SETORES_RESTRITOS = {"ENCARREGADOS","OPERADOR DE LOJA","OPERADOR DE CAIXAS"}
SETOR_ORDER = ["ENCARREGADOS","OPERADOR DE LOJA","OPERADOR DE CAIXAS","MANOBRISTA","ASG","COZINHA","SUPRIMENTOS","LOGÍSTICA","ESTAGIÁRIAS"]
FOLGA_DISPLAY = {"F":("F","Folga regular"),"FF":("FF","Folga feriado"),"FD":("FD","Folga domingo")}

def fmt(b):
    if not b or b == "Falta": return "<em style='color:#999'>—</em>"
    return html.escape(str(b).strip())

def parse_prev(v):
    if isinstance(v, (list, tuple)) and len(v)>=2: return f"{v[0]} → {v[1]}"
    return ""

def alerta_html(a):
    sev = a["severidade"]; desc = html.escape(a["descricao"])
    if sev == "crit": return f'<div class="at crit"><span class="ic">🔴</span><span>{desc}</span></div>'
    if sev == "alert": return f'<div class="at warn"><span class="ic">⚠</span><span>{desc}</span></div>'
    if sev == "info": return f'<div class="at info"><span class="ic">ℹ</span><span>{desc}</span></div>'
    return f'<div class="at info"><span class="ic">·</span><span>{desc}</span></div>'

def render_dia(dia):
    tipo = dia["tipo_escala"]
    if tipo == "FOLGA":
        v = dia["valor_escala"]
        if isinstance(v, list): v = v[0] if v else ""
        cod, label = FOLGA_DISPLAY.get(v, (v, "Folga"))
        return f'<td><div class="dia-celula folga"><div class="tag-grande folga">{cod}<span class=\'sub\'>{label}</span></div></div></td>'
    if tipo == "FERIAS":
        return '<td><div class="dia-celula ferias"><div class="tag-grande ferias">FÉRIAS<span class=\'sub\'>Período de férias</span></div></div></td>'
    if tipo == "BH":
        return '<td><div class="dia-celula folga"><div class="tag-grande folga">BH<span class=\'sub\'>Banco de horas</span></div></div></td>'
    if tipo == "INATIVO":
        return '<td><div class="dia-celula folga"><div class="tag-grande folga">—<span class=\'sub\'>Sem escala</span></div></div></td>'
    status = dia["status"]
    classe = status if status in ("ok","alert","crit") else "alert"
    if status == "falta": classe = "crit"
    prev = parse_prev(dia["valor_escala"])
    bat = dia["batidas"]
    e1 = fmt(bat[0]) if len(bat)>0 else "—"
    s1 = fmt(bat[1]) if len(bat)>1 else "—"
    e2 = fmt(bat[2]) if len(bat)>2 else "—"
    s2 = fmt(bat[3]) if len(bat)>3 else "—"
    e3 = fmt(bat[4]) if len(bat)>4 else "—"
    s3 = fmt(bat[5]) if len(bat)>5 else "—"
    linhas = []
    if (len(bat)>0 and bat[0]) or (len(bat)>1 and bat[1]): linhas.append(f"{e1} / {s1}")
    if (len(bat)>2 and bat[2]) or (len(bat)>3 and bat[3]): linhas.append(f"{e2} / {s2}")
    if (len(bat)>4 and bat[4]) or (len(bat)>5 and bat[5]): linhas.append(f"{e3} / {s3}")
    if not linhas: linhas = ["<em style='color:#999'>Falta total</em>"]
    al = "".join(alerta_html(a) for a in dia["alertas"])
    if not al and status == "ok": al = '<div class="at ok"><span class="ic">✓</span><span>OK</span></div>'
    return (f'<td><div class="dia-celula {classe}">\n'
            f'        <div class="row-prev"><span class="lbl-mini">Previsto</span>{prev}</div>\n'
            f'        <div class="row-bateu"><span class="lbl-mini">Bateu</span>{"<br>".join(linhas)}</div>\n'
            f'        <div class="alertas-list">{al}</div>\n'
            f'    </div></td>')

# ============ CARREGAR HISTÓRICO COMPLETO ============
def carregar_todas_semanas():
    """Carrega todos os JSONs de historico/ ordenados por período."""
    arquivos = [f for f in os.listdir(HIST) if f.startswith("2026-") and f.endswith(".json")]
    arquivos.sort()
    semanas = []
    for arq in arquivos:
        d = json.load(open(f"{HIST}/{arq}"))
        # Extrair sid do conteúdo
        d["sid"] = d.get("semana", "?").split("/")[0]
        semanas.append(d)
    return semanas

# ============ CARREGAR DETALHE DA SEMANA ATUAL ============
def carregar_semana_atual():
    """Carrega resultados detalhados da semana atual (com batidas/dias) do pipeline_v31."""
    res_path = _os.environ.get("JORNADA_RESULTADOS_FILE") or (_os.environ.get("JORNADA_PROJECT_DIR","") + "/outputs_s20/resultados_v31.json")
    if os.path.exists(res_path):
        return json.load(open(res_path))
    return None

def main():
    semanas_hist = carregar_todas_semanas()
    semana_atual = carregar_semana_atual()
    if not semana_atual:
        print("ERRO: resultados_v31.json não encontrado", file=sys.stderr)
        sys.exit(1)

    # ============ DADOS DA SEMANA ATUAL (Abas 02-04) ============
    indicador = [r for r in semana_atual["resultados"] if not r["suspenso"] and not r["tratativa_rh"]]
    suspensos = [r for r in semana_atual["resultados"] if r["suspenso"]]
    n_crit = sum(1 for r in indicador if r["status"]=="crit")
    n_alert = sum(1 for r in indicador if r["status"]=="alert")
    n_ok = sum(1 for r in indicador if r["status"]=="ok")
    n_total = len(indicador)
    total_falta = sum(r["contadores"]["falta_seca"] for r in indicador)
    total_atraso = sum(r["contadores"]["atraso"] for r in indicador)
    total_jp = sum(r["contadores"]["janela_proib"] for r in indicador)
    casos = semana_atual.get("casos_suspeitos", [])
    cat_investigar = [c for c in casos if c.get("categoria") == "INVESTIGAR"]
    cat_ajuste = [c for c in casos if c.get("categoria") == "AJUSTE_RHID"]
    cat_verificar = [c for c in casos if c.get("categoria") == "VERIFICAR"]

    def top_by(key):
        items = [(r["nome_display"], r["contadores"][key]) for r in indicador if r["contadores"][key] > 0]
        items.sort(key=lambda x: -x[1])
        return items[:5]
    top_falta_atual = top_by("falta_seca")
    top_atraso_atual = top_by("atraso")
    top_jp_atual = top_by("janela_proib")

    def sort_key(r):
        st = {"crit":0,"alert":1,"ok":2}.get(r["status"],3)
        total_oc = sum(v for k,v in r["contadores"].items() if k!="falta_justificada")
        return (st, -total_oc, r["nome_display"])
    panorama = sorted(indicador, key=sort_key)

    def setor_key_r(r):
        return SETOR_ORDER.index(r["setor"]) if r["setor"] in SETOR_ORDER else 99
    detalhe_order = sorted(indicador, key=lambda r: (setor_key_r(r), r["nome_display"]))

    # ============ DADOS HISTÓRICOS (Aba 01) ============
    por_colab = defaultdict(lambda: {"setor":"?","semanas":{},"totais":{}})
    for s in semanas_hist:
        for c in s["colaboradores_indicador"]:
            nome = c["nome"]
            por_colab[nome]["setor"] = c["setor"]
            por_colab[nome]["semanas"][s["sid"]] = c
            for k, v in c["contadores"].items():
                por_colab[nome]["totais"].setdefault(k, 0)
                por_colab[nome]["totais"][k] += v

    serie = []
    for s in semanas_hist:
        k = s["kpis_indicador"]
        serie.append({
            "sid": s["sid"], "periodo": s["periodo"],
            "crit": k["criticos"], "alert": k["alerta"], "ok": k["ok"],
            "atrasos": k["atrasos"], "jp": k["janela_proibida"], "falta": k["falta_seca_dias"],
            "tratativa": s["tratativa_rh_resumo"]["total_casos"]
        })

    total_crit_cum = sum(s["crit"] for s in serie)
    total_alert_cum = sum(s["alert"] for s in serie)
    total_ok_cum = sum(s["ok"] for s in serie)
    total_falta_cum = sum(s["falta"] for s in serie)
    total_jp_cum = sum(s["jp"] for s in serie)
    total_atraso_cum = sum(s["atrasos"] for s in serie)

    reincidentes_jp = sorted(por_colab.items(), key=lambda x: -x[1]["totais"].get("janela_proib",0))
    reincidentes_jp = [(n,d) for n,d in reincidentes_jp if d["totais"].get("janela_proib",0)>0][:7]
    reincidentes_atraso = sorted(por_colab.items(), key=lambda x: -x[1]["totais"].get("atraso",0))
    reincidentes_atraso = [(n,d) for n,d in reincidentes_atraso if d["totais"].get("atraso",0)>0][:7]
    reincidentes_interv = sorted(por_colab.items(), key=lambda x: -(x[1]["totais"].get("interv_curto",0)+x[1]["totais"].get("interv_longo",0)))
    reincidentes_interv = [(n,d) for n,d in reincidentes_interv if (d["totais"].get("interv_curto",0)+d["totais"].get("interv_longo",0))>0][:7]

    # Tornado (último 1/3 vs 2/3 anteriores; pelo menos 4 semanas)
    melhoraram = []; pioraram = []
    if len(semanas_hist) >= 4:
        n_split = max(1, len(semanas_hist) // 3)
        recente_ids = [s["sid"] for s in semanas_hist[-n_split:]]
        baseline_ids = [s["sid"] for s in semanas_hist[:-n_split]]
        deltas = []
        for nome, c in por_colab.items():
            def soma(c, sids):
                t = 0; n = 0
                for sid in sids:
                    if sid in c["semanas"]:
                        ct = c["semanas"][sid]["contadores"]
                        t += sum(v for k,v in ct.items() if k != "falta_justificada"); n += 1
                return t, n
            tb, nb = soma(c, baseline_ids); tr, nr = soma(c, recente_ids)
            if nb == 0 or nr == 0: continue
            mb = tb/nb; mr = tr/nr; delta = mr - mb
            deltas.append((nome, c["setor"], delta, mb, mr))
        deltas.sort(key=lambda x: x[2])
        melhoraram = [d for d in deltas if d[2] < -0.5][:7]
        pioraram = [d for d in deltas if d[2] > 0.5][-7:][::-1]

    def setor_key_n(nome):
        s = por_colab[nome]["setor"]
        return SETOR_ORDER.index(s) if s in SETOR_ORDER else 99
    nomes_hist_ord = sorted(por_colab.keys(), key=lambda n: (setor_key_n(n), n))

    now = datetime.now().strftime("%d/%m %H:%M")

    out = []
    out.append("""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Monitoramento de Jornada · """ + SEMANA_ATUAL_ID + """/2026 · v3.2</title>
<link href="https://fonts.googleapis.com/css2?family=Nunito+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;0,900;1,400&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
:root { --bg:#fff; --bg-soft:#f6f4ee; --bg-cream:#faf7ef; --border:#e8e3d4; --border-soft:#f0ebdc;
  --ink:#1a1f1a; --ink-dim:#4a5248; --ink-mute:#8b8f86;
  --gran-verde:#1e4d2b; --gran-verde-3:#3f8654; --gran-verde-bg:#e7f0e9;
  --gran-dourado:#c9a227; --gran-dourado-2:#e8b93a; --gran-dourado-bg:#faf1d4;
  --vermelho:#b8362f; --vermelho-bg:#f2d9d3; --vermelho-soft:#fce7e3;
  --amarelo:#d4a52e; --amarelo-soft:#fcf6dd;
  --verde:#3f8654; --verde-bg:#e7f0e9; --verde-soft:#f3f9f4;
  --azul:#3a7bc8; --azul-soft:#e8f0f9;
  --laranja:#f97316; --laranja-soft:#fff4e6;
  --shadow:0 1px 2px rgba(30,77,43,0.04), 0 4px 12px rgba(30,77,43,0.06); }
* { box-sizing:border-box; margin:0; padding:0; }
body { font-family:'Nunito Sans', sans-serif; background:var(--bg-cream); color:var(--ink); font-size:14px; line-height:1.45; }
.mono { font-family:'JetBrains Mono', monospace; }
.banner-real { background:#e7f0e9; border-bottom:2px solid var(--verde); padding:10px 40px; font-size:12px; color:var(--gran-verde); }
.banner-real strong { color:#0d3a1a; }
.main-header { background:var(--gran-verde); color:#fff; padding:28px 40px 24px; display:flex; justify-content:space-between; align-items:flex-end; }
.main-header .eyebrow { font-family:'JetBrains Mono'; font-size:11px; letter-spacing:1.5px; color:var(--gran-dourado-2); margin-bottom:8px; font-weight:500; }
.main-header h1 { font-size:38px; font-weight:800; letter-spacing:-0.8px; line-height:1.1; }
.main-header h1 em { color:var(--gran-dourado-2); font-style:normal; }
.main-header .subtitle { font-size:14px; color:rgba(255,255,255,0.7); margin-top:6px; font-weight:500; }
.main-header .meta { text-align:right; font-size:12px; color:rgba(255,255,255,0.85); line-height:1.7; }
.main-header .meta strong { color:var(--gran-dourado-2); }
.tabs-wrap { background:#fff; border-bottom:1px solid var(--border); position:sticky; top:0; z-index:50; }
.tabs { display:flex; padding:0 40px; max-width:1500px; margin:0 auto; }
.tab { background:transparent; border:0; padding:16px 22px; font-family:inherit; font-size:13px; font-weight:700; color:var(--ink-mute); cursor:pointer; border-bottom:3px solid transparent; display:flex; align-items:center; gap:10px; }
.tab:hover { color:var(--ink-dim); background:var(--bg-soft); }
.tab.active { color:var(--gran-verde); border-bottom-color:var(--gran-dourado); background:var(--bg-cream); }
.tab .num { font-family:'JetBrains Mono'; font-size:11px; font-weight:600; padding:2px 6px; border-radius:3px; background:var(--bg-soft); color:var(--ink-mute); }
.tab.active .num { background:var(--gran-verde); color:var(--gran-dourado-2); }
.tab.rh .num { background:var(--azul); color:#fff; }
main { max-width:1500px; margin:0 auto; padding:28px 40px 60px; }
.tab-panel { display:none; }
.tab-panel.active { display:block; }
.panel-header { margin-bottom:24px; padding-bottom:12px; border-bottom:1px solid var(--border); }
.panel-header h2 { font-size:22px; font-weight:700; }
.panel-header p { font-size:13px; color:var(--ink-dim); margin-top:4px; }

/* Aba 01 — formato consolidado */
.section { background:#fff; border:1px solid var(--border); border-radius:8px; padding:22px 26px; margin-bottom:22px; box-shadow:var(--shadow); }
.section h3.sec { font-size:16px; font-weight:800; margin-bottom:6px; }
.section .subt { font-size:12px; color:var(--ink-dim); margin-bottom:16px; }
.kpis-cum { display:grid; grid-template-columns:repeat(6, 1fr); gap:10px; margin-bottom:0; }
.kpi-card { background:var(--bg-soft); border-radius:6px; padding:12px 14px; }
.kpi-card .lbl { font-family:'JetBrains Mono'; font-size:9px; color:var(--ink-mute); text-transform:uppercase; letter-spacing:1px; font-weight:700; margin-bottom:4px; }
.kpi-card .val { font-size:24px; font-weight:800; line-height:1; }
.kpi-card.crit .val { color:var(--vermelho); }
.kpi-card.alert .val { color:var(--amarelo); }
.kpi-card.ok .val { color:var(--verde); }
.heatmap-multi { display:grid; gap:3px; }
.hm-header-multi { display:grid; gap:3px; align-items:center; margin-bottom:4px; padding:4px 0; border-bottom:1px solid var(--border); }
.hm-header-multi .h { font-family:'JetBrains Mono'; font-size:10px; color:var(--ink-mute); text-align:center; font-weight:700; }
.hm-row-multi { display:grid; gap:3px; align-items:center; }
.hm-row-multi .nome { font-size:11px; font-weight:600; color:var(--ink-dim); text-align:right; padding-right:8px; line-height:1.3; }
.hm-row-multi .nome small { display:block; font-size:9px; color:var(--ink-mute); }
.hm-row-multi .cell-mt { height:22px; border-radius:2px; display:flex; align-items:center; justify-content:center; font-family:'JetBrains Mono'; font-size:9px; color:#fff; font-weight:700; }
.cell-mt.cs-crit { background:var(--vermelho); }
.cell-mt.cs-alert { background:var(--amarelo); color:#5c3d00; }
.cell-mt.cs-ok { background:var(--verde); }
.cell-mt.cs-na { background:var(--bg-soft); }
.tabela-semanas { width:100%; border-collapse:collapse; }
.tabela-semanas th { background:var(--gran-verde); color:var(--gran-dourado-2); font-family:'JetBrains Mono'; font-size:10px; text-transform:uppercase; letter-spacing:1px; padding:10px 12px; text-align:left; font-weight:700; }
.tabela-semanas td { padding:10px 12px; border-bottom:1px solid var(--border); font-size:13px; font-family:'JetBrains Mono'; text-align:center; }
.tabela-semanas td.sid { font-weight:700; text-align:left; }
.tabela-semanas td.periodo { color:var(--ink-mute); font-size:11px; text-align:left; }
.tabela-semanas td.atual { background:var(--gran-dourado-bg); }
.v-crit { color:var(--vermelho); font-weight:700; } .v-alert { color:var(--amarelo); font-weight:700; } .v-ok { color:var(--verde); font-weight:700; }
.tornado { display:grid; grid-template-columns:1fr 1fr; gap:18px; }
.tornado-card { background:var(--bg-soft); border-radius:6px; padding:14px 16px; }
.tornado-card h4 { font-size:13px; margin-bottom:10px; }
.tornado-card.melhora h4 { color:var(--verde); }
.tornado-card.piora h4 { color:var(--vermelho); }
.tornado-bar { display:flex; align-items:center; padding:6px 0; border-bottom:1px dashed var(--border); font-size:12px; gap:8px; }
.tornado-bar .nm { flex:1; font-weight:600; }
.tornado-bar .delta { font-family:'JetBrains Mono'; font-weight:700; font-size:11px; padding:2px 6px; border-radius:3px; }
.tornado-bar .delta.neg { background:var(--verde-bg); color:var(--verde); }
.tornado-bar .delta.pos { background:var(--vermelho-soft); color:var(--vermelho); }
.top-rank { display:grid; grid-template-columns:repeat(3,1fr); gap:18px; }
.top-rank .top-card { background:var(--bg-soft); border-radius:6px; padding:14px 16px; }
.top-rank .top-card h4 { font-family:'JetBrains Mono'; font-size:11px; text-transform:uppercase; letter-spacing:1px; margin-bottom:10px; padding-bottom:6px; border-bottom:1px solid var(--border); }
.top-rank ol { list-style:none; counter-reset:t; }
.top-rank li { padding:6px 0; counter-increment:t; display:flex; align-items:center; gap:8px; font-size:12px; border-bottom:1px dashed rgba(0,0,0,0.05); }
.top-rank li::before { content:counter(t); font-family:'JetBrains Mono'; font-size:10px; color:var(--ink-mute); width:18px; }
.top-rank li .nm { flex:1; font-weight:600; }
.top-rank li .total { font-family:'JetBrains Mono'; font-weight:700; font-size:12px; color:var(--vermelho); }
.chart-wrap { padding:10px; background:var(--bg-soft); border-radius:6px; }
canvas { max-height:260px; }

/* Abas 02-04 (mesmo do v3.1) */
.kpis { display:grid; grid-template-columns:repeat(5,1fr); gap:12px; margin-bottom:24px; }
.kpi { background:#fff; border:1px solid var(--border); border-radius:8px; padding:16px; box-shadow:var(--shadow); }
.kpi .lbl { font-family:'JetBrains Mono'; font-size:10px; color:var(--ink-mute); text-transform:uppercase; letter-spacing:1px; font-weight:600; margin-bottom:6px; }
.kpi .val { font-size:32px; font-weight:800; line-height:1; letter-spacing:-1px; }
.kpi.crit .val { color:var(--vermelho); } .kpi.alert .val { color:var(--amarelo); } .kpi.ok .val { color:var(--verde); }
.tops { display:grid; grid-template-columns:repeat(3,1fr); gap:16px; margin-bottom:24px; }
.top-card-w { background:#fff; border:1px solid var(--border); border-radius:8px; padding:16px 18px; box-shadow:var(--shadow); }
.top-card-w h3 { font-family:'JetBrains Mono'; font-size:11px; text-transform:uppercase; letter-spacing:1px; font-weight:700; margin-bottom:10px; padding-bottom:8px; border-bottom:1px solid var(--border-soft); }
.top-card-w.crit h3 { color:var(--vermelho); }
.top-card-w.alert h3 { color:var(--amarelo); }
.top-card-w.warn h3 { color:var(--gran-dourado); }
.top-card-w ol { list-style:none; counter-reset:t; }
.top-card-w li { display:flex; justify-content:space-between; align-items:center; padding:8px 0; border-bottom:1px dashed var(--border-soft); font-size:13px; counter-increment:t; }
.top-card-w li::before { content:counter(t); font-family:'JetBrains Mono'; font-size:11px; color:var(--ink-mute); margin-right:10px; width:18px; }
.top-card-w li.empty { color:var(--verde); font-style:italic; }
.top-card-w .nm { font-weight:600; flex:1; } .top-card-w .vl { font-family:'JetBrains Mono'; font-weight:700; font-size:12px; }
.table-wrap { background:#fff; border:1px solid var(--border); border-radius:8px; overflow:hidden; box-shadow:var(--shadow); }
table.panorama { width:100%; border-collapse:collapse; }
table.panorama thead { background:var(--gran-verde); color:#fff; }
table.panorama th { padding:12px 14px; font-family:'JetBrains Mono'; font-size:10px; text-transform:uppercase; letter-spacing:1px; font-weight:600; color:var(--gran-dourado-2); text-align:left; }
table.panorama th.num { text-align:center; }
table.panorama td { padding:12px 14px; font-size:13px; border-top:1px solid var(--border-soft); vertical-align:middle; }
table.panorama tbody tr:hover { background:var(--bg-cream); }
.badge { display:inline-block; font-family:'JetBrains Mono'; font-size:10px; font-weight:700; padding:3px 8px; border-radius:3px; letter-spacing:0.5px; white-space:nowrap; }
.badge.crit { background:var(--vermelho); color:#fff; } .badge.alert { background:var(--amarelo); color:#fff; } .badge.ok { background:var(--verde); color:#fff; }
.badge.medio { background:var(--laranja); color:#fff; } .badge.info { background:#64748b; color:#fff; } .badge.rh { background:var(--azul); color:#fff; }
.nome-cell { font-weight:700; }
.setor-cell { font-family:'JetBrains Mono'; font-size:11px; color:var(--ink-mute); text-transform:uppercase; letter-spacing:0.5px; }
.setor-cell.restrito { color:var(--gran-dourado); }
.num-cell { font-family:'JetBrains Mono'; text-align:center; font-weight:600; }
.num-cell.zero { color:#cbd5e1; } .num-cell.alert { color:var(--amarelo); font-weight:700; } .num-cell.crit { color:var(--vermelho); font-weight:700; }
.detalhe-wrap { background:#fff; border:1px solid var(--border); border-radius:8px; box-shadow:var(--shadow); overflow:auto; }
table.detalhe { width:100%; border-collapse:collapse; min-width:1320px; }
table.detalhe thead { background:var(--gran-verde); color:#fff; }
table.detalhe thead th { padding:10px 8px; font-family:'JetBrains Mono'; font-size:10px; text-transform:uppercase; letter-spacing:0.5px; font-weight:700; color:var(--gran-dourado-2); border-right:1px solid rgba(255,255,255,0.1); vertical-align:middle; }
table.detalhe thead th.col-nome { text-align:left; width:180px; padding-left:16px; }
table.detalhe thead th.col-dia { text-align:center; width:calc((100% - 180px) / 7); min-width:155px; }
table.detalhe thead th.col-dia .dia-num { display:block; font-size:13px; color:#fff; font-weight:800; margin-top:2px; }
table.detalhe tbody tr { border-top:1px solid var(--border); }
table.detalhe tbody tr.setor-divider { background:var(--bg-soft); }
table.detalhe tbody tr.setor-divider td { padding:6px 16px; font-family:'JetBrains Mono'; font-size:10px; text-transform:uppercase; letter-spacing:1px; font-weight:700; color:var(--ink-dim); border-bottom:1px solid var(--border); }
table.detalhe tbody tr.setor-divider.restrito td { color:var(--gran-dourado); }
table.detalhe tbody tr.setor-divider.restrito td::before { content:"● "; }
table.detalhe td { padding:0; border-right:1px solid var(--border-soft); vertical-align:top; }
table.detalhe td.nome-cell { padding:14px 16px; font-size:13px; font-weight:700; vertical-align:middle; background:var(--bg-cream); border-right:2px solid var(--border); }
.dia-celula { padding:10px 8px; min-height:120px; font-size:11px; display:flex; flex-direction:column; gap:4px; }
.dia-celula.ok { background:var(--verde-soft); }
.dia-celula.alert { background:var(--amarelo-soft); }
.dia-celula.crit { background:var(--vermelho-soft); }
.dia-celula.folga { background:var(--bg-soft); }
.dia-celula.ferias { background:rgba(232,185,58,0.12); }
.dia-celula .row-prev { font-family:'JetBrains Mono'; font-size:10.5px; color:var(--ink-mute); }
.dia-celula .row-prev .lbl-mini { font-weight:600; letter-spacing:0.5px; text-transform:uppercase; font-size:9px; margin-right:4px; }
.dia-celula .row-bateu { font-family:'JetBrains Mono'; font-size:11.5px; font-weight:600; }
.dia-celula .row-bateu .lbl-mini { font-weight:700; letter-spacing:0.5px; text-transform:uppercase; font-size:9px; margin-right:4px; color:var(--ink-dim); }
.dia-celula .alertas-list { margin-top:auto; padding-top:6px; border-top:1px solid rgba(0,0,0,0.06); font-size:10.5px; line-height:1.4; }
.dia-celula .alertas-list .at { display:flex; gap:4px; align-items:flex-start; font-weight:600; margin-top:3px; }
.dia-celula .alertas-list .at.crit { color:var(--vermelho); }
.dia-celula .alertas-list .at.warn { color:#8a6d10; }
.dia-celula .alertas-list .at.ok { color:var(--verde); }
.dia-celula .alertas-list .at.info { color:var(--ink-dim); }
.dia-celula .tag-grande { text-align:center; font-family:'JetBrains Mono'; font-weight:700; padding:22px 0; font-size:12px; }
.dia-celula .tag-grande.folga { color:var(--ink-mute); }
.dia-celula .tag-grande.ferias { color:#8a6d10; }
.dia-celula .tag-grande .sub { display:block; font-size:9px; font-weight:500; margin-top:4px; }
.suspensos-block { margin-top:28px; background:var(--bg-soft); border:1px dashed var(--border); border-radius:8px; padding:16px 20px; font-size:12px; color:var(--ink-dim); }
.suspensos-block h4 { font-family:'JetBrains Mono'; font-size:10px; color:var(--ink-mute); text-transform:uppercase; letter-spacing:1px; margin-bottom:8px; }
.suspensos-block strong { color:var(--ink); }
.foot { margin-top:36px; padding:18px 0; border-top:1px solid var(--border); font-family:'JetBrains Mono'; font-size:11px; color:var(--ink-mute); text-align:center; }
.notas { background:#fff; border:1px solid var(--border); border-radius:8px; padding:14px 18px; margin-top:20px; font-size:12px; color:var(--ink-dim); line-height:1.7; }
.rh-resumo { display:grid; grid-template-columns:repeat(3,1fr); gap:14px; margin-bottom:22px; }
.rh-resumo-card { background:#fff; border:1px solid var(--border); border-radius:8px; padding:16px 18px; box-shadow:var(--shadow); }
.rh-resumo-card h4 { font-family:'JetBrains Mono'; font-size:10px; text-transform:uppercase; letter-spacing:1px; color:var(--ink-mute); margin-bottom:6px; font-weight:700; }
.rh-resumo-card .val { font-size:28px; font-weight:800; line-height:1.1; margin-bottom:4px; }
.rh-resumo-card .sub { font-size:11px; color:var(--ink-dim); }
.rh-resumo-card.investigar { border-left:4px solid var(--vermelho); }
.rh-resumo-card.investigar .val { color:var(--vermelho); }
.rh-resumo-card.ajuste { border-left:4px solid var(--laranja); }
.rh-resumo-card.ajuste .val { color:var(--laranja); }
.rh-resumo-card.verificar { border-left:4px solid var(--azul); }
.rh-resumo-card.verificar .val { color:var(--azul); }
.kpi-rh-perf { background:linear-gradient(135deg, var(--gran-verde), #0d3a1a); color:#fff; border-radius:8px; padding:18px 22px; margin-bottom:22px; }
.kpi-rh-perf h4 { font-family:'JetBrains Mono'; font-size:10px; color:var(--gran-dourado-2); text-transform:uppercase; letter-spacing:1.5px; margin-bottom:6px; }
.kpi-rh-perf .legenda { font-size:12px; color:rgba(255,255,255,0.7); margin-top:6px; }
.kpi-rh-perf .num-grande { font-size:34px; font-weight:800; }
.tratativa-card { background:#fff; border:1px solid var(--border); border-radius:8px; padding:18px 20px; margin-bottom:14px; box-shadow:var(--shadow); border-left:4px solid var(--ink-mute); }
.tratativa-card.cat-investigar { border-left-color:var(--vermelho); background:linear-gradient(to right, var(--vermelho-soft) 0%, #fff 30%); }
.tratativa-card.cat-ajuste { border-left-color:var(--laranja); }
.tratativa-card.cat-verificar { border-left-color:var(--azul); }
.tratativa-card .topo { display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:10px; gap:12px; }
.tratativa-card h3 { font-size:16px; font-weight:800; margin-bottom:4px; }
.tratativa-card .meta-tag { font-family:'JetBrains Mono'; font-size:10px; color:var(--ink-mute); text-transform:uppercase; letter-spacing:1px; }
.tratativa-card .descricao { font-size:13px; color:var(--ink-dim); margin:8px 0 10px; }
.tratativa-card .historico-mini { background:var(--azul-soft); border-radius:6px; padding:10px 14px; font-size:12px; color:#1a4380; margin:8px 0; line-height:1.6; }
.tratativa-card .meta-info { display:grid; grid-template-columns:repeat(4, 1fr); gap:10px; padding:10px 12px; background:var(--bg-soft); border-radius:6px; margin-top:8px; font-size:11px; }
.tratativa-card .meta-info .lbl-mini { display:block; color:var(--ink-mute); font-size:9px; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:2px; }
.tratativa-card .meta-info .val-mini { color:var(--ink); font-weight:700; font-size:12px; font-family:'JetBrains Mono'; }
.tratativa-card .acao-row { display:flex; align-items:center; gap:10px; padding:10px 12px; background:var(--bg-cream); border-radius:6px; font-size:12px; color:var(--ink); margin-top:8px; }
.tratativa-card .acao-row .lbl { font-family:'JetBrains Mono'; font-size:9px; text-transform:uppercase; letter-spacing:1px; color:var(--ink-mute); font-weight:700; flex-shrink:0; }
.tratativa-card .acao-row .lbl::before { content:""; }
.tratativa-card .status-row { display:flex; align-items:center; gap:8px; padding:8px 12px; background:#fff; border:1px dashed var(--border); border-radius:6px; margin-top:10px; font-size:11px; }
.tratativa-card .check-box { width:14px; height:14px; border:2px solid var(--ink-mute); border-radius:3px; display:inline-block; flex-shrink:0; }
.section-title { font-size:15px; font-weight:800; margin:22px 0 12px; padding-bottom:6px; border-bottom:2px solid var(--border); display:flex; align-items:center; gap:10px; }
.section-title.investigar { color:var(--vermelho); border-bottom-color:var(--vermelho-bg); }
.section-title.ajuste { color:var(--laranja); border-bottom-color:#fed7aa; }
.section-title.verificar { color:var(--azul); border-bottom-color:#bfdbfe; }
.section-title .count { font-family:'JetBrains Mono'; font-size:12px; padding:2px 8px; background:var(--bg-soft); border-radius:3px; color:var(--ink-dim); margin-left:auto; }
</style>
</head>
<body>

<div class="banner-real">
  <strong>✅ DADOS REAIS · v3.2 · Histórico cumulativo + tendência multi-semana.</strong>
  Aba 01 alimenta-se automaticamente do histórico/. Aba 04 acompanha resolução de casos pela Consultora RH ao longo das semanas.
</div>

<header class="main-header">
  <div>
    <p class="eyebrow">MONITORAMENTO · """ + SEMANA_ATUAL_ID + """/2026 · """ + semana_atual["periodo_ini"] + """ a """ + semana_atual["periodo_fim"] + """</p>
    <h1>Monitoramento de <em>Jornada</em></h1>
    <p class="subtitle">Gran + GRSM · """ + str(n_total) + """ ativos no indicador · """ + str(len(casos)) + """ casos em tratativa RH · """ + str(len(suspensos)) + """ suspenso · """ + str(len(semanas_hist)) + """ semanas no histórico</p>
  </div>
  <div class="meta">
    <div>Gerado em <strong>""" + now + """</strong></div>
    <div>Skill <strong>v3.2</strong> · histórico cumulativo</div>
    <div>Fonte <strong>RHID + Escalas Abr+Mai/26</strong></div>
  </div>
</header>

<div class="tabs-wrap">
  <div class="tabs">
    <button class="tab active" data-tab="01"><span class="num">01</span>Histórico &amp; Tendência</button>
    <button class="tab" data-tab="02"><span class="num">02</span>Panorama da Semana</button>
    <button class="tab" data-tab="03"><span class="num">03</span>Detalhe Diário</button>
    <button class="tab rh" data-tab="04"><span class="num">04</span>Tratativa RH (""" + str(len(casos)) + """)</button>
  </div>
</div>

<main>
""")

    # ============ ABA 01 ============
    out.append(f"""
<div class="tab-panel active" id="tab-01">
  <div class="panel-header">
    <h2>Histórico &amp; Tendência</h2>
    <p>Visão cumulativa de {len(semanas_hist)} semanas (S{semanas_hist[0]['sid'][1:]} a S{semanas_hist[-1]['sid'][1:]}/2026). Atualizado a cada rodada — quanto mais semanas, mais sólida a leitura.</p>
  </div>

  <div class="section">
    <h3 class="sec">● KPIs cumulativos · {len(semanas_hist)} semanas</h3>
    <p class="subt">Soma de todas as semanas. Cada colaborador conta múltiplas vezes (uma por semana ativa).</p>
    <div class="kpis-cum">
      <div class="kpi-card crit"><div class="lbl">CRIT (semanas-colab)</div><div class="val">{total_crit_cum}</div></div>
      <div class="kpi-card alert"><div class="lbl">ALERT (semanas-colab)</div><div class="val">{total_alert_cum}</div></div>
      <div class="kpi-card ok"><div class="lbl">OK (semanas-colab)</div><div class="val">{total_ok_cum}</div></div>
      <div class="kpi-card"><div class="lbl">Faltas secas total</div><div class="val">{total_falta_cum}</div></div>
      <div class="kpi-card"><div class="lbl">Janela proib total</div><div class="val">{total_jp_cum}</div></div>
      <div class="kpi-card"><div class="lbl">Atrasos &gt;15 total</div><div class="val">{total_atraso_cum}</div></div>
    </div>
  </div>

  <div class="section">
    <h3 class="sec">● Tendência semanal</h3>
    <p class="subt">Evolução do mix CRIT/ALERT/OK e ocorrências. Quando RH e gestores estão atuando, o vermelho desce.</p>
    <div class="chart-wrap"><canvas id="trend"></canvas></div>
    <div class="chart-wrap" style="margin-top:14px"><canvas id="trend2"></canvas></div>
  </div>

  <div class="section">
    <h3 class="sec">● Tabela semana a semana</h3>
    <table class="tabela-semanas">
      <thead><tr><th>Semana</th><th>Período</th><th>CRIT</th><th>ALERT</th><th>OK</th><th>Faltas</th><th>Janela proib</th><th>Atrasos</th><th>Tratativa RH</th></tr></thead>
      <tbody>""")

    sid_atual = SEMANA_ATUAL_ID
    for s in semanas_hist:
        k = s["kpis_indicador"]
        cls = ' atual' if s["sid"] == sid_atual else ''
        out.append(f"""
        <tr>
          <td class="sid{cls}">{s["sid"]}/2026</td>
          <td class="periodo{cls}">{s["periodo"]}</td>
          <td class="{cls.strip()}"><span class="v-crit">{k['criticos']}</span></td>
          <td class="{cls.strip()}"><span class="v-alert">{k['alerta']}</span></td>
          <td class="{cls.strip()}"><span class="v-ok">{k['ok']}</span></td>
          <td class="{cls.strip()}">{k['falta_seca_dias']}</td>
          <td class="{cls.strip()}">{k['janela_proibida']}</td>
          <td class="{cls.strip()}">{k['atrasos']}</td>
          <td class="{cls.strip()}">{s['tratativa_rh_resumo']['total_casos']}</td>
        </tr>""")
    out.append("""
      </tbody>
    </table>
  </div>

  <div class="section">
    <h3 class="sec">● Heatmap colaborador × semana</h3>
    <p class="subt">Cada célula = status da semana. Reincidentes saltam aos olhos. Coluna destacada = semana atual.</p>
    <div class="heatmap-multi">""")

    n_sem = len(semanas_hist)
    grid_cols = f"200px repeat({n_sem}, 1fr)"
    out.append(f'<div class="hm-header-multi" style="grid-template-columns:{grid_cols}"><div></div>')
    for s in semanas_hist:
        flag = ' style="color:var(--gran-dourado);font-weight:800"' if s["sid"] == sid_atual else ''
        out.append(f'<div class="h"{flag}>{s["sid"]}</div>')
    out.append('</div>')

    setor_atual_h = None
    for nome in nomes_hist_ord:
        setor = por_colab[nome]["setor"]
        if setor != setor_atual_h:
            setor_atual_h = setor
            sd = SETOR_DISPLAY.get(setor, setor)
            cor = "var(--gran-dourado)" if setor in SETORES_RESTRITOS else "var(--ink-dim)"
            out.append(f'<div style="grid-column:1/-1;padding:8px 0 4px;font-family:JetBrains Mono;font-size:10px;text-transform:uppercase;letter-spacing:1px;color:{cor};font-weight:700">● {sd}</div>')

        cells = []
        for s in semanas_hist:
            sid = s["sid"]
            if sid in por_colab[nome]["semanas"]:
                st = por_colab[nome]["semanas"][sid]["status"].lower()
                cls = f"cs-{st}" if st in ("crit","alert","ok") else "cs-na"
                label = {"crit":"!","alert":"·","ok":"✓"}.get(st, "")
                cells.append(f'<div class="cell-mt {cls}">{label}</div>')
            else:
                cells.append('<div class="cell-mt cs-na">—</div>')
        sd_short = SETOR_DISPLAY.get(setor, setor)
        out.append(f'<div class="hm-row-multi" style="grid-template-columns:{grid_cols}"><div class="nome">{html.escape(nome)}<small>{sd_short}</small></div>{"".join(cells)}</div>')

    out.append("""
    </div>
  </div>

  <div class="section">
    <h3 class="sec">● Top reincidentes (cumulativo)</h3>
    <p class="subt">Quem mais acumula. Casos isolados saem; padrões comportamentais ficam.</p>
    <div class="top-rank">""")

    out.append('<div class="top-card"><h4>● JANELA PROIBIDA (cumulativo)</h4><ol>')
    if reincidentes_jp:
        for nome, dados in reincidentes_jp:
            out.append(f'<li><span class="nm">{html.escape(nome)}</span><small style="color:var(--ink-mute)">{SETOR_DISPLAY.get(dados["setor"],dados["setor"])}</small><span class="total">{dados["totais"]["janela_proib"]}x</span></li>')
    else:
        out.append('<li class="empty" style="color:var(--verde);font-style:italic">Sem ocorrências</li>')
    out.append('</ol></div>')

    out.append('<div class="top-card"><h4>● ATRASOS &gt;15MIN (cumulativo)</h4><ol>')
    if reincidentes_atraso:
        for nome, dados in reincidentes_atraso:
            out.append(f'<li><span class="nm">{html.escape(nome)}</span><small style="color:var(--ink-mute)">{SETOR_DISPLAY.get(dados["setor"],dados["setor"])}</small><span class="total">{dados["totais"]["atraso"]}x</span></li>')
    else:
        out.append('<li class="empty" style="color:var(--verde);font-style:italic">Sem ocorrências</li>')
    out.append('</ol></div>')

    out.append('<div class="top-card"><h4>● INTERVALO FORA (cumulativo)</h4><ol>')
    if reincidentes_interv:
        for nome, dados in reincidentes_interv:
            t = dados["totais"].get("interv_curto",0) + dados["totais"].get("interv_longo",0)
            out.append(f'<li><span class="nm">{html.escape(nome)}</span><small style="color:var(--ink-mute)">{SETOR_DISPLAY.get(dados["setor"],dados["setor"])}</small><span class="total">{t}x</span></li>')
    else:
        out.append('<li class="empty" style="color:var(--verde);font-style:italic">Sem ocorrências</li>')
    out.append('</ol></div>')
    out.append('</div></div>')

    # Tornado
    if melhoraram or pioraram:
        out.append("""
  <div class="section">
    <h3 class="sec">● Tornado · piora vs melhora</h3>
    <p class="subt">Variação na média semanal de ocorrências entre 2 períodos do histórico.</p>
    <div class="tornado">
      <div class="tornado-card melhora"><h4>▼ Quem MELHOROU</h4>""")
        if melhoraram:
            for nome, setor, delta, base, rec in melhoraram:
                out.append(f'<div class="tornado-bar"><span class="nm">{html.escape(nome)}</span><small style="color:var(--ink-mute);font-size:10px">{SETOR_DISPLAY.get(setor,setor)}</small><span class="delta neg">{delta:+.1f}/sem</span></div>')
        else:
            out.append('<div style="color:var(--ink-mute);font-style:italic;font-size:12px">Nenhuma melhora significativa.</div>')
        out.append('</div><div class="tornado-card piora"><h4>▲ Quem PIOROU</h4>')
        if pioraram:
            for nome, setor, delta, base, rec in pioraram:
                out.append(f'<div class="tornado-bar"><span class="nm">{html.escape(nome)}</span><small style="color:var(--ink-mute);font-size:10px">{SETOR_DISPLAY.get(setor,setor)}</small><span class="delta pos">+{delta:.1f}/sem</span></div>')
        else:
            out.append('<div style="color:var(--ink-mute);font-style:italic;font-size:12px">Nenhuma piora significativa.</div>')
        out.append('</div></div></div>')

    out.append("</div>")  # fecha tab-01

    # ============ ABA 02 — Panorama (igual v3.1) ============
    out.append(f"""
<div class="tab-panel" id="tab-02">
  <div class="panel-header">
    <h2>Panorama da semana</h2>
    <p>Visão executiva dos {n_total} ativos no indicador da semana {SEMANA_ATUAL_ID}/2026.</p>
  </div>
  <div class="kpis">
    <div class="kpi crit"><div class="lbl">Críticos</div><div class="val">{n_crit}</div></div>
    <div class="kpi alert"><div class="lbl">Alertas</div><div class="val">{n_alert}</div></div>
    <div class="kpi ok"><div class="lbl">OK</div><div class="val">{n_ok}</div></div>
    <div class="kpi"><div class="lbl">Janela proibida (total)</div><div class="val" style="color:var(--vermelho)">{total_jp}</div></div>
    <div class="kpi"><div class="lbl">Atrasos &gt;15min</div><div class="val" style="color:var(--amarelo)">{total_atraso}</div></div>
  </div>
  <div class="tops">""")
    out.append('<div class="top-card-w crit"><h3>● Top 5 — Faltas secas</h3><ol>')
    if top_falta_atual:
        for nm, vl in top_falta_atual: out.append(f'<li><span class="nm">{nm}</span><span class="vl">{vl} {"dia" if vl==1 else "dias"}</span></li>')
    else: out.append('<li class="empty">Sem faltas secas</li>')
    out.append('</ol></div>')
    out.append('<div class="top-card-w alert"><h3>● Top 5 — Atrasos &gt;15min</h3><ol>')
    for nm, vl in top_atraso_atual: out.append(f'<li><span class="nm">{nm}</span><span class="vl">{vl} ocorr.</span></li>')
    if not top_atraso_atual: out.append('<li class="empty">Sem atrasos</li>')
    out.append('</ol></div>')
    out.append('<div class="top-card-w warn"><h3>● Top 5 — Janela proibida</h3><ol>')
    for nm, vl in top_jp_atual: out.append(f'<li><span class="nm">{nm}</span><span class="vl">{vl} ocorr.</span></li>')
    if not top_jp_atual: out.append('<li class="empty">Sem ocorrências</li>')
    out.append('</ol></div></div>')

    out.append("""
  <div class="table-wrap"><table class="panorama">
    <thead><tr><th>Status</th><th>Colaborador</th><th>Setor</th><th class="num">Faltas</th><th class="num">Atrasos &gt;15</th><th class="num">Saídas fora</th><th class="num">Interv. fora</th><th class="num">Janela proib.</th><th class="num">Pulou interv.</th></tr></thead>
    <tbody>""")

    def cell(v, kind="alert"):
        if v == 0: return '<td class="num-cell zero">—</td>'
        return f'<td class="num-cell {kind}">{v}</td>'

    for r in panorama:
        c = r["contadores"]; st = r["status"]
        bl = {"crit":"CRÍTICO","alert":"ALERTA","ok":"OK"}[st]
        sd = SETOR_DISPLAY.get(r["setor"], r["setor"])
        rc = " restrito" if r["setor"] in SETORES_RESTRITOS else ""
        out.append(f"""
      <tr><td><span class="badge {st}">{bl}</span></td><td class="nome-cell">{r["nome_display"]}</td>
        <td class="setor-cell{rc}">{sd}</td>
        {cell(c["falta_seca"],"crit")}{cell(c["atraso"],"alert")}{cell(c["saida_fora"],"alert")}
        {cell(c["interv_curto"]+c["interv_longo"],"alert")}{cell(c["janela_proib"],"crit")}{cell(c["pulou_interv"],"crit")}
      </tr>""")
    out.append("""
    </tbody></table></div>
  <div class="suspensos-block"><h4>● Colaboradores suspensos</h4>
    <strong>Emilly Brito</strong> · Suprimentos · suspensa em 07/05/2026.
  </div>
</div>
""")

    # ============ ABA 03 — Detalhe diário ============
    out.append("""
<div class="tab-panel" id="tab-03">
  <div class="panel-header">
    <h2>Detalhe diário · 29/04 a 05/05</h2>
    <p>Tabela espelhando a escala. Casos em tratativa RH ficam fora — ver aba 04.</p>
  </div>
  <div class="detalhe-wrap"><table class="detalhe">
    <thead><tr><th class="col-nome">Colaborador</th>""")
    for _, dl, dn in DIAS_LABELS:
        out.append(f'<th class="col-dia">{dl}<span class="dia-num">{dn}</span></th>')
    out.append("</tr></thead><tbody>")

    setor_atual_d = None
    for r in detalhe_order:
        if r["setor"] != setor_atual_d:
            setor_atual_d = r["setor"]
            sl = SETOR_DISPLAY_LONG.get(setor_atual_d, setor_atual_d)
            rc = " restrito" if setor_atual_d in SETORES_RESTRITOS else ""
            label = f"{sl} (setor restrito)" if setor_atual_d in SETORES_RESTRITOS else sl
            out.append(f'<tr class="setor-divider{rc}"><td colspan="8">{label}</td></tr>')
        st = r["status"]
        bl = {"crit":"CRÍTICO","alert":"ALERTA","ok":"OK"}[st]
        out.append(f'<tr><td class="nome-cell">{r["nome_display"]} <span class="badge {st}" style="margin-left:6px">{bl}</span></td>')
        dias_by = {d["data"]: d for d in r["dias"]}
        for di, _, _ in DIAS_LABELS:
            dia = dias_by.get(di)
            if dia: out.append(render_dia(dia))
            else: out.append('<td><div class="dia-celula folga"><div class="tag-grande folga">—</div></div></td>')
        out.append('</tr>')
    out.append("""
    </tbody></table></div>
</div>
""")

    # ============ ABA 04 — Tratativa RH ============
    out.append(f"""
<div class="tab-panel" id="tab-04">
  <div class="panel-header">
    <h2>Tratativa RH — acompanhamento ativo</h2>
    <p>Casos sob responsabilidade da Consultora RH. Status visível pra cobrança e KPI de desempenho.</p>
  </div>
  <div class="kpi-rh-perf">
    <h4>● Desempenho RH na semana</h4>
    <div class="num-grande">{len(casos)} casos abertos</div>
    <div class="legenda">{len(cat_investigar)} pra investigar · {len(cat_ajuste)} pra ajustar no RHID · {len(cat_verificar)} pra verificar</div>
    <div class="legenda" style="margin-top:8px">→ Próxima rodada vai medir % resolvido e tempo médio.</div>
  </div>
  <div class="rh-resumo">
    <div class="rh-resumo-card investigar"><h4>● INVESTIGAR (REG-S1/S6)</h4><div class="val">{len(cat_investigar)}</div><div class="sub">Falha biométrica suspeita ou abandono — fora dos indicadores.</div></div>
    <div class="rh-resumo-card ajuste"><h4>● AJUSTE NO RHID (REG-S2/S3)</h4><div class="val">{len(cat_ajuste)}</div><div class="sub">Esquecimento de batidas — corrigir antes do fechamento.</div></div>
    <div class="rh-resumo-card verificar"><h4>● VERIFICAR (REG-S4)</h4><div class="val">{len(cat_verificar)}</div><div class="sub">Trabalhou em folga — confirmar convocação.</div></div>
  </div>
""")

    def render_caso(c):
        sev_class = {"CRITICO":"crit","ALERTA":"alert","MEDIO":"medio","INFO":"info"}.get(c["severidade"],"info")
        sev_label = {"CRITICO":"CRÍTICO","ALERTA":"ALERTA","MEDIO":"MÉDIO","INFO":"INFO"}.get(c["severidade"], c["severidade"])
        cat = c.get("categoria","").lower()
        cat_class = {"investigar":"cat-investigar","ajuste_rhid":"cat-ajuste","verificar":"cat-verificar"}.get(cat,"")
        responsavel = c.get("responsavel","Consultora RH")
        prazo = c.get("prazo_sugerido","-")
        dias_str = ", ".join(c.get("dias_afetados",[])[:3])
        if len(c.get("dias_afetados",[])) > 3: dias_str += f" + {len(c['dias_afetados'])-3}"

        historico_extra = ""
        if c["tipo"] == "FALTAS_EXCESSIVAS" and "Elissandro" in c["nome"]:
            historico_extra = """<div class="historico-mini"><strong>Histórico (01/04 a 05/05):</strong><br>
            • 01-16/04 (16 dias): batidas regulares 06:30/12:00/13:30/16:00<br>
            • <strong>17/04</strong>: quebra de padrão (12:18 / 16:01 só)<br>
            • <strong>18/04 a 04/05 (18 dias)</strong>: ZERO batidas no relógio<br>
            • Sem atestado/licença/ajuste lançado<br>
            <strong>Diagnóstico:</strong> falha biométrica/cadastro desde ~17/04.</div>"""

        return f"""<div class="tratativa-card {cat_class}">
          <div class="topo">
            <div><h3>{html.escape(c["nome"])}</h3>
              <div class="meta-tag">{SETOR_DISPLAY.get(c["setor"], c["setor"])} · <span class="mono">{c["tipo"]}</span></div>
            </div>
            <div><span class="badge {sev_class}">{sev_label}</span></div>
          </div>
          <div class="descricao">{html.escape(c["descricao"])}</div>
          {historico_extra}
          <div class="meta-info">
            <div><span class="lbl-mini">Responsável</span><span class="val-mini">{html.escape(responsavel)}</span></div>
            <div><span class="lbl-mini">Prazo</span><span class="val-mini">{html.escape(prazo)}</span></div>
            <div><span class="lbl-mini">Dias</span><span class="val-mini">{html.escape(dias_str) if dias_str else '—'}</span></div>
            <div><span class="lbl-mini">Aberto</span><span class="val-mini">{datetime.now().strftime('%d/%m')}</span></div>
          </div>
          <div class="acao-row"><span class="lbl">→ AÇÃO</span><span>{html.escape(c["acao_sugerida"])}</span></div>
          <div class="status-row"><span class="check-box"></span><strong>Status:</strong> <span style="color:var(--ink-mute)">Pendente</span> · próxima rodada compara com S20.</div>
        </div>"""

    if cat_investigar:
        out.append(f'<div class="section-title investigar">● INVESTIGAR <span class="count">{len(cat_investigar)} caso(s)</span></div>')
        for c in cat_investigar: out.append(render_caso(c))
    if cat_ajuste:
        out.append(f'<div class="section-title ajuste">● AJUSTE NO RHID <span class="count">{len(cat_ajuste)} caso(s)</span></div>')
        for c in cat_ajuste: out.append(render_caso(c))
    if cat_verificar:
        out.append(f'<div class="section-title verificar">● VERIFICAR <span class="count">{len(cat_verificar)} caso(s)</span></div>')
        for c in cat_verificar: out.append(render_caso(c))

    out.append("""
  <div class="suspensos-block" style="margin-top:18px">
    <h4>● Inconsistências de cadastro</h4>
    <strong>Josemaria Maximiana</strong> · saiu mas continua ativa no RHID.<br>
    <strong>Alana</strong> · escala diz mas não bate ponto.<br>
    <strong>Conflito Grasiela</strong> · escala manda (regra atual).
  </div>
</div>

</main>
""")

    # Footer + scripts
    serie_json = json.dumps(serie)
    out.append(f"""
<div class="foot">
  Skill <span class="mono">monitoramento-jornada-gran v3.2</span> · Histórico cumulativo · {now} · {n_total} ativos · {len(casos)} tratativa RH · {len(suspensos)} suspenso · {len(semanas_hist)} semanas no histórico
</div>

<script>
const dados = {serie_json};
const labels = dados.map(d => d.sid);
new Chart(document.getElementById('trend'), {{
  type: 'bar',
  data: {{labels, datasets:[
    {{label:'CRIT', data:dados.map(d=>d.crit), backgroundColor:'#b8362f', stack:'st'}},
    {{label:'ALERT', data:dados.map(d=>d.alert), backgroundColor:'#d4a52e', stack:'st'}},
    {{label:'OK', data:dados.map(d=>d.ok), backgroundColor:'#3f8654', stack:'st'}},
  ]}},
  options:{{responsive:true,maintainAspectRatio:false,plugins:{{title:{{display:true,text:'Mix de status por semana'}}}},scales:{{x:{{stacked:true}},y:{{stacked:true,beginAtZero:true}}}}}}
}});
new Chart(document.getElementById('trend2'), {{
  type:'line',
  data:{{labels, datasets:[
    {{label:'Atrasos >15min', data:dados.map(d=>d.atrasos), borderColor:'#d4a52e', backgroundColor:'rgba(212,165,46,0.1)', tension:0.3, fill:true}},
    {{label:'Janela proibida', data:dados.map(d=>d.jp), borderColor:'#b8362f', backgroundColor:'rgba(184,54,47,0.1)', tension:0.3, fill:true}},
    {{label:'Tratativa RH', data:dados.map(d=>d.tratativa), borderColor:'#3a7bc8', backgroundColor:'rgba(58,123,200,0.1)', tension:0.3, fill:true, borderDash:[5,5]}},
  ]}},
  options:{{responsive:true,maintainAspectRatio:false,plugins:{{title:{{display:true,text:'Tendência de ocorrências e Tratativa RH'}}}},scales:{{y:{{beginAtZero:true}}}}}}
}});

document.querySelectorAll('.tab').forEach(btn => {{
  btn.addEventListener('click', () => {{
    document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
    window.scrollTo({{top:0, behavior:'smooth'}});
  }});
}});
</script>

</body>
</html>
""")

    sys.stdout.write("".join(out))

if __name__ == "__main__":
    main()
