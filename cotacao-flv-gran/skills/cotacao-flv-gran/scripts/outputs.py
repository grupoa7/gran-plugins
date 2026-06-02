"""
outputs.py — Geradores dos 2 entregáveis.

1) gerar_mapa_html  -> Cotação Inteligente (HTML desktop, identidade visual do Survey Gran:
   claro/creme + verde #1e4d2b + dourado #c9a227; Aptos/Nunito no texto e JetBrains Mono
   nos números). 5 abas: 01 Matriz de Cotação · 02 Inteligência CEASA · 03 Mercado & Decisão
   · 04 Vendas & Perdas · 05 Alertas.
2) gerar_pedidos_whatsapp -> Pedido por Fornecedor (texto WhatsApp: blocos/emojis,
   sem %, sem centavos, sem parênteses, 1 envio).

Linguagem: português claro, sem jargão de inglês. A compradora (Marize) é o leitor-alvo.
Gráficos: SVG inline / barras em % (sem CDN — roda offline).
"""
from __future__ import annotations
import html
import json
import re
import unicodedata
from datetime import date, datetime

CURVA_RANK = {"A*": 0, "A": 1, "B": 2, "C+": 3, "C": 4, "": 9}


def _prioridade(d):
    return (CURVA_RANK.get((d.get("curva") or "").strip(), 9), -(d.get("qtd") or 0))


def _fmt_q(q):
    q = float(q or 0)
    return str(int(q)) if q == int(q) else f"{q:.1f}".replace(".", ",")


def _brl(v, dec=2):
    s = f"{float(v or 0):,.{dec}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def _esc(s):
    return html.escape(str(s if s is not None else ""))


# semanas em 60 dias (60 / 7) — divisor para giro semanal médio
_SEMANAS_60D = 8.6


# =========================================================================== #
# Match CEASA <-> item do Gran (heurística por palavras-chave)
# =========================================================================== #
_STOP = {
    "kg", "un", "und", "uni", "unidade", "pct", "pacote", "quilo", "kilo", "g", "gr",
    "cx", "sc", "saco", "mol", "duzia", "duzias", "cento", "bdj", "bandeja", "vacuo",
    "de", "da", "do", "com", "sem", "tipo", "premium",
}


def _norm(s):
    s = unicodedata.normalize("NFKD", str(s or "").lower()).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _sig_words(desc):
    """Palavras significativas do desc Gran (sem unidades/stopwords/números)."""
    out = []
    for w in _norm(desc).split():
        if w in _STOP or re.fullmatch(r"\d+\w*", w):
            continue
        out.append(w)
    return out


# prefixos de embalagem que aparecem grudados em chaves do CEASA
_CEASA_PREFIX = {
    "hortalicas", "frutas", "legumes", "ce", "se", "cx", "sc", "kg", "und", "un",
    "centro", "cento", "duzias", "ovos", "mol", "frd", "fd", "c", "kgs",
}


def _ceasa_tokens(produto_norm):
    """Tokens limpos de uma chave CEASA, descartando prefixos de embalagem grudados."""
    toks = produto_norm.split()
    # remove prefixos de embalagem do começo
    while toks and (toks[0] in _CEASA_PREFIX or re.fullmatch(r"\d+\w*", toks[0])):
        toks.pop(0)
    return [t for t in toks if not re.fullmatch(r"\d+\w*", t)]


def _ceasa_serie_para_item(d, ceasa_series):
    """Acha a série temporal CEASA do item (mesma lógica, mas chaves são nomes legíveis)."""
    if not ceasa_series:
        return None
    ws = _sig_words(d.get("desc"))
    if not ws:
        return None
    chave = ws[:2]
    melhor = None
    for k, v in ceasa_series.items():
        toks = set(_ceasa_tokens(_norm(k)))
        if not toks or chave[0] not in toks:
            continue
        sc = len(toks & set(ws))
        if len(chave) >= 2 and chave[1] in toks:
            sc += 3
        if melhor is None or sc > melhor[0]:
            melhor = (sc, k, v)
    return (melhor[1], melhor[2]) if melhor else None


