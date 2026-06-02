"""
Build Dados · Survey Gran Mesa v2
==================================

Reconstrução profunda inspirada no Survey global. Gera dados ricos para 7 abas:
  01 Headline (KPIs + chart-diario + tornado dual + tabela YoY)
  02 Panorama 13 sem (chart-evolucao + chart-horario + chart-faixas + tabela YoY 13sem)
  03 Subgrupos (hbars + tornado dual + cards com sparkline + heatmap + tabela)
  04 Raio-X SKU + Cesta Cross-sell (top 30 + linha tempo + companheiros por SKU)
  05 Margem × Volume (quadrantes + drill subgrupo)
  06 Ruptura + Subprodução (tabela ruptura + esgotamento + curva intra-dia)
  07 Lançamentos + Carteiras (90d + cards colaborador com sparkline)

Lê: base_classificada.pkl + gran_margens.xlsx + parametros.json + Mapa e Producao.xlsx + omie_gmpro.xlsx
Salva: data/gran-mesa/dados_gran_mesa.json

Uso:
    python build_dados.py [--data-ref YYYY-MM-DD]
"""
import argparse
import json
import os
import sys
import warnings
from collections import defaultdict
from datetime import datetime, timedelta, date
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')

# ─────────────────────────────────────────────────────────────────────
# CHECAGEM DE COMPATIBILIDADE
# ─────────────────────────────────────────────────────────────────────
def checar_versao_pandas():
    """
    base_classificada.pkl é gerado pelo survey-gran com pandas 3.0+ (StringDtype com na_value=nan).
    Versões anteriores não conseguem desserializar. Avisa cedo se a versão for incompatível.
    """
    versao = pd.__version__
    major = int(versao.split('.')[0])
    if major < 3:
        msg = f"⚠️  pandas {versao} pode não conseguir ler base_classificada.pkl (precisa 3.0+).\n"
        msg += "   Se ocorrer NotImplementedError ao ler o pickle, atualize:\n"
        msg += "       pip install --upgrade 'pandas>=3.0'\n"
        msg += "   Ou crie virtualenv com Python 3.11+:\n"
        msg += "       python3.11 -m venv ~/venv-survey && ~/venv-survey/bin/pip install 'pandas>=3.0' numpy openpyxl"
        print(msg)
        return False
    return True


# ─────────────────────────────────────────────────────────────────────
# CONSTANTES DE NEGÓCIO (calibradas) — exportadas pra fácil tuning
# ─────────────────────────────────────────────────────────────────────
SELO_VERDE_SHARE_MIN = 0.5      # % do fat Gran Mesa para selo verde
SELO_VERDE_CUPONS_MIN = 10      # cupons atual mínimos para selo verde (alternativa ao share)
RUPTURA_SEMANAS_MIN = 4         # SKU vendeu em <X de 6 sem = ruptura recorrente
SUBPRODUCAO_PCT_MIN = 30        # % dias com último cupom <17h para sinalizar subprodução
SUBPRODUCAO_HORA_LIMITE = 17    # esgotou antes desta hora = precoce
LANCAMENTO_DIAS_MAX = 90        # SKU lançado nos últimos N dias
ALERTA_QUEDA_L4W_MIN = -15      # queda L4W severa para virar alerta
ALERTA_QUEDA_YOY_EXTREMA = -50  # queda YoY extrema para alerta independente do L4W
ALERTAS_TOP_N = 5               # máximo de alertas na Aba 01
TORNADO_TOP_N = 12              # SKUs no tornado (cada lado)
TOP_30_LIMIT = 30               # tabela top-N
TENDENCIA_QUEDA_L4W = -20       # queda L4W para entrar em tendência
TENDENCIA_QUEDA_YOY = -25       # ou queda YoY
SUBPRODUCAO_FATOR_PERDA = 0.5   # fator multiplicador para estimar potencial perdido
RUPTURA_FATOR_IMPACTO = 0.30    # fator de impacto de ruptura no alerta
SUBPRODUCAO_FATOR_IMPACTO = 0.20
CESTA_MIN_CUPONS_SKU = 5        # SKU Mesa precisa ter ≥X cupons para entrar na cesta
CESTA_MIN_CUPONS_COMPANHEIRO = 3  # companheiro precisa de ≥X cupons compartilhados
CESTA_TOP_COMPANHEIROS = 10
SCORE_PESO_FAT = 0.60           # Score: peso do faturamento absoluto
SCORE_PESO_MARGEM_RS = 0.25     # Score: peso da margem R$ absoluta
SCORE_PESO_MARGEM_PCT = 0.10    # Score: peso da margem %
SCORE_PESO_SAUDE = 0.05         # Score: peso de saúde da carteira

# ─────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────
PADARIA_GRAN_CODES = {'1','589','590','591','592','593','594','595','602','616','759','763','6424','6584'}

FERIADOS_2025 = {
    '2025-01-01': ('Confraternização', True),
    '2025-03-03': ('Carnaval segunda', True),
    '2025-03-04': ('Carnaval terça', True),
    '2025-03-05': ('Quarta de Cinzas', True),
    '2025-04-18': ('Sexta-Feira Santa', True),
    '2025-04-21': ('Tiradentes', True),
    '2025-05-01': ('Dia do Trabalho', True),
    '2025-06-19': ('Corpus Christi', True),
    '2025-07-02': ('Independência BA', True),
    '2025-09-07': ('Independência', True),
    '2025-10-12': ('N. Sra. Aparecida', True),
    '2025-11-02': ('Finados', True),
    '2025-11-15': ('República', True),
    '2025-11-20': ('Consciência Negra', True),
    '2025-12-25': ('Natal', True),
}
FERIADOS_2026 = {
    '2026-01-01': ('Confraternização', True),
    '2026-02-16': ('Carnaval segunda', True),
    '2026-02-17': ('Carnaval terça', True),
    '2026-02-18': ('Quarta de Cinzas', True),
    '2026-04-03': ('Sexta-Feira Santa', True),
    '2026-04-21': ('Tiradentes', True),
    '2026-05-01': ('Dia do Trabalho', True),
    '2026-06-04': ('Corpus Christi', True),
    '2026-07-02': ('Independência BA', True),
    '2026-09-07': ('Independência', True),
    '2026-10-12': ('N. Sra. Aparecida', True),
    '2026-11-02': ('Finados', True),
    '2026-11-15': ('República', True),
    '2026-11-20': ('Consciência Negra', True),
    '2026-12-25': ('Natal', True),
}

# Mapeamento ARIUS subgrupo → nome amigável
NOMES_SUBGRUPO_MAP = {
    'REFEICOES': 'Refeições',
    'FRUTAS HIGIENIZADAS': 'Frutas Higienizadas',
    'SUCOS': 'Sucos',
    'HORTALICAS & LEGUMES': 'Hortaliças & Legumes',
    'MOLHOS & CALDOS': 'Molhos & Caldos',
    'SOBREMESA': 'Sobremesas',
    'P O DIVERSOS': 'Padaria Gran',
    'PAES FATIADOS': 'Pães Fatiados',
    'GRAOS & OLEAGINOSAS': 'Granel · Grãos',
    'FRUTAS SECAS': 'Granel · Frutas Secas',
    'TEMPEROS & ERVAS': 'Granel · Temperos',
    'FARINACEOS': 'Granel · Farináceos',
    'PETISCOS': 'Granel · Petiscos',
}

DIAS_PT_SHORT = ['SEG','TER','QUA','QUI','SEX','SAB','DOM']
DIAS_PT_FULL = ['Segunda','Terça','Quarta','Quinta','Sexta','Sábado','Domingo']
ORDEM_GRAN = [2,3,4,5,6,0,1]  # quarta(2), quinta(3), sexta(4), sábado(5), domingo(6), segunda(0), terça(1)

# ─────────────────────────────────────────────────────────────────────
# PATH
# ─────────────────────────────────────────────────────────────────────
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
MESA_INPUTS = MESA_DIR / 'inputs'
MESA_OUTPUT = MESA_DIR / 'dados_gran_mesa.json'
PROD_INPUTS = DATA_DIR / 'produtividade' / 'inputs'

# ─────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────
def normalize_sg(s):
    if not s or pd.isna(s): return 'N/A'
    u = str(s).upper().strip()
    # mojibake fix
    if 'GR' in u and 'OS' in u and 'OLEAGIN' in u: return 'GRAOS & OLEAGINOSAS'
    return u

def subgrupo_limpo(s):
    n = normalize_sg(s)
    if n in NOMES_SUBGRUPO_MAP: return NOMES_SUBGRUPO_MAP[n]
    if n == 'N/A' or n == '' or n == 'NONE': return 'Sem classificação'
    return n.title()

def dia_label_br(dt):
    """datetime → 'Quarta · 22/04'"""
    try:
        d = pd.to_datetime(dt)
        return f"{DIAS_PT_FULL[d.weekday()]} · {d.strftime('%d/%m')}"
    except Exception:
        return str(dt)

def calcular_janela_semana(data_ref=None):
    """Última quarta→terça encerrada."""
    if data_ref is None:
        data_ref = datetime.now()
    dias_ate_terca = (data_ref.weekday() - 1) % 7
    if dias_ate_terca == 0:
        dias_ate_terca = 7
    ultima_terca = data_ref - timedelta(days=dias_ate_terca)
    inicio = ultima_terca - timedelta(days=6)
    return inicio.replace(hour=0,minute=0,second=0,microsecond=0), \
           ultima_terca.replace(hour=23,minute=59,second=59)

def safe_pct(num, den):
    if den is None or den == 0 or pd.isna(den): return None
    if num is None or pd.isna(num): return None
    return (num/den - 1) * 100

def parse_hora(h):
    """Aceita datetime.time, str 'HH:MM:SS', ou None. Retorna int 0-23 ou None."""
    if h is None or pd.isna(h): return None
    if hasattr(h, 'hour'): return h.hour
    try:
        s = str(h)
        return int(s.split(':')[0])
    except Exception:
        return None

def iso_label_da_data(dt):
    """Retorna 'S{NN}/{YY}' a partir de uma data."""
    try:
        d = pd.to_datetime(dt)
        iso_y, iso_w, _ = d.isocalendar()
        return f'S{iso_w:02d}/{str(iso_y)[2:]}'
    except Exception:
        return ''

