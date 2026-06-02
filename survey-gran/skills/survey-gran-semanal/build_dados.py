"""
Build Dados · Survey Gran v12
==============================

Gera o JSON consolidado com todos os indicadores que o HTML precisa renderizar.
Consolida lógica das versões v6 → v10 num único arquivo.

Uso:
    python build_dados.py

Lê:
    ~/Documents/SurveyGran/base/base_classificada.pkl
    ~/Documents/SurveyGran/base/base_historica.pkl
    ~/Documents/SurveyGran/cadastros/export_base_arius.xlsx
    ~/Documents/SurveyGran/cadastros/kvi.xlsx

Salva:
    ~/Documents/SurveyGran/base/dados_survey.json
"""
import pandas as pd
import numpy as np
import json
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# =====================================================================
# Paths
# =====================================================================
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
BASE_DIR = ROOT / "base"
CADASTROS = ROOT / "cadastros"

BASE_HIST_FILE = BASE_DIR / "base_historica.pkl"
BASE_CLAS_FILE = BASE_DIR / "base_classificada.pkl"
ARIUS_FILE = CADASTROS / "export_base_arius.xlsx"
KVI_FILE = CADASTROS / "kvi.xlsx"
DADOS_JSON = BASE_DIR / "dados_survey.json"

# =====================================================================
# CONFIGURAÇÃO — atualizar manualmente
# =====================================================================

# Feriados 2024-2027 (ATUALIZAR ANUALMENTE — ver conhecimento/feriados_2025_2026.md)
FERIADOS_2024 = {
    '2024-09-07': 'Independência', '2024-10-12': 'Crianças',
    '2024-11-02': 'Finados', '2024-11-15': 'República',
    '2024-11-20': 'Consciência Negra', '2024-12-25': 'Natal',
}
FERIADOS_2025 = {
    '2025-01-01': 'Ano Novo',
    '2025-03-03': 'Carnaval (segunda)', '2025-03-04': 'Carnaval (terça)',
    '2025-03-05': 'Quarta de Cinzas',
    '2025-04-18': 'Sexta-Feira Santa', '2025-04-20': 'Domingo de Páscoa',
    '2025-04-21': 'Tiradentes',
    '2025-05-01': 'Dia do Trabalho', '2025-05-11': 'Dia das Mães',
    '2025-06-19': 'Corpus Christi',
    '2025-07-02': 'Independência da Bahia',
    '2025-09-07': 'Independência', '2025-10-12': 'Crianças',
    '2025-11-02': 'Finados', '2025-11-15': 'República',
    '2025-11-20': 'Consciência Negra', '2025-12-25': 'Natal',
}
FERIADOS_2026 = {
    '2026-01-01': 'Ano Novo',
    '2026-02-16': 'Carnaval (segunda)', '2026-02-17': 'Carnaval (terça)',
    '2026-02-18': 'Quarta de Cinzas',
    '2026-04-03': 'Sexta-Feira Santa', '2026-04-05': 'Domingo de Páscoa',
    '2026-04-21': 'Tiradentes',
    '2026-05-01': 'Dia do Trabalho', '2026-05-10': 'Dia das Mães',
    '2026-06-04': 'Corpus Christi',
    '2026-07-02': 'Independência da Bahia',
    '2026-09-07': 'Independência', '2026-10-12': 'Crianças',
    '2026-11-02': 'Finados', '2026-11-15': 'República',
    '2026-11-20': 'Consciência Negra', '2026-12-25': 'Natal',
}

# Cash & Carry EANs (atualizar quando promoção mudar)
CC_EANS = ['7896045506873','7891991297479','7892840800079','5602154382442',
           '5600233182006','7896074600993','7891025122067','7896030520648',
           '7898925773122','7898925773016','7895144603148','78910041',
           '7895800304211','78912359','7891000092606','7896423420326',
           '7891000065440','7891095911349','7896348300895','7898366001396']

DIAS_CC = ['Friday','Saturday','Sunday']

# Estratégia de ofertas por dia
OFERTAS_DIA = {
    'Monday':    {'nome_pt':'Segunda', 'alvo':'Mercearia → Funcionais',
                  'filtro_tipo':'subgrupo', 'filtro':'FUNCIONAIS', 'setor_mae':'MERCEARIA'},
    'Tuesday':   {'nome_pt':'Terça',   'alvo':'Hortifruti completo',
                  'filtro_tipo':'hortifruti', 'filtro':None, 'setor_mae':None},
    'Wednesday': {'nome_pt':'Quarta',  'alvo':'Carnes, Aves & Pescados',
                  'filtro_tipo':'setor', 'filtro':'CARNES, AVES & PESCADOS', 'setor_mae':None},
    'Thursday':  {'nome_pt':'Quinta',  'alvo':'Gran Mesa',
                  'filtro_tipo':'setor', 'filtro':'GRAN MESA', 'setor_mae':None},
}

# =====================================================================
# Helpers
# =====================================================================

def clean(x):
    s = str(x).strip()
    if s.endswith('.0'):
        s = s[:-2]
    return s


def detectar_semana_atual(base):
    """Detecta sem_id_global da última semana (quarta→terça) com dados completos."""
    hoje = pd.Timestamp.now().normalize()
    delta_para_terca = (hoje.weekday() - 1) % 7
    if delta_para_terca == 0:
        delta_para_terca = 7
    ultima_terca = hoje - pd.Timedelta(days=delta_para_terca)
    inicio_semana = ultima_terca - pd.Timedelta(days=6)

    sub = base[(base['Data'] >= inicio_semana) & (base['Data'] <= ultima_terca)]
    if len(sub) == 0:
        # Fallback: usar última semana com dados na base
        ultima_data = base['Data'].max()
        sem_id = int(base[base['Data'] == ultima_data]['sem_id_global'].iloc[0])
        sub = base[base['sem_id_global'] == sem_id]
        return sem_id, sub['Data'].min(), sub['Data'].max()
    sem_id = int(sub['sem_id_global'].iloc[0])
    return sem_id, inicio_semana, ultima_terca