# =========================================================================== #
# CSS — espelha a identidade do Survey Gran (string pura, sem f-string)
# =========================================================================== #
CSS = """
:root{
 --bg:#ffffff;--bg-soft:#f6f4ee;--bg-cream:#faf7ef;--border:#e8e3d4;--border-soft:#f0ebdc;
 --ink:#1a1f1a;--ink-dim:#4a5248;--ink-mute:#8b8f86;
 --verde:#1e4d2b;--verde-2:#2d6a3f;--verde-3:#3f8654;--verde-bg:#e7f0e9;
 --dourado:#c9a227;--dourado-2:#e8b93a;--dourado-bg:#faf1d4;
 --vermelho:#b8362f;--vermelho-bg:#f2d9d3;--amarelo:#d4a52e;--amarelo-bg:#faf1d4;
 --azul:#2c5d7c;--azul-bg:#e4eef4;
 --shadow:0 1px 2px rgba(30,77,43,.04),0 4px 12px rgba(30,77,43,.06);}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
 font-family:'Aptos','Nunito Sans',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;}
.container{max-width:1560px;margin:0 auto;padding:28px 32px 80px;}
.mono{font-family:'JetBrains Mono',ui-monospace,monospace;}
.main-header{display:flex;justify-content:space-between;align-items:flex-end;gap:24px;
 border-bottom:2px solid var(--verde);padding-bottom:18px;margin-bottom:8px;flex-wrap:wrap;}
.eyebrow{font-family:'JetBrains Mono',monospace;font-size:11px;letter-spacing:.18em;
 text-transform:uppercase;color:var(--dourado);margin:0 0 6px;}
.main-header h1{font-size:36px;margin:0;font-weight:700;letter-spacing:-.02em;color:var(--verde);}
.subtitle{color:var(--ink-mute);font-size:13px;margin:8px 0 0;}
.subtitle b{color:var(--ink-dim);font-weight:600;}
.meta{text-align:right;font-size:12px;color:var(--ink-dim);line-height:1.7;}
.meta strong{color:var(--verde);font-family:'JetBrains Mono',monospace;}
.tabs-wrap{position:sticky;top:0;background:var(--bg);z-index:20;border-bottom:1px solid var(--border);margin:18px 0 0;}
.tabs{display:flex;gap:2px;overflow-x:auto;}
.tab{flex:0 0 auto;padding:12px 18px;border:none;background:transparent;cursor:pointer;
 font-family:'Aptos','Nunito Sans',sans-serif;font-size:13px;font-weight:600;color:var(--ink-mute);
 border-bottom:3px solid transparent;}
.tab:hover{color:var(--verde);background:var(--bg-soft);}
.tab.active{color:var(--verde);border-bottom-color:var(--dourado);background:var(--bg-cream);}
.tab .num{font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--ink-mute);margin-right:7px;}
.tab.active .num{color:var(--dourado);}
.tab-panel{display:none;padding-top:22px;}
.tab-panel.active{display:block;animation:fade .25s ease;}
@keyframes fade{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}
.section-kicker{font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:.15em;
 text-transform:uppercase;color:var(--dourado);margin:0;}
.section-title{font-size:22px;margin:4px 0 2px;color:var(--ink);letter-spacing:-.01em;}
.section-desc{color:var(--ink-mute);font-size:13px;margin:0 0 18px;max-width:980px;line-height:1.55;}
.kpi-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-bottom:24px;}
/* KPIs do cabeçalho — 3 cartões em LINHA (lado a lado), topo mais baixo */
.kpi-row{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:14px 0 4px;}
.kpi-row .kpi-card{display:flex;flex-direction:column;justify-content:center;}
@media(max-width:720px){.kpi-row{grid-template-columns:1fr;}}
.kpi-card{background:var(--bg-cream);border:1px solid var(--border);border-radius:12px;padding:14px 16px;box-shadow:var(--shadow);}
.kpi-card.big{background:var(--verde);color:#fff;border-color:var(--verde);}
.kpi-label{font-family:'JetBrains Mono',monospace;font-size:9px;letter-spacing:.12em;text-transform:uppercase;
 color:var(--ink-mute);margin:0;}
.kpi-card.big .kpi-label{color:var(--dourado-2);}
.kpi-value{font-family:'JetBrains Mono',monospace;font-size:26px;font-weight:700;margin:6px 0 2px;color:var(--verde);}
.kpi-card.big .kpi-value{color:#fff;}
.kpi-unit{font-size:14px;color:var(--ink-mute);}
.kpi-sub{font-size:11px;color:var(--ink-mute);margin:0;}
.kpi-card.big .kpi-sub{color:rgba(255,255,255,.78);}
.chart-box{background:var(--bg-cream);border:1px solid var(--border);border-radius:14px;padding:20px 22px;margin-bottom:22px;box-shadow:var(--shadow);}
.chart-box h3{font-size:15px;margin:0 0 4px;color:var(--verde);}
.chart-box .desc{font-size:12px;color:var(--ink-mute);margin:0 0 16px;line-height:1.5;}
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:22px;}
@media(max-width:1100px){.two-col{grid-template-columns:1fr;}}
.tbl-scroll{overflow-x:auto;}
table.data{width:100%;border-collapse:collapse;font-size:13px;}
table.data th{background:var(--verde);color:#fff;font-family:'JetBrains Mono',monospace;font-size:10px;
 letter-spacing:.04em;text-transform:uppercase;padding:8px 7px;text-align:right;}
table.data th.l,table.data td.l{text-align:left;}
/* grupo de fornecedores: sinalizado por FUNDO levemente destacado (não por cabeçalho 2 níveis).
   th usa um verde um tom diferente; td usa um creme levemente diferente do branco. */
table.data th.grp-cell{background:var(--verde-2);}
table.data td.grp-cell{background:var(--bg-cream);}
table.data tbody tr:hover td.grp-cell{background:var(--bg-soft);}
table.data td{padding:7px;border-bottom:1px solid var(--border-soft);text-align:right;
 font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--ink-dim);white-space:nowrap;}
table.data td.l{text-align:left;font-family:'Aptos','Nunito Sans',sans-serif;color:var(--ink);font-weight:500;white-space:normal;}
table.data td.sep{border-left:3px solid var(--dourado);}
table.data th.sep{border-left:3px solid var(--dourado);}
table.data tbody tr:hover td{background:var(--bg-soft);}
table.data tfoot td{background:var(--verde-bg);color:var(--verde);font-weight:700;border-top:2px solid var(--verde);
 font-family:'JetBrains Mono',monospace;}
/* vencedor: destaque por FUNDO verde suave, texto normal escuro (sem verde/negrito forte) */
.cell-win{background:var(--verde-bg)!important;color:var(--ink)!important;font-weight:600;}
table.data tbody tr:hover td.cell-win{background:var(--verde-bg)!important;}
.cell-ex{color:var(--ink-mute)!important;text-decoration:line-through;}
.ceasa-sit{display:block;font-size:9px;color:var(--ink-mute);font-family:'Aptos','Nunito Sans',sans-serif;}
.tag{display:inline-block;padding:1px 7px;border-radius:5px;font-family:'JetBrains Mono',monospace;
 font-size:9px;font-weight:700;letter-spacing:.04em;}
.tag.astar{background:var(--dourado);color:#fff;}.tag.curva{background:var(--border);color:var(--ink-dim);}
.tag.ent{background:var(--verde-3);color:#fff;}.tag.busca{background:var(--dourado-bg);color:#8a6500;border:1px solid #e0c97a;}
/* chip de recomendação (só a palavra, sem símbolo) */
.rec{display:inline-flex;align-items:center;gap:4px;padding:4px 10px;border-radius:7px;
 font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700;letter-spacing:.03em;white-space:nowrap;}
.rec .rico{font-size:12px;line-height:1;}
.rec.verde{background:var(--verde);color:#fff;}
.rec.ambar{background:var(--dourado-bg);color:#8a6500;border:1px solid #e0c97a;}
.rec.vermelho{background:var(--vermelho-bg);color:var(--vermelho);border:1px solid #e0b4ad;}
.rec.cinza{background:var(--border);color:var(--ink-dim);}
/* Departamento (col 1) — texto curto, secundário */
td.dept{font-family:'JetBrains Mono',monospace;font-size:10px;letter-spacing:.04em;
 text-transform:uppercase;color:var(--ink-mute);max-width:96px;white-space:normal;}
/* CEASA — coluna um pouco mais larga p/ o conteúdo (preço + % vs melhor) não cortar.
   O separador dourado fica deslocado p/ a direita via padding-left maior. */
th.ceasa-th{min-width:118px;text-align:center;}
td.ceasa-cell{min-width:118px;white-space:normal;line-height:1.25;}
table.data th.sep.ceasa-th,table.data td.sep.ceasa-cell{padding-left:14px;}
/* valores financeiros semanais (Venda/sem, Custo/sem) */
.valnum{font-family:'JetBrains Mono',monospace;font-size:13px;font-weight:600;color:var(--ink-dim);white-space:nowrap;}
.valnum small{font-size:9px;color:var(--ink-mute);font-weight:400;display:block;margin-top:1px;}
/* Economia/sem — o prêmio por trocar de fornecedor (destaque verde) */
.econ{font-family:'JetBrains Mono',monospace;font-size:16px;font-weight:700;color:var(--verde);white-space:nowrap;}
.econ small{font-size:10px;color:var(--verde-3);font-weight:600;display:block;margin-top:1px;}
.econ.zero{color:var(--ink-mute);font-weight:400;font-size:13px;}
.econ.neg{color:#b3261e;}.econ.neg small{color:#b3261e;opacity:.85;display:block;}
/* faixas de intensidade da Economia/sem — fundo verde crescente conforme o R$/sem */
td .econ.e1,td .econ.e2,td .econ.e3,td .econ.e4{display:inline-block;padding:2px 8px;border-radius:7px;}
.econ.e1{background:#eef5ef;color:var(--verde-3);}
.econ.e2{background:#d6e8da;color:var(--verde-2);}
.econ.e3{background:#b3d3bb;color:var(--verde);}
.econ.e4{background:#7fb38d;color:#0f2e18;}
.econ.e4 small,.econ.e3 small{color:inherit;opacity:.85;}
/* item na matriz — nome + tags (curva/canal); justificativa fica na coluna "Por quê" */
td.item{max-width:300px;}
td.item .nome{font-weight:600;color:var(--ink);}
/* coluna "Por quê" — justificativa em até 2 linhas, largura controlada */
td.porque{max-width:240px;}
td.porque .jus{display:block;font-family:'Aptos','Nunito Sans',sans-serif;font-size:11px;color:var(--ink-mute);
 line-height:1.35;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;max-width:240px;}
/* CEASA: 3 estados */
.ceasa-pc{font-family:'JetBrains Mono',monospace;color:var(--ink-dim);}
.ceasa-vs{display:block;font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:700;margin-top:1px;}
.ceasa-vs.acima{color:var(--vermelho);}.ceasa-vs.abaixo{color:var(--verde-3);}
.ceasa-perg{display:inline-block;padding:1px 7px;border-radius:5px;font-family:'JetBrains Mono',monospace;
 font-size:9px;font-weight:700;background:var(--azul-bg);color:var(--azul);border:1px solid #b8d2e2;}
.ceasa-perg .cand{display:block;font-family:'Aptos','Nunito Sans',sans-serif;font-weight:400;font-size:9px;color:var(--ink-mute);margin-top:2px;}
/* bandeirinha de feedback */
.fbflag{font-size:13px;cursor:default;}
.fbflag.pref{color:var(--dourado);}.fbflag.ok{color:var(--verde-3);}
.fbflag.ruim{color:var(--amarelo);}.fbflag.evitar{color:var(--vermelho);}
/* bloco "a confirmar" no topo da aba CEASA */
.confirmar-box{background:var(--azul-bg);border:1px solid #b8d2e2;border-left:4px solid var(--azul);
 border-radius:10px;padding:14px 16px;margin-bottom:22px;}
.confirmar-box h3{font-size:14px;margin:0 0 4px;color:var(--azul);}
.confirmar-box .desc{font-size:12px;color:var(--ink-dim);margin:0 0 10px;line-height:1.5;}
.confirmar-box ul{margin:0;padding-left:18px;font-size:12.5px;color:var(--ink);line-height:1.6;}
.confirmar-box ul .cand{color:var(--ink-mute);font-size:11px;}
.pos{color:var(--verde);font-weight:700;}.neg{color:var(--vermelho);font-weight:700;}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:5px;vertical-align:middle;}
.dot.ok{background:var(--verde-3);}.dot.warn{background:var(--amarelo);}.dot.bad{background:var(--vermelho);}
.filters{display:flex;gap:14px;flex-wrap:wrap;align-items:flex-end;margin-bottom:16px;
 background:var(--bg-cream);border:1px solid var(--border);border-radius:12px;padding:14px 18px;}
.filters label{display:flex;flex-direction:column;gap:4px;font-size:11px;color:var(--ink-mute);
 font-family:'JetBrains Mono',monospace;letter-spacing:.06em;text-transform:uppercase;}
.filters select{font-family:'Aptos','Nunito Sans',sans-serif;font-size:13px;padding:6px 10px;
 border:1px solid var(--border);border-radius:8px;background:#fff;color:var(--ink);min-width:170px;}
.filters .fdir{margin-left:auto;display:flex;gap:18px;align-items:center;
 background:var(--bg-cream);border:1px solid var(--border);border-radius:10px;padding:7px 16px;}
.filters .fdir .fd-i{display:flex;flex-direction:column;text-align:right;line-height:1.25;}
.filters .fdir .fl{font-size:9px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-mute);}
.filters .fdir b{font-family:'JetBrains Mono',monospace;font-size:16px;color:var(--verde);}
.alert{display:flex;gap:12px;align-items:flex-start;padding:12px 14px;border-radius:10px;border-left:4px solid;
 background:var(--bg-soft);margin-bottom:10px;font-size:13px;line-height:1.45;}
.alert.vermelho{background:var(--vermelho-bg);border-left-color:var(--vermelho);}
.alert.amarelo{background:var(--amarelo-bg);border-left-color:var(--amarelo);}
.alert.verde{background:var(--verde-bg);border-left-color:var(--verde-3);}
.alert .acount{font-family:'JetBrains Mono',monospace;font-size:22px;font-weight:700;min-width:44px;text-align:center;}
.alert.vermelho .acount{color:var(--vermelho);}.alert.amarelo .acount{color:#9c7a14;}.alert.verde .acount{color:var(--verde);}
.alert b{display:block;margin-bottom:3px;}
.alert .alist{color:var(--ink-dim);font-size:12px;}
.hbar-row{display:grid;grid-template-columns:240px 1fr 110px;gap:12px;align-items:center;margin-bottom:7px;}
.hbar-row .lbl{font-size:12px;color:var(--ink);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.hbar-row .lbl .sub{color:var(--ink-mute);font-size:11px;}
.hbar-row .track{height:18px;background:var(--border-soft);border-radius:5px;overflow:hidden;}
.hbar-row .fill{height:100%;border-radius:5px;background:linear-gradient(90deg,var(--verde) 0%,var(--verde-3) 100%);}
.hbar-row .fill.red{background:linear-gradient(90deg,#8f2a24 0%,var(--vermelho) 100%);}
.hbar-row .fill.gold{background:linear-gradient(90deg,var(--dourado) 0%,var(--dourado-2) 100%);}
.hbar-row .val{font-family:'JetBrains Mono',monospace;font-size:12px;text-align:right;color:var(--verde);font-weight:600;}
.hbar-row .val.red{color:var(--vermelho);}
.spk-row{display:grid;grid-template-columns:200px 86px 1fr 96px;gap:12px;align-items:center;margin-bottom:8px;
 padding-bottom:8px;border-bottom:1px solid var(--border-soft);}
.spk-row:last-child{border-bottom:none;}
.spk-row .lbl{font-size:12px;color:var(--ink);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.spk-row .lbl .sub{display:block;color:var(--ink-mute);font-size:10px;}
.spk-row .now{font-family:'JetBrains Mono',monospace;font-size:12px;text-align:right;color:var(--ink-dim);}
.spk-row .pct{font-family:'JetBrains Mono',monospace;font-size:13px;text-align:right;font-weight:700;}
.spk svg{display:block;}
.legend{display:flex;gap:18px;flex-wrap:wrap;font-size:11px;color:var(--ink-mute);margin-top:6px;}
.legend span{display:inline-flex;align-items:center;gap:5px;}
.sit-bars{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;}
.sit-cell{background:#fff;border:1px solid var(--border);border-radius:10px;padding:12px;text-align:center;}
.sit-cell .v{font-family:'JetBrains Mono',monospace;font-size:24px;font-weight:700;color:var(--verde);}
.sit-cell .k{font-size:11px;color:var(--ink-mute);text-transform:capitalize;}
/* gráfico interativo de linha — aba CEASA */
.gchart-head{display:flex;gap:18px;align-items:flex-end;flex-wrap:wrap;margin-bottom:14px;}
.gchart-head label{display:flex;flex-direction:column;gap:4px;font-size:11px;color:var(--ink-mute);
 font-family:'JetBrains Mono',monospace;letter-spacing:.06em;text-transform:uppercase;}
.gchart-head select{font-family:'Aptos','Nunito Sans',sans-serif;font-size:14px;padding:7px 12px;
 border:1px solid var(--border);border-radius:8px;background:#fff;color:var(--ink);min-width:280px;}
.gchart-stats{display:flex;gap:24px;align-items:flex-end;margin-left:auto;text-align:right;}
.gchart-stats .st{font-size:11px;color:var(--ink-mute);}
.gchart-stats .st b{display:block;font-family:'JetBrains Mono',monospace;font-size:18px;font-weight:700;color:var(--verde);}
.gchart-stats .st b.neg{color:var(--vermelho);}.gchart-stats .st b.pos{color:var(--verde-3);}
.gchart-svg{width:100%;height:auto;display:block;background:#fff;border:1px solid var(--border-soft);border-radius:10px;}
footer{margin-top:60px;padding-top:20px;border-top:1px solid var(--border);
 font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--ink-mute);letter-spacing:.1em;text-transform:uppercase;}
.muted{color:var(--ink-mute);font-size:12px;}
"""