# ─────────────────────────────────────────────────────────────────────
# FILTRAR ESCOPO MESA
# ─────────────────────────────────────────────────────────────────────
def filtrar_escopo_mesa(df):
    df = df.copy()
    df['cod_str'] = df['cod_arius_str'].fillna('').astype(str)
    setor = df['setor'].fillna('').astype(str).str.upper()
    cond_mesa = setor == 'GRAN MESA'
    cond_granel = (~cond_mesa) & (setor == 'GRANEL')
    cond_padaria = (~cond_mesa) & (~cond_granel) & df['cod_str'].isin(PADARIA_GRAN_CODES)
    cond_excl_760 = df['cod_str'] == '760'
    df['categoria_mesa'] = None
    df.loc[cond_mesa, 'categoria_mesa'] = 'gran_mesa'
    df.loc[cond_granel, 'categoria_mesa'] = 'granel'
    df.loc[cond_padaria, 'categoria_mesa'] = 'padaria_gran'
    return df[df['categoria_mesa'].notna() & ~cond_excl_760].copy()

# ─────────────────────────────────────────────────────────────────────
# CUSTOS (gran_margens.xlsx)
# ─────────────────────────────────────────────────────────────────────
def carregar_custos():
    path = PROD_INPUTS / 'gran_margens.xlsx'
    if not path.exists():
        return pd.DataFrame(columns=['cod','p_custo']), 9999, '—'
    try:
        m = pd.read_excel(path, sheet_name='PRECIFICAÇÃO', header=[0,1])
        m.columns = ['_'.join([str(g).strip(), str(s).strip()]).strip() for g,s in m.columns]
        col_cod = next((c for c in m.columns if c.upper()=='DADOS ESTOQUE_COD'), None)
        col_pc = next((c for c in m.columns if 'P. CUSTO' in c.upper() or 'P.CUSTO' in c.upper()), None)
        if not col_cod or not col_pc:
            return pd.DataFrame(columns=['cod','p_custo']), 9999, '—'
        out = m[[col_cod, col_pc]].copy()
        out.columns = ['cod','p_custo']
        out['cod'] = pd.to_numeric(out['cod'], errors='coerce')
        out = out.dropna(subset=['cod']).copy()
        out['cod'] = out['cod'].astype(int).astype(str)
        out['p_custo'] = pd.to_numeric(out['p_custo'], errors='coerce')
        out = out.drop_duplicates('cod', keep='first')
        idade = (datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)).days
        data_atu = datetime.fromtimestamp(path.stat().st_mtime).strftime('%d/%m/%Y')
        return out, idade, data_atu
    except Exception as e:
        print(f"  ⚠️ erro lendo gran_margens: {e}")
        return pd.DataFrame(columns=['cod','p_custo']), 9999, '—'

def aplicar_margens(df, custos):
    df = df.copy()
    df = df.merge(custos[['cod','p_custo']], left_on='cod_str', right_on='cod', how='left')
    df['cmv'] = df['Quantidade'] * df['p_custo']
    df['margem_rs'] = df['Valor'] - df['cmv']
    df['margem_indispo'] = df['p_custo'].isna()
    return df

# ─────────────────────────────────────────────────────────────────────
# MAPA PRODUÇÃO (colaboradores)
# ─────────────────────────────────────────────────────────────────────
def carregar_tempos_estimados():
    """
    Lê tempos_producao_estimados.json (3 níveis de matching):
      1. overrides_por_cod (mais específico, fixo por SKU)
      2. overrides_por_padrao_desc (substring match na descrição)
      3. tempos_min_por_unidade (por subgrupo)
      4. fallback_min (genérico)
    """
    path = MESA_INPUTS / 'tempos_producao_estimados.json'
    if path.exists():
        with open(path, encoding='utf-8') as f:
            d = json.load(f)
        return {
            'por_cod': d.get('overrides_por_cod', {}),
            'por_padrao': d.get('overrides_por_padrao_desc', {}),
            'por_subgrupo': d.get('tempos_min_por_unidade', {}),
            'fallback': d.get('fallback_min', 5),
        }
    return {
        'por_cod': {},
        'por_padrao': {},
        'por_subgrupo': {
            'Refeições': 25, 'Frutas Higienizadas': 8, 'Sucos': 5,
            'Hortaliças & Legumes': 10, 'Molhos & Caldos': 18, 'Sobremesas': 22,
            'Padaria Gran': 12, 'Granel · Grãos': 1, 'Granel · Frutas Secas': 1,
            'Granel · Temperos': 2, 'Granel · Farináceos': 1, 'Granel · Petiscos': 1,
        },
        'fallback': 5,
    }


def buscar_tempo_min(cod, descricao, subgrupo, tempos_cfg):
    """Aplica matching multinível: cod > padrao desc > subgrupo > fallback."""
    # 1. Override por cod
    if cod and cod in tempos_cfg.get('por_cod', {}):
        return tempos_cfg['por_cod'][cod]
    # v2.1.3: NaN guard — algumas SKUs têm DESCRICAO/subgrupo NaN (float)
    import math
    def _safe(x):
        if x is None: return ''
        if isinstance(x, float) and math.isnan(x): return ''
        return str(x)
    desc_upper = _safe(descricao).upper()
    subgrupo_safe = _safe(subgrupo)
    # 2. Override por padrão na descrição (case-insensitive substring)
    for padrao, tempo in tempos_cfg.get('por_padrao', {}).items():
        if padrao.upper() in desc_upper:
            return tempo
    # 3. Por subgrupo
    return tempos_cfg.get('por_subgrupo', {}).get(subgrupo_safe, tempos_cfg.get('fallback', 5))


def carregar_mapa():
    """
    Aceita nomes de coluna: 'COLABORADOR RESPONSÁVEL' (legado) ou
    'COLABORADOR PRINCIPAL' + 'COLABORADOR SECUNDÁRIO' (novo, com split 50/50).
    Prioriza 'Mapa e Producao.xlsx'. Se 'Mapa e Producao - Para Preencher.xlsx'
    existir e for mais recente, usa esse (Hugo pode editar e salvar com novo nome
    pra teste sem mexer no arquivo principal).
    """
    p_principal = MESA_INPUTS / 'Mapa e Producao.xlsx'
    p_preencher = MESA_INPUTS / 'Mapa e Producao - Para Preencher.xlsx'
    if p_preencher.exists() and (not p_principal.exists() or
        p_preencher.stat().st_mtime > p_principal.stat().st_mtime):
        path = p_preencher
        print(f"  → Usando '{path.name}' (mais recente)")
    elif p_principal.exists():
        path = p_principal
    else:
        return pd.DataFrame(columns=['cod','colaborador','colaborador_secundario','grupo_producao','tipo_pessoa','tipo_item'])
    try:
        mp = pd.read_excel(path, sheet_name='MAPA PRODUÇÃO')
        mp.columns = [c.strip().upper() for c in mp.columns]
        # Detecta formato: legado ou novo
        col_principal = None
        col_secundario = None
        for c in mp.columns:
            cu = c.strip().upper()
            if cu == 'COLABORADOR PRINCIPAL': col_principal = c
            elif cu == 'COLABORADOR SECUNDÁRIO' or cu == 'COLABORADOR SECUNDARIO': col_secundario = c
            elif cu == 'COLABORADOR RESPONSÁVEL' and not col_principal: col_principal = c
        if not col_principal:
            print("  ⚠️ Coluna de colaborador não encontrada na planilha")
            return pd.DataFrame(columns=['cod','colaborador','colaborador_secundario','grupo_producao','tipo_pessoa','tipo_item'])

        mp = mp.rename(columns={'COD':'cod','GRUPO':'grupo_producao','DESCRIÇÃO':'descricao_mapa',
                                col_principal:'colaborador'})
        if col_secundario:
            mp = mp.rename(columns={col_secundario:'colaborador_secundario'})
        else:
            mp['colaborador_secundario'] = None

        mp = mp.dropna(subset=['cod']).copy()
        mp['cod'] = pd.to_numeric(mp['cod'], errors='coerce')
        mp = mp.dropna(subset=['cod']).copy()
        mp['cod'] = mp['cod'].astype(int).astype(str)
        mp['colaborador'] = mp['colaborador'].fillna('Não Atribuído').astype(str).str.strip()
        mp['colaborador_secundario'] = mp['colaborador_secundario'].astype(str).str.strip().replace({'nan': None, 'None': None, '': None})
        mp['tipo_pessoa'] = mp['colaborador'].apply(
            lambda c: 'fornecedor_externo' if c.upper().startswith('FORNECEDOR') else 'colaborador_interno'
        )
        mp['tipo_item'] = mp['descricao_mapa'].fillna('').astype(str).apply(
            lambda d: 'insumo_producao' if 'PRODUCAO' in d.upper() else 'produto_final'
        )
        return mp[['cod','colaborador','colaborador_secundario','grupo_producao','tipo_pessoa','tipo_item']]
    except Exception as e:
        print(f"  ⚠️ erro lendo mapa: {e}")
        return pd.DataFrame(columns=['cod','colaborador','colaborador_secundario','grupo_producao','tipo_pessoa','tipo_item'])

def aplicar_mapa(df, mapa):
    df = df.copy()
    if mapa.empty:
        df['colaborador'] = 'Não Atribuído'
        df['colaborador_secundario'] = None
        df['grupo_producao'] = 'Sem mapping'
        df['tipo_pessoa'] = 'nao_atribuido'
        df['tipo_item'] = 'produto_final'
        return df
    df = df.merge(mapa, left_on='cod_str', right_on='cod', how='left', suffixes=('','_map'))
    df['colaborador'] = df['colaborador'].fillna('Não Atribuído')
    if 'colaborador_secundario' not in df.columns:
        df['colaborador_secundario'] = None
    df['grupo_producao'] = df['grupo_producao'].fillna('Sem mapping')
    df['tipo_pessoa'] = df['tipo_pessoa'].fillna('nao_atribuido')
    df['tipo_item'] = df['tipo_item'].fillna('produto_final')
    return df

# ─────────────────────────────────────────────────────────────────────
# FERIADOS — DESALINHAMENTO E ALIGNED YoY
# ─────────────────────────────────────────────────────────────────────
def feriados_da_semana(inicio, fim, feriados_dict):
    """Lista de (data, nome) que caem entre inicio e fim."""
    out = []
    cur = inicio.date() if hasattr(inicio,'date') else inicio
    end = fim.date() if hasattr(fim,'date') else fim
    while cur <= end:
        key = cur.strftime('%Y-%m-%d')
        if key in feriados_dict:
            out.append((key, feriados_dict[key][0]))
        cur += timedelta(days=1)
    return out