def calc_sem_id_global(base):
    """Calcula sem_id_global = ((data - quarta inicial) / 7) + 1."""
    primeira = base['Data'].min()
    delta = (primeira.weekday() - 2) % 7  # 2 = quarta
    inicio = primeira - pd.Timedelta(days=delta)
    return ((base['Data'] - inicio).dt.days // 7 + 1).astype(int)


def get_sem_focal_no_ano(data, inicio_focal_ano):
    """Em qual sem 1-13 essa data cai relativo ao início focal do ano."""
    delta_d = (data - inicio_focal_ano).days
    if delta_d < 0:
        return None
    sem = (delta_d // 7) + 1
    return int(sem) if 1 <= sem <= 13 else None


def parse_brnum(x):
    if pd.isna(x):
        return None
    try:
        return float(str(x).replace(',', '.'))
    except Exception:
        return None


# =====================================================================
# MÓDULOS DE BUILD
# =====================================================================

def build_kpis_macro(v_atual, base, sem_atual_id, inicio_sem_atual, fim_sem_atual,
                    semanas_info, v_clas, sids_focais):
    """KPIs macro semana atual + YoY semanal + YoY mensal."""
    fat = float(v_atual['Valor'].sum())
    cupons = int(v_atual.groupby(['Pdv','Cupom','Data']).ngroups)
    qtd_dias = int(v_atual['Data'].nunique())
    media_dia = fat / qtd_dias if qtd_dias else 0
    ticket = fat / cupons if cupons else 0
    itens_nf = len(v_atual) / cupons if cupons else 0

    # SKUs ativos
    skus_ativos = int(v_atual[v_atual['cod_arius_str'].notna()]['cod_arius_str'].nunique())

    # Cobertura
    fat_total = v_atual['Valor'].sum()
    cobertura_fat = (v_atual[v_atual['metodo_match']!='N/A']['Valor'].sum() / fat_total * 100) if fat_total else 0

    # YoY semana
    sid_yoy = sem_atual_id - 52
    v_yoy = base[base['sem_id_global']==sid_yoy]
    fat_yoy = float(v_yoy['Valor'].sum()) if len(v_yoy) else 0
    yoy_pct = (fat / fat_yoy - 1) * 100 if fat_yoy > 0 else None
    periodo_yoy = (f"{v_yoy['Data'].min().strftime('%d/%m/%Y')}–"
                   f"{v_yoy['Data'].max().strftime('%d/%m/%Y')}") if len(v_yoy) else None

    # YoY mês (mesmo intervalo de dia, ano anterior)
    fim_dia = fim_sem_atual.day
    mes_atual = fim_sem_atual.month
    ano_atual = fim_sem_atual.year
    inicio_mes = pd.Timestamp(year=ano_atual, month=mes_atual, day=1)
    fat_mes = float(base[(base['Data']>=inicio_mes) & (base['Data']<=fim_sem_atual)]['Valor'].sum())
    inicio_mes_y = inicio_mes - pd.DateOffset(years=1)
    fim_mes_y = fim_sem_atual - pd.DateOffset(years=1)
    fat_mes_y = float(base[(base['Data']>=inicio_mes_y) & (base['Data']<=fim_mes_y)]['Valor'].sum())
    yoy_mes_pct = (fat_mes / fat_mes_y - 1) * 100 if fat_mes_y > 0 else None

    # ============= COMPARADORES LW/L4W/L8W (todos KPIs) =============
    # Calcular fat, cupons, dias, ticket, itens_nf, skus por semana
    sids_compare = [sem_atual_id - i for i in range(1, 9)]  # 8 sem anteriores
    sub_compare = v_clas[v_clas['sem_id_global'].isin(sids_compare)]

    def kpi_por_sem(sub):
        fat = float(sub['Valor'].sum())
        cup = int(sub.groupby(['Pdv','Cupom','Data']).ngroups) if len(sub) else 0
        dias = int(sub['Data'].nunique()) if len(sub) else 0
        skus = int(sub[sub['cod_arius_str'].notna()]['cod_arius_str'].nunique()) if len(sub) else 0
        return {
            'fat': fat,
            'cupons': cup,
            'dias': dias,
            'skus': skus,
            'media_dia': fat/dias if dias else 0,
            'ticket': fat/cup if cup else 0,
            'itens_nf': len(sub)/cup if cup else 0,
        }

    kpi_atual = {
        'fat': fat, 'cupons': cupons, 'media_dia': media_dia,
        'ticket': ticket, 'itens_nf': itens_nf, 'skus': skus_ativos,
    }
    kpi_por_sid = {sid: kpi_por_sem(v_clas[v_clas['sem_id_global']==sid]) for sid in sids_compare}

    def var_pct(atual, comp):
        if comp is None or comp == 0: return None
        return (atual/comp - 1) * 100

    def media_kpi(metric, k):
        sids = [sem_atual_id - i for i in range(1, k+1) if kpi_por_sid.get(sem_atual_id-i, {}).get(metric, 0) > 0]
        vals = [kpi_por_sid[s][metric] for s in sids]
        return float(np.mean(vals)) if vals else None

    # LW = sem_atual_id - 1
    lw = kpi_por_sid.get(sem_atual_id - 1, {})
    # L4W média, L8W média
    metrics_full = ['fat', 'cupons', 'media_dia', 'ticket', 'itens_nf', 'skus']

    # Calcular sem_label baseado na contagem Gran (quarta→terça): nº de terças do ano até fim_sem_atual.
    ano_atual_int = fim_sem_atual.year
    primeiro_dia = pd.Timestamp(year=ano_atual_int, month=1, day=1)
    delta_p = (1 - primeiro_dia.weekday()) % 7
    primeira_terca = primeiro_dia + pd.Timedelta(days=delta_p)
    n_semana_gran = ((fim_sem_atual - primeira_terca).days // 7) + 1
    sem_label = f"S{int(n_semana_gran):02d}/{ano_atual_int}"
    sem_label_short = f"S{int(n_semana_gran):02d}"
    sem_label_yoy = f"S{int(n_semana_gran):02d}/{ano_atual_int-1}"
    # Janela 13 semanas focais
    primeira_focal_n = max(1, int(n_semana_gran) - 12)
    sem_range_label = f"S{primeira_focal_n:02d}-S{int(n_semana_gran):02d}"

    out = {
        'sem_label': sem_label,
        'sem_label_short': sem_label_short,
        'sem_label_yoy': sem_label_yoy,
        'sem_range_label': sem_range_label,
        'sem_id_global': sem_atual_id,
        'sem_gran_no_ano': int(n_semana_gran),
        'ano': int(ano_atual_int),
        'periodo': f"{inicio_sem_atual.strftime('%d/%m')}–{fim_sem_atual.strftime('%d/%m')}/{fim_sem_atual.year}",
        'n_sem': 13,
        'fat_total': fat,
        'qtd_cupons': cupons,
        'qtd_dias': qtd_dias,
        'media_dia': media_dia,
        'ticket_medio': ticket,
        'itens_nf': itens_nf,
        'skus_ativos': skus_ativos,
        'cobertura_fat': cobertura_fat,
        'fat_yoy_pct': float(yoy_pct) if yoy_pct is not None else None,
        'fat_yoy_rs': fat - fat_yoy,
        'fat_yoy_periodo': periodo_yoy,
        'fat_yoy_valor': fat_yoy,
        'mes_yoy_pct': float(yoy_mes_pct) if yoy_mes_pct is not None else None,
        'mes_yoy_rs': fat_mes - fat_mes_y,
    }

    # Map de output keys → metric internas
    api_map = {'fat':'fat', 'cupons':'cupons', 'media_dia':'media_dia',
               'ticket':'ticket', 'itens_nf':'itens_nf', 'skus':'skus'}
    out_prefix = {'fat':'fat', 'cupons':'cupons', 'media_dia':'media_dia',
                  'ticket':'ticket', 'itens_nf':'itens_nf', 'skus':'skus'}

    for met in metrics_full:
        atual_v = kpi_atual[met]
        lw_v = lw.get(met, 0) if lw else None
        l4w_v = media_kpi(met, 4)
        l8w_v = media_kpi(met, 8)
        out[f'{out_prefix[met]}_lw']  = var_pct(atual_v, lw_v)
        out[f'{out_prefix[met]}_l4w'] = var_pct(atual_v, l4w_v)
        out[f'{out_prefix[met]}_l8w'] = var_pct(atual_v, l8w_v)

    return out


def build_setores(v_atual):
    """Tabela setores S atual: fat, share, ticket, presença, cupons."""
    fat_total = v_atual['Valor'].sum()
    out = []
    for setor in v_atual['setor'].unique():
        if setor == 'N/A':
            continue
        sub = v_atual[v_atual['setor']==setor]
        fat_s = float(sub['Valor'].sum())
        cup_s = int(sub['Cupom'].nunique())
        out.append({
            'setor': setor,
            'fat': fat_s,
            'share': fat_s / fat_total * 100 if fat_total else 0,
            'cupons': cup_s,
            'ticket_medio': fat_s / cup_s if cup_s else 0,
            'presenca_cupom': cup_s / v_atual['Cupom'].nunique() * 100 if v_atual['Cupom'].nunique() else 0,
        })
    out.sort(key=lambda x: x['fat'], reverse=True)
    return out


def build_setores_expand(v_clas, sem_atual_id, sids_focais, setores_atual):
    """Setores expandidos com LW, L4W, L8W, YoY S13 e YoY 13sem."""
    setor_sem = v_clas[v_clas['setor']!='N/A'].groupby(
        ['setor','sem_id_global'])['Valor'].sum().reset_index()
    pivot = setor_sem.pivot(index='setor', columns='sem_id_global', values='Valor').fillna(0)

    sid_yoy = sem_atual_id - 52
    sids_yoy_13 = [s-52 for s in sids_focais]
    set_share_map = {s['setor']: s for s in setores_atual}

    out = []
    for setor in pivot.index:
        if setor == 'N/A':
            continue
        if sem_atual_id not in pivot.columns:
            continue
        fat_atual = float(pivot.loc[setor, sem_atual_id])
        fat_lw = float(pivot.loc[setor, sem_atual_id-1]) if (sem_atual_id-1) in pivot.columns else None

        l4w_sids = [sem_atual_id-i for i in range(1,5) if (sem_atual_id-i) in pivot.columns]
        l8w_sids = [sem_atual_id-i for i in range(1,9) if (sem_atual_id-i) in pivot.columns]
        fat_l4w = float(np.mean([pivot.loc[setor, s] for s in l4w_sids])) if l4w_sids else None
        fat_l8w = float(np.mean([pivot.loc[setor, s] for s in l8w_sids])) if l8w_sids else None

        # YoY S13
        fat_y_s13 = float(v_clas[(v_clas['sem_id_global']==sid_yoy)&(v_clas['setor']==setor)]['Valor'].sum())
        var_yoy = (fat_atual/fat_y_s13 - 1)*100 if fat_y_s13 > 0 else None

        # YoY 13 sem
        fat_a_13 = float(v_clas[(v_clas['sem_id_global'].isin(sids_focais))&(v_clas['setor']==setor)]['Valor'].sum())
        fat_y_13 = float(v_clas[(v_clas['sem_id_global'].isin(sids_yoy_13))&(v_clas['setor']==setor)]['Valor'].sum())
        yoy_13 = (fat_a_13/fat_y_13 - 1)*100 if fat_y_13 > 0 else None

        share_info = set_share_map.get(setor, {})

        var_lw  = (fat_atual/fat_lw-1)*100 if fat_lw and fat_lw > 0 else None
        var_l4w = (fat_atual/fat_l4w-1)*100 if fat_l4w and fat_l4w > 0 else None
        var_l8w = (fat_atual/fat_l8w-1)*100 if fat_l8w and fat_l8w > 0 else None

        out.append({
            'setor': setor,
            'fat_atual': fat_atual,
            'fat_lw': fat_lw, 'fat_l4w_media': fat_l4w, 'fat_l8w_media': fat_l8w,
            'var_lw_pct':  float(var_lw)  if var_lw  is not None else None,
            'var_l4w_pct': float(var_l4w) if var_l4w is not None else None,
            'var_l8w_pct': float(var_l8w) if var_l8w is not None else None,
            'var_lw_rs':  fat_atual - fat_lw if fat_lw is not None else None,
            'var_l4w_rs': fat_atual - fat_l4w if fat_l4w is not None else None,
            'var_l8w_rs': fat_atual - fat_l8w if fat_l8w is not None else None,
            'fat_yoy': fat_y_s13,
            'var_yoy_pct': float(var_yoy) if var_yoy is not None else None,
            'var_yoy_rs': fat_atual - fat_y_s13 if fat_y_s13 else None,
            'fat_2026_13sem': fat_a_13,
            'fat_2025_13sem': fat_y_13,
            'yoy_13sem_pct': float(yoy_13) if yoy_13 is not None else None,
            'yoy_13sem_rs': fat_a_13 - fat_y_13 if fat_y_13 else None,
            'share': share_info.get('share'),
            'cupons': share_info.get('cupons'),
            'ticket_medio': share_info.get('ticket_medio'),
            'presenca_cupom': share_info.get('presenca_cupom'),
        })
    out.sort(key=lambda x: x['fat_atual'], reverse=True)
    return out


def build_evolucao_semanal(v13, sids_focais, sem_atual_id):
    """Série dos KPIs ao longo das 13 semanas."""
    out = []
    for i in range(1, 14):
        sub = v13[v13['sem_id']==i]
        if len(sub) == 0:
            continue
        fat = float(sub['Valor'].sum())
        cup = int(sub.groupby(['Pdv','Cupom','Data']).ngroups)
        dias = int(sub['Data'].nunique())
        out.append({
            'sem_id': i,
            'label': f'S{i:02d}',
            'fat': fat,
            'cupons': cup,
            'ticket_medio': fat/cup if cup else 0,
            'media_dia': fat/dias if dias else 0,
            'itens_nf': len(sub)/cup if cup else 0,
        })
    return out


def build_evolucao_yoy_kpis(base, sids_focais):
    """KPIs da série YoY posicional (sids_focais - 52)."""
    out = {'fat':[], 'cupons':[], 'ticket_medio':[], 'itens_nf':[], 'media_dia':[]}
    for sid in sids_focais:
        sid_y = sid - 52
        sub = base[base['sem_id_global']==sid_y]
        if len(sub) == 0:
            for k in out: out[k].append(None)
            continue
        fat = sub['Valor'].sum()
        cup = sub.groupby(['Pdv','Cupom','Data']).ngroups
        dias = sub['Data'].nunique()
        out['fat'].append(float(fat))
        out['cupons'].append(int(cup))
        out['ticket_medio'].append(float(fat/cup) if cup else 0)
        out['itens_nf'].append(float(len(sub)/cup) if cup else 0)
        out['media_dia'].append(float(fat/dias) if dias else 0)
    return out


def build_heatmaps(v_clas, sids_focais, sem_atual_id):
    """Heatmaps L4W e YoY por setor × semana focal."""
    sids_yoy_13 = [s-52 for s in sids_focais]

    fat_total_setor = v_clas[v_clas['sem_id_global'].isin(sids_focais)].groupby('setor')['Valor'].sum().sort_values(ascending=False)
    setores_ord = [s for s in fat_total_setor.index if s != 'N/A']

    setor_sem = v_clas[v_clas['setor']!='N/A'].groupby(['setor','sem_id_global'])['Valor'].sum().reset_index()
    pivot = setor_sem.pivot(index='setor', columns='sem_id_global', values='Valor').fillna(0)

    heatmap_l4w = []
    heatmap_yoy = []
    for setor in setores_ord:
        if setor not in pivot.index:
            continue
        row_l4w = {'setor': setor}
        row_yoy = {'setor': setor}
        for i, sid in enumerate(sids_focais):
            sn = i + 1
            fat_a = float(pivot.loc[setor, sid]) if sid in pivot.columns else 0
            # L4W: média das 4 semanas anteriores ao sid
            sids_4_prev = [sid - k for k in range(1,5) if (sid-k) in pivot.columns]
            fat_l4w = float(np.mean([pivot.loc[setor, s] for s in sids_4_prev])) if sids_4_prev else None
            row_l4w[f'sem_{sn}_l4w'] = float((fat_a/fat_l4w-1)*100) if fat_l4w and fat_l4w > 0 else None

            # YoY: mesmo sid menos 52
            sid_y = sid - 52
            fat_y = float(pivot.loc[setor, sid_y]) if sid_y in pivot.columns else 0
            row_yoy[f'sem_{sn}_yoy'] = float((fat_a/fat_y-1)*100) if fat_y > 0 else None
        heatmap_l4w.append(row_l4w)
        heatmap_yoy.append(row_yoy)
    return heatmap_l4w, heatmap_yoy


def build_yoy_por_sem(base, sids_focais):
    """YoY semana a semana posicional + total."""
    out = []
    for i, sid in enumerate(sids_focais):
        sid_y = sid - 52
        a = base[base['sem_id_global']==sid]
        y = base[base['sem_id_global']==sid_y]
        fat_a = float(a['Valor'].sum())
        fat_y = float(y['Valor'].sum())
        out.append({
            'sem_label': f'S{i+1:02d}',
            'sem_id_focal': i+1,
            'fat_2026': fat_a,
            'fat_2025': fat_y,
            'yoy_pct': float((fat_a/fat_y-1)*100) if fat_y > 0 else None,
            'yoy_rs': fat_a - fat_y,
            'periodo_2026': f"{a['Data'].min().strftime('%d/%m')}–{a['Data'].max().strftime('%d/%m')}/{a['Data'].max().year-2000:02d}" if len(a) else '',
            'periodo_2025': f"{y['Data'].min().strftime('%d/%m')}–{y['Data'].max().strftime('%d/%m')}/{y['Data'].max().year-2000:02d}" if len(y) else '',
        })
    fat_a_tot = sum(x['fat_2026'] for x in out)
    fat_y_tot = sum(x['fat_2025'] for x in out)
    return out, {
        'fat_2026': fat_a_tot,
        'fat_2025': fat_y_tot,
        'yoy_pct': (fat_a_tot/fat_y_tot - 1)*100 if fat_y_tot > 0 else None,
        'yoy_rs': fat_a_tot - fat_y_tot,
    }


def build_feriados_e_alinhamento(base, sids_focais, sem_atual_id, anos):
    """Mapeia feriados e gera estrutura de alinhamento por feriado móvel."""
    feriados_por_ano = {}
    if 2024 in anos: feriados_por_ano[2024] = FERIADOS_2024
    if 2025 in anos: feriados_por_ano[2025] = FERIADOS_2025
    if 2026 in anos: feriados_por_ano[2026] = FERIADOS_2026

    # Identificar ano "atual" (da S13 focal)
    sid_s13 = sids_focais[-1]
    ano_atual = base[base['sem_id_global']==sid_s13]['Data'].max().year
    ano_yoy = ano_atual - 1

    fer_atual = feriados_por_ano.get(ano_atual, {})
    fer_yoy = feriados_por_ano.get(ano_yoy, {})

    # S01 do ano focal (primeira semana das 13)
    sub_s01 = base[base['sem_id_global']==sids_focais[0]]
    inicio_focal_atual = sub_s01['Data'].min()
    sub_s01_yoy = base[base['sem_id_global']==sids_focais[0]-52]
    inicio_focal_yoy = sub_s01_yoy['Data'].min() if len(sub_s01_yoy) else None

    def get_sem_focal_no_ano(data_str, inicio_focal):
        if inicio_focal is None: return None
        d = pd.Timestamp(data_str)
        delta_d = (d - inicio_focal).days
        if delta_d < 0: return None
        sem = (delta_d // 7) + 1
        return int(sem) if 1 <= sem <= 13 else None

    # Mapear feriados em semanas focais
    fer_em_sem_atual = {}
    for data, nome in fer_atual.items():
        sem = get_sem_focal_no_ano(data, inicio_focal_atual)
        if sem is None: continue
        fer_em_sem_atual.setdefault(sem, []).append({
            'data': data, 'nome': nome,
            'dia_semana': pd.Timestamp(data).strftime('%a'),
            'data_br': pd.Timestamp(data).strftime('%d/%m'),
        })

    fer_em_sem_yoy = {}
    for data, nome in fer_yoy.items():
        sem = get_sem_focal_no_ano(data, inicio_focal_yoy)
        if sem is None: continue
        fer_em_sem_yoy.setdefault(sem, []).append({
            'data': data, 'nome': nome,
            'dia_semana': pd.Timestamp(data).strftime('%a'),
            'data_br': pd.Timestamp(data).strftime('%d/%m'),
        })

    # Calcular desalinhamento por semana focal
    desalinhamento = {}
    for sem in range(1, 14):
        f_a = fer_em_sem_atual.get(sem, [])
        f_y_pos = fer_em_sem_yoy.get(sem, [])

        sugestoes = []
        for f in f_a:
            for sem_y, lista_y in fer_em_sem_yoy.items():
                if any(fy['nome']==f['nome'] for fy in lista_y):
                    if sem_y != sem:
                        sugestoes.append({
                            'feriado': f['nome'],
                            'sem_2025_real': int(sem_y),
                            'data_2025': next(fy['data_br'] for fy in lista_y if fy['nome']==f['nome']),
                        })
                    break

        nomes_a = set(f['nome'] for f in f_a)
        nomes_y = set(f['nome'] for f in f_y_pos)
        so_em_atual = nomes_a - nomes_y
        so_em_yoy = nomes_y - nomes_a
        tem_problema = bool(so_em_atual or so_em_yoy) and (len(f_a) > 0 or len(f_y_pos) > 0)

        desalinhamento[str(sem)] = {
            'sem_focal': sem,
            'feriados_2026': f_a,
            'feriados_2025_mesma_sem': f_y_pos,
            'so_em_2026': list(so_em_atual),
            'so_em_2025': list(so_em_yoy),
            'tem_alerta': tem_problema,
            'sugestoes_alternativas': sugestoes,
        }
    return desalinhamento, fer_atual, fer_yoy


def build_yoy_opcoes(base, desalinhamento, sids_focais, sem_atual_id):
    """Para cada semana focal, opções de YoY (posicional + alinhada)."""
    yoy_opcoes = {}
    yoy_dados = []
    for i, sid in enumerate(sids_focais):
        sem_focal = i + 1
        sid_yoy_def = sid - 52
        opcoes = []
        sub_def = base[base['sem_id_global']==sid_yoy_def]
        if len(sub_def) > 0:
            opcoes.append({
                'tipo': 'posicional',
                'label': f'S{sem_focal:02d}/2025 (mesma posição)',
                'sem_id_global': int(sid_yoy_def),
                'sem_focal_2025': sem_focal,
                'periodo': f"{sub_def['Data'].min().strftime('%d/%m')}–{sub_def['Data'].max().strftime('%d/%m')}/{sub_def['Data'].max().year-2000:02d}",
                'fat': float(sub_def['Valor'].sum()),
            })

        info_des = desalinhamento.get(str(sem_focal), {})
        for sug in info_des.get('sugestoes_alternativas', []):
            sem_alt = sug['sem_2025_real']
            sid_alt = sids_focais[0] - 52 + (sem_alt - 1)
            sub_alt = base[base['sem_id_global']==sid_alt]
            if len(sub_alt) == 0: continue
            if any(o['sem_id_global']==int(sid_alt) for o in opcoes): continue
            opcoes.append({
                'tipo': 'feriado_aligned',
                'label': f'S{sem_alt:02d}/2025 (alinha {sug["feriado"]})',
                'sem_id_global': int(sid_alt),
                'sem_focal_2025': int(sem_alt),
                'periodo': f"{sub_alt['Data'].min().strftime('%d/%m')}–{sub_alt['Data'].max().strftime('%d/%m')}/{sub_alt['Data'].max().year-2000:02d}",
                'fat': float(sub_alt['Valor'].sum()),
            })

        # Pra S13 (semana atual): adicionar S+1/2025 se a S13/2025 tiver Páscoa
        if sem_focal == 13 and info_des.get('feriados_2025_mesma_sem'):
            sid_pos_pascoa = sid - 52 + 1
            sub = base[base['sem_id_global']==sid_pos_pascoa]
            if len(sub) > 0 and not any(o['sem_id_global']==int(sid_pos_pascoa) for o in opcoes):
                opcoes.append({
                    'tipo': 'pos_pascoa',
                    'label': f'S{sem_focal+1:02d}/2025 (sem feriado, pós-Páscoa)',
                    'sem_id_global': int(sid_pos_pascoa),
                    'sem_focal_2025': sem_focal+1,
                    'periodo': f"{sub['Data'].min().strftime('%d/%m')}–{sub['Data'].max().strftime('%d/%m')}/{sub['Data'].max().year-2000:02d}",
                    'fat': float(sub['Valor'].sum()),
                })

        yoy_opcoes[sem_focal] = {
            'sem_focal_2026': sem_focal,
            'opcoes': opcoes,
            'tem_alerta': info_des.get('tem_alerta', False),
            'feriados_2026': info_des.get('feriados_2026', []),
            'feriados_2025_mesma_sem': info_des.get('feriados_2025_mesma_sem', []),
        }

        sub_a = base[base['sem_id_global']==sid]
        yoy_dados.append({
            'sem_focal_2026': sem_focal,
            'sem_label': f'S{sem_focal:02d}',
            'fat_2026': float(sub_a['Valor'].sum()),
            'periodo_2026': f"{sub_a['Data'].min().strftime('%d/%m')}–{sub_a['Data'].max().strftime('%d/%m')}/{sub_a['Data'].max().year-2000:02d}" if len(sub_a) else '',
            'tem_alerta': info_des.get('tem_alerta', False),
            'feriados_2026': info_des.get('feriados_2026', []),
            'feriados_2025_posicional': info_des.get('feriados_2025_mesma_sem', []),
            'opcoes_2025': opcoes,
        })
    return yoy_opcoes, yoy_dados


def build_yoy_kpis_aligned(base, yoy_opcoes, sids_focais):
    """Série YoY usando alternativa quando há desalinhamento."""
    sids_aligned = []
    for i, sid in enumerate(sids_focais):
        sem_focal = i + 1
        info = yoy_opcoes.get(sem_focal, {})
        if info.get('tem_alerta') and len(info.get('opcoes', [])) >= 2:
            sids_aligned.append(info['opcoes'][1]['sem_id_global'])
        else:
            sids_aligned.append(sid - 52)

    out = {'fat':[], 'cupons':[], 'ticket_medio':[], 'itens_nf':[], 'media_dia':[]}
    for sid_y in sids_aligned:
        sub = base[base['sem_id_global']==sid_y]
        if len(sub) == 0:
            for k in out: out[k].append(None)
            continue
        fat = sub['Valor'].sum()
        cup = sub.groupby(['Pdv','Cupom','Data']).ngroups
        dias = sub['Data'].nunique()
        out['fat'].append(float(fat))
        out['cupons'].append(int(cup))
        out['ticket_medio'].append(float(fat/cup) if cup else 0)
        out['itens_nf'].append(float(len(sub)/cup) if cup else 0)
        out['media_dia'].append(float(fat/dias) if dias else 0)
    return out, sids_aligned


def build_evol_diaria_l4w(v, base, sem_atual, sem_atual_id, sids_aligned_por_sem):
    """Evolução diária da semana atual com baselines L4W e YoY (posicional + aligned)."""
    v_atual = v[v['sem_id']==sem_atual].copy()
    v_atual['dia_en'] = v_atual['Data'].dt.strftime('%A')

    v_l4w = v[(v['sem_id']>=sem_atual-4) & (v['sem_id']<sem_atual)].copy()
    v_l4w['dia_en'] = v_l4w['Data'].dt.strftime('%A')
    base_dia = v_l4w.groupby(['sem_id','dia_en'])['Valor'].sum().reset_index()
    base_media = base_dia.groupby('dia_en')['Valor'].mean().to_dict()

    # YoY posicional (sem_atual_id - 52)
    v_yoy_def = base[base['sem_id_global']==sem_atual_id-52].copy()
    v_yoy_def['dia_en'] = v_yoy_def['Data'].dt.strftime('%A')
    fat_yoy_def = v_yoy_def.groupby('dia_en')['Valor'].sum().to_dict()

    # YoY aligned: S13 alternativa
    sid_aligned_s13 = sids_aligned_por_sem[-1] if sids_aligned_por_sem else (sem_atual_id - 52)
    v_yoy_alt = base[base['sem_id_global']==sid_aligned_s13].copy()
    v_yoy_alt['dia_en'] = v_yoy_alt['Data'].dt.strftime('%A')
    fat_yoy_alt = v_yoy_alt.groupby('dia_en')['Valor'].sum().to_dict()

    atual_dia = v_atual.groupby(['Data','dia_en']).agg(
        fat=('Valor','sum'), cupons=('Cupom','nunique')
    ).reset_index().sort_values('Data')

    dias_pt = {'Monday':'Seg','Tuesday':'Ter','Wednesday':'Qua','Thursday':'Qui',
               'Friday':'Sex','Saturday':'Sáb','Sunday':'Dom'}
    out = []
    for _, r in atual_dia.iterrows():
        base_v = base_media.get(r['dia_en'])
        diff_l4w = (r['fat']/base_v-1)*100 if base_v and base_v > 0 else None
        fy_def = fat_yoy_def.get(r['dia_en'])
        fy_alt = fat_yoy_alt.get(r['dia_en'])
        out.append({
            'data_br': r['Data'].strftime('%d/%m'),
            'dia_label': f"{dias_pt.get(r['dia_en'],r['dia_en'])} {r['Data'].strftime('%d/%m')}",
            'fat': float(r['fat']),
            'baseline_l4w': float(base_v) if base_v else None,
            'lift_pct': float(diff_l4w) if diff_l4w is not None else None,
            'baseline_yoy': float(fy_def) if fy_def else None,
            'lift_yoy_pct': float((r['fat']/fy_def-1)*100) if fy_def and fy_def>0 else None,
            'baseline_yoy_aligned': float(fy_alt) if fy_alt else None,
            'lift_yoy_aligned_pct': float((r['fat']/fy_alt-1)*100) if fy_alt and fy_alt>0 else None,
        })
    return out


def build_setor_sparkline(v_clas, sids_focais, sids_aligned_por_sem, setores_expand, top_n=8):
    """Cards top N setores com série YoY% por semana (posicional + aligned)."""
    fat_total = v_clas[v_clas['sem_id_global'].isin(sids_focais)].groupby('setor')['Valor'].sum().sort_values(ascending=False)
    setores_ord = [s for s in fat_total.index if s != 'N/A'][:top_n]

    out = []
    for setor in setores_ord:
        serie_pos = []
        serie_aligned = []
        for sid_a, sid_y_aligned in zip(sids_focais, sids_aligned_por_sem):
            sid_y_pos = sid_a - 52
            fa = float(v_clas[(v_clas['sem_id_global']==sid_a)&(v_clas['setor']==setor)]['Valor'].sum())
            fy_pos = float(v_clas[(v_clas['sem_id_global']==sid_y_pos)&(v_clas['setor']==setor)]['Valor'].sum())
            fy_alig = float(v_clas[(v_clas['sem_id_global']==sid_y_aligned)&(v_clas['setor']==setor)]['Valor'].sum())
            serie_pos.append((fa/fy_pos-1)*100 if fy_pos > 0 else None)
            serie_aligned.append((fa/fy_alig-1)*100 if fy_alig > 0 else None)

        setor_data = next((s for s in setores_expand if s['setor']==setor), None)
        if not setor_data:
            continue
        out.append({
            'setor': setor,
            'fat_2026_13sem': setor_data.get('fat_2026_13sem', 0),
            'fat_2025_13sem': setor_data.get('fat_2025_13sem', 0),
            'yoy_13sem_pct': setor_data.get('yoy_13sem_pct'),
            'yoy_13sem_rs': setor_data.get('yoy_13sem_rs'),
            'yoy_serie': serie_pos,
            'yoy_serie_aligned': serie_aligned,
            'fat_atual_s13': setor_data.get('fat_atual'),
            'var_yoy_s13_pct': setor_data.get('var_yoy_pct'),
        })
    return out


def build_kvis(v, kvi_df, sem_atual):
    """Listas de KVI+ e KVI normais com métricas da semana atual."""
    kvi_df['cod_clean'] = kvi_df['COD'].apply(clean)
    kvi_lookup = kvi_df.set_index('cod_clean')

    v_atual = v[v['sem_id']==sem_atual]
    cupons_total = v_atual['Cupom'].nunique()

    kvi_plus = []
    kvi_norm = []
    for cod_str in v_atual[v_atual['cod_arius_str'].notna()]['cod_arius_str'].unique():
        if cod_str not in kvi_lookup.index:
            continue
        info = kvi_lookup.loc[cod_str]
        kvi_tipo = info.get('KVI', '-')
        if kvi_tipo not in ['KVI+', 'KVI']:
            continue

        sub = v_atual[v_atual['cod_arius_str']==cod_str]
        fat = float(sub['Valor'].sum())
        qtd = float(sub['Quantidade'].sum())
        cup = int(sub['Cupom'].nunique())
        item = {
            'cod': cod_str,
            'desc': sub.iloc[0]['desc_oficial'] if len(sub) else cod_str,
            'setor': sub.iloc[0]['setor'] if len(sub) else 'N/A',
            'CURVA': info.get('CURVA','-'),
            'fat': fat,
            'qtd': qtd,
            'cupons': cup,
            'preco_medio': fat/qtd if qtd > 0 else 0,
            'presenca': cup/cupons_total*100 if cupons_total else 0,
        }
        if kvi_tipo == 'KVI+':
            kvi_plus.append(item)
        else:
            kvi_norm.append(item)

    kvi_plus.sort(key=lambda x: x['fat'], reverse=True)
    kvi_norm.sort(key=lambda x: x['fat'], reverse=True)
    return kvi_plus, kvi_norm


def build_kvi_expand(v, kvi_plus, kvi_norm, sem_atual):
    """KVIs com comparadores LW/L4W/L8W."""
    fat_sku_sem = v[v['cod_arius_str'].notna()].groupby(['cod_arius_str','sem_id'])['Valor'].sum().reset_index()

    def calc_comp(cod):
        sub = fat_sku_sem[fat_sku_sem['cod_arius_str']==cod]
        s_map = dict(zip(sub['sem_id'], sub['Valor']))
        fat_atual = s_map.get(sem_atual, 0)
        fat_lw = s_map.get(sem_atual-1) if sem_atual-1 in s_map else None
        l4w = [s_map.get(sem_atual-i, 0) for i in range(1,5)]
        l8w = [s_map.get(sem_atual-i, 0) for i in range(1,9)]
        return {
            'cod':cod,
            'fat_atual': float(fat_atual),
            'var_lw_pct':  float((fat_atual/fat_lw-1)*100) if fat_lw and fat_lw>0 else None,
            'var_l4w_pct': float((fat_atual/np.mean(l4w)-1)*100) if np.mean(l4w)>0 else None,
            'var_l8w_pct': float((fat_atual/np.mean(l8w)-1)*100) if np.mean(l8w)>0 else None,
        }

    expand_plus = []
    for k in kvi_plus:
        c = calc_comp(k['cod'])
        c.update({k_: v_ for k_, v_ in k.items() if k_ != 'cod'})
        expand_plus.append(c)
    expand_plus.sort(key=lambda x: x['fat_atual'], reverse=True)

    expand_norm = []
    for k in kvi_norm:
        c = calc_comp(k['cod'])
        c.update({k_: v_ for k_, v_ in k.items() if k_ != 'cod'})
        expand_norm.append(c)
    expand_norm.sort(key=lambda x: x['fat_atual'], reverse=True)
    return expand_plus, expand_norm


def build_top30_loja(v, sem_atual, v_full=None, sem_global=None):
    """Top 30 SKUs da loja na semana atual com comparadores. v12.7: adiciona YoY fat e YoY qtd
    se v_full (base completa com sem_id_global) e sem_global passados."""
    v_atual = v[v['sem_id']==sem_atual]
    vn = v_atual[v_atual['cod_arius_str'].notna()]
    top_cods = vn.groupby('cod_arius_str')['Valor'].sum().sort_values(ascending=False).head(30).index.tolist()

    # v12.7: agregar fat E qtd por sem_id (intra-13sem) e por sem_id_global (para YoY se disponível)
    fat_sku_sem = v[v['cod_arius_str'].notna()].groupby(['cod_arius_str','sem_id']).agg(
        fat=('Valor','sum'), qtd=('Quantidade','sum')
    ).reset_index()
    fat_sku_global = None
    if v_full is not None and sem_global is not None:
        # filtrar apenas para os 30 cods de interesse para acelerar
        f = v_full[v_full['cod_arius_str'].isin(top_cods)]
        fat_sku_global = f.groupby(['cod_arius_str','sem_id_global']).agg(
            fat=('Valor','sum'), qtd=('Quantidade','sum')
        ).reset_index()

    sku_atual = vn.groupby(['cod_arius_str','desc_oficial','KVI','CURVA','setor']).agg(
        fat=('Valor','sum'), qtd=('Quantidade','sum'), cupons=('Cupom','nunique')
    ).reset_index()
    sku_atual['preco_medio'] = sku_atual['fat']/sku_atual['qtd']

    def calc_comp(cod):
        sub = fat_sku_sem[fat_sku_sem['cod_arius_str']==cod]
        s_fat = dict(zip(sub['sem_id'], sub['fat']))
        s_qtd = dict(zip(sub['sem_id'], sub['qtd']))
        fat_atual = s_fat.get(sem_atual, 0)
        qtd_atual = s_qtd.get(sem_atual, 0)
        fat_lw = s_fat.get(sem_atual-1)
        l4w = [s_fat.get(sem_atual-i, 0) for i in range(1,5)]
        l8w = [s_fat.get(sem_atual-i, 0) for i in range(1,9)]
        # v12.7: YoY (mesma semana ano anterior = sem_global-52)
        fat_yoy = qtd_yoy = 0
        if fat_sku_global is not None:
            sg = fat_sku_global[fat_sku_global['cod_arius_str']==cod]
            sgmap_fat = dict(zip(sg['sem_id_global'], sg['fat']))
            sgmap_qtd = dict(zip(sg['sem_id_global'], sg['qtd']))
            fat_yoy = sgmap_fat.get(sem_global-52, 0) or 0
            qtd_yoy = sgmap_qtd.get(sem_global-52, 0) or 0
        return {
            'var_lw_pct':  float((fat_atual/fat_lw-1)*100) if fat_lw and fat_lw>0 else None,
            'var_l4w_pct': float((fat_atual/np.mean(l4w)-1)*100) if np.mean(l4w)>0 else None,
            'var_l8w_pct': float((fat_atual/np.mean(l8w)-1)*100) if np.mean(l8w)>0 else None,
            'var_yoy_fat_pct': float((fat_atual/fat_yoy-1)*100) if fat_yoy>0 else None,
            'var_yoy_qtd_pct': float((qtd_atual/qtd_yoy-1)*100) if qtd_yoy>0 else None,
            'fat_yoy': float(fat_yoy),
            'qtd_yoy': float(qtd_yoy),
        }

    out = []
    for cod in top_cods:
        match = sku_atual[sku_atual['cod_arius_str']==cod]
        if len(match)==0: continue
        r = match.iloc[0]
        comp = calc_comp(cod)
        out.append({
            'cod': cod, 'desc': r['desc_oficial'], 'setor': r['setor'],
            'KVI': r['KVI'], 'CURVA': r['CURVA'],
            'fat': float(r['fat']), 'qtd': float(r['qtd']),
            'cupons': int(r['cupons']), 'preco_medio': float(r['preco_medio']),
            **comp,
        })
    return out


def build_serie_top30(v, top30_loja, v_full=None, sem_global=None):
    """Série temporal de fat/qtd/preço para Top 30 SKUs.
    v12.7: se v_full+sem_global passados, adiciona série YoY (mesma sem ano anterior)."""
    out = {}
    # Pré-agregar v_full por (cod, sem_id_global) — só os 30 cods de interesse
    yoy_lookup = None
    if v_full is not None and sem_global is not None:
        cods = [s['cod'] for s in top30_loja]
        f = v_full[v_full['cod_arius_str'].isin(cods)]
        agg = f.groupby(['cod_arius_str','sem_id_global']).agg(
            fat=('Valor','sum'), qtd=('Quantidade','sum')
        ).reset_index()
        yoy_lookup = {}
        for cod_v, grp in agg.groupby('cod_arius_str'):
            yoy_lookup[cod_v] = {
                int(r['sem_id_global']): {'fat': float(r['fat']), 'qtd': float(r['qtd'])}
                for _, r in grp.iterrows()
            }

    for s in top30_loja:
        cod = s['cod']
        sub = v[v['cod_arius_str']==cod]
        by_sem = sub.groupby('sem_id').agg(fat=('Valor','sum'), qtd=('Quantidade','sum')).reset_index()
        by_sem['preco_medio'] = by_sem['fat']/by_sem['qtd']
        series = {}
        for _, r in by_sem.iterrows():
            sid = int(r['sem_id'])
            series_entry = {
                'fat': float(r['fat']), 'qtd': float(r['qtd']),
                'preco_medio': float(r['preco_medio']),
            }
            # v12.7: YoY (mesma sem 2025 = sem_global - 52)
            if yoy_lookup and cod in yoy_lookup:
                # converte sem_id (1-13) para sem_global e subtrai 52
                sem_g_atual = sem_global - (13 - sid)
                yoy_data = yoy_lookup[cod].get(sem_g_atual - 52, {})
                series_entry['fat_yoy'] = yoy_data.get('fat', 0)
                series_entry['qtd_yoy'] = yoy_data.get('qtd', 0)
                yqtd = series_entry['qtd_yoy']
                yfat = series_entry['fat_yoy']
                series_entry['preco_medio_yoy'] = (yfat / yqtd) if yqtd else 0
            series[sid] = series_entry
        out[cod] = {
            'info': {'desc':s['desc'], 'setor':s['setor'], 'KVI':s.get('KVI','-'), 'CURVA':s.get('CURVA','-')},
            'series': series,
        }
    return out


def build_cash_carry(v, sem_atual, arius):
    """Métricas Cash & Carry (sex/sáb/dom) com lift L4W."""
    arius['ean_clean'] = arius['EAN'].apply(clean)
    ean_to_cod = {}
    for ean in CC_EANS:
        m = arius[arius['ean_clean']==ean]
        if len(m)>0:
            ean_to_cod[ean] = {'cod': clean(m.iloc[0]['Código']), 'desc': m.iloc[0]['Descrição']}

    v_atual = v[v['sem_id']==sem_atual].copy()
    v_atual['dia_en'] = v_atual['Data'].dt.strftime('%A')
    v_l4w = v[(v['sem_id']>=sem_atual-4)&(v['sem_id']<sem_atual)].copy()
    v_l4w['dia_en'] = v_l4w['Data'].dt.strftime('%A')

    itens = []
    total_promo = 0
    total_base = 0
    for ean, info in ean_to_cod.items():
        cod = info['cod']
        m_sem = v_atual[(v_atual['cod_arius_str']==cod) & (v_atual['dia_en'].isin(DIAS_CC))]
        fat_promo = float(m_sem['Valor'].sum())
        qtd_promo = float(m_sem['Quantidade'].sum())
        cup_promo = int(m_sem['Cupom'].nunique())
        cup_leve3 = int(m_sem.groupby('Cupom')['Quantidade'].sum().pipe(lambda s: (s>=3).sum()))
        m_l4w = v_l4w[(v_l4w['cod_arius_str']==cod) & (v_l4w['dia_en'].isin(DIAS_CC))]
        nw = m_l4w['sem_id'].nunique() if len(m_l4w)>0 else 0
        fat_base = float(m_l4w['Valor'].sum()/nw) if nw else 0
        qtd_base = float(m_l4w['Quantidade'].sum()/nw) if nw else 0
        incr = fat_promo - fat_base
        lift = (fat_promo/fat_base-1)*100 if fat_base > 0 else None
        pm = fat_promo/qtd_promo if qtd_promo > 0 else 0
        total_promo += fat_promo
        total_base += fat_base
        itens.append({
            'ean': ean, 'cod': cod, 'desc': info['desc'],
            'fat_promo': fat_promo, 'qtd_promo': qtd_promo,
            'cupons_promo': cup_promo, 'cupons_leve3': cup_leve3,
            'preco_medio': pm,
            'fat_baseline_l4w': fat_base, 'qtd_baseline_l4w': qtd_base,
            'fat_incremental': incr, 'lift_fat': lift,
            'n_weeks_base': nw,
        })
    itens.sort(key=lambda x: x['fat_incremental'] if x['fat_incremental'] is not None else -999999, reverse=True)
    resumo = {
        'total_promo': total_promo, 'total_baseline': total_base,
        'total_incremental': total_promo - total_base,
        'lift_total': (total_promo/total_base-1)*100 if total_base>0 else None,
        'n_itens': len(itens),
        'n_pegou': sum(1 for x in itens if x['lift_fat'] is not None and x['lift_fat']>=15),
        'n_nao_pegou': sum(1 for x in itens if x['lift_fat'] is not None and x['lift_fat']<0),
    }
    return itens, resumo


def build_ofertas_full(v, sem_atual):
    """Lift L4W e intra-semana das ofertas dia-temáticas."""
    v_atual = v[v['sem_id']==sem_atual].copy()
    v_atual['dia_en'] = v_atual['Data'].dt.strftime('%A')
    v_l4w = v[(v['sem_id']>=sem_atual-4)&(v['sem_id']<sem_atual)].copy()
    v_l4w['dia_en'] = v_l4w['Data'].dt.strftime('%A')

    out = []
    for dia_en, cfg in OFERTAS_DIA.items():
        if cfg['filtro_tipo']=='subgrupo':
            sa = v_atual[(v_atual['setor']==cfg['setor_mae']) & (v_atual['subgrupo']==cfg['filtro'])].copy()
            sl = v_l4w[(v_l4w['setor']==cfg['setor_mae']) & (v_l4w['subgrupo']==cfg['filtro'])].copy()
        elif cfg['filtro_tipo']=='setor':
            sa = v_atual[v_atual['setor']==cfg['filtro']].copy()
            sl = v_l4w[v_l4w['setor']==cfg['filtro']].copy()
        elif cfg['filtro_tipo']=='hortifruti':
            sa = v_atual[v_atual['setor'].str.startswith('HORTIFRUTI', na=False)].copy()
            sl = v_l4w[v_l4w['setor'].str.startswith('HORTIFRUTI', na=False)].copy()

        sa['dia_en'] = sa['Data'].dt.strftime('%A')
        sl['dia_en'] = sl['Data'].dt.strftime('%A')
        da = sa[sa['dia_en']==dia_en]
        od = sa[sa['dia_en']!=dia_en]
        md = sl[sl['dia_en']==dia_en]

        data_br = da['Data'].iloc[0].strftime('%d/%m') if len(da) else '—'
        fat_dia = float(da['Valor'].sum())
        cup_dia = int(da['Cupom'].nunique())
        do_n = od['Data'].nunique()
        fat_intra = float(od['Valor'].sum()/do_n) if do_n else 0
        lift_intra = (fat_dia/fat_intra-1)*100 if fat_intra > 0 else None
        nw = md['sem_id'].nunique() if len(md) else 0
        fat_l4w_b = float(md['Valor'].sum()/nw) if nw else 0
        lift_l4w = (fat_dia/fat_l4w_b-1)*100 if fat_l4w_b > 0 else None

        out.append({
            'dia_pt': cfg['nome_pt'], 'data_br': data_br, 'alvo': cfg['alvo'],
            'fat_dia': fat_dia, 'cupons_dia': cup_dia,
            'fat_base_intra': fat_intra, 'lift_intra': lift_intra,
            'fat_base_l4w': fat_l4w_b, 'lift_l4w': lift_l4w,
            'n_weeks_base': nw,
        })
    return out


def build_ruptura(v, sem_atual, kvi_df, arius_df=None, v_full=None):
    """Ruptura recorrente: KVI+ e KVI com venda em <4 das últimas 6 sem focais.
    Inclui departamento (ARIUS) e preço atual (último preço observado em KW = base, mais atualizado).
    `v_full` é a base classificada completa (pra puxar último preço além das 6 sem focais).
    """
    sids_recent = list(range(sem_atual-5, sem_atual+1))
    sub = v[(v['sem_id'].isin(sids_recent)) & (v['cod_arius_str'].notna())].copy()
    if sub.empty:
        return [], []
    sems_por_sku = sub.groupby('cod_arius_str')['sem_id'].nunique()
    skus_em_ruptura = sems_por_sku[sems_por_sku < 4].index.tolist()
    info = sub.drop_duplicates('cod_arius_str').set_index('cod_arius_str')
    kvi_df = kvi_df.copy()
    kvi_df['cod_clean'] = kvi_df['COD'].apply(clean)
    kvi_lookup = kvi_df.drop_duplicates('cod_clean').set_index('cod_clean')[['KVI','CURVA']]
    # Lookup departamento via ARIUS
    dept_lookup = {}
    if arius_df is not None:
        arius_df = arius_df.copy()
        arius_df['cod_clean'] = arius_df['Código'].apply(clean)
        for _, r in arius_df.drop_duplicates('cod_clean').iterrows():
            dept_lookup[r['cod_clean']] = str(r.get('DEPARTAMENTO', ''))

    # Preço atual: prioridade — último preço em KW (v_full toda a base) → últimas 6 sem como fallback
    preco_lookup = {}
    fonte_lookup = {}  # 'KW_recente' (na janela 6 sem) ou 'KW_historico' (mais antigo)
    if v_full is not None:
        v_pq = v_full[(v_full['cod_arius_str'].notna()) & (v_full['Quantidade'].fillna(0) > 0)]
        if not v_pq.empty:
            ultima_venda = v_pq.groupby('cod_arius_str')['Data'].max()
            v_idx = v_pq.merge(ultima_venda.rename('Data_max'), left_on='cod_arius_str', right_index=True)
            ultima = v_idx[v_idx['Data'] == v_idx['Data_max']]
            agg = ultima.groupby('cod_arius_str').agg(
                fat=('Valor', 'sum'), qtd=('Quantidade', 'sum')
            )
            agg['preco'] = (agg['fat'] / agg['qtd']).where(agg['qtd'] > 0, 0.0)
            for cod, p in agg['preco'].items():
                preco_lookup[cod] = float(p)
                fonte_lookup[cod] = 'KW_historico'
    # Sobrescrever com últimas 6 sem onde houver venda recente (mais relevante)
    if 'Quantidade' in sub.columns:
        agg_recent = sub.groupby('cod_arius_str').agg(fat=('Valor','sum'), qtd=('Quantidade','sum'))
        for cod, r in agg_recent.iterrows():
            if r['qtd'] > 0:
                preco_lookup[cod] = float(r['fat']/r['qtd'])
                fonte_lookup[cod] = 'KW_recente'

    rup_plus, rup_norm = [], []
    for cod_str in skus_em_ruptura:
        cod_clean_str = clean(cod_str)
        if cod_clean_str not in kvi_lookup.index:
            continue
        kvi_tipo = kvi_lookup.loc[cod_clean_str, 'KVI']
        if kvi_tipo not in ['KVI+','KVI']:
            continue
        setor = str(info.loc[cod_str, 'setor']) if cod_str in info.index else ''
        item = {
            'cod': str(cod_str),
            'desc': str(info.loc[cod_str, 'desc_oficial']) if cod_str in info.index else '',
            'setor': setor,
            'departamento': dept_lookup.get(cod_clean_str, setor),
            'CURVA': str(kvi_lookup.loc[cod_clean_str, 'CURVA']) if pd.notna(kvi_lookup.loc[cod_clean_str, 'CURVA']) else '-',
            'sem_venda_em': int(6 - sems_por_sku.loc[cod_str]),
            'sems_sem_venda': int(6 - sems_por_sku.loc[cod_str]),
            'preco_atual': preco_lookup.get(cod_str, 0.0),
            'preco_fonte': fonte_lookup.get(cod_str, 'sem_dado'),
        }
        if kvi_tipo == 'KVI+':
            rup_plus.append(item)
        else:
            rup_norm.append(item)
    return rup_plus, rup_norm


def build_elasticidade(v, sids_focais, kvi_df=None):
    """Elasticidade: corr preço×qtd entre semanas focais.
    Inclui campos: cod, desc, setor, kvi, corr, classificacao, preco_medio, preco_range_pct, qtd_total.
    """
    vn = v[(v['cod_arius_str'].notna()) & (v['sem_id_global'].isin(sids_focais))].copy()
    if vn.empty:
        return []
    agg = vn.groupby(['cod_arius_str', 'sem_id_global'], observed=True).agg(
        fat=('Valor', 'sum'),
        qtd=('Quantidade', 'sum'),
    ).reset_index()
    agg = agg[agg['qtd'] > 0].copy()
    agg['preco'] = agg['fat'] / agg['qtd']
    sem_count = agg.groupby('cod_arius_str').size()
    skus_validos = sem_count[sem_count >= 4].index
    agg = agg[agg['cod_arius_str'].isin(skus_validos)]
    if agg.empty:
        return []

    def _corr(g):
        if g['preco'].std() == 0 or g['qtd'].std() == 0:
            return None
        c = g['preco'].corr(g['qtd'])
        return None if pd.isna(c) else float(c)
    corrs = agg.groupby('cod_arius_str').apply(_corr, include_groups=False).dropna()

    desc_setor = vn.drop_duplicates('cod_arius_str').set_index('cod_arius_str')[['desc_oficial', 'setor']]
    qtd_total = agg.groupby('cod_arius_str')['qtd'].sum()
    fat_total = agg.groupby('cod_arius_str')['fat'].sum()
    preco_mm = agg.groupby('cod_arius_str')['preco'].agg(['min', 'max', 'mean'])

    # Lookup KVI (se kvi_df fornecido)
    kvi_lookup = {}
    if kvi_df is not None:
        kvi_df = kvi_df.copy()
        kvi_df['cod_clean'] = kvi_df['COD'].apply(clean)
        kvi_lookup = dict(zip(kvi_df['cod_clean'], kvi_df['KVI']))

    def classificar(c, preco_range_pct=None):
        # Convenção alinhada ao JS:
        #   'Alta elasticidade'   → corr fortemente negativa (preço↑ → qtd↓ MUITO)
        #   'Baixa elasticidade'  → corr próxima de 0 (preço quase não afeta volume)
        #   'Atípico (preço↑ → qtd↑)' → corr positiva (anomalia)
        #   'Sem variação de preço' → range pct < 1% (não dá pra medir)
        if preco_range_pct is not None and preco_range_pct < 1.0:
            return 'Sem variação de preço'
        if c <= -0.4: return 'Alta elasticidade'
        if c >= 0.3:  return 'Atípico (preço↑ → qtd↑)'
        return 'Baixa elasticidade'

    out = []
    for cod_str, corr in corrs.items():
        if cod_str not in desc_setor.index:
            continue
        cod_str_str = str(cod_str)
        cod_clean_str = clean(cod_str_str)
        preco_min = float(preco_mm.loc[cod_str, 'min'])
        preco_max = float(preco_mm.loc[cod_str, 'max'])
        preco_medio = float(preco_mm.loc[cod_str, 'mean'])
        # Preço médio ponderado por fat
        fat_t = float(fat_total.loc[cod_str])
        qtd_t = float(qtd_total.loc[cod_str])
        if qtd_t > 0:
            preco_medio = fat_t / qtd_t
        # Range em %: (max - min) / min × 100
        preco_range_pct = ((preco_max - preco_min) / preco_min * 100) if preco_min > 0 else 0.0
        kvi_val = kvi_lookup.get(cod_clean_str, '-')
        out.append({
            'cod': cod_str_str,
            'desc': str(desc_setor.loc[cod_str, 'desc_oficial']),
            'setor': str(desc_setor.loc[cod_str, 'setor']),
            'kvi': str(kvi_val) if pd.notna(kvi_val) else '-',
            'corr': float(corr),
            'corr_preco_qtd': float(corr),  # alias retrocompat
            'classificacao': classificar(corr, preco_range_pct),
            'preco_medio': preco_medio,
            'preco_min': preco_min,
            'preco_max': preco_max,
            'preco_range_pct': float(preco_range_pct),
            'qtd_total': qtd_t,
        })
    return out


def build_sazonalidade(base):
    """Sazonalidade mensal 2025 vs 2026."""
    mensal_2025 = base[base['Data'].dt.year==2025].groupby(base[base['Data'].dt.year==2025]['Data'].dt.month)['Valor'].sum().to_dict()
    mensal_2026 = base[base['Data'].dt.year==2026].groupby(base[base['Data'].dt.year==2026]['Data'].dt.month)['Valor'].sum().to_dict()
    nomes = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']
    out = []
    for i, nome in enumerate(nomes):
        f25 = mensal_2025.get(i+1)
        f26 = mensal_2026.get(i+1)
        out.append({
            'mes': nome, 'mes_num': i+1,
            'fat_2025': float(f25) if f25 else None,
            'fat_2026': float(f26) if f26 else None,
            'yoy_pct': float((f26/f25-1)*100) if f25 and f26 else None,
        })
    return out


def build_alertas(setores_expand, kpis_macro, ofertas, yoy_13sem, evol_diaria):
    """Alertas priorizados."""
    out = []
    if yoy_13sem and yoy_13sem.get('yoy_pct') is not None:
        p = yoy_13sem['yoy_pct']
        if p <= -5:
            out.append({'cor':'vermelho','icone':'✕',
                        'titulo':f'13 semanas focais caem {p:+.1f}% YoY',
                        'texto':f'Tendência consolidada de queda — 2026 acumulou R$ {yoy_13sem["fat_2026"]:,.0f} contra R$ {yoy_13sem["fat_2025"]:,.0f} em 2025.'.replace(',','X').replace('.',',').replace('X','.')})
        elif p >= 5:
            out.append({'cor':'verde','icone':'✓',
                        'titulo':f'13 semanas focais crescem {p:+.1f}% YoY',
                        'texto':f'2026: R$ {yoy_13sem["fat_2026"]:,.0f} vs 2025: R$ {yoy_13sem["fat_2025"]:,.0f}.'.replace(',','X').replace('.',',').replace('X','.')})

    for s in setores_expand[:8]:
        if s.get('yoy_13sem_pct') is not None:
            p = s['yoy_13sem_pct']
            if p <= -15:
                out.append({'cor':'vermelho','icone':'✕',
                            'titulo':f'{s["setor"]} cai {p:+.1f}% YoY (13 sem)',
                            'texto':f'2026: R$ {s["fat_2026_13sem"]:,.0f} vs 2025: R$ {s["fat_2025_13sem"]:,.0f}.'.replace(',','X').replace('.',',').replace('X','.')})
            elif p >= 15:
                out.append({'cor':'verde','icone':'✓',
                            'titulo':f'{s["setor"]} cresce {p:+.1f}% YoY (13 sem)',
                            'texto':f'2026: R$ {s["fat_2026_13sem"]:,.0f} vs 2025: R$ {s["fat_2025_13sem"]:,.0f}.'.replace(',','X').replace('.',',').replace('X','.')})

    if kpis_macro.get('fat_l4w') is not None and kpis_macro['fat_l4w'] < -10:
        out.append({'cor':'vermelho','icone':'✕',
                    'titulo':f'Semana atual cai {kpis_macro["fat_l4w"]:.1f}% vs L4W',
                    'texto':'Pior semana das últimas 4. Ver gráfico diário no headline.'})

    out.append({'cor':'verde','icone':'✓',
                'titulo':f'Base histórica atualizada',
                'texto':f'Cobertura {kpis_macro["cobertura_fat"]:.1f}%.'})

    for o in ofertas:
        if o['lift_l4w'] is not None and o['lift_intra'] is not None:
            if o['lift_l4w'] >= 15 and o['lift_intra'] >= 15:
                out.append({'cor':'verde','icone':'✓',
                            'titulo':f'Oferta {o["dia_pt"]} funcionou',
                            'texto':f'{o["alvo"]}: +{o["lift_l4w"]:.1f}% L4W e +{o["lift_intra"]:.1f}% intra.'})
            elif o['lift_l4w'] < 0 or o['lift_intra'] < 0:
                out.append({'cor':'amarelo','icone':'!',
                            'titulo':f'Oferta {o["dia_pt"]} não pegou',
                            'texto':f'{o["alvo"]}: L4W {o["lift_l4w"]:+.1f}%, intra {o["lift_intra"]:+.1f}%.'})

    return out


def build_aviso_na(v_atual):
    """Aviso de % do faturamento sem classificação ARIUS."""
    total = v_atual['Valor'].sum()
    fat_na = v_atual[v_atual['setor']=='N/A']['Valor'].sum()
    linhas_na = (v_atual['setor']=='N/A').sum()
    return {
        'fat_na': float(fat_na),
        'pct_na_fat': float(fat_na/total*100) if total else 0,
        'linhas_na': int(linhas_na),
    }


def build_faixas_ticket(v_atual):
    """Distribuição de cupons da semana atual em faixas de R$."""
    cup = v_atual.groupby(['Pdv','Cupom','Data'])['Valor'].sum().reset_index()
    faixas = [
        (0, 25, 'até R$ 25'),
        (25, 50, 'R$ 25–50'),
        (50, 100, 'R$ 50–100'),
        (100, 200, 'R$ 100–200'),
        (200, 500, 'R$ 200–500'),
        (500, float('inf'), '> R$ 500'),
    ]
    out = []
    for low, high, label in faixas:
        sel = cup[(cup['Valor'] >= low) & (cup['Valor'] < high)]
        out.append({
            'faixa': label,
            'qtd': int(len(sel)),
            'fat': float(sel['Valor'].sum()),
        })
    return out


def build_padrao_horario(v_atual):
    """Cupons e fat por hora do dia (semana atual). v12.7: inclui breakdown por DOW."""
    df = v_atual.copy()
    df['hora_int'] = df['Hora'].astype(str).str.slice(0, 2).astype(int, errors='ignore')
    try:
        df['hora_int'] = pd.to_numeric(df['Hora'].astype(str).str.slice(0, 2), errors='coerce').fillna(-1).astype(int)
    except Exception:
        pass
    df = df[(df['hora_int'] >= 0) & (df['hora_int'] <= 23)]
    # v12.7: dia da semana (0=segunda, 6=domingo no pandas)
    df['dow'] = pd.to_datetime(df['Data']).dt.dayofweek
    DOW_LBL = {0:'seg', 1:'ter', 2:'qua', 3:'qui', 4:'sex', 5:'sab', 6:'dom'}
    out = []
    for h in range(24):
        sub = df[df['hora_int'] == h]
        if len(sub) == 0:
            continue
        cup = sub.groupby(['Pdv','Cupom','Data']).ngroups
        fat = float(sub['Valor'].sum())
        if cup == 0 and fat == 0:
            continue
        # Breakdown por DOW
        by_dow = {}
        for dow_idx, dow_lbl in DOW_LBL.items():
            sd = sub[sub['dow'] == dow_idx]
            if len(sd) == 0:
                by_dow[dow_lbl] = {'cupons': 0, 'fat': 0.0}
            else:
                by_dow[dow_lbl] = {
                    'cupons': int(sd.groupby(['Pdv','Cupom','Data']).ngroups),
                    'fat': float(sd['Valor'].sum()),
                }
        out.append({
            'hora_int': int(h),
            'cupons': int(cup),
            'fat': fat,
            'by_dow': by_dow,  # v12.7: filtro dia da semana
        })
    return out


def build_sku_por_setor(v_atual, top_n=50, v_full=None, sem_atual=None):
    """Dict {setor: [skus top N por fat]} pra dropdown da aba SKUs.
    v12.7: se v_full e sem_atual passados, calcula comparadores LW/L4W/L8W/YoY igual ao top30 loja.
    """
    out = {}
    setores = v_atual[v_atual['setor'] != 'N/A']['setor'].unique()
    # Pré-calcular fat/qtd por (cod, sem_global) para todos os SKUs — só se v_full disponível
    # v12.7: aceita v_clas (que tem 'sem_id_global', não 'sem_id') do main
    fat_sku_sem = None
    sem_col = None
    if v_full is not None and sem_atual is not None:
        sem_col = 'sem_id_global' if 'sem_id_global' in v_full.columns else 'sem_id'
        fat_sku_sem = v_full[v_full['cod_arius_str'].notna()].groupby(
            ['cod_arius_str', sem_col]
        ).agg(fat=('Valor','sum'), qtd=('Quantidade','sum')).reset_index()
    for s in sorted(setores):
        sub = v_atual[v_atual['setor'] == s]
        agg = sub.groupby(['cod_arius_str', 'desc_oficial']).agg(
            fat=('Valor', 'sum'),
            qtd=('Quantidade', 'sum'),
            cupons=('Cupom', 'nunique'),
        ).reset_index()
        agg = agg.sort_values('fat', ascending=False).head(top_n)
        # Lookup KVI/CURVA do v_atual (primeira ocorrência)
        kvi_lookup = sub.drop_duplicates('cod_arius_str').set_index('cod_arius_str')[['KVI', 'CURVA']]
        skus = []
        for _, r in agg.iterrows():
            cod = r['cod_arius_str']
            kvi = kvi_lookup.loc[cod, 'KVI'] if cod in kvi_lookup.index else '-'
            curva = kvi_lookup.loc[cod, 'CURVA'] if cod in kvi_lookup.index else '-'
            preco_medio = float(r['fat']/r['qtd']) if r['qtd'] else 0
            d = {
                'cod': str(cod),
                'desc': str(r['desc_oficial']),
                'fat': float(r['fat']),
                'qtd': float(r['qtd']),
                'cupons': int(r['cupons']),
                'preco_medio': preco_medio,
                'KVI': str(kvi) if pd.notna(kvi) else '-',
                'CURVA': str(curva) if pd.notna(curva) else '-',
            }
            # v12.7: comparadores LW/L4W/L8W/YoY (mesma lógica do top30 loja)
            if fat_sku_sem is not None:
                sub_sem = fat_sku_sem[fat_sku_sem['cod_arius_str']==cod]
                s_fat = dict(zip(sub_sem[sem_col], sub_sem['fat']))
                s_qtd = dict(zip(sub_sem[sem_col], sub_sem['qtd']))
                fat_a = s_fat.get(sem_atual, 0); qtd_a = s_qtd.get(sem_atual, 0)
                fat_lw = s_fat.get(sem_atual-1)
                l4w = [s_fat.get(sem_atual-i, 0) for i in range(1,5)]
                l8w = [s_fat.get(sem_atual-i, 0) for i in range(1,9)]
                fat_yoy = s_fat.get(sem_atual-52, 0) or 0
                qtd_yoy = s_qtd.get(sem_atual-52, 0) or 0
                d.update({
                    'var_lw_pct':  float((fat_a/fat_lw-1)*100) if fat_lw and fat_lw>0 else None,
                    'var_l4w_pct': float((fat_a/np.mean(l4w)-1)*100) if np.mean(l4w)>0 else None,
                    'var_l8w_pct': float((fat_a/np.mean(l8w)-1)*100) if np.mean(l8w)>0 else None,
                    'var_yoy_fat_pct': float((fat_a/fat_yoy-1)*100) if fat_yoy>0 else None,
                    'var_yoy_qtd_pct': float((qtd_a/qtd_yoy-1)*100) if qtd_yoy>0 else None,
                    'fat_yoy': float(fat_yoy), 'qtd_yoy': float(qtd_yoy),
                })
            skus.append(d)
        out[str(s)] = skus
    return out


def build_nunca_venderam(v13_full, kvi_plus, kvi_norm, sids_focais):
    """KVI+ e KVI que NÃO venderam em NENHUMA das 13 semanas focais.

    kvi_plus/kvi_norm são as listas vindas de build_kvis (que filtram quem TEM venda).
    'Nunca venderam' = está cadastrado como KVI mas não aparece na base focal.
    """
    if v13_full is None or v13_full.empty:
        return [], []

    # Codigo de SKUs que VENDERAM no período focal
    venderam = set(v13_full[v13_full['cod_arius_str'].notna()]['cod_arius_str'].astype(str).unique())

    plus = []
    norm = []
    # kvi_plus/kvi_norm têm 'cod' string
    for item in (kvi_plus or []):
        if str(item.get('cod', '')) not in venderam:
            plus.append({**item, 'sem_venda_em': len(sids_focais)})
    for item in (kvi_norm or []):
        if str(item.get('cod', '')) not in venderam:
            norm.append({**item, 'sem_venda_em': len(sids_focais)})
    return plus, norm


# =====================================================================
# v0.12.8: Tornado Ganhadores/Perdedores no Headline (3 visões)
# =====================================================================
def build_skus_tornado(v_clas, sem_atual_id, top30_loja, sku_por_setor):
    """
    Constrói dataset por SKU para o painel Ganhadores e Perdedores no Headline.
    Universo (Opção A): união dos cods de top30_loja + sku_por_setor (todos setores).
    3 visões: YoY semana, YoY 13 sem acumuladas, L4W.
    Cada SKU traz fat e delta R$ pra cada visão (frontend ordena por delta R$ absoluto).
    """
    # Universo de cods (string)
    cods_univ = set()
    for s in (top30_loja or []):
        if s.get('cod'):
            cods_univ.add(str(s['cod']))
    if isinstance(sku_por_setor, dict):
        for setor_lista in sku_por_setor.values():
            for s in (setor_lista or []):
                if s.get('cod'):
                    cods_univ.add(str(s['cod']))
    cods_univ = list(cods_univ)
    if not cods_univ:
        return []

    # Lookup desc/setor a partir de top30_loja + sku_por_setor (consistente)
    meta = {}
    for s in (top30_loja or []):
        cod = str(s['cod'])
        meta[cod] = {'desc': s.get('desc',''), 'setor': s.get('setor','—')}
    if isinstance(sku_por_setor, dict):
        for setor_nome, lista in sku_por_setor.items():
            for s in (lista or []):
                cod = str(s['cod'])
                if cod not in meta:
                    meta[cod] = {'desc': s.get('desc',''), 'setor': setor_nome}

    # Pré-agrega fat por (cod, sem_id_global)
    sem_col = 'sem_id_global' if 'sem_id_global' in v_clas.columns else 'sem_id'
    f = v_clas[v_clas['cod_arius_str'].notna() & v_clas['cod_arius_str'].astype(str).isin(cods_univ)]
    fat_sku_sem = f.groupby(['cod_arius_str', sem_col])['Valor'].sum().reset_index().rename(columns={'Valor':'fat'})

    # Range das 13 semanas focais 2026 e 2025
    sids_13_2026 = list(range(sem_atual_id-12, sem_atual_id+1))
    sids_13_2025 = [s-52 for s in sids_13_2026]

    out = []
    for cod in cods_univ:
        sub = fat_sku_sem[fat_sku_sem['cod_arius_str'].astype(str) == cod]
        s_fat = dict(zip(sub[sem_col], sub['fat']))

        fat_atual = float(s_fat.get(sem_atual_id, 0) or 0)
        fat_yoy = float(s_fat.get(sem_atual_id-52, 0) or 0)
        # L4W: média das 4 semanas anteriores
        l4w_vals = [float(s_fat.get(sem_atual_id-i, 0) or 0) for i in range(1,5)]
        fat_l4w_media = sum(l4w_vals) / 4 if l4w_vals else 0.0

        # 13 sem 2026 e 2025
        fat_13sem_2026 = sum(float(s_fat.get(sid, 0) or 0) for sid in sids_13_2026)
        fat_13sem_2025 = sum(float(s_fat.get(sid, 0) or 0) for sid in sids_13_2025)

        # Filtro: pelo menos uma das 3 visões precisa ter referência > 0
        if fat_yoy <= 0 and fat_l4w_media <= 0 and fat_13sem_2025 <= 0 and fat_atual <= 0:
            continue

        m = meta.get(cod, {})
        out.append({
            'cod': cod,
            'desc': m.get('desc',''),
            'setor': m.get('setor','—'),
            # Visão SEMANA YoY
            'fat_atual': fat_atual,
            'fat_yoy_rs': fat_yoy,
            'delta_yoy_sem_rs': fat_atual - fat_yoy,
            'var_yoy_fat_pct': (fat_atual/fat_yoy - 1)*100 if fat_yoy > 0 else None,
            # Visão L4W
            'fat_l4w_media': fat_l4w_media,
            'delta_l4w_rs': fat_atual - fat_l4w_media,
            'var_l4w_pct': (fat_atual/fat_l4w_media - 1)*100 if fat_l4w_media > 0 else None,
            # Visão 13 SEM acumuladas
            'fat_13sem_2026': fat_13sem_2026,
            'fat_13sem_2025': fat_13sem_2025,
            'delta_yoy_13sem_rs': fat_13sem_2026 - fat_13sem_2025,
            'var_yoy_13sem_pct': (fat_13sem_2026/fat_13sem_2025 - 1)*100 if fat_13sem_2025 > 0 else None,
        })
    return out


# =====================================================================
# MAIN
# =====================================================================

def main():
    print("=" * 70)
    print("BUILD DADOS · Survey Gran v12")
    print("=" * 70)

    if not BASE_CLAS_FILE.exists():
        print(f"❌ Base classificada não encontrada: {BASE_CLAS_FILE}")
        print("   Rode pipeline_consolidacao.py primeiro.")
        return 1

    print(f"\nCarregando dados...")
    v_clas = pd.read_pickle(BASE_CLAS_FILE)
    v_clas['Data'] = pd.to_datetime(v_clas['Data'])
    base = pd.read_pickle(BASE_HIST_FILE)
    base['Data'] = pd.to_datetime(base['Data'])
    arius = pd.read_excel(ARIUS_FILE)
    kvi = pd.read_excel(KVI_FILE, sheet_name='PRECIFICAÇÃO', header=1)

    base['sem_id_global'] = calc_sem_id_global(base)
    v_clas['sem_id_global'] = calc_sem_id_global(v_clas)

    # Detectar semana atual
    sem_atual_id, inicio_sem_atual, fim_sem_atual = detectar_semana_atual(v_clas)
    print(f"  Semana atual: id global {sem_atual_id} ({inicio_sem_atual.date()} → {fim_sem_atual.date()})")

    # 13 semanas focais
    sids_focais = list(range(sem_atual_id-12, sem_atual_id+1))
    sids_yoy_pos = [s-52 for s in sids_focais]

    # Marcar sem_id focal (1-13)
    v_clas['sem_id_focal'] = v_clas['sem_id_global'].apply(
        lambda sid: sid - (sem_atual_id-13) if sid in sids_focais else None)
    v13 = v_clas[v_clas['sem_id_focal'].notna()].copy()
    v13['sem_id'] = v13['sem_id_focal'].astype(int)

    # =================== Construção dos módulos ===================
    print(f"\nConstruindo módulos do Survey...")

    # 1. Semanas info
    semanas_info = []
    for i in range(1, 14):
        sub = v13[v13['sem_id']==i]
        if len(sub) == 0: continue
        dmin, dmax = sub['Data'].min(), sub['Data'].max()
        semanas_info.append({
            'sem_id': i, 'label': f"S{i:02d}",
            'inicio': dmin.strftime('%d/%m'), 'fim': dmax.strftime('%d/%m'),
            'periodo': f"{dmin.strftime('%d/%m')}–{dmax.strftime('%d/%m')}",
        })
    print(f"  ✓ Semanas info ({len(semanas_info)} sem)")

    # 2. KPIs macro
    v_atual = v13[v13['sem_id']==13]
    kpis_macro = build_kpis_macro(v_atual, base, sem_atual_id, inicio_sem_atual, fim_sem_atual,
                                   semanas_info, v_clas, sids_focais)
    print(f"  ✓ KPIs macro: R$ {kpis_macro['fat_total']:,.2f}, {kpis_macro['qtd_cupons']:,} cupons, "
          f"YoY {kpis_macro['fat_yoy_pct']:+.1f}%" if kpis_macro['fat_yoy_pct'] is not None else f"  ✓ KPIs macro")

    # 3. Setores
    setores = build_setores(v_atual)
    setores_expand = build_setores_expand(v_clas, sem_atual_id, sids_focais, setores)
    print(f"  ✓ Setores ({len(setores_expand)} setores)")

    # 4. Heatmaps
    heatmap_l4w, heatmap_yoy = build_heatmaps(v_clas, sids_focais, sem_atual_id)
    print(f"  ✓ Heatmaps L4W e YoY")

    # 5. Evolução semanal
    evolucao_semanal = build_evolucao_semanal(v13, sids_focais, sem_atual_id)
    evolucao_yoy_kpis = build_evolucao_yoy_kpis(base, sids_focais)
    print(f"  ✓ Evolução semanal (13 sem)")

    # 6. Feriados e alinhamento
    anos_na_base = sorted(base['Data'].dt.year.unique().tolist())
    desalinhamento, fer_atual, fer_yoy = build_feriados_e_alinhamento(base, sids_focais, sem_atual_id, anos_na_base)
    yoy_opcoes_por_sem, yoy_dados_completo = build_yoy_opcoes(base, desalinhamento, sids_focais, sem_atual_id)
    n_alertas = sum(1 for s in desalinhamento.values() if s.get('tem_alerta'))
    print(f"  ✓ Feriados e alinhamento ({n_alertas}/13 sem com desalinhamento)")

    # 7. YoY KPIs aligned + sids aligned
    evolucao_yoy_kpis_aligned, sids_aligned_por_sem = build_yoy_kpis_aligned(base, yoy_opcoes_por_sem, sids_focais)
    print(f"  ✓ YoY aligned por feriado")

    # 8. YoY por semana (posicional)
    yoy_por_semana, yoy_13sem_total = build_yoy_por_sem(base, sids_focais)
    print(f"  ✓ YoY semana a semana (total 13sem: "
          f"{yoy_13sem_total['yoy_pct']:+.1f}%)" if yoy_13sem_total['yoy_pct'] is not None else f"  ✓ YoY semana a semana")

    # 9. Evol diária
    evol_diaria_l4w = build_evol_diaria_l4w(v13, base, 13, sem_atual_id, sids_aligned_por_sem)
    print(f"  ✓ Evolução diária ({len(evol_diaria_l4w)} dias)")

    # 10. Sparkline cards
    setor_yoy_sparkline = build_setor_sparkline(v_clas, sids_focais, sids_aligned_por_sem, setores_expand, top_n=8)
    print(f"  ✓ Sparkline cards (top 8)")

    # 11. KVIs
    kvi_plus, kvi_norm = build_kvis(v13, kvi, 13)
    kvi_plus_expand, kvi_norm_expand = build_kvi_expand(v13, kvi_plus, kvi_norm, 13)
    print(f"  ✓ KVIs ({len(kvi_plus)} KVI+ · {len(kvi_norm)} KVI)")

    # 12. Top 30 loja + série
    top30_loja = build_top30_loja(v13, 13, v_full=v_clas, sem_global=sem_atual_id)
    serie_top30 = build_serie_top30(v13, top30_loja, v_full=v_clas, sem_global=sem_atual_id)
    print(f"  ✓ Top 30 loja com série temporal")

    # 13. Cash & Carry
    cash_carry_itens, cash_carry_resumo = build_cash_carry(v13, 13, arius)
    print(f"  ✓ Cash & Carry ({len(cash_carry_itens)} itens)")

    # 14. Ofertas
    ofertas_full = build_ofertas_full(v13, 13)
    print(f"  ✓ Ofertas dia-temáticas ({len(ofertas_full)})")

    # 15. Ruptura recorrente (preço via KW = base completa; ARIUS só pra desc/dept)
    rup_plus, rup_norm = build_ruptura(v13, 13, kvi, arius, v_full=v_clas)
    print(f"  ✓ Ruptura recorrente ({len(rup_plus)} KVI+ · {len(rup_norm)} KVI)")

    # 15b. Nunca venderam (KVI+ e KVI cadastrados sem venda em nenhuma das 13 sem)
    # Estratégia: KW (base histórica) é mais atualizado que ARIUS — priorizar último
    # preço observado em qualquer ponto da base. Cair em ARIUS só pra desc/departamento.
    kvi_lookup_full = kvi.copy()
    kvi_lookup_full['cod_clean'] = kvi_lookup_full['COD'].apply(clean)
    arius_idx = arius.copy()
    arius_idx['cod_clean'] = arius_idx['Código'].apply(clean)
    arius_idx = arius_idx.drop_duplicates('cod_clean').set_index('cod_clean')

    skus_venderam = set(v13[v13['cod_arius_str'].notna()]['cod_arius_str'].astype(str).unique())

    # Pré-computar último preço observado por SKU em TODA a base classificada
    # (KW = source-of-truth de preço; mais recente que ARIUS)
    v_com_qtd = v_clas[(v_clas['cod_arius_str'].notna()) & (v_clas['Quantidade'].fillna(0) > 0)].copy()
    # Última data de venda por SKU
    ultima_venda = v_com_qtd.groupby('cod_arius_str')['Data'].max()
    # Para cada SKU, pegar registros da última data e calcular preço médio ponderado
    ultimo_preco_sku = {}
    if not v_com_qtd.empty:
        # Otimização: merge ultima_venda back e filtrar
        v_com_qtd_idx = v_com_qtd.merge(
            ultima_venda.rename('Data_max'),
            left_on='cod_arius_str', right_index=True
        )
        ultima = v_com_qtd_idx[v_com_qtd_idx['Data'] == v_com_qtd_idx['Data_max']]
        agg = ultima.groupby('cod_arius_str').agg(
            fat=('Valor', 'sum'),
            qtd=('Quantidade', 'sum'),
        )
        agg['preco'] = (agg['fat'] / agg['qtd']).where(agg['qtd'] > 0, 0.0)
        for cod, p in agg['preco'].items():
            ultimo_preco_sku[str(cod)] = (float(p), ultima_venda.loc[cod])

    def _build_nunca_item(cod_clean):
        # 1. Desc + departamento via ARIUS (estável)
        if cod_clean in arius_idx.index:
            r = arius_idx.loc[cod_clean]
            desc = str(r.get('Descrição', ''))
            dept = str(r.get('DEPARTAMENTO', ''))
        else:
            desc = ''
            dept = ''
        # 2. Preço atual via KW (último preço observado em qualquer ponto da base)
        preco = 0.0
        ultima_data = None
        if cod_clean in ultimo_preco_sku:
            preco, ultima_data = ultimo_preco_sku[cod_clean]
        return {
            'cod': cod_clean,
            'desc': desc,
            'departamento': dept,
            'preco_atual': preco,
            'preco_fonte_kw': preco > 0,
            'ultima_venda': ultima_data.strftime('%d/%m/%Y') if ultima_data is not None else None,
            'sem_venda_em': 13,
        }

    kvi_plus_cad = kvi_lookup_full[kvi_lookup_full['KVI']=='KVI+']['cod_clean'].astype(str).tolist()
    kvi_norm_cad = kvi_lookup_full[kvi_lookup_full['KVI']=='KVI']['cod_clean'].astype(str).tolist()
    nv_plus = [_build_nunca_item(c) for c in kvi_plus_cad if c not in skus_venderam]
    nv_norm = [_build_nunca_item(c) for c in kvi_norm_cad if c not in skus_venderam]
    n_com_preco = sum(1 for x in nv_plus + nv_norm if x['preco_atual'] > 0)
    print(f"  ✓ Nunca venderam ({len(nv_plus)} KVI+ · {len(nv_norm)} KVI · {n_com_preco} com preço KW)")

    # 15c. Faixas de ticket, padrão horário, SKUs por setor
    faixas_ticket = build_faixas_ticket(v_atual)
    padrao_horario = build_padrao_horario(v_atual)
    sku_por_setor = build_sku_por_setor(v_atual, v_full=v_clas, sem_atual=sem_atual_id)
    print(f"  ✓ Faixas ticket ({len(faixas_ticket)} faixas) · Padrão horário ({len(padrao_horario)}h) · SKUs/setor ({len(sku_por_setor)} setores)")

    # 15d. Tornado Ganhadores/Perdedores (Headline) — universo opção A: top30 + sku_por_setor
    skus_tornado = build_skus_tornado(v_clas, sem_atual_id, top30_loja, sku_por_setor)
    print(f"  ✓ Tornado Headline ({len(skus_tornado)} SKUs no universo)")

    # 16. Elasticidade
    elasticidade = build_elasticidade(v_clas, sids_focais, kvi)
    print(f"  ✓ Elasticidade ({len(elasticidade)} SKUs)")

    # 17. Sazonalidade
    sazonalidade = build_sazonalidade(base)
    print(f"  ✓ Sazonalidade mensal")

    # 18. Alertas
    alertas = build_alertas(setores_expand, kpis_macro, ofertas_full, yoy_13sem_total, evol_diaria_l4w)
    print(f"  ✓ Alertas ({len(alertas)})")

    # 19. Aviso N/A
    aviso_na = build_aviso_na(v_atual)
    print(f"  ✓ Aviso N/A ({aviso_na['pct_na_fat']:.1f}% do fat sem classificação)")

    # =================== Construir JSON final ===================
    D = {
        'kpis_macro': kpis_macro,
        'semanas_info': semanas_info,
        'setores': setores,
        'setores_expand': setores_expand,
        'heatmap_l4w': heatmap_l4w,
        'heatmap_yoy': heatmap_yoy,
        'evolucao_semanal': evolucao_semanal,
        'evolucao_yoy_kpis': evolucao_yoy_kpis,
        'evolucao_yoy_kpis_aligned': evolucao_yoy_kpis_aligned,
        'evol_diaria_l4w': evol_diaria_l4w,
        'desalinhamento_por_sem': desalinhamento,
        'yoy_opcoes_por_sem': yoy_opcoes_por_sem,
        'yoy_dados_completo': yoy_dados_completo,
        'yoy_por_semana': yoy_por_semana,
        'yoy_13sem_total': yoy_13sem_total,
        'feriados_2025': FERIADOS_2025,
        'feriados_2026': FERIADOS_2026,
        'setor_yoy_sparkline': setor_yoy_sparkline,
        'kvis_plus': kvi_plus,
        'kvis': kvi_norm,
        'kvi_plus_expand': kvi_plus_expand,
        'kvi_norm_expand': kvi_norm_expand,
        'top30_loja': top30_loja,
        'skus_tornado': skus_tornado,
        'serie_top30': serie_top30,
        'cash_carry_itens': cash_carry_itens,
        'cash_carry_resumo': cash_carry_resumo,
        'ofertas_full': ofertas_full,
        'ruptura_recorrente_kvi_plus': rup_plus,
        'ruptura_recorrente_kvi': rup_norm,
        'nunca_venderam_kvi_plus': nv_plus,
        'nunca_venderam_kvi': nv_norm,
        'faixas_ticket': faixas_ticket,
        'padrao_horario': padrao_horario,
        'sku_por_setor': sku_por_setor,
        'excecoes': [],  # placeholder pra futuras exceções operacionais
        'elasticidade': elasticidade,
        'sazonalidade': sazonalidade,
        'alertas_v2': alertas,
        'aviso_na': aviso_na,
    }

    DADOS_JSON.write_text(json.dumps(D, default=str, ensure_ascii=False), encoding='utf-8')
    print(f"\n✓ {DADOS_JSON.name} salvo ({DADOS_JSON.stat().st_size/1024:.1f} KB)")
    print(f"\n{'=' * 70}")
    print("Build concluído. Próximo passo: python gerar_html_survey.py")
    print(f"{'=' * 70}\n")
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