JS = """
document.querySelectorAll('.tab').forEach(function(t){
  t.addEventListener('click',function(){
    document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));
    document.querySelectorAll('.tab-panel').forEach(p=>p.classList.remove('active'));
    t.classList.add('active');
    document.getElementById('tab-'+t.dataset.tab).classList.add('active');
    window.scrollTo({top:0,behavior:'smooth'});
  });
});
function aplicarFiltros(){
  var fg=document.getElementById('f-grupo'),fv=document.getElementById('f-venc'),fc=document.getElementById('f-curva'),fr=document.getElementById('f-rec');
  var g=fg?fg.value:'',v=fv?fv.value:'',c=fc?fc.value:'',r=fr?fr.value:'';
  var venda=0,custo=0,pos=0,econ=0,n=0;
  document.querySelectorAll('#tabela-matriz tbody tr').forEach(function(tr){
    var ok=(g===''||tr.dataset.grupo===g)&&(v===''||tr.dataset.venc===v)&&(c===''||tr.dataset.curva===c)&&(r===''||tr.dataset.rec===r);
    tr.style.display=ok?'':'none';
    if(ok){ venda+=parseFloat(tr.dataset.venda||'0'); custo+=parseFloat(tr.dataset.custo||'0'); pos+=parseFloat(tr.dataset.pos||'0'); econ+=parseFloat(tr.dataset.econ||'0'); n++; }
  });
  var fmt=function(x){return x.toLocaleString('pt-BR',{minimumFractionDigits:0,maximumFractionDigits:0});};
  var tv=document.getElementById('tot-venda'),ct=document.getElementById('tot-custo'),tp=document.getElementById('tot-pos'),te=document.getElementById('tot-econ'),cn=document.getElementById('tot-itens');
  if(tv) tv.textContent=fmt(venda);
  if(ct) ct.textContent=fmt(custo);
  if(tp) tp.textContent=fmt(pos);
  if(te) te.textContent=fmt(econ);
  if(cn) cn.textContent=n;
  var fd1=document.getElementById('fd-custo'),fd2=document.getElementById('fd-itens'),fd3=document.getElementById('fd-econ'),fd4=document.getElementById('fd-pos');
  if(fd1) fd1.textContent='R$ '+fmt(custo);
  if(fd2) fd2.textContent=n;
  if(fd3) fd3.textContent='R$ '+fmt(econ);
  if(fd4) fd4.textContent='R$ '+fmt(pos);
}
document.querySelectorAll('.filters select').forEach(function(s){s.addEventListener('change',aplicarFiltros);});
aplicarFiltros();

/* ---- gráfico interativo de linha (aba CEASA) ---- */
(function(){
  var raw=document.getElementById('g-dados');
  if(!raw) return;
  var DADOS=JSON.parse(raw.textContent);
  var sel=document.getElementById('g-sel'), svg=document.getElementById('g-svg');
  var NS='http://www.w3.org/2000/svg';
  var W=880,H=320,ml=58,mr=24,mt=22,mb=42;
  var brl=function(x){return x.toLocaleString('pt-BR',{minimumFractionDigits:2,maximumFractionDigits:2});};
  function el(t,a){var e=document.createElementNS(NS,t);for(var k in a)e.setAttribute(k,a[k]);return e;}
  function desenhar(nome){
    var d=DADOS[nome]; if(!d) return;
    while(svg.firstChild) svg.removeChild(svg.firstChild);
    var pts=d.pts, n=pts.length;
    var vals=pts.map(function(p){return p.v;});
    var lo=Math.min.apply(null,vals), hi=Math.max.apply(null,vals);
    if(hi===lo){hi=lo+1;lo=Math.max(0,lo-1);}
    var pad=(hi-lo)*0.12; lo=Math.max(0,lo-pad); hi=hi+pad;
    var px=function(i){return ml+(n<=1?0:i/(n-1)*(W-ml-mr));};
    var py=function(v){return H-mb-(v-lo)/(hi-lo)*(H-mt-mb);};
    // grid horizontal + rótulos de eixo Y (4 linhas)
    for(var g=0;g<=4;g++){
      var vy=lo+(hi-lo)*g/4, y=py(vy);
      svg.appendChild(el('line',{x1:ml,y1:y,x2:W-mr,y2:y,stroke:'#e8e3d4','stroke-width':1}));
      var ty=el('text',{x:ml-8,y:y+3,'text-anchor':'end','font-size':10,fill:'#8b8f86','font-family':'JetBrains Mono,monospace'});
      ty.textContent='R$ '+brl(vy); svg.appendChild(ty);
    }
    // rótulos de eixo X (datas) — afina se muitos pontos
    var step=Math.ceil(n/9);
    pts.forEach(function(p,i){
      if(i%step!==0 && i!==n-1) return;
      var tx=el('text',{x:px(i),y:H-mb+16,'text-anchor':'middle','font-size':9,fill:'#8b8f86','font-family':'JetBrains Mono,monospace'});
      tx.textContent=p.d; svg.appendChild(tx);
    });
    // linha (polyline) verde
    var poly=pts.map(function(p,i){return px(i)+','+py(p.v);}).join(' ');
    svg.appendChild(el('polyline',{points:poly,fill:'none',stroke:'#1e4d2b','stroke-width':2.4,'stroke-linejoin':'round','stroke-linecap':'round'}));
    // marcadores (círculos dourados) + rótulo de valor (mín/máx/atual destacados)
    var iMin=vals.indexOf(Math.min.apply(null,vals)), iMax=vals.indexOf(Math.max.apply(null,vals));
    pts.forEach(function(p,i){
      var destaque=(i===iMin||i===iMax||i===n-1);
      svg.appendChild(el('circle',{cx:px(i),cy:py(p.v),r:destaque?4.5:3,fill:'#c9a227',stroke:'#fff','stroke-width':1.5}));
      if(destaque){
        var lab=el('text',{x:px(i),y:py(p.v)-9,'text-anchor':'middle','font-size':10,'font-weight':700,fill:i===n-1?'#1e4d2b':'#8b8f86','font-family':'JetBrains Mono,monospace'});
        lab.textContent=brl(p.v); svg.appendChild(lab);
      }
    });
    // estatísticas ao lado
    document.getElementById('g-atual').textContent='R$ '+brl(d.atual);
    document.getElementById('g-faixa').textContent='R$ '+brl(d.min)+' – '+brl(d.max);
    var te=document.getElementById('g-tend'), t=d.tend;
    te.textContent=(t>0?'+':'')+t.toFixed(0)+'%';
    te.className=t>5?'neg':(t<-5?'pos':'');
    document.getElementById('g-sit').textContent=d.sit||'—';
  }
  sel.addEventListener('change',function(){desenhar(sel.value);});
  desenhar(sel.value);
})();
"""