def construir_desalinhamento(sids_focais, periodos_2026, periodos_2025):
    """Para cada sid focal, lista feriados em 2026 vs 2025 e detecta desalinhamento."""
    out = {}
    for sid in sids_focais:
        ini26, fim26 = periodos_2026[sid]
        ini25, fim25 = periodos_2025.get(sid, (None,None))
        f26 = feriados_da_semana(ini26, fim26, FERIADOS_2026)
        f25 = feriados_da_semana(ini25, fim25, FERIADOS_2025) if ini25 else []
        # Detectar desalinhamento: feriado em 2026 e não em 2025 (ou vice-versa)
        nomes_26 = set(n for _,n in f26)
        nomes_25 = set(n for _,n in f25)
        tem_alerta = nomes_26 != nomes_25 and (nomes_26 or nomes_25)
        out[sid] = {
            'feriados_2026': f26,
            'feriados_2025': f25,
            'tem_alerta': tem_alerta,
            'sugestoes_aligned': []  # preenchido depois
        }
    return out

def calcular_periodos_semana(base, sids):
    """Para cada sem_id_global, retorna (data_min, data_max)."""
    out = {}
    for sid in sids:
        sub = base[base['sem_id_global'] == sid]
        if len(sub) == 0: continue
        d_min = pd.to_datetime(sub['Data']).min()
        d_max = pd.to_datetime(sub['Data']).max()
        out[sid] = (d_min, d_max)
    return out

# ─────────────────────────────────────────────────────────────────────
# KPIs MACRO
# ─────────────────────────────────────────────────────────────────────
def calc_kpis_sem(df_mesa, df_loja, sid):
    """KPIs de uma semana específica para Mesa + ratio loja."""
    m = df_mesa[df_mesa['sem_id_global']==sid]
    l = df_loja[df_loja['sem_id_global']==sid]
    if len(m) == 0:
        return {'fat':0,'cupons':0,'ticket':0,'itens_nf':0,'margem_rs':0,'margem_pct':None,
                'pct_loja':0,'media_dia':0,'skus':0,'fat_loja':float(l['Valor'].sum())}
    fat = float(m['Valor'].sum())
    cupons = m.groupby(['Pdv','Cupom','Data']).ngroups
    ticket = fat/cupons if cupons else 0
    itens_nf = len(m)/cupons if cupons else 0
    margem_rs = float(m[~m['margem_indispo']]['margem_rs'].sum())
    margem_disp_fat = float(m[~m['margem_indispo']]['Valor'].sum())
    margem_pct = (margem_rs/margem_disp_fat*100) if margem_disp_fat else None
    fat_loja = float(l['Valor'].sum())
    pct_loja = (fat/fat_loja*100) if fat_loja else 0
    dias = m['Data'].nunique()
    media_dia = fat/dias if dias else 0
    skus = m['cod_str'].nunique()
    return {'fat':fat,'cupons':cupons,'ticket':ticket,'itens_nf':itens_nf,
            'margem_rs':margem_rs,'margem_pct':margem_pct,'pct_loja':pct_loja,
            'media_dia':media_dia,'skus':skus,'fat_loja':fat_loja,
            'margem_disp_fat':margem_disp_fat}

def build_kpis_macro(df_mesa, df_loja, sem_atual_id, periodos):
    cur = calc_kpis_sem(df_mesa, df_loja, sem_atual_id)
    lw = calc_kpis_sem(df_mesa, df_loja, sem_atual_id-1)
    # Médias L4W e L8W
    def media(metric, n):
        vals = []
        for s in range(sem_atual_id-n, sem_atual_id):
            v = calc_kpis_sem(df_mesa, df_loja, s).get(metric)
            if v is not None and v > 0: vals.append(v)
        return float(np.mean(vals)) if vals else None
    l4w = {k: media(k,4) for k in ['fat','cupons','ticket','itens_nf','media_dia','skus','margem_pct','pct_loja']}
    l8w = {k: media(k,8) for k in ['fat','cupons','ticket','itens_nf','media_dia','skus','margem_pct','pct_loja']}
    # YoY posicional: mesma sem ano anterior
    yoy = calc_kpis_sem(df_mesa, df_loja, sem_atual_id-52)
    ini, fim = periodos.get(sem_atual_id, (None,None))
    sem_label = 'S??'
    # v2.1.3: alinhar nomenclatura com Survey Gran global (cadência quarta→terça,
    # não ISO week). Tenta ler dados_survey.json se já foi rodado.
    try:
        import json
        from pathlib import Path
        survey_global = Path(MESA_OUTPUT).parent.parent / 'base' / 'dados_survey.json'
        if survey_global.exists():
            with open(survey_global) as _f:
                dg = json.load(_f)
            if dg.get('kpis_macro', {}).get('sem_label'):
                sem_label = dg['kpis_macro']['sem_label']
    except Exception:
        pass
    # Fallback: usar ISO week (legado v2.1.0-2.1.2)
    if sem_label == 'S??' and fim:
        iso_y, iso_w, _ = pd.to_datetime(fim).isocalendar()
        sem_label = f'S{iso_w:02d}/{str(iso_y)[2:]}'
    periodo_str = f'{ini.strftime("%d/%m")} a {fim.strftime("%d/%m/%Y")}' if ini else '—'
    return {
        'sem_atual_id': sem_atual_id, 'sem_label': sem_label, 'periodo': periodo_str,
        'fat': cur['fat'], 'cupons': cur['cupons'], 'ticket': cur['ticket'],
        'itens_nf': cur['itens_nf'], 'margem_rs': cur['margem_rs'], 'margem_pct': cur['margem_pct'],
        'pct_loja': cur['pct_loja'], 'media_dia': cur['media_dia'], 'skus': cur['skus'],
        'fat_loja_atual': cur['fat_loja'],
        # Comparadores
        'fat_lw': safe_pct(cur['fat'], lw['fat']),
        'fat_l4w': safe_pct(cur['fat'], l4w['fat']),
        'fat_l8w': safe_pct(cur['fat'], l8w['fat']),
        'fat_yoy': safe_pct(cur['fat'], yoy['fat']),
        'cupons_lw': safe_pct(cur['cupons'], lw['cupons']),
        'cupons_l4w': safe_pct(cur['cupons'], l4w['cupons']),
        'cupons_l8w': safe_pct(cur['cupons'], l8w['cupons']),
        'ticket_lw': safe_pct(cur['ticket'], lw['ticket']),
        'ticket_l4w': safe_pct(cur['ticket'], l4w['ticket']),
        'ticket_l8w': safe_pct(cur['ticket'], l8w['ticket']),
        'itens_lw': safe_pct(cur['itens_nf'], lw['itens_nf']),
        'itens_l4w': safe_pct(cur['itens_nf'], l4w['itens_nf']),
        'itens_l8w': safe_pct(cur['itens_nf'], l8w['itens_nf']),
        'media_lw': safe_pct(cur['media_dia'], lw['media_dia']),
        'media_l4w': safe_pct(cur['media_dia'], l4w['media_dia']),
        'media_l8w': safe_pct(cur['media_dia'], l8w['media_dia']),
        'skus_lw': safe_pct(cur['skus'], lw['skus']),
        'skus_l4w': safe_pct(cur['skus'], l4w['skus']),
        'skus_l8w': safe_pct(cur['skus'], l8w['skus']),
        'margem_pct_lw': safe_pct(cur['margem_pct'], lw['margem_pct']),
        'margem_pct_l4w': safe_pct(cur['margem_pct'], l4w['margem_pct']),
        'margem_pct_l8w': safe_pct(cur['margem_pct'], l8w['margem_pct']),
        # NOVO: comparador % do fat da loja com tri-cmp
        'pct_loja_lw': safe_pct(cur['pct_loja'], lw['pct_loja']),
        'pct_loja_l4w': safe_pct(cur['pct_loja'], l4w['pct_loja']),
        'pct_loja_l8w': safe_pct(cur['pct_loja'], l8w['pct_loja']),
    }

# ─────────────────────────────────────────────────────────────────────
# CHART DIÁRIO (semana atual + L4W + YoY)
# ─────────────────────────────────────────────────────────────────────
def build_chart_diario(df_mesa, sem_atual_id):
    """Para cada dia da semana atual: fat + baseline L4W + baseline YoY."""
    cur = df_mesa[df_mesa['sem_id_global']==sem_atual_id].copy()
    cur['Data_dt'] = pd.to_datetime(cur['Data'])
    cur['dow'] = cur['Data_dt'].dt.dayofweek  # 0=Mon
    fat_dia = cur.groupby(['Data_dt','dow'])['Valor'].sum().reset_index()

    # Baseline L4W: mesmo dow nas 4 sem anteriores
    base_l4w = df_mesa[df_mesa['sem_id_global'].isin(range(sem_atual_id-4, sem_atual_id))].copy()
    base_l4w['dow'] = pd.to_datetime(base_l4w['Data']).dt.dayofweek
    l4w_por_dow = base_l4w.groupby(['sem_id_global','dow'])['Valor'].sum().reset_index()
    l4w_med = l4w_por_dow.groupby('dow')['Valor'].mean().to_dict()

    # Baseline YoY: mesma sem ano anterior
    base_yoy = df_mesa[df_mesa['sem_id_global']==sem_atual_id-52].copy()
    base_yoy['dow'] = pd.to_datetime(base_yoy['Data']).dt.dayofweek
    yoy_por_dow = base_yoy.groupby('dow')['Valor'].sum().to_dict()

    out = []
    for _, r in fat_dia.sort_values('Data_dt').iterrows():
        dow = int(r['dow'])
        d = r['Data_dt']
        fat = float(r['Valor'])
        bl4w = float(l4w_med.get(dow, 0))
        byoy = float(yoy_por_dow.get(dow, 0))
        out.append({
            'data_iso': d.strftime('%Y-%m-%d'),
            'dia_label': dia_label_br(d),
            'dia_short': DIAS_PT_SHORT[dow],
            'fat': fat,
            'baseline_l4w': bl4w,
            'baseline_yoy': byoy,
            'lift_l4w_pct': safe_pct(fat, bl4w),
            'lift_yoy_pct': safe_pct(fat, byoy),
        })
    return out