# =========================================================================== #
# Mapa de Cotação
# =========================================================================== #
def gerar_mapa_html(resultado, validades, semana, vendas=None, periodo="",
                    ceasa_atual=None, ceasa_series=None, ceasa_datas=None, revisao=None):
    ceasa_atual = ceasa_atual or {}
    ceasa_series = ceasa_series or {}
    ceasa_datas = ceasa_datas or []
    revisao = revisao or []
    perguntar_ceasa = resultado.get("perguntar_ceasa") or []
    # NÃO re-ordenar aqui (a matriz reordena por curva ABC em _panel_matriz).
    dec = list(resultado["decisoes"])
    ok = [d for d in dec if d["status"] == "ok"]
    sem = [d for d in dec if d["status"] != "ok"]
    # economia possível = soma das economias POSITIVAS vs custo atual do BI (onde a cotação ganha).
    economia = sum(d["economia_sem"] for d in ok if (d.get("economia_sem") or 0) > 0)
    trocas = [d for d in ok if d.get("troca_recomendada")]
    fornecedores = sorted({f for d in ok for f in d["candidatos"]})
    acionados = sorted({d["vencedor"]["fornecedor"] for d in ok})
    multifonte = [d for d in ok if d["n_fontes"] >= 2]

    # compra estimada da semana = custo pós-cotação total (giro × melhor preço, já na unidade
    # de venda do Gran e com conversão aplicada). Usa custo_pos_sem p/ bater com a matriz —
    # NÃO qtd×preço bruto (que inflava itens por caixa/maço, ex.: ovos).
    custo_total = sum(d.get("custo_pos_sem") or 0 for d in ok)
    # quantos itens da matriz têm referência CEASA confiável (campo pronto de decisao.py)
    casados_ceasa = sum(1 for d in ok if (d.get("ceasa") or {}).get("status") == "ok")

    chips = " · ".join(f"{_esc(k)}: {_esc(v) or '—'}" for k, v in validades.items())

    head = (
        "<!doctype html><html lang=pt-BR><head><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width,initial-scale=1'>"
        f"<title>Cotação Inteligente FLV — {_esc(semana)}</title>"
        "<style>" + CSS + "</style></head><body><div class=container>"
    )
    header = f"""
<header class=main-header>
 <div><p class=eyebrow>Mapa de Cotação · Gran Hortifruti</p>
 <h1>Cotação Inteligente</h1>
 <p class=subtitle>FLV · Gran Hortifruti &nbsp;·&nbsp; <b>Semana {_esc(semana)}</b>
 {(' · ' + _esc(periodo)) if periodo else ''} &nbsp;·&nbsp; <b>{len(fornecedores)}</b> fornecedores cotando</p>
 <p class=subtitle style="margin-top:4px">Validade das tabelas — {_esc(chips)}</p></div>
 <div class=meta>
 <div>compra estimada da semana <strong>R$ {_brl(custo_total,0)}</strong></div>
 <div><strong>{len(ok)}</strong> itens cotados de <strong>{len(dec)}</strong> na demanda</div>
 <div>economia possível <strong>R$ {_brl(economia,0)}</strong></div>
 <div class=mono>gerado {datetime.now():%d/%m %H:%M}</div></div>
</header>"""

    # KPIs do cabeçalho — 3 cartões LADO A LADO (em linha), para reduzir a altura do topo.
    kpis = f"""
<div class=kpi-row>
 <div class='kpi-card big'><p class=kpi-label>Economia possível</p>
  <p class=kpi-value><span class=kpi-unit>R$</span> {_brl(economia,0)}</p>
  <p class=kpi-sub>em {len(trocas)} trocas de fornecedor sugeridas</p></div>
 <div class=kpi-card><p class=kpi-label>Itens cotados</p>
  <p class=kpi-value>{len(ok)}</p>
  <p class=kpi-sub>de {len(dec)} pedidos na semana</p></div>
 <div class=kpi-card><p class=kpi-label>Compra estimada da semana</p>
  <p class=kpi-value><span class=kpi-unit>R$</span> {_brl(custo_total,0)}</p>
  <p class=kpi-sub>melhor preço de cada item × quantidade</p></div>
</div>"""

    tabs_nav = """
<div class=tabs-wrap><nav class=tabs>
 <button class='tab active' data-tab=matriz><span class=num>01</span>Matriz de Cotação</button>
 <button class=tab data-tab=ceasa><span class=num>02</span>Inteligência CEASA</button>
 <button class=tab data-tab=mercado><span class=num>03</span>Mercado &amp; Decisão</button>
 <button class=tab data-tab=vendas><span class=num>04</span>Vendas &amp; Perdas</button>
 <button class=tab data-tab=alertas><span class=num>05</span>Alertas</button>
</nav></div>"""

    panels = (
        _panel_matriz(ok, fornecedores, vendas, custo_total)
        + _panel_ceasa(ok, ceasa_series, ceasa_datas, ceasa_atual, perguntar_ceasa)
        + _panel_mercado(ok, trocas, economia)
        + _panel_vendas(vendas)
        + _panel_alertas(resultado, sem, revisao=revisao)
    )
    footer = (f"<footer>Cotação Inteligente FLV · Gran Hortifruti · {_esc(semana)} · "
              f"melhor preço por item · referências: mediana da semana + CEASA-BA + último custo · "
              f"{casados_ceasa} itens com referência CEASA</footer>")
    return head + header + kpis + tabs_nav + panels + footer + "<script>" + JS + "</script></div></body></html>"


# --------------------------------------------------------------------------- #
# helpers de apresentação
# --------------------------------------------------------------------------- #
def _grupo_item(d, vendas):
    """Departamento do item (frutas/legumes/verduras...) — via vendas ou heurística."""
    if vendas:
        v = vendas.get(d.get("cod"))
        if v and v.get("grupo"):
            g = v["grupo"]
            return g.split("/")[-1].strip() or g
    # heurística de fallback pelo nome
    n = _norm(d.get("desc"))
    folhas = ("alface", "coentro", "cebolinha", "salsa", "rucula", "hortela",
              "manjericao", "couve", "agriao", "espinafre", "salvia")
    if any(f in n for f in folhas):
        return "VERDURAS"
    return "OUTROS"


def _tags_item(d):
    # Apenas a etiqueta de curva. O canal (ENTREGA/BUSCA) foi removido a pedido do dono:
    # é irrelevante na matriz e já fica claro pelo fornecedor escolhido.
    cv = (d.get("curva") or "").strip()
    cls = "astar" if cv in ("A*", "A") else "curva"
    return f"<span class='tag {cls}'>{_esc(cv or '—')}</span>"


# chip de recomendação: SÓ a palavra (sem símbolo) + classe de cor.
# TROCAR/COMPRAR (verde) · MANTER (cinza/neutro) · NEGOCIAR (âmbar) · CONFERIR/ATENÇÃO (vermelho)
_REC_INFO = {
    "TROCAR": ("Trocar", "verde"),
    "COMPRAR": ("Comprar", "verde"),
    "MANTER": ("Manter", "cinza"),
    "NEGOCIAR": ("Negociar", "ambar"),
    "CONFERIR": ("Conferir", "vermelho"),
    "ATENÇÃO": ("Conferir", "vermelho"),
    "ATENCAO": ("Conferir", "vermelho"),
    "DEFINIR": ("Definir", "cinza"),
}


# Economia/sem — faixa de intensidade de cor proporcional ao valor em R$/sem.
# 4 faixas: quanto maior a economia, mais forte o verde de fundo/texto.
def _econ_faixa(v):
    v = float(v or 0)
    if v >= 400:
        return "e4"
    if v >= 150:
        return "e3"
    if v >= 50:
        return "e2"
    return "e1"

# bandeirinha de feedback do fornecedor vencedor
_FB_FLAG = {
    "preferido": ("pref", "⭐", "fornecedor preferido"),
    "ok": ("ok", "✔", "fornecedor ok"),
    "ruim": ("ruim", "⚠", "fornecedor marcado como ruim"),
    "evitar": ("evitar", "⛔", "fornecedor a evitar"),
}


def _rec_chip(d):
    rec = (d.get("recomendacao") or "DEFINIR").strip()
    label, cls = _REC_INFO.get(rec.upper(), (rec.title(), "cinza"))
    return f"<span class='rec {cls}'>{_esc(label)}</span>"