# ─────────────────────────────────────────────────────────────────────
# EVOLUÇÃO 13 SEM (chart-evolucao)
# ─────────────────────────────────────────────────────────────────────
def build_evolucao_13sem(df_mesa, df_loja, sids_focais, periodos):
    out = []
    for sid in sids_focais:
        k = calc_kpis_sem(df_mesa, df_loja, sid)
        ini, fim = periodos.get(sid, (None,None))
        sem_label_short = ''
        if fim:
            _, iso_w, _ = pd.to_datetime(fim).isocalendar()
            sem_label_short = f'S{iso_w:02d}'
        out.append({
            'sem_id': sid,
            'label': sem_label_short,
            'periodo': f'{ini.strftime("%d/%m")}-{fim.strftime("%d/%m")}' if ini else '',
            'fat': k['fat'], 'cupons': k['cupons'], 'ticket': k['ticket'],
            'itens_nf': k['itens_nf'], 'media_dia': k['media_dia'],
            'margem_rs': k['margem_rs'], 'margem_pct': k['margem_pct'],
            'pct_loja': k['pct_loja'], 'fat_loja': k['fat_loja'],
        })
    return out

def build_evolucao_yoy_13sem(df_mesa, df_loja, sids_focais, periodos):
    """Para cada sid focal, traz fat 2026 vs fat 2025 (mesma sid - 52)."""
    out = []
    for sid in sids_focais:
        k26 = calc_kpis_sem(df_mesa, df_loja, sid)
        k25 = calc_kpis_sem(df_mesa, df_loja, sid-52)
        ini26, fim26 = periodos.get(sid, (None,None))
        ini25, fim25 = periodos.get(sid-52, (None,None))
        sem_label_short = ''
        if fim26:
            _, iso_w, _ = pd.to_datetime(fim26).isocalendar()
            sem_label_short = f'S{iso_w:02d}'
        out.append({
            'sem_id': sid, 'label': sem_label_short,
            'periodo_2026': f'{ini26.strftime("%d/%m")}-{fim26.strftime("%d/%m")}' if ini26 else '',
            'periodo_2025': f'{ini25.strftime("%d/%m")}-{fim25.strftime("%d/%m")}' if ini25 else '',
            'fat_2026': k26['fat'], 'fat_2025': k25['fat'],
            'yoy_pct': safe_pct(k26['fat'], k25['fat']),
            'delta_rs': k26['fat'] - k25['fat'],
        })
    return out

# ─────────────────────────────────────────────────────────────────────
# PADRÃO HORÁRIO
# ─────────────────────────────────────────────────────────────────────
def build_padrao_horario(df_mesa, sem_atual_id):
    """
    Padrão horário Gran Mesa — semana atual, granular por (hora, dia da semana).
    Permite filtrar no JS por dia específico, dias úteis ou fim de semana.
    """
    cur = df_mesa[df_mesa['sem_id_global']==sem_atual_id].copy()
    if 'Hora' not in cur.columns or len(cur)==0: return []
    cur['hora_int'] = cur['Hora'].apply(parse_hora)
    cur = cur[cur['hora_int'].notna()].copy()
    cur['hora_int'] = cur['hora_int'].astype(int)
    cur['dow'] = pd.to_datetime(cur['Data']).dt.dayofweek  # 0=Mon, 6=Sun
    out = []
    for h in range(6, 23):
        for dow in range(7):
            sub = cur[(cur['hora_int']==h) & (cur['dow']==dow)]
            cup = sub.groupby(['Pdv','Cupom','Data']).ngroups if len(sub) else 0
            fat = float(sub['Valor'].sum()) if len(sub) else 0
            out.append({'hora_int': h, 'dow': dow, 'cupons': cup, 'fat': fat})
    return out

# ─────────────────────────────────────────────────────────────────────
# FAIXAS DE TICKET
# ─────────────────────────────────────────────────────────────────────
def build_faixas_ticket(df_mesa, sem_atual_id):
    cur = df_mesa[df_mesa['sem_id_global']==sem_atual_id]
    cupons_fat = cur.groupby(['Pdv','Cupom','Data'])['Valor'].sum().reset_index()
    faixas = [
        ('Até R$ 25', 0, 25),
        ('R$ 25 – 50', 25, 50),
        ('R$ 50 – 100', 50, 100),
        ('R$ 100 – 200', 100, 200),
        ('R$ 200 – 500', 200, 500),
        ('Acima de R$ 500', 500, 1e9),
    ]
    out = []
    for nome, lo, hi in faixas:
        sub = cupons_fat[(cupons_fat['Valor']>=lo) & (cupons_fat['Valor']<hi)]
        out.append({'faixa': nome, 'cupons': len(sub), 'fat': float(sub['Valor'].sum())})
    return out

# ─────────────────────────────────────────────────────────────────────
# SUBGRUPOS — expand com tornado dual
# ─────────────────────────────────────────────────────────────────────
def build_subgrupos_expand(df_mesa, sem_atual_id, sids_focais):
    """Subgrupos com fat sem atual, fat 13sem, comparadores LW/L4W/L8W, YoY, share."""
    df_mesa = df_mesa.copy()
    df_mesa['subgrupo_clean'] = df_mesa['subgrupo'].apply(subgrupo_limpo)

    cur_sid = sem_atual_id
    out = []
    sgs = df_mesa['subgrupo_clean'].unique()
    fat_total_atual = df_mesa[df_mesa['sem_id_global']==cur_sid]['Valor'].sum()
    for sg in sgs:
        d = df_mesa[df_mesa['subgrupo_clean']==sg]
        # Sem atual
        cur = d[d['sem_id_global']==cur_sid]
        fat_atual = float(cur['Valor'].sum())
        fat_13sem_check = float(d[d['sem_id_global'].isin(sids_focais)]['Valor'].sum())
        if fat_13sem_check == 0:
            continue
        cupons = cur.groupby(['Pdv','Cupom','Data']).ngroups
        margem_disp = cur[~cur['margem_indispo']]
        margem_rs = float(margem_disp['margem_rs'].sum())
        margem_disp_fat = float(margem_disp['Valor'].sum())
        margem_pct = (margem_rs/margem_disp_fat*100) if margem_disp_fat else None

        # LW, L4W, L8W
        fat_lw = float(d[d['sem_id_global']==cur_sid-1]['Valor'].sum())
        l4w_vals = [float(d[d['sem_id_global']==s]['Valor'].sum()) for s in range(cur_sid-4,cur_sid)]
        l4w_vals = [v for v in l4w_vals if v > 0]
        fat_l4w_med = float(np.mean(l4w_vals)) if l4w_vals else None
        l8w_vals = [float(d[d['sem_id_global']==s]['Valor'].sum()) for s in range(cur_sid-8,cur_sid)]
        l8w_vals = [v for v in l8w_vals if v > 0]
        fat_l8w_med = float(np.mean(l8w_vals)) if l8w_vals else None

        # YoY semana atual
        fat_yoy = float(d[d['sem_id_global']==cur_sid-52]['Valor'].sum())

        # 13sem totais
        fat_2026_13sem = float(d[d['sem_id_global'].isin(sids_focais)]['Valor'].sum())
        sids_2025 = [s-52 for s in sids_focais]
        fat_2025_13sem = float(d[d['sem_id_global'].isin(sids_2025)]['Valor'].sum())

        # Série 13sem (pra sparkline)
        sparkline = []
        for sid in sids_focais:
            f26 = float(d[d['sem_id_global']==sid]['Valor'].sum())
            f25 = float(d[d['sem_id_global']==sid-52]['Valor'].sum())
            yoy_pct = safe_pct(f26, f25)
            sparkline.append({'sid': sid, 'fat_2026': f26, 'fat_2025': f25, 'yoy_pct': yoy_pct})

        # Heatmap row: fat por sid + var L4W + var YoY
        heat_l4w = []
        heat_yoy = []
        for sid in sids_focais:
            fa = float(d[d['sem_id_global']==sid]['Valor'].sum())
            l4_vals = [float(d[d['sem_id_global']==s]['Valor'].sum()) for s in range(sid-4,sid)]
            l4_vals = [v for v in l4_vals if v > 0]
            l4_med = float(np.mean(l4_vals)) if l4_vals else None
            fy = float(d[d['sem_id_global']==sid-52]['Valor'].sum())
            heat_l4w.append(safe_pct(fa, l4_med))
            heat_yoy.append(safe_pct(fa, fy))

        out.append({
            'subgrupo': sg,
            'fat_atual': fat_atual,
            'fat_lw': fat_lw, 'fat_l4w_med': fat_l4w_med, 'fat_l8w_med': fat_l8w_med,
            'fat_yoy': fat_yoy,
            'cupons': cupons,
            'margem_rs': margem_rs, 'margem_pct': margem_pct,
            'fat_2026_13sem': fat_2026_13sem, 'fat_2025_13sem': fat_2025_13sem,
            'yoy_13sem_pct': safe_pct(fat_2026_13sem, fat_2025_13sem),
            'var_lw_pct': safe_pct(fat_atual, fat_lw),
            'var_l4w_pct': safe_pct(fat_atual, fat_l4w_med),
            'var_l8w_pct': safe_pct(fat_atual, fat_l8w_med),
            'var_yoy_pct': safe_pct(fat_atual, fat_yoy),
            'share_pct': (fat_atual/fat_total_atual*100) if fat_total_atual else 0,
            'sparkline': sparkline,
            'heatmap_l4w': heat_l4w,
            'heatmap_yoy': heat_yoy,
            'n_skus': d['cod_str'].nunique(),
        })
    out.sort(key=lambda x: -x['fat_atual'])
    return out

# ─────────────────────────────────────────────────────────────────────
# SKUs (raio-X com tri-cmp)
# ─────────────────────────────────────────────────────────────────────
def build_skus(df_mesa, sem_atual_id, sids_focais, tempos_cfg=None, custo_hora_homem=15.0):
    df_mesa = df_mesa.copy()
    df_mesa['subgrupo_clean'] = df_mesa['subgrupo'].apply(subgrupo_limpo)

    skus_map = {}
    cur_sid = sem_atual_id
    fat_total_mesa_atual = df_mesa[df_mesa['sem_id_global']==cur_sid]['Valor'].sum()
    tempos_cfg = tempos_cfg or {'por_cod':{},'por_padrao':{},'por_subgrupo':{},'fallback':5}

    for cod in df_mesa['cod_str'].unique():
        d = df_mesa[df_mesa['cod_str']==cod]
        cur = d[d['sem_id_global']==cur_sid]
        # Pular SKUs sem venda nas 13 sem
        fat_13sem = float(d[d['sem_id_global'].isin(sids_focais)]['Valor'].sum())
        if fat_13sem == 0: continue

        fat_atual = float(cur['Valor'].sum())
        qtd_atual = float(cur['Quantidade'].sum())
        cupons_atual = cur.groupby(['Pdv','Cupom','Data']).ngroups
        preco_med = (fat_atual/qtd_atual) if qtd_atual else 0

        # Comparadores
        fat_lw = float(d[d['sem_id_global']==cur_sid-1]['Valor'].sum())
        l4w = [float(d[d['sem_id_global']==s]['Valor'].sum()) for s in range(cur_sid-4,cur_sid)]
        l4w_v = [v for v in l4w if v>0]
        fat_l4w = float(np.mean(l4w_v)) if l4w_v else None
        l8w = [float(d[d['sem_id_global']==s]['Valor'].sum()) for s in range(cur_sid-8,cur_sid)]
        l8w_v = [v for v in l8w if v>0]
        fat_l8w = float(np.mean(l8w_v)) if l8w_v else None
        fat_yoy = float(d[d['sem_id_global']==cur_sid-52]['Valor'].sum())
        # v2.1.4: YoY de quantidade
        qtd_yoy = float(d[d['sem_id_global']==cur_sid-52]['Quantidade'].sum())

        # Margem
        margem_rs = float(cur[~cur['margem_indispo']]['margem_rs'].sum())
        margem_disp_fat = float(cur[~cur['margem_indispo']]['Valor'].sum())
        margem_pct = (margem_rs/margem_disp_fat*100) if margem_disp_fat else None
        margem_indispo = bool(cur['margem_indispo'].all()) if len(cur) else True

        # Share + selo (constantes calibradas no topo do arquivo)
        share = (fat_atual/fat_total_mesa_atual*100) if fat_total_mesa_atual else 0
        selo = 'verde' if (share >= SELO_VERDE_SHARE_MIN or cupons_atual >= SELO_VERDE_CUPONS_MIN) else 'cinza'

        # Evolução 13sem com YoY (linha 2025) e label ISO real
        evol = []
        for sid in sids_focais:
            ds = d[d['sem_id_global']==sid]
            f = float(ds['Valor'].sum())
            q = float(ds['Quantidade'].sum())
            # YoY: mesma posição calendária ano anterior
            ds_yoy = d[d['sem_id_global']==sid-52]
            f_yoy = float(ds_yoy['Valor'].sum())
            q_yoy = float(ds_yoy['Quantidade'].sum())
            # Label ISO real
            ds_full = df_mesa[df_mesa['sem_id_global']==sid]
            iso_lbl = ''
            if len(ds_full):
                d_max = pd.to_datetime(ds_full['Data']).max()
                iso_lbl = iso_label_da_data(d_max)
            evol.append({
                'sid': sid, 'iso_label': iso_lbl,
                'fat': f, 'qtd': q, 'preco_medio': (f/q) if q else 0,
                'fat_yoy': f_yoy, 'qtd_yoy': q_yoy, 'preco_medio_yoy': (f_yoy/q_yoy) if q_yoy else 0,
            })

        # Lift por dia (sem atual)
        lift_dia = {}
        if len(cur):
            cur_dt = cur.copy()
            cur_dt['dow'] = pd.to_datetime(cur_dt['Data']).dt.dayofweek
            fat_por_dow = cur_dt.groupby('dow')['Valor'].sum().to_dict()
            for dow_idx, dow_nm in [(2,'qua'),(3,'qui'),(4,'sex'),(5,'sab'),(6,'dom'),(0,'seg'),(1,'ter')]:
                outros = [v for k,v in fat_por_dow.items() if k != dow_idx]
                med = np.mean(outros) if outros else 0
                if med and dow_idx in fat_por_dow:
                    lift_dia[dow_nm] = (fat_por_dow[dow_idx]/med - 1)*100
                else:
                    lift_dia[dow_nm] = None

        # Hora último cupom + esgotamento precoce
        hora_ult = None
        dias_precoce = 0
        if 'Hora' in cur.columns and len(cur):
            try:
                cur_hh = cur.copy()
                cur_hh['hora_int'] = cur_hh['Hora'].apply(parse_hora)
                cur_hh = cur_hh[cur_hh['hora_int'].notna()]
                if len(cur_hh):
                    hora_ult_dia = cur_hh.groupby('Data')['hora_int'].max()
                    hora_ult = float(hora_ult_dia.mean()) if len(hora_ult_dia) else None
                    dias_precoce = float((hora_ult_dia < 17).sum() / len(hora_ult_dia) * 100) if len(hora_ult_dia) else 0
            except Exception: pass

        # Ruptura recorrente: vendeu em <4 das últimas 6 sem focais
        ult6 = sids_focais[-6:]
        sems_com_venda = sum(1 for s in ult6 if float(d[d['sem_id_global']==s]['Valor'].sum()) > 0)
        ruptura = sems_com_venda < 4

        # Lançamento
        primeira = pd.to_datetime(d['Data']).min()
        try:
            dias_lanc = (datetime.now() - primeira).days
        except Exception:
            dias_lanc = 9999
        lancamento = dias_lanc <= 90

        # Elasticidade simplificada (corr preço × qtd nas 13 sem)
        precos = [e['preco_medio'] for e in evol if e['preco_medio']>0]
        qtds = [e['qtd'] for e in evol if e['preco_medio']>0]
        elast_corr = None
        if len(precos) >= 4 and np.std(precos) > 0 and np.std(qtds) > 0:
            try: elast_corr = float(np.corrcoef(precos, qtds)[0,1])
            except Exception: pass

        descricao = d['DESCRICAO'].iloc[0] if 'DESCRICAO' in d.columns else '?'
        kvi = d['KVI'].iloc[0] if 'KVI' in d.columns and len(d) else '-'
        curva = d['CURVA'].iloc[0] if 'CURVA' in d.columns and len(d) else '-'
        setor = d['setor'].iloc[0] if 'setor' in d.columns else '?'
        subgrupo = d['subgrupo_clean'].iloc[0]
        categoria = d['categoria_mesa'].iloc[0]
        colab = d['colaborador'].iloc[0] if 'colaborador' in d.columns else 'Não Atribuído'
        colab_sec = d['colaborador_secundario'].iloc[0] if 'colaborador_secundario' in d.columns else None
        if pd.isna(colab_sec) or not colab_sec or str(colab_sec).strip() in ('','nan','None'):
            colab_sec = None
        tipo_pessoa = d['tipo_pessoa'].iloc[0] if 'tipo_pessoa' in d.columns else 'nao_atribuido'

        # Estimativa de horas e Margem R$/hora estimada (matching multinível: cod > padrão desc > subgrupo)
        tempo_min_unit = buscar_tempo_min(cod, descricao, subgrupo, tempos_cfg)
        horas_estim = (qtd_atual * tempo_min_unit) / 60 if qtd_atual > 0 else 0
        # "Eficiência R$/h" = margem bruta dividida pelas horas (rendimento da hora trabalhada)
        margem_rs_por_hora_est = (margem_rs / horas_estim) if horas_estim > 0.01 else None
        # v2.1.4: Margem LÍQUIDA pós-custo (Hugo S18) — abate custo da hora-homem (~R$15/h por default)
        custo_horas_rs = horas_estim * custo_hora_homem
        margem_liquida_rs = margem_rs - custo_horas_rs if margem_rs is not None else None
        margem_liquida_pct = (margem_liquida_rs / fat_atual * 100) if (fat_atual > 0 and margem_liquida_rs is not None) else None

        # Fat 13sem (acumulado) e YoY 13sem por SKU
        fat_13sem_2026 = sum(e['fat'] for e in evol)
        fat_13sem_2025 = sum(e['fat_yoy'] for e in evol)
        yoy_13sem_pct = safe_pct(fat_13sem_2026, fat_13sem_2025)

        skus_map[cod] = {
            'cod': cod, 'descricao': descricao, 'setor': setor, 'subgrupo': subgrupo,
            'categoria_mesa': categoria, 'kvi': kvi or '-', 'curva': curva or '-',
            'colaborador': colab, 'colaborador_secundario': colab_sec, 'tipo_pessoa': tipo_pessoa,
            'tempo_min_unit_est': tempo_min_unit,
            'horas_estim_sem': float(horas_estim),
            'margem_rs_por_hora_est': float(margem_rs_por_hora_est) if margem_rs_por_hora_est is not None else None,
            # v2.1.4: margem líquida pós-custo de hora-homem
            'custo_hora_homem_rs': float(custo_hora_homem),
            'custo_horas_rs': float(custo_horas_rs),
            'margem_liquida_rs': float(margem_liquida_rs) if margem_liquida_rs is not None else None,
            'margem_liquida_pct': float(margem_liquida_pct) if margem_liquida_pct is not None else None,
            'fat_atual': fat_atual, 'qtd_atual': qtd_atual, 'cupons_atual': cupons_atual,
            'preco_medio': preco_med,
            'share_fat_mesa': share, 'selo_relevancia': selo,
            'margem_rs': margem_rs, 'margem_pct': margem_pct, 'margem_indispo': margem_indispo,
            'var_lw_pct': safe_pct(fat_atual, fat_lw),
            'var_l4w_pct': safe_pct(fat_atual, fat_l4w),
            'var_l8w_pct': safe_pct(fat_atual, fat_l8w),
            'yoy_fat_pct': safe_pct(fat_atual, fat_yoy),
            'fat_yoy_rs': fat_yoy,
            # v2.1.4: YoY de quantidade
            'yoy_qtd_pct': safe_pct(qtd_atual, qtd_yoy),
            'qtd_yoy': qtd_yoy,
            'fat_13sem_2026': fat_13sem_2026,
            'fat_13sem_2025': fat_13sem_2025,
            'yoy_13sem_pct': yoy_13sem_pct,
            'evolucao_13sem': evol,
            'lift_por_dia': lift_dia,
            'hora_ultimo_cupom_med': hora_ult,
            'dias_esgotamento_precoce_pct': dias_precoce,
            'ruptura_recorrente': ruptura,
            'lancamento': lancamento, 'dias_desde_lancamento': dias_lanc,
            'elast_corr': elast_corr,
        }
    return skus_map