def _fb_flag(d):
    fb = d.get("fb")
    if not fb:
        return ""
    cls, ico, base = _FB_FLAG.get(fb.get("veredito"), ("ok", "✔", "feedback"))
    nota = fb.get("nota") or ""
    title = f"{base}: {nota}" if nota else base
    return f"<span class='fbflag {cls}' title='{_esc(title)}'>{ico}</span>"


def _ceasa_cell(d):
    """Coluna CEASA — compacta. Estado 'ok' → preço (na unidade Gran) + '% vs melhor'
    (quanto o vencedor está acima/abaixo do atacado). Demais estados → '—'
    (a resolução das incertezas é feita fora da matriz)."""
    c = d.get("ceasa") or {}
    st = c.get("status")
    if st == "ok" and c.get("preco"):
        pc = c["preco"]
        vs = ""
        vprc = (d.get("vencedor") or {}).get("preco_norm")
        if vprc and pc:
            desv = (vprc / pc - 1) * 100
            if abs(desv) >= 2:
                klass = "acima" if desv > 0 else "abaixo"
                sinal = "+" if desv > 0 else ""
                vs = f"<span class='ceasa-vs {klass}'>{sinal}{desv:.0f}% vs melhor</span>"
        return f"<span class=ceasa-pc>R$ {_brl(pc)}</span>{vs}"
    return "<span class=muted>—</span>"


# --------------------------------------------------------------------------- #
# 01 · Matriz de Cotação — decisão-primeiro, ordenada por R$ em jogo
# --------------------------------------------------------------------------- #
def _panel_matriz(ok, fornecedores, vendas, custo_total):
    # NOVA ordem de colunas (definida pelo dono), esquerda → direita:
    #   REALIDADE GRAN: 1 Departamento · 2 Item(+curva) · 3 Venda qtd/sem · 4 Venda R$/sem · 5 Custo/sem
    #   PREÇOS:         6..N Fornecedores (vencedor com FUNDO verde) · CEASA (estreita, % vs melhor)
    #   DECISÃO:        Recomendação(+fb) · Por quê · Economia/sem(+%)
    # CABEÇALHO: UMA ÚNICA <tr> (sem linha de grupo / sem colspan). O agrupamento das colunas
    # de fornecedor é sinalizado por FUNDO levemente destacado (classe grp-cell), não por
    # cabeçalho de 2 níveis — assim a barra verde fica com altura uniforme e sem linha-fantasma.
    # Ordem da matriz: por CURVA ABC de VENDA (decisão do dono 25/05) — NÃO pelo impacto
    # financeiro da cotação (R$ em jogo, que é como as decisões chegam de decisao.enriquecer).
    # Dentro da mesma curva, maior faturamento/sem primeiro (qtd como desempate).
    ok = sorted(ok, key=lambda d: (CURVA_RANK.get((d.get("curva") or "").strip(), 9),
                                   -(d.get("venda_sem") or 0), -(d.get("qtd") or 0)))
    nforn = len(fornecedores)
    venda_total = sum(d.get("venda_sem") or 0 for d in ok)
    custo_sem_total = sum(d.get("custo_sem") or 0 for d in ok)          # custo ATUAL (BI)
    custo_pos_total = sum(d.get("custo_pos_sem") or 0 for d in ok)      # pós-cotação (vencedor)
    economia_total = sum(d.get("economia_sem") or 0 for d in ok)       # atual − pós (com sinal)

    th_forn = "".join(
        f"<th class='grp-cell{' sep' if i==0 else ''}'>{_esc(f)}</th>"
        for i, f in enumerate(fornecedores)
    )
    head = (
        "<tr>"
        "<th class=l>Item</th>"
        "<th>Venda qtd/sem</th>"
        "<th>Venda R$/sem</th>"
        "<th>Custo atual/sem</th>"
        f"{th_forn}"
        "<th class='sep ceasa-th'>CEASA</th>"
        "<th class=sep>Recomendação</th>"
        "<th class=l>Por quê</th>"
        "<th>Custo pós-cotação</th>"
        "<th>Economia/sem</th>"
        "</tr>"
    )

    # selects de filtro
    grupos = sorted({_grupo_item(d, vendas) for d in ok})
    vencs = sorted({d["vencedor"]["fornecedor"] for d in ok})
    curvas = [c for c in ["A*", "A", "B", "C+", "C"] if c in {(d.get("curva") or "").strip() for d in ok}]
    recs = sorted({(d.get("recomendacao") or "").strip() for d in ok if (d.get("recomendacao") or "").strip()})
    opt = lambda xs: "".join(f"<option value='{_esc(x)}'>{_esc(x)}</option>" for x in xs)
    filtros = f"""
<div class=filters>
 <label>Departamento<select id=f-grupo><option value=''>Todos</option>{opt(grupos)}</select></label>
 <label>Fornecedor vencedor<select id=f-venc><option value=''>Todos</option>{opt(vencs)}</select></label>
 <label>Curva<select id=f-curva><option value=''>Todas</option>{opt(curvas)}</select></label>
 <label>Recomendação<select id=f-rec><option value=''>Todas</option>{opt(recs)}</select></label>
 <div class=fdir>
  <div class=fd-i><span class=fl>economia</span><b id=fd-econ>R$ {_brl(economia_total,0)}</b></div>
  <div class=fd-i><span class=fl>itens</span><b id=fd-itens>{len(ok)}</b></div>
  <div class=fd-i><span class=fl>custo atual/sem</span><b id=fd-custo>R$ {_brl(custo_sem_total,0)}</b></div>
  <div class=fd-i><span class=fl>compra pós-cotação</span><b id=fd-pos>R$ {_brl(custo_pos_total,0)}</b></div>
 </div>
</div>"""

    rows = []
    for d in ok:
        v = d["vencedor"]
        grupo = _grupo_item(d, vendas)
        venda_sem = d.get("venda_sem")
        custo_sem = d.get("custo_sem")            # custo ATUAL (BI); None se BI sem custo
        custo_pos = d.get("custo_pos_sem") or 0   # pós-cotação (vencedor)
        economia_sem = d.get("economia_sem")      # atual − pós (com sinal); None se sem custo atual
        economia_pct = d.get("economia_pct") or 0

        # giro semanal (campo pronto, com fallback à base de vendas) — vira a coluna "Venda qtd/sem"
        gs = d.get("giro_sem")
        if gs:
            giro_n = round(gs)
        else:
            ven = vendas.get(d.get("cod")) if vendas else None
            giro_n = round(ven["qtd"] / _SEMANAS_60D) if (ven and ven.get("qtd")) else None
        # unidade física de venda do Gran (kg / un) para acompanhar a quantidade
        und = (d.get("und") or "").strip().lower()
        und_lbl = "kg" if und in ("kg", "quilo", "kilo") else "un"

        # células por fornecedor — fundo de grupo levemente destacado (grp-cell).
        # Vencedor: fundo verde suave (cell-win). Barrado: riscado/cinza (cell-ex).
        # SEM marcação vermelha de "acima do mercado" (removida a pedido do dono).
        cells = []
        for i, f in enumerate(fornecedores):
            sep = " sep" if i == 0 else ""
            r = d["candidatos"].get(f)
            if not r:
                cells.append(f"<td class='grp-cell muted{sep}'>—</td>")
                continue
            cls = ["grp-cell"]
            if f == v["fornecedor"]:
                cls.append("cell-win")
            if f in (d.get("barrados") or []):
                cls.append("cell-ex")
            cells.append(f"<td class='{(' '.join(cls)).strip()}{sep}'>{_brl(r['preco_norm'])}</td>")

        ceasa_v = _ceasa_cell(d)

        # Venda qtd/sem — quantidade física vendida na semana + unidade (ex "205 kg")
        qtd_html = (f"<span class=valnum>{giro_n} {und_lbl}</span>"
                    if giro_n else "<span class=muted>—</span>")

        # Venda R$/sem
        venda_html = (f"<span class=valnum>R$ {_brl(venda_sem,0)}</span>"
                      if venda_sem else "<span class=muted>—</span>")

        # Custo atual/sem = giro × custo ATUAL do BI (o que o Gran gasta hoje). None se BI sem custo.
        custo_html = (f"<span class=valnum>R$ {_brl(custo_sem,0)}</span>"
                      if custo_sem is not None else "<span class=muted>—</span>")

        # Custo pós-cotação = giro × preço do vencedor (projeção da compra no melhor preço).
        pos_html = f"<span class=valnum>R$ {_brl(custo_pos,0)}</span>"

        # Economia/sem = Custo atual − Custo pós (reconcilia com as 2 colunas acima).
        # >0 verde (economia real vs custo de hoje); =0/—; <0 vermelho (cotação ACIMA do custo atual).
        if economia_sem is None:
            econ_html = "<span class=muted>—</span>"
        elif economia_sem > 0:
            econ_html = (f"<span class='econ {_econ_faixa(economia_sem)}'>R$ {_brl(economia_sem,0)}"
                         f"<small>{_brl(economia_pct,1)}%</small></span>")
        elif economia_sem < 0:
            econ_html = (f"<span class='econ neg'>−R$ {_brl(abs(economia_sem),0)}"
                         f"<small>{_brl(economia_pct,1)}%</small></span>")
        else:
            econ_html = "<span class='econ zero'>—</span>"

        # Item: nome + etiqueta de curva (sem canal).
        # Recomendação: chip (só palavra) + ícone de feedback.
        # Por quê: SÓ o motivo extra (vazio quando a recomendação é puramente "preço barato").
        motivo = d.get("motivo_extra") or ""
        jus_html = (f"<span class=jus title='{_esc(motivo)}'>{_esc(motivo)}</span>"
                    if motivo else "<span class=muted>—</span>")
        rec_val = (d.get("recomendacao") or "").strip()

        rows.append(
            f"<tr data-grupo='{_esc(grupo)}' data-venc='{_esc(v['fornecedor'])}' "
            f"data-curva='{_esc((d.get('curva') or '').strip())}' "
            f"data-rec='{_esc(rec_val)}' "
            f"data-venda='{(venda_sem or 0):.2f}' data-custo='{(custo_sem or 0):.2f}' "
            f"data-pos='{custo_pos:.2f}' data-econ='{(economia_sem or 0):.2f}'>"
            f"<td class='l item'><span class=nome>{_esc(d['desc'])}</span> {_tags_item(d)}</td>"
            f"<td>{qtd_html}</td>"
            f"<td>{venda_html}</td>"
            f"<td>{custo_html}</td>"
            f"{''.join(cells)}"
            f"<td class='sep ceasa-cell'>{ceasa_v}</td>"
            f"<td class=sep>{_rec_chip(d)}{_fb_flag(d)}</td>"
            f"<td class='l porque'>{jus_html}</td>"
            f"<td>{pos_html}</td>"
            f"<td>{econ_html}</td></tr>")

    # totalizador APENAS no rodapé (sem linha-fantasma no topo).
    # Ordem: Dept | Item | VendaQtd | VendaR$ | Custo | [forn×N] | CEASA | Recomendação | Porquê | Economia.
    # Qtd física NÃO soma (mistura kg/un) — célula vazia. Total recalcula Venda R$, Custo e Economia.
    pos_cols = nforn + 3  # fornecedores + CEASA + Recomendação + Por quê (entre Custo atual e pós-cotação)
    tfoot = (f"<tfoot><tr><td class=l>"
             f"Total — <b id=tot-itens>{len(ok)}</b> itens visíveis</td>"
             f"<td class=muted>—</td>"
             f"<td><span class=valnum>R$ <b id=tot-venda>{_brl(venda_total,0)}</b></span></td>"
             f"<td><span class=valnum>R$ <b id=tot-custo>{_brl(custo_sem_total,0)}</b></span></td>"
             f"<td colspan={pos_cols}></td>"
             f"<td><span class=valnum>R$ <b id=tot-pos>{_brl(custo_pos_total,0)}</b></span></td>"
             f"<td><span class=econ>R$ <b id=tot-econ>{_brl(economia_total,0)}</b></span></td>"
             f"</tr></tfoot>")

    return f"""
<section class='tab-panel active' id=tab-matriz>
 <p class=section-kicker>01 · Matriz de Cotação</p>
 <h2 class=section-title>A decisão de fornecedor da semana — e o que ela rende</h2>
 <p class=section-desc>Da esquerda, a realidade do Gran: <b>departamento</b>, item, <b>quanto vende por semana</b> (em quantidade e em R$)
 e o <b>custo atual/sem</b> (giro × custo do BI). No meio, os preços de todos os fornecedores lado a lado
 (<b>fundo verde = melhor escolha</b>, riscado = barrado) e o <b>CEASA-BA</b> com a comparação <i>vs melhor</i> — sua munição de negociação.
 À direita, a decisão: <b>recomendação</b>, o <b>por quê</b>, o <b>custo pós-cotação</b> (giro × melhor preço) e a <b>economia</b>
 (custo atual − pós-cotação; vermelho = cotação acima do custo de hoje).
 As linhas vêm ordenadas por <b>curva ABC de venda</b> (A* no topo). O total no rodapé recalcula com o filtro.</p>
 {filtros}
 <div class=chart-box style="padding:14px 14px"><div class=tbl-scroll>
 <table class=data id=tabela-matriz><thead>{head}</thead><tbody>{''.join(rows)}</tbody>{tfoot}</table>
 </div></div>
</section>"""