# ─────────────────────────────────────────────────────────────────────
# CESTA / CROSS-SELL — Market Basket Analysis
# ─────────────────────────────────────────────────────────────────────
def build_cesta(df_loja, sids_focais, mesa_cods, min_cupons_sku=5, min_cupons_companheiro=3):
    """
    Para cada SKU Mesa, identifica top 10 SKUs companheiros via lift.
    Lift = P(B|A) / P(B). Threshold reduzido pra capturar mais SKUs.
    """
    df13 = df_loja[df_loja['sem_id_global'].isin(sids_focais)].copy()
    df13['cupom_key'] = df13['Pdv'].astype(str)+'_'+df13['Cupom'].astype(str)+'_'+df13['Data'].astype(str)
    df13 = df13[df13['cod_arius_str'].notna()].copy()

    n_total_cupons = df13['cupom_key'].nunique()
    freq_total = df13.groupby('cod_arius_str')['cupom_key'].nunique()

    out = {}
    for cod in mesa_cods:
        cupons_com_sku = df13[df13['cod_arius_str']==cod]['cupom_key'].unique()
        n_com = len(cupons_com_sku)
        if n_com < min_cupons_sku: continue

        df_comp = df13[df13['cupom_key'].isin(cupons_com_sku) & (df13['cod_arius_str']!=cod)]
        if len(df_comp) == 0: continue

        comp_agg = df_comp.groupby('cod_arius_str').agg(
            n_cupons=('cupom_key','nunique'),
            desc=('DESCRICAO','first'),
            setor=('setor','first'),
            fat_total=('Valor','sum'),
        ).reset_index()
        comp_agg = comp_agg[comp_agg['n_cupons']>=min_cupons_companheiro]
        if len(comp_agg) == 0: continue

        comp_agg['p_b_dado_a'] = comp_agg['n_cupons'] / n_com
        comp_agg['p_b'] = comp_agg['cod_arius_str'].map(freq_total) / n_total_cupons
        comp_agg['lift'] = comp_agg['p_b_dado_a'] / comp_agg['p_b']
        comp_agg['suporte_pct'] = comp_agg['n_cupons'] / n_total_cupons * 100

        top = comp_agg.sort_values('lift', ascending=False).head(10)
        comp_list = []
        for _, r in top.iterrows():
            comp_list.append({
                'cod': r['cod_arius_str'],
                'desc': r['desc'],
                'setor': r['setor'],
                'lift': float(r['lift']),
                'cupons_juntos': int(r['n_cupons']),
                'suporte_pct': float(r['suporte_pct']),
                'p_b_dado_a_pct': float(r['p_b_dado_a']*100),
                'fat_total_companheiro': float(r['fat_total']),
            })
        out[cod] = {
            'n_cupons_com_sku': int(n_com),
            'companheiros': comp_list,
        }
    return out

# ─────────────────────────────────────────────────────────────────────
# QUADRANTES MARGEM x VOLUME
# ─────────────────────────────────────────────────────────────────────
def build_quadrantes(skus):
    """
    Classificação por quadrantes usando MEDIANA DO SUBGRUPO (não global).
    Compara cada SKU apenas com SKUs do mesmo subgrupo — Refeições competem entre si,
    Sucos entre si, Granel entre si. Resolve o problema de SKUs Granel virarem 'Estrelas'
    porque a mediana global é puxada pra baixo por SKUs pequenos.
    Subgrupos com <3 SKUs caem na mediana global (fallback).
    """
    skus_ok = [s for s in skus if s['margem_pct'] is not None and not s['margem_indispo'] and s['fat_atual']>0]
    if not skus_ok: return [], None, None, {}
    med_fat_global = float(np.median([s['fat_atual'] for s in skus_ok]))
    med_marg_global = float(np.median([s['margem_pct'] for s in skus_ok]))

    # Mediana por subgrupo (mín 3 SKUs)
    by_sg = {}
    for s in skus_ok:
        by_sg.setdefault(s['subgrupo'], []).append(s)
    medianas_sg = {}
    for sg, lst in by_sg.items():
        if len(lst) >= 3:
            medianas_sg[sg] = {
                'fat': float(np.median([s['fat_atual'] for s in lst])),
                'margem': float(np.median([s['margem_pct'] for s in lst])),
                'n_skus': len(lst),
            }

    out = []
    for s in skus_ok:
        sg_med = medianas_sg.get(s['subgrupo'])
        if sg_med:
            mf, mm = sg_med['fat'], sg_med['margem']
            ref = 'subgrupo'
        else:
            mf, mm = med_fat_global, med_marg_global
            ref = 'global'
        if s['fat_atual'] >= mf and s['margem_pct'] >= mm: q = 'Estrela'
        elif s['fat_atual'] >= mf: q = 'Vaca'
        elif s['margem_pct'] >= mm: q = 'Interrogação'
        else: q = 'Abacaxi'
        out.append({**s, 'quadrante': q, 'med_fat_ref': mf, 'med_marg_ref': mm, 'ref_quadrante': ref})
    return out, med_fat_global, med_marg_global, medianas_sg

# ─────────────────────────────────────────────────────────────────────
# CARTEIRAS (colaborador)
# ─────────────────────────────────────────────────────────────────────
def build_carteiras(skus, sids_focais, df_mesa):
    """
    Suporte a split 50/50 quando SKU tem 2 colaboradores.
    SKU com colaborador_secundario válido divide fat/margem/horas igualmente entre os 2.
    """
    def get_alocacao(sku):
        """Retorna lista de (colaborador, tipo_pessoa, peso) — 1 ou 2 entradas."""
        c1 = sku['colaborador']
        c2 = sku.get('colaborador_secundario')
        if c2 and c2 not in ('Não Atribuído', None) and c1 != c2:
            tp1 = 'fornecedor_externo' if c1.upper().startswith('FORNECEDOR') else 'colaborador_interno'
            tp2 = 'fornecedor_externo' if str(c2).upper().startswith('FORNECEDOR') else 'colaborador_interno'
            if c1 == 'Não Atribuído': tp1 = 'nao_atribuido'
            return [(c1, tp1, 0.5), (c2, tp2, 0.5)]
        return [(c1, sku['tipo_pessoa'], 1.0)]

    cart = {}
    for s in skus:
        for colab, tp, peso in get_alocacao(s):
            if colab not in cart:
                cart[colab] = {'colaborador': colab, 'tipo_pessoa': tp, 'fat':0,
                               'margem_rs':0, 'margem_disp_fat':0, 'n_skus':0, 'n_skus_alerta':0,
                               'n_skus_ruptura':0, 'fat_2026_13sem':0, 'fat_2025_13sem':0,
                               'horas_estim_sem':0, 'cods_associados': [], 'pesos_cods': {},
                               'sparkline': [], 'top_skus':[]}
            cart[colab]['fat'] += s['fat_atual'] * peso
            if not s['margem_indispo']:
                cart[colab]['margem_rs'] += s['margem_rs'] * peso
                cart[colab]['margem_disp_fat'] += s['fat_atual'] * peso
            cart[colab]['n_skus'] += peso  # vira fracionário em split
            if s['ruptura_recorrente']: cart[colab]['n_skus_ruptura'] += peso
            if s['ruptura_recorrente'] or (s['yoy_fat_pct'] is not None and s['yoy_fat_pct']<=-20):
                cart[colab]['n_skus_alerta'] += peso
            cart[colab]['horas_estim_sem'] += s.get('horas_estim_sem', 0) * peso
            cart[colab]['cods_associados'].append(s['cod'])
            cart[colab]['pesos_cods'][s['cod']] = peso

    # Sparkline 13sem por colaborador (com peso)
    df_mesa = df_mesa.copy()
    for colab, d in cart.items():
        cods_c = d['cods_associados']
        pesos_c = d['pesos_cods']
        sub = df_mesa[df_mesa['cod_str'].isin(cods_c)]
        spark = []
        for sid in sids_focais:
            fa = 0.0; fy = 0.0
            for cod in cods_c:
                p = pesos_c[cod]
                fa += float(sub[(sub['sem_id_global']==sid) & (sub['cod_str']==cod)]['Valor'].sum()) * p
                fy += float(sub[(sub['sem_id_global']==sid-52) & (sub['cod_str']==cod)]['Valor'].sum()) * p
            d['fat_2026_13sem'] += fa
            d['fat_2025_13sem'] += fy
            spark.append({'sid': sid, 'fat_2026': fa, 'fat_2025': fy, 'yoy_pct': safe_pct(fa,fy)})
        d['sparkline'] = spark
        d['yoy_13sem_pct'] = safe_pct(d['fat_2026_13sem'], d['fat_2025_13sem'])
        d['margem_pct'] = (d['margem_rs']/d['margem_disp_fat']*100) if d['margem_disp_fat'] else None
        # Top SKUs ponderado por peso
        skus_da_carteira = []
        for s in skus:
            if s['cod'] in pesos_c:
                p = pesos_c[s['cod']]
                skus_da_carteira.append({**s, '_peso': p, '_fat_alocado': s['fat_atual']*p})
        skus_top = sorted(skus_da_carteira, key=lambda x: -x['_fat_alocado'])[:5]
        d['top_skus'] = [{'cod':s['cod'],'desc':s['descricao'],'fat':s['_fat_alocado'],
                          'share':s['share_fat_mesa'],'selo':s['selo_relevancia'],
                          'yoy_pct':s['yoy_fat_pct'],
                          'split': s['_peso']<1.0} for s in skus_top]
        # Arredonda n_skus pra inteiro pra display (se precisar)
        d['n_skus'] = round(d['n_skus'], 1)
        d['n_skus_alerta'] = round(d['n_skus_alerta'], 1)
        d['n_skus_ruptura'] = round(d['n_skus_ruptura'], 1)
        d['pct_alerta'] = (d['n_skus_alerta']/d['n_skus']*100) if d['n_skus'] else 0

    fat_total = sum(c['fat'] for c in cart.values())
    for c in cart.values():
        c['share_fat_mesa'] = (c['fat']/fat_total*100) if fat_total else 0
        # Limpa campos internos
        c.pop('cods_associados', None)
        c.pop('pesos_cods', None)
    return sorted(cart.values(), key=lambda x: (x['tipo_pessoa']!='colaborador_interno', -x['fat']))

# ─────────────────────────────────────────────────────────────────────
# ALERTAS TOP 5
# ─────────────────────────────────────────────────────────────────────
def build_alertas(skus, kpis, subgrupos):
    """
    Eixo PRINCIPAL: queda L4W (desatenção recente — mais acionável que YoY).
    YoY entra como AGRAVANTE: SKUs com queda L4W + YoY negativo recebem boost de impacto
    (problema crônico, está pior agora E está pior que antes).
    """
    cand_skus = []

    # 1. PRINCIPAL — Queda L4W em SKU verde (threshold reduzido pra -15%, mais sensível)
    for s in skus:
        l4w = s.get('var_l4w_pct')
        yoy = s.get('yoy_fat_pct')
        if l4w is None or s['selo_relevancia']!='verde': continue
        if l4w >= -15: continue
        impacto_base = abs(s['fat_atual'] * l4w/100)
        # AGRAVANTE: se YoY também é negativo, problema é crônico — boost de 50%
        if yoy is not None and yoy < -10:
            impacto = impacto_base * 1.5
            detalhe = f"L4W {l4w:+.0f}% · YoY {yoy:+.0f}% (crônico) · share {s['share_fat_mesa']:.1f}% · {s['subgrupo']}"
        else:
            impacto = impacto_base
            detalhe = f"L4W {l4w:+.0f}% · share {s['share_fat_mesa']:.1f}% · {s['subgrupo']}"
        cand_skus.append({'tipo':'queda_l4w','cod':s['cod'],'desc':s['descricao'],
                          'impacto_rs': float(impacto),'detalhe': detalhe})

    # 2. Subprodução defensiva
    for s in skus:
        if s['dias_esgotamento_precoce_pct']>=30 and s['selo_relevancia']=='verde':
            impacto = s['fat_atual'] * 0.20
            cand_skus.append({'tipo':'subproducao','cod':s['cod'],'desc':s['descricao'],
                              'impacto_rs': float(impacto),
                              'detalhe': f"esgota antes 17h em {s['dias_esgotamento_precoce_pct']:.0f}% dos dias · {s['subgrupo']}"})

    # 3. Ruptura
    for s in skus:
        if s['ruptura_recorrente'] and s['selo_relevancia']=='verde':
            impacto = s['fat_atual'] * 0.30
            cand_skus.append({'tipo':'ruptura','cod':s['cod'],'desc':s['descricao'],
                              'impacto_rs': float(impacto),
                              'detalhe': f"vendeu em <4 das últimas 6 sem · share {s['share_fat_mesa']:.1f}% · {s['subgrupo']}"})

    # 4. Queda YoY MUITO severa (<-50%) — sinal extremo, mesmo se L4W ok
    for s in skus:
        yoy = s.get('yoy_fat_pct')
        l4w = s.get('var_l4w_pct')
        if yoy is None or yoy >= -50 or s['selo_relevancia']!='verde': continue
        # Só entra se ainda não foi capturado pela queda L4W
        if l4w is not None and l4w < -15: continue  # já está no critério principal
        impacto = abs(s['fat_yoy_rs'] - s['fat_atual']) * 0.7  # menor peso pq não é problema agora
        cand_skus.append({'tipo':'queda_yoy_extrema','cod':s['cod'],'desc':s['descricao'],
                          'impacto_rs': float(impacto),
                          'detalhe': f"YoY {yoy:+.0f}% (extremo) · L4W {l4w if l4w is not None else 0:+.0f}% · {s['subgrupo']}"})

    # 5. Lançamento fraco
    for s in skus:
        if s['lancamento'] and s['dias_desde_lancamento']>=60 and s['fat_atual']<200:
            cand_skus.append({'tipo':'lancamento','cod':s['cod'],'desc':s['descricao'],
                              'impacto_rs': 500,
                              'detalhe': f"{s['dias_desde_lancamento']}d desde lançamento · sem atual R$ {s['fat_atual']:.0f}"})

    # Dedup por SKU (mantém o de maior impacto)
    cand_skus.sort(key=lambda x: -x['impacto_rs'])
    seen = set()
    skus_top = []
    for c in cand_skus:
        if c['cod'] in seen: continue
        seen.add(c['cod'])
        skus_top.append(c)
        if len(skus_top) >= 4: break

    # Subgrupo com maior queda L4W (1 slot)
    cand_sg = []
    for sg in subgrupos:
        l4w_sg = sg.get('var_l4w_pct')
        if l4w_sg is not None and l4w_sg < -10 and sg['fat_atual'] > 500:
            impacto = abs(sg['fat_atual'] * l4w_sg/100)
            cand_sg.append({'tipo':'queda_subgrupo','cod':'—',
                            'desc':f"Subgrupo '{sg['subgrupo']}' em queda L4W",
                            'impacto_rs': float(impacto),
                            'detalhe': f"L4W {l4w_sg:+.1f}% · YoY 13sem {sg.get('yoy_13sem_pct') or 0:+.1f}%"})
    cand_sg.sort(key=lambda x: -x['impacto_rs'])

    out = skus_top[:4]
    if cand_sg:
        out.append(cand_sg[0])
    return out[:5]


def build_aba06_extras(df_mesa, skus, sids_focais):
    """Análises adicionais para Aba 06: tendência queda + evolução ruptura semanal + potencial perdido."""
    out = {}

    # 1. Tendência de queda: SKUs com queda L4W severa OU YoY severa (selo verde)
    tend_queda = []
    for s in skus:
        if s['selo_relevancia'] != 'verde': continue
        l4w = s.get('var_l4w_pct')
        yoy = s.get('yoy_fat_pct')
        criterio_l4w = (l4w is not None and l4w < -20)
        criterio_yoy = (yoy is not None and yoy < -25)
        if criterio_l4w or criterio_yoy:
            severidade = max(abs(l4w or 0), abs(yoy or 0))
            tend_queda.append({**s, 'severidade': severidade})
    tend_queda.sort(key=lambda x: -x['severidade'])
    out['tendencia_queda'] = tend_queda[:15]

    # 2. Evolução semanal de SKUs em ruptura
    df_mesa_local = df_mesa.copy()
    n_rupt_por_sem = []
    for sid in sids_focais:
        # Para cada sid, ruptura = SKUs Mesa que vendem em <4 das 6 semanas anteriores ao sid
        ult6 = list(range(sid-5, sid+1))
        sub = df_mesa_local[df_mesa_local['sem_id_global'].isin(ult6)]
        sems_por_sku = sub.groupby('cod_str')['sem_id_global'].nunique()
        n_rupt = (sems_por_sku < 4).sum()
        n_skus_ativos = sub['cod_str'].nunique()
        # Label ISO
        ds_full = df_mesa_local[df_mesa_local['sem_id_global']==sid]
        iso_lbl = ''
        if len(ds_full):
            d_max = pd.to_datetime(ds_full['Data']).max()
            iso_lbl = iso_label_da_data(d_max)
        n_rupt_por_sem.append({'sid': sid, 'iso_label': iso_lbl, 'n_ruptura': int(n_rupt),
                                'n_skus_ativos': int(n_skus_ativos),
                                'pct_ruptura': float(n_rupt/n_skus_ativos*100) if n_skus_ativos else 0})
    out['evolucao_ruptura'] = n_rupt_por_sem

    # 3. Potencial perdido por subprodução (top 10): fat_atual * (1 + fator de recovery)
    sub_skus = [s for s in skus if s['dias_esgotamento_precoce_pct']>=30 and s['selo_relevancia']=='verde']
    for s in sub_skus:
        # Estimativa simples: cada % de esgotamento precoce vale 0.5% de fat perdido
        s['potencial_perdido'] = s['fat_atual'] * (s['dias_esgotamento_precoce_pct']/100) * 0.5
    sub_skus.sort(key=lambda x: -x['potencial_perdido'])
    out['subproducao_top'] = sub_skus[:15]

    return out


def build_carteiras_ranking(carteiras):
    """Adiciona score, ranking e badges às carteiras para competição interna."""
    # Filtrar apenas colaboradores internos (excluir fornecedores e Não Atribuído)
    internos = [c for c in carteiras if c['tipo_pessoa']=='colaborador_interno']
    if not internos: return carteiras

    # Métricas adicionais por colaborador
    for c in internos:
        c['fat_por_sku'] = (c['fat']/c['n_skus']) if c['n_skus'] else 0
        c['margem_por_sku'] = (c['margem_rs']/c['n_skus']) if c['n_skus'] else 0
        # SKUs em alerta como % do total da carteira
        c['pct_alerta'] = (c['n_skus_alerta']/c['n_skus']*100) if c['n_skus'] else 0
        # SKUs com YoY positivo
        c['n_skus_crescendo'] = 0  # preenchido depois

    # Score composto (0-100): pesos confirmados pelo Hugo (v4):
    # 60% Faturamento + 25% Margem R$ absoluta + 10% Margem % + 5% Saúde da carteira
    def normalize(vals, invert=False):
        if not vals: return [50]*len(vals)
        mn, mx = min(vals), max(vals)
        if mx == mn: return [50]*len(vals)
        if invert: return [(mx-v)/(mx-mn)*100 for v in vals]
        return [(v-mn)/(mx-mn)*100 for v in vals]

    fats = [c['fat'] for c in internos]
    margens_rs = [c['margem_rs'] for c in internos]
    margens_pct = [c['margem_pct'] or 0 for c in internos]
    alertas_pct = [c['pct_alerta'] for c in internos]

    n_fats = normalize(fats)
    n_marg_rs = normalize(margens_rs)
    n_marg_pct = normalize(margens_pct)
    n_alertas = normalize(alertas_pct, invert=True)  # menos alertas = melhor

    for i, c in enumerate(internos):
        c['score'] = round(n_fats[i]*0.60 + n_marg_rs[i]*0.25 + n_marg_pct[i]*0.10 + n_alertas[i]*0.05, 1)
        c['score_componentes'] = {
            'fat_norm': round(n_fats[i],1),
            'margem_rs_norm': round(n_marg_rs[i],1),
            'margem_pct_norm': round(n_marg_pct[i],1),
            'saude_norm': round(n_alertas[i],1),
        }

    # Ranking
    internos.sort(key=lambda x: -x['score'])
    for i, c in enumerate(internos, 1):
        c['rank'] = i

    # Badges
    if internos:
        # Líder do ranking
        internos[0]['badge'] = '🏆 LÍDER GERAL'
    # Maior fat
    if internos:
        max_fat = max(internos, key=lambda x: x['fat'])
        max_fat.setdefault('badges_extra',[]).append('💰 MAIOR VOLUME')
    # Maior margem
    valid_marg = [c for c in internos if c['margem_pct'] is not None]
    if valid_marg:
        max_marg = max(valid_marg, key=lambda x: x['margem_pct'])
        max_marg.setdefault('badges_extra',[]).append('📈 MAIOR MARGEM')
    # Maior crescimento
    valid_yoy = [c for c in internos if c.get('yoy_13sem_pct') is not None]
    if valid_yoy:
        max_yoy = max(valid_yoy, key=lambda x: x['yoy_13sem_pct'] or -999)
        if (max_yoy.get('yoy_13sem_pct') or 0) > 0:
            max_yoy.setdefault('badges_extra',[]).append('🚀 MAIOR CRESCIMENTO')
    # Saúde da carteira
    if internos:
        min_alerta = min(internos, key=lambda x: x['pct_alerta'])
        if min_alerta['pct_alerta'] < 30:
            min_alerta.setdefault('badges_extra',[]).append('💚 CARTEIRA SAUDÁVEL')

    return carteiras