# --------------------------------------------------------------------------- #
# 02 · Inteligência CEASA
# --------------------------------------------------------------------------- #
def _sparkline(serie, w=120, h=30, cor="var(--verde-3)"):
    """Mini gráfico de linha SVG a partir de [(data,preco)]."""
    vals = [v for _, v in serie]
    if len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1
    n = len(vals)
    pts = []
    for i, v in enumerate(vals):
        x = round(i / (n - 1) * (w - 4) + 2, 1)
        y = round(h - 3 - (v - lo) / rng * (h - 6), 1)
        pts.append(f"{x},{y}")
    poly = " ".join(pts)
    last_x, last_y = pts[-1].split(",")
    return (f"<span class=spk><svg width={w} height={h} viewBox='0 0 {w} {h}'>"
            f"<polyline fill=none stroke='{cor}' stroke-width=1.8 stroke-linejoin=round points='{poly}'/>"
            f"<circle cx={last_x} cy={last_y} r=2.6 fill='{cor}'/></svg></span>")


def _spk_row(prod, info):
    tend = info["tend_pct"]
    cor = "var(--vermelho)" if tend > 5 else ("var(--verde-3)" if tend < -5 else "var(--ink-mute)")
    pct_cls = "neg" if tend > 5 else ("pos" if tend < -5 else "muted")
    sinal = "+" if tend > 0 else ""
    sit = info.get("sit") or ""
    return (f"<div class=spk-row><div class=lbl>{_esc(prod.title())}"
            f"<span class=sub>{_esc(sit)}</span></div>"
            f"<div class=now>R$ {_brl(info['atual'])}<br><span class=muted style='font-size:10px'>por kg</span></div>"
            f"<div>{_sparkline(info['serie'], cor=cor)}</div>"
            f"<div class='pct {pct_cls}'>{sinal}{tend:.0f}%</div></div>")


def _confirmar_box(perguntar_ceasa):
    """Bloco no topo da aba CEASA listando itens cujo match precisa de confirmação do Hugo."""
    pc = perguntar_ceasa or []
    if not pc:
        return ""
    lis = []
    for it in pc:
        cand = it.get("candidato_ceasa")
        cand_html = f" <span class=cand>(parece: {_esc(cand)}?)</span>" if cand else ""
        lis.append(f"<li>{_esc(it.get('item') or it.get('cod'))}{cand_html}</li>")
    return f"""
<div class=confirmar-box>
 <h3>A confirmar ({len(pc)})</h3>
 <p class=desc>Itens sem correspondência automática confiável no boletim — confirme uma vez e a base aprende.</p>
 <ul>{''.join(lis)}</ul>
</div>"""


def _grafico_interativo_ceasa(ceasa_series):
    """Lista suspensa + gráfico de LINHA em SVG, redesenhado por JS ao trocar o item.
    Dados embutidos como JSON (offline, sem CDN). Só itens com série n>=4."""
    elig = {k: v for k, v in ceasa_series.items() if (v.get("n") or 0) >= 4}
    if not elig:
        return ""
    # ordena por n desc, depois nome — começa no de maior n
    ordem = sorted(elig.items(), key=lambda kv: (-(kv[1].get("n") or 0), kv[0]))

    # prioriza um item "âncora" relevante (TOMATE/BATATA) como inicial, se existir
    inicial = ordem[0][0]
    for nome, _v in ordem:
        if any(t in _norm(nome) for t in ("tomate", "batata")):
            inicial = nome
            break

    # JSON: para cada produto, série de pontos {d:'DD/MM', v:preco} + estatísticas
    dados = {}
    for nome, v in elig.items():
        pts = []
        for dt, preco in v["serie"]:
            if isinstance(dt, (date, datetime)):
                lbl = dt.strftime("%d/%m")
            else:
                s = str(dt)
                lbl = f"{s[8:10]}/{s[5:7]}" if len(s) >= 10 else s
            pts.append({"d": lbl, "v": round(float(preco), 2)})
        dados[nome] = {
            "pts": pts, "atual": v["atual"], "min": v["min"], "max": v["max"],
            "media": v.get("media"), "tend": v["tend_pct"], "sit": v.get("sit") or "", "n": v["n"],
        }

    opts = "".join(
        f"<option value='{_esc(nome)}'{' selected' if nome == inicial else ''}>"
        f"{_esc(nome.title())} ({v.get('n')} semanas)</option>"
        for nome, v in ordem
    )
    dados_json = json.dumps(dados, ensure_ascii=False)

    return f"""
<div class=chart-box><h3>Histórico de preço por produto — escolha e veja a evolução</h3>
 <p class=desc>Selecione um produto na lista para ver o preço de atacado (R$/kg) semana a semana no trimestre.
 A linha verde liga os pontos; cada ponto dourado é uma semana do boletim. Mínimo, máximo e preço de hoje ficam marcados.</p>
 <div class=gchart-head>
  <label>Produto<select id=g-sel>{opts}</select></label>
  <div class=gchart-stats>
   <div class=st>Hoje<b id=g-atual></b></div>
   <div class=st>Mín · Máx<b id=g-faixa></b></div>
   <div class=st>Tendência<b id=g-tend></b></div>
   <div class=st>Situação<b id=g-sit style='font-size:13px'></b></div>
  </div>
 </div>
 <svg id=g-svg class=gchart-svg viewBox='0 0 880 320' preserveAspectRatio='xMidYMid meet'></svg>
 <script id=g-dados type='application/json'>{dados_json}</script>
</div>"""


def _panel_ceasa(ok, ceasa_series, ceasa_datas, ceasa_atual, perguntar_ceasa=None):
    confirmar = _confirmar_box(perguntar_ceasa)
    grafico = _grafico_interativo_ceasa(ceasa_series)
    if not ceasa_series:
        return f"""
<section class=tab-panel id=tab-ceasa>
 <p class=section-kicker>02 · Inteligência CEASA</p><h2 class=section-title>Tendência do mercado de atacado</h2>
 {confirmar}
 <p class=section-desc>Sem dados do boletim CEASA-BA carregados nesta rodada.</p></section>"""

    itens = list(ceasa_series.values())
    n_alta = sum(1 for v in itens if v["dir"] == "alta")
    n_queda = sum(1 for v in itens if v["dir"] == "queda")
    n_estavel = sum(1 for v in itens if v["dir"] == "estável")
    n_sem = len(ceasa_datas)

    kpis = f"""
<div class=kpi-grid>
 <div class=kpi-card><p class=kpi-label>Itens acompanhados</p><p class=kpi-value>{len(itens)}</p>
  <p class=kpi-sub>produtos no boletim CEASA-BA</p></div>
 <div class=kpi-card><p class=kpi-label>Em alta</p><p class=kpi-value style='color:var(--vermelho)'>{n_alta}</p>
  <p class=kpi-sub>preço de atacado subindo no trimestre</p></div>
 <div class=kpi-card><p class=kpi-label>Em queda</p><p class=kpi-value>{n_queda}</p>
  <p class=kpi-sub>preço de atacado caindo no trimestre</p></div>
 <div class=kpi-card><p class=kpi-label>Estáveis</p><p class=kpi-value style='color:var(--ink-dim)'>{n_estavel}</p>
  <p class=kpi-sub>variação pequena</p></div>
 <div class=kpi-card><p class=kpi-label>Histórico</p><p class=kpi-value>{n_sem}</p>
  <p class=kpi-sub>semanas de boletim acumuladas</p></div>
</div>"""

    ranked = sorted(itens, key=lambda v: v["tend_pct"])
    altas = list(reversed(ranked))[:8]
    quedas = ranked[:8]
    # mapear de volta produto->info pra usar no _spk_row
    by_info = {id(v): k for k, v in ceasa_series.items()}
    altas_html = "".join(_spk_row(by_info[id(v)], v) for v in altas)
    quedas_html = "".join(_spk_row(by_info[id(v)], v) for v in quedas)

    # cesta do Gran: itens da demanda que casam com série CEASA
    cesta = []
    vistos = set()
    for d in ok:
        m = _ceasa_serie_para_item(d, ceasa_series)
        if m and m[0] not in vistos:
            vistos.add(m[0])
            cesta.append((d["desc"], m[0], m[1]))
    cesta.sort(key=lambda x: -abs(x[2]["tend_pct"]))
    if cesta:
        cesta_html = "".join(_spk_row(p, info) for _, p, info in cesta[:12])
    else:
        cesta_html = "<p class=muted>Nenhum item da sua compra casou com a série do CEASA nesta rodada.</p>"

    # distribuição de situação atual
    sit_count = {}
    for v in ceasa_atual.values():
        if len(str(v.get("produto", ""))) > 60:
            continue
        s = (v.get("sit") or "—").strip() or "—"
        sit_count[s] = sit_count.get(s, 0) + 1
    sit_count = sorted(sit_count.items(), key=lambda x: -x[1])
    sit_html = "".join(
        f"<div class=sit-cell><div class=v>{c}</div><div class=k>{_esc(s)}</div></div>"
        for s, c in sit_count if s != "—")

    return f"""
<section class=tab-panel id=tab-ceasa>
 <p class=section-kicker>02 · Inteligência CEASA</p>
 <h2 class=section-title>Para onde o mercado de atacado está indo</h2>
 <p class=section-desc>O CEASA-BA publica o preço de atacado de Salvador. Aqui acompanhamos cada produto ao longo de
 um trimestre (13 semanas) para você antecipar: o que está encarecendo na fonte tende a chegar nas tabelas dos
 fornecedores; o que está barateando abre espaço para negociar ou estocar. O mini-gráfico mostra a trajetória do preço por quilo.</p>
 {confirmar}
 {grafico}
 {kpis}
 <div class=two-col>
  <div class=chart-box><h3>Maiores altas do trimestre</h3>
   <p class=desc>Produtos que mais encareceram no atacado — atenção redobrada ao negociar.</p>{altas_html}</div>
  <div class=chart-box><h3>Maiores quedas do trimestre</h3>
   <p class=desc>Produtos que mais baratearam — bom momento para comprar mais ou pressionar preço.</p>{quedas_html}</div>
 </div>
 <div class=chart-box><h3>Foco na sua cesta — o que você compra está subindo ou caindo</h3>
  <p class=desc>Apenas os produtos da compra desta semana que aparecem no boletim CEASA, ordenados pela variação mais forte.</p>
  {cesta_html}</div>
 <div class=chart-box><h3>Como está o mercado agora</h3>
  <p class=desc>Quantos produtos o CEASA classifica como firme (vendendo bem, preço sustentado), estável ou fraco hoje.</p>
  <div class=sit-bars>{sit_html or '<p class=muted>—</p>'}</div></div>
</section>"""


# --------------------------------------------------------------------------- #
# 03 · Mercado & Decisão
# --------------------------------------------------------------------------- #
def _panel_mercado(ok, trocas, economia):
    # bloco 1: onde trocar de fornecedor
    trocas = sorted(trocas, key=lambda d: -(d.get("economia_vs_titular") or 0))
    if not trocas:
        body_troca = ("<p class=muted>Nenhuma troca sugerida nesta rodada — o fornecedor atual já é o mais barato "
                      "nos itens cotados.</p>")
    else:
        mx = max((d.get("economia_vs_titular") or 0) for d in trocas) or 1
        linhas = []
        for d in trocas:
            e = d.get("economia_vs_titular") or 0
            w = max(4, round(100 * e / mx))
            linhas.append(
                f"<div class=hbar-row><div class=lbl>{_esc(d['desc'])} "
                f"<span class=sub>{_esc(d.get('titular_forn') or '?')} → {_esc(d['vencedor']['fornecedor'])}</span></div>"
                f"<div class=track><div class='fill' style='width:{w}%'></div></div>"
                f"<div class=val>+R$ {_brl(e,0)}</div></div>")
        body_troca = "".join(linhas)

    # bloco 2: quem está acima do mercado
    casos = []
    for d in ok:
        med = d.get("mediana_mercado")
        if not med or d["n_fontes"] < 2:
            continue
        for f, r in d["candidatos"].items():
            if f in (d.get("barrados") or []):
                continue
            desv = (r["preco_norm"] / med - 1) * 100
            if desv > 15:
                casos.append((desv, d, f, r))
    casos.sort(key=lambda x: -x[0])
    if not casos:
        body_acima = "<p class=muted>Nenhum fornecedor mais de 15% acima da mediana nos itens com comparação.</p>"
    else:
        mx = max(c[0] for c in casos) or 1
        linhas = []
        for desv, d, f, r in casos[:25]:
            w = max(4, round(100 * desv / mx))
            linhas.append(
                f"<div class=hbar-row><div class=lbl>{_esc(d['desc'])} "
                f"<span class=sub>{_esc(f)} · R$ {_brl(r['preco_norm'])}</span></div>"
                f"<div class=track><div class='fill red' style='width:{w}%'></div></div>"
                f"<div class='val red'>+{desv:.0f}%</div></div>")
        body_acima = "".join(linhas)

    return f"""
<section class=tab-panel id=tab-mercado>
 <p class=section-kicker>03 · Mercado &amp; Decisão</p>
 <h2 class=section-title>Onde ganhar dinheiro nesta compra</h2>
 <p class=section-desc>Duas leituras práticas: onde vale trocar de fornecedor para economizar, e onde alguém está
 cobrando bem acima do mercado da semana (sinal para conferir ou negociar).</p>
 <div class=chart-box><h3>Onde trocar de fornecedor — total a economizar: R$ {_brl(economia,0)}</h3>
  <p class=desc>Itens em que outro fornecedor está mais barato que o atual. A barra é o tamanho da economia na quantidade desta semana.</p>
  {body_troca}</div>
 <div class=chart-box><h3>Quem está acima do mercado</h3>
  <p class=desc>Comparando cada fornecedor com a mediana da semana (só itens com 2 ou mais cotações). Acima de 15% acende alerta.</p>
  {body_acima}</div>
</section>"""


# --------------------------------------------------------------------------- #
# 04 · Vendas & Perdas
# --------------------------------------------------------------------------- #
def _hbar(label, valor, vmax, fmt="R$ {}", cls="", sub=""):
    w = max(3, round(100 * valor / (vmax or 1)))
    sub_html = f" <span class=sub>{_esc(sub)}</span>" if sub else ""
    return (f"<div class=hbar-row><div class=lbl>{_esc(label)}{sub_html}</div>"
            f"<div class=track><div class='fill {cls}' style='width:{w}%'></div></div>"
            f"<div class='val {'red' if cls=='red' else ''}'>{fmt.format(_brl(valor,0))}</div></div>")