# ─────────────────────────────────────────────────────────────────────
# GMPRO
# ─────────────────────────────────────────────────────────────────────
def carregar_gmpro():
    path = PROD_INPUTS / 'omie_gmpro.xlsx'
    out = {'fat': 0, 'cmv_pct': 49, 'margem_rs': 0, 'clientes': 0, 'cupons': 0, 'ticket': 0}
    if not path.exists(): return out
    try:
        # Tentar várias abas e padrões
        for sheet in ['NFs Detalhe', 'NFs', 'Detalhe', 0]:
            try:
                omie = pd.read_excel(path, sheet_name=sheet)
                break
            except Exception: continue
        else:
            return out
        # Identificar colunas
        col_data = next((c for c in omie.columns if 'DATA' in str(c).upper()), None)
        col_valor = next((c for c in omie.columns if str(c).upper() in ('VALOR','VLR','TOTAL','VALOR TOTAL')), None)
        col_cliente = next((c for c in omie.columns if 'CLIENTE' in str(c).upper() or 'CNPJ' in str(c).upper()), None)
        if col_data:
            omie[col_data] = pd.to_datetime(omie[col_data], errors='coerce')
            cutoff = datetime.now() - timedelta(days=30)
            omie = omie[omie[col_data]>=cutoff]
        if col_valor:
            fat = float(pd.to_numeric(omie[col_valor], errors='coerce').sum())
            out['fat'] = fat
            out['margem_rs'] = fat * (1 - out['cmv_pct']/100)
            out['cupons'] = len(omie)
            out['ticket'] = fat/len(omie) if len(omie) else 0
        if col_cliente:
            out['clientes'] = omie[col_cliente].nunique()
    except Exception as e:
        print(f"  ⚠️ erro lendo Omie GMPro: {e}")
    return out

# ─────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-ref', default=None)
    args = parser.parse_args()

    data_ref = datetime.fromisoformat(args.data_ref) if args.data_ref else None
    inicio_atual, fim_atual = calcular_janela_semana(data_ref)
    print(f"=== Survey Gran Mesa v2.1 · build_dados ===")
    checar_versao_pandas()
    print(f"Janela atual: {inicio_atual.date()} → {fim_atual.date()}")

    pkl = DATA_DIR / 'base' / 'base_classificada.pkl'
    if not pkl.exists():
        print(f"❌ {pkl} não encontrado. Rode /survey primeiro."); sys.exit(1)
    print(f"Lendo {pkl.name}...")
    df = pd.read_pickle(pkl)
    print(f"  ✓ {len(df):,} linhas")

    # cod_str e Data tipo
    df['cod_str'] = df['cod_arius_str'].fillna('').astype(str)
    df['Data'] = pd.to_datetime(df['Data'], errors='coerce')

    # Filtrar Mesa
    df_mesa = filtrar_escopo_mesa(df)
    print(f"  ✓ Escopo Mesa: {len(df_mesa):,} linhas, {df_mesa['cod_str'].nunique()} SKUs")

    # Cruzar margens
    custos, idade_marg, data_atu_marg = carregar_custos()
    df_mesa = aplicar_margens(df_mesa, custos)
    cob_marg = (~df_mesa['margem_indispo']).sum()/len(df_mesa)*100 if len(df_mesa) else 0
    print(f"  ✓ Cobertura margem: {cob_marg:.1f}%")

    # Cruzar mapa produção
    mapa = carregar_mapa()
    df_mesa = aplicar_mapa(df_mesa, mapa)
    cob_map = (df_mesa['colaborador']!='Não Atribuído').sum()/len(df_mesa)*100 if len(df_mesa) else 0
    print(f"  ✓ Cobertura mapping: {cob_map:.1f}%")

    # Identificar sem_atual
    sem_atual_id = int(df_mesa[df_mesa['Data']<=fim_atual]['sem_id_global'].max())
    sids_focais = list(range(sem_atual_id-12, sem_atual_id+1))
    print(f"  ✓ sem_atual_id: {sem_atual_id}, focais: {sids_focais[0]}-{sids_focais[-1]}")

    # Períodos por sid (incluindo 2025 pra YoY)
    sids_all = list(range(sem_atual_id-13-52, sem_atual_id+1))
    periodos = calcular_periodos_semana(df, sids_all)

    # Desalinhamento de feriados
    desalinha = construir_desalinhamento(sids_focais, periodos, periodos)

    # KPIs macro
    kpis = build_kpis_macro(df_mesa, df, sem_atual_id, periodos)
    print(f"  ✓ KPIs macro · fat R$ {kpis['fat']:,.0f}")

    # Chart diário
    chart_diario = build_chart_diario(df_mesa, sem_atual_id)

    # Evolução 13 sem
    evolucao_13sem = build_evolucao_13sem(df_mesa, df, sids_focais, periodos)
    evolucao_yoy = build_evolucao_yoy_13sem(df_mesa, df, sids_focais, periodos)

    # Padrão horário e faixas
    padrao_horario = build_padrao_horario(df_mesa, sem_atual_id)
    faixas_ticket = build_faixas_ticket(df_mesa, sem_atual_id)

    # Subgrupos expand
    subgrupos = build_subgrupos_expand(df_mesa, sem_atual_id, sids_focais)
    print(f"  ✓ Subgrupos: {len(subgrupos)}")

    # Tempos de produção estimados (proxy multinível: cod > padrão desc > subgrupo)
    tempos_cfg = carregar_tempos_estimados()
    print(f"  ✓ Tempos: {len(tempos_cfg.get('por_padrao',{}))} padrões desc · {len(tempos_cfg.get('por_subgrupo',{}))} subgrupos · {len(tempos_cfg.get('por_cod',{}))} cod-overrides · fallback {tempos_cfg.get('fallback',5)}min")

    # v2.1.4: custo da hora-homem (configurável em parametros.json)
    try:
        with open(PROD_INPUTS / 'parametros.json', 'r', encoding='utf-8') as _f:
            _params = json.load(_f)
        custo_hora_homem = float(_params.get('custo_hora_homem_rs', 15.0))
    except Exception:
        custo_hora_homem = 15.0
    print(f"  ✓ Custo hora-homem: R$ {custo_hora_homem:.2f}/h (para margem líquida pós-custo)")

    # SKUs (com estimativa de horas)
    skus_map = build_skus(df_mesa, sem_atual_id, sids_focais, tempos_cfg, custo_hora_homem)
    skus_list = list(skus_map.values())
    print(f"  ✓ SKUs: {len(skus_list)}")

    # Cesta cross-sell — TODOS SKUs Mesa com cupons mínimos (não só selo verde)
    mesa_cods_all = [s['cod'] for s in skus_list]
    print(f"  Calculando cesta para {len(mesa_cods_all)} SKUs Mesa...")
    cesta = build_cesta(df, sids_focais, mesa_cods_all)
    print(f"  ✓ Cesta: {len(cesta)} SKUs com companheiros")

    # Quadrantes (mediana por subgrupo)
    quadrantes, med_fat, med_marg, medianas_sg = build_quadrantes(skus_list)
    print(f"  ✓ Quadrantes: {len(quadrantes)} · med_fat global R$ {med_fat:.0f} · med_margem {med_marg:.1f}% · {len(medianas_sg)} subgrupos com mediana própria")

    # Carteiras + ranking p/ competição
    carteiras = build_carteiras(skus_list, sids_focais, df_mesa)
    carteiras = build_carteiras_ranking(carteiras)
    print(f"  ✓ Carteiras: {len(carteiras)}")

    # Análises adicionais Aba 06 — tendência queda + evolução ruptura
    aba06 = build_aba06_extras(df_mesa, skus_list, sids_focais)
    print(f"  ✓ Aba 06 extras")

    # Alertas
    alertas = build_alertas(skus_list, kpis, subgrupos)
    print(f"  ✓ Alertas: {len(alertas)}")

    # GMPro
    gmpro = carregar_gmpro()

    # Monta JSON
    out = {
        'meta': {
            'sem_atual_id': sem_atual_id,
            'sem_label': kpis['sem_label'],
            'periodo': kpis['periodo'],
            'gerado_em': datetime.now().isoformat(),
            'cobertura_margem_pct': round(cob_marg,1),
            'cobertura_mapping_pct': round(cob_map,1),
            'margens_idade_dias': idade_marg,
            'margens_data_atualizacao': data_atu_marg,
            'sids_focais': sids_focais,
        },
        'kpis_macro': kpis,
        'chart_diario': chart_diario,
        'evolucao_13sem': evolucao_13sem,
        'evolucao_yoy': evolucao_yoy,
        'padrao_horario': padrao_horario,
        'faixas_ticket': faixas_ticket,
        'subgrupos': subgrupos,
        'desalinhamento': {str(k): v for k,v in desalinha.items()},
        'skus': skus_list,
        'cesta': cesta,
        'quadrantes_meta': {'mediana_fat': med_fat, 'mediana_margem_pct': med_marg, 'n_skus': len(quadrantes), 'medianas_subgrupo': medianas_sg},
        'quadrantes': quadrantes,
        'carteiras': carteiras,
        'aba06_extras': aba06,
        'alertas_top5': alertas,
        'gmpro': gmpro,
    }

    # v2.1.3: sanitizar NaN antes de serializar — alguns SKUs têm desc=NaN (float)
    # e o gerar_html_survey_mesa.py faz t["desc"][:32] que falha em float
    import math as _math
    def _sanitize(o):
        if isinstance(o, dict): return {k: _sanitize(v) for k, v in o.items()}
        if isinstance(o, list): return [_sanitize(v) for v in o]
        if isinstance(o, float) and _math.isnan(o): return ''
        return o
    out = _sanitize(out)

    MESA_DIR.mkdir(parents=True, exist_ok=True)
    with open(MESA_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, default=str, indent=1)
    print(f"\n✅ Salvo: {MESA_OUTPUT}")
    print(f"   {len(skus_list)} SKUs · {len(subgrupos)} subgrupos · {len(carteiras)} carteiras · {len(alertas)} alertas · {len(cesta)} cestas")


if __name__ == '__main__':
    main()