def _panel_vendas(vendas):
    if not vendas:
        return """
<section class=tab-panel id=tab-vendas>
 <p class=section-kicker>04 · Vendas &amp; Perdas</p><h2 class=section-title>Como o Gran está vendendo</h2>
 <p class=section-desc>Sem base de vendas carregada nesta rodada.</p></section>"""

    # faturamento por grupo
    grp = {}
    for v in vendas.values():
        g = (v.get("grupo") or "—").split("/")[-1].strip() or "—"
        grp[g] = grp.get(g, 0) + (v.get("fat") or 0)
    grp = sorted(grp.items(), key=lambda x: -x[1])[:10]
    gmx = max((x[1] for x in grp), default=1)
    grp_html = "".join(_hbar(g, f, gmx) for g, f in grp)

    # top itens por faturamento
    top = sorted(vendas.values(), key=lambda v: -(v.get("fat") or 0))[:12]
    tmx = max((v.get("fat") or 0 for v in top), default=1)
    top_html = "".join(_hbar(v["desc"], v.get("fat") or 0, tmx) for v in top)

    # top perda (R$) — perda_valor é negativo
    perdas = [v for v in vendas.values() if (v.get("perda_valor") or 0) != 0]
    perdas.sort(key=lambda v: v.get("perda_valor") or 0)  # mais negativo primeiro
    perdas = perdas[:12]
    pmx = max((abs(v.get("perda_valor") or 0) for v in perdas), default=1)
    perda_html = "".join(
        _hbar(v["desc"], abs(v.get("perda_valor") or 0), pmx, cls="red",
              sub=f"{abs((v.get('perda_pct') or 0))*100:.0f}% do giro")
        for v in perdas) or "<p class=muted>Sem perdas registradas.</p>"

    return f"""
<section class=tab-panel id=tab-vendas>
 <p class=section-kicker>04 · Vendas &amp; Perdas</p>
 <h2 class=section-title>O que mais vende e onde está sobrando</h2>
 <p class=section-desc>Contexto dos últimos 60 dias do Gran para priorizar a compra: o que pesa no faturamento merece
 atenção na negociação; o que mais dá perda merece comprar com mais cuidado.</p>
 <div class=chart-box><h3>Faturamento por departamento · últimos 60 dias</h3>
  <p class=desc>Quanto cada categoria de FLV faturou no período.</p>{grp_html}</div>
 <div class=two-col>
  <div class=chart-box><h3>12 produtos que mais faturam · 60 dias</h3>
   <p class=desc>Os carros-chefe da loja — onde cada centavo de compra conta mais.</p>{top_html}</div>
  <div class=chart-box><h3>12 produtos com mais perda · 60 dias</h3>
   <p class=desc>Onde mais se joga dinheiro fora (em reais). Comprar bem aqui evita desperdício.</p>{perda_html}</div>
 </div>
</section>"""


# --------------------------------------------------------------------------- #
# 05 · Alertas
# --------------------------------------------------------------------------- #
def _panel_alertas(resultado, sem, revisao=None):
    dec = resultado["decisoes"]
    fora = [d for d in dec if "FORA_DA_BANDA" in d.get("alertas", [])]
    unica = [d for d in dec if d.get("status") == "ok" and d.get("fonte_unica")]
    barr = [d for d in dec if d.get("barrados")]
    revisao = revisao or []

    def lista(items):
        return ", ".join(_esc(d["desc"]) for d in items) or "—"

    barr_txt = ", ".join(
        f"{_esc(d['desc'])} ({', '.join(_esc(b) for b in d['barrados'])})" for d in barr) or "—"
    sem_txt = ", ".join(_esc(d["desc"]) for d in sem) or "—"

    # ---- Revisão crítica (preços fora da banda) ------------------------------
    TIPO_LABEL = {
        "VENCEDOR_VS_BI": "Vencedor > 2× custo BI",
        "VENCEDOR_VS_CEASA": "Vencedor > 1,5× CEASA-BA",
        "VENCEDOR_BAIXO_DEMAIS": "Vencedor < ½ custo BI (unidade trocada?)",
        "FORNECEDOR_OUTLIER": "Fornecedor > 2× mediana dos demais",
        "SALTO_VS_SEMANA": "Salto >30% vs semana anterior",
    }
    if revisao:
        por_tipo = {}
        for e in revisao:
            por_tipo.setdefault(e["tipo"], []).append(e)
        rev_html_blocks = []
        for tipo, eventos in por_tipo.items():
            label = TIPO_LABEL.get(tipo, tipo)
            sev_classe = "vermelho" if any(e["severidade"] == "alta" for e in eventos) else "amarelo"
            linhas = "".join(
                f"<tr><td><b>{_esc(e['desc'])}</b><br><span class=muted>COD {e['cod']}</span></td>"
                f"<td>{_esc(e['fornecedor'])}</td>"
                f"<td class=num>R$ {e['preco_kg']:.2f}/kg</td>"
                f"<td class=num>{e['razao']}×</td>"
                f"<td>{_esc(e['ref_label'])}<br><span class=num>R$ {e['ref']:.2f}/kg</span></td>"
                f"<td>R$ {e['r_em_jogo']:.2f}</td></tr>"
                for e in sorted(eventos, key=lambda x: -float(x.get('r_em_jogo') or 0))
            )
            rev_html_blocks.append(
                f"<div class='rev-block {sev_classe}'>"
                f"<div class=rev-head><span class=rev-pill>{len(eventos)}</span><b>{_esc(label)}</b></div>"
                f"<table class='data rev-table'><thead><tr>"
                f"<th>Item</th><th>Fornecedor</th><th class=num>Preço</th><th class=num>vs ref</th>"
                f"<th>Referência</th><th>R$ em jogo</th></tr></thead><tbody>{linhas}</tbody></table>"
                f"</div>"
            )
        rev_panel = (
            "<div class='rev-panel'>"
            f"<h3>Revisão crítica · {len(revisao)} item(ns) fora da banda</h3>"
            "<p class=section-desc>Pode ser realidade (fornecedor sistematicamente caro) ou erro de embalagem/parse. "
            "Bata o olho antes de fechar — o motor não bloqueia, só sinaliza.</p>"
            + "".join(rev_html_blocks)
            + "</div>"
        )
    else:
        rev_panel = ("<div class='rev-panel'><h3>Revisão crítica</h3>"
                     "<p class=section-desc>Nenhum preço fora da banda nesta rodada.</p></div>")

    rev_css = """<style>
.rev-panel{margin:18px 0 24px 0;padding:16px 18px;border:1px solid var(--linha);border-radius:10px;background:var(--bg-card,#fff);}
.rev-panel h3{margin:0 0 4px 0;font-size:16px;}
.rev-block{margin-top:14px;border-left:4px solid #d8a200;padding:10px 12px;background:#fff8e6;border-radius:6px;}
.rev-block.vermelho{border-left-color:#c0392b;background:#fdecea;}
.rev-head{display:flex;align-items:center;gap:8px;margin-bottom:6px;}
.rev-pill{background:#0f0f0f;color:#fff;border-radius:999px;padding:2px 9px;font-size:12px;font-weight:600;}
.rev-table{width:100%;font-size:13px;margin-top:6px;}
.rev-table td,.rev-table th{padding:6px 8px;border-bottom:1px solid #eee;text-align:left;vertical-align:top;}
.rev-table td.num,.rev-table th.num{font-family:'JetBrains Mono',monospace;text-align:right;}
</style>"""

    return f"""
<section class=tab-panel id=tab-alertas>
 <p class=section-kicker>05 · Alertas</p>
 <h2 class=section-title>O que conferir antes de fechar</h2>
 <p class=section-desc>Revisão crítica (preços anômalos) primeiro; depois os alertas operacionais.</p>
 {rev_css}
 {rev_panel}
 <div class='alert vermelho'><div class=acount>{len(fora)}</div>
  <div><b>Conferir preço (fora da banda do custo BI)</b><div class=alist>{lista(fora)}</div></div></div>
 <div class='alert amarelo'><div class=acount>{len(unica)}</div>
  <div><b>Só uma cotação</b><div class=alist>{lista(unica)}</div></div></div>
 <div class='alert amarelo'><div class=acount>{len(barr)}</div>
  <div><b>Fornecedor barrado por item</b><div class=alist>{barr_txt}</div></div></div>
 <div class='alert'><div class=acount>{len(sem)}</div>
  <div><b>Sem cotação esta semana</b><div class=alist>{sem_txt}</div></div></div>
</section>"""


# =========================================================================== #
# Pedido por Fornecedor — WhatsApp
# =========================================================================== #
def gerar_pedidos_whatsapp(resultado, semana):
    por_forn = {}
    for d in resultado["decisoes"]:
        if d["status"] != "ok":
            continue
        f = d["vencedor"]["fornecedor"]
        por_forn.setdefault(f, []).append(d)
    saidas = {}
    for f, itens in por_forn.items():
        itens.sort(key=_prioridade)
        canal = itens[0]["vencedor"]["canal"]
        emoji = "🚚" if canal == "entrega" else "🛒"
        linhas = [f"{emoji} *PEDIDO {f.upper()}* — {semana}", ""]
        for d in itens:
            linhas.append(f"• {d['desc']} — {_fmt_q(d['qtd'])} {d['und'] or ''}".strip())
        linhas += ["", f"Total de itens: {len(itens)}", "Confirmar separação e disponibilidade 🙏"]
        saidas[f] = "\n".join(linhas)
    return saidas
