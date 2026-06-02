"""
Build Dados · Produtividade Gran v1
====================================

Pipeline mensal que cruza:
  - KW (fat + qtd últimos 30d) ← base_classificada.pkl do survey-gran
  - gran_margens.xlsx (P. Custo unitário) ← cadastro de precificação
  - cadastro_equipe.xlsx ← folha CLT classificada por equipe
  - omie_gmpro.xlsx ← faturamento Gran Mesa Pro (Omie)
  - parametros.json ← premissas editáveis

Gera: data/produtividade/dados_produtividade.json

Uso:
    python build_dados.py [--mes MM/AAAA] [--data-ref YYYY-MM-DD]

Defaults:
    mes = mês anterior fechado
    data-ref = último dia do mês de referência
    janela = 30 dias rolling antes da data-ref
"""
import argparse
import json
import os
import sys
import warnings
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

warnings.filterwarnings('ignore')

# ─────────────────────────────────────────────────────────────────────
# Path resolution (compatível com survey-gran v0.12.6+)
# ─────────────────────────────────────────────────────────────────────
def get_data_dir() -> Path:
    """Mesma convenção do survey-gran: env var ou padrão do projeto."""
    if env := os.environ.get('SURVEY_DATA_DIR'):
        return Path(env)
    # Tenta o projeto Cowork
    home_proj = Path.home() / 'Documents' / 'Claude' / 'Projects' / '[GRAN] Survey' / 'data'
    if home_proj.exists():
        return home_proj
    # Fallback legacy
    legacy = Path.home() / 'Documents' / 'SurveyGran'
    if legacy.exists():
        return legacy
    raise FileNotFoundError(
        "Pasta data/ não encontrada. Defina SURVEY_DATA_DIR ou rode dentro do projeto [GRAN] Survey."
    )

DATA_DIR = get_data_dir()
PROD_DIR = DATA_DIR / 'produtividade'
INPUTS_DIR = PROD_DIR / 'inputs'

# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────
def fix_encoding(s):
    """Conserta mojibake — UTF-8 lido como cp1252 (ou latin1) é o caso mais comum."""
    if pd.isna(s):
        return s
    txt = str(s)
    # Tenta cp1252 primeiro (cobre mais caracteres como • que latin1 não tem)
    for enc in ['cp1252', 'latin1']:
        try:
            return txt.encode(enc).decode('utf-8')
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
    return txt


def load_parametros() -> dict:
    """Carrega parâmetros da pasta inputs."""
    path = INPUTS_DIR / 'parametros.json'
    if not path.exists():
        raise FileNotFoundError(f"parametros.json não encontrado em {path}")
    with open(path, encoding='utf-8') as f:
        return json.load(f)


# ─────────────────────────────────────────────────────────────────────
# Fonte 1: KW (fat + qtd dos últimos N dias)
# ─────────────────────────────────────────────────────────────────────
def carregar_vendas_kw(data_ini: datetime, data_fim: datetime, fonte: str = 'auto') -> pd.DataFrame:
    """
    Carrega vendas do KW filtradas pelo período.
    fonte: 'auto' (pkl→csv→margens), 'pkl', 'csv', 'margens'
    Retorna DataFrame com colunas: cod, ean, descricao, qtd, fat, setor, grupo.
    """
    if fonte == 'margens':
        return carregar_vendas_via_margens()

    pkl = DATA_DIR / 'base' / 'base_classificada.pkl'
    if pkl.exists() and fonte in ('auto', 'pkl'):
        try:
            df = pd.read_pickle(pkl)
            print(f"  ✓ Lido base_classificada.pkl: {len(df):,} linhas")
            # Filtra período
            df['Data'] = pd.to_datetime(df['Data'], format='mixed', errors='coerce', dayfirst=True)
            df = df[(df['Data'] >= data_ini) & (df['Data'] <= data_fim)]
            print(f"  ✓ Período {data_ini.date()}-{data_fim.date()}: {len(df):,} linhas")
            # Renomear colunas pro padrão interno
            df = df.rename(columns={
                'Codigo EAN': 'ean', 'DESCRICAO': 'descricao',
                'Quantidade': 'qtd', 'Valor': 'fat',
                'setor': 'setor_arius', 'subgrupo': 'grupo_arius',
            })
            return df[['ean', 'descricao', 'qtd', 'fat', 'setor_arius', 'grupo_arius']].copy()
        except (NotImplementedError, AttributeError, TypeError) as e:
            if fonte == 'pkl':
                raise
            print(f"  ⚠️  base_classificada.pkl incompatível ({type(e).__name__}). Tentando fallback...")

    # Fallback: ler CSVs processados + cruzar com ARIUS
    if fonte in ('auto', 'csv'):
        df = carregar_vendas_kw_csv_fallback(data_ini, data_fim)
        # Em modo auto, se CSV cobrir < 25 dias, usa margens (demo) também
        if fonte == 'auto' and len(df) > 0:
            return df
        elif fonte == 'csv':
            return df

    # Última tentativa: ler de gran_margens (4 semanas consolidadas)
    print(f"  ⚠️  CSVs insuficientes ou ausentes. Usando gran_margens.xlsx como fonte de fat/qtd (modo DEMO).")
    return carregar_vendas_via_margens()


def carregar_vendas_via_margens() -> pd.DataFrame:
    """
    Modo DEMO/fallback: usa SEMANA 1-4 da gran_margens.xlsx como fat+qtd dos últimos 30 dias.
    Útil quando .pkl bloqueia e CSVs cobrem < 30 dias.
    """
    path = INPUTS_DIR / 'gran_margens.xlsx'
    if not path.exists():
        raise FileNotFoundError(f"Sem fonte de KW e gran_margens.xlsx ausente em {path}.")
    m = pd.read_excel(path, sheet_name='PRECIFICAÇÃO', header=[0, 1])
    m.columns = ['_'.join([str(g).strip(), str(s).strip()]).strip() for g, s in m.columns]
    m = m.rename(columns={
        'DADOS ESTOQUE_COD': 'cod',
        'DADOS ESTOQUE_EAN': 'ean',
        'DADOS ESTOQUE_DEPARTAMENTO': 'depto',
        'DADOS ESTOQUE_GRUPO': 'grupo',
        'DADOS ESTOQUE_DESCRIÇÃO': 'descricao',
        'SEMANA 1_QTD': 'q1', 'SEMANA 1_VALOR': 'v1',
        'SEMANA 2_QTD': 'q2', 'SEMANA 2_VALOR': 'v2',
        'SEMANA 3_QTD': 'q3', 'SEMANA 3_VALOR': 'v3',
        'SEMANA 4_QTD': 'q4', 'SEMANA 4_VALOR': 'v4',
    })
    for c in ['q1','v1','q2','v2','q3','v3','q4','v4']:
        m[c] = pd.to_numeric(m[c], errors='coerce').fillna(0)
    m['qtd'] = m[['q1','q2','q3','q4']].sum(axis=1)
    m['fat'] = m[['v1','v2','v3','v4']].sum(axis=1)
    m['cod'] = m['cod'].astype(str).str.strip().str.replace('.0', '', regex=False)
    m['depto'] = m['depto'].apply(fix_encoding)
    m['grupo'] = m['grupo'].apply(fix_encoding)
    m['setor_arius'] = m['depto'].astype(str).str.split(' / ').str[0]
    m['ean'] = m['ean'].fillna('').astype(str)
    m = m[m['fat'] > 0].copy()
    out = m[['cod', 'ean', 'descricao', 'qtd', 'fat', 'setor_arius']].copy()
    out['grupo_arius'] = m['grupo']
    print(f"  ✓ Fonte: gran_margens (DEMO mode): {len(out):,} SKUs com venda nas 4 últimas semanas")
    return out


def carregar_vendas_kw_csv_fallback(data_ini: datetime, data_fim: datetime) -> pd.DataFrame:
    """
    Fallback: lê CSVs em data/extracoes/processed/ e cruza com export_base_arius.xlsx.
    """
    csvs_dir = DATA_DIR / 'extracoes' / 'processed'
    arius_path = DATA_DIR / 'cadastros' / 'export_base_arius.xlsx'
    if not csvs_dir.exists():
        raise FileNotFoundError(f"Sem extrações processadas em {csvs_dir}.")
    if not arius_path.exists():
        raise FileNotFoundError(f"export_base_arius.xlsx não encontrado em {arius_path}.")

    # Carrega ARIUS pra mapping
    arius = pd.read_excel(arius_path, dtype={'EAN': str, 'Código': str})
    arius['Código'] = arius['Código'].astype(str).str.strip()
    arius['EAN'] = arius['EAN'].fillna('').astype(str).str.strip()
    arius['DEPARTAMENTO'] = arius['DEPARTAMENTO'].apply(fix_encoding)
    arius['GRUPO'] = arius['GRUPO'].apply(fix_encoding)

    by_ean, by_cod = {}, {}
    for _, r in arius.iterrows():
        if r['EAN']:
            by_ean[r['EAN']] = r
        if r['Código']:
            by_cod[r['Código']] = r

    def classificar_ean(ean: str):
        if ean in by_ean:
            r = by_ean[ean]
            return r['Código'], r['Descrição'], r['DEPARTAMENTO'], r['GRUPO']
        if ean.startswith('2') and len(ean) == 13:
            for span in [(1, 6), (1, 7)]:
                plu = ean[span[0]:span[1]].lstrip('0') or '0'
                if plu in by_cod:
                    r = by_cod[plu]
                    return r['Código'], r['Descrição'], r['DEPARTAMENTO'], r['GRUPO']
        if ean in by_cod:
            r = by_cod[ean]
            return r['Código'], r['Descrição'], r['DEPARTAMENTO'], r['GRUPO']
        return None, None, None, None

    # Lê todos os CSVs e concatena
    dfs = []
    for csv_path in csvs_dir.glob('*.csv'):
        df = pd.read_csv(csv_path, sep=';', on_bad_lines='skip', dtype={'Codigo EAN': str})
        df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
        df = df[(df['Data'] >= data_ini) & (df['Data'] <= data_fim)]
        if len(df) > 0:
            dfs.append(df)
    if not dfs:
        print(f"  ⚠️  Nenhum CSV cobre o período {data_ini.date()}–{data_fim.date()}.")
        return pd.DataFrame(columns=['cod', 'ean', 'descricao', 'qtd', 'fat', 'setor_arius', 'grupo_arius'])

    df = pd.concat(dfs, ignore_index=True)
    df['Codigo EAN'] = df['Codigo EAN'].astype(str).str.strip()
    df['fat'] = pd.to_numeric(df['Valor'].astype(str).str.replace(',', '.'), errors='coerce')
    df['qtd'] = pd.to_numeric(df['Quantidade'].astype(str).str.replace(',', '.'), errors='coerce')

    classified = df['Codigo EAN'].apply(lambda x: pd.Series(classificar_ean(x)))
    classified.columns = ['cod', 'descricao_arius', 'depto_arius', 'grupo_arius']
    df = pd.concat([df, classified], axis=1)

    # Setor raiz
    df['setor_arius'] = df['depto_arius'].astype(str).str.split(' / ').str[0]
    df = df.rename(columns={'Codigo EAN': 'ean', 'Descrição': 'descricao'})
    print(f"  ✓ Fallback CSV+ARIUS: {len(df):,} linhas no período")
    return df[['cod', 'ean', 'descricao', 'qtd', 'fat', 'setor_arius', 'grupo_arius']].copy()


# ─────────────────────────────────────────────────────────────────────
# Fonte 2: gran_margens (P. Custo unitário por SKU)
# ─────────────────────────────────────────────────────────────────────
def carregar_margens() -> pd.DataFrame:
    """Carrega gran_margens.xlsx → cod + p_custo + depto + grupo + unidade."""
    path = INPUTS_DIR / 'gran_margens.xlsx'
    if not path.exists():
        raise FileNotFoundError(f"gran_margens.xlsx não encontrado em {path}")
    m = pd.read_excel(path, sheet_name='PRECIFICAÇÃO', header=[0, 1])
    m.columns = ['_'.join([str(g).strip(), str(s).strip()]).strip() for g, s in m.columns]
    m = m.rename(columns={
        'DADOS ESTOQUE_COD': 'cod',
        'DADOS ESTOQUE_EAN': 'ean',
        'DADOS ESTOQUE_DEPARTAMENTO': 'depto',
        'DADOS ESTOQUE_GRUPO': 'grupo',
        'DADOS ESTOQUE_DESCRIÇÃO': 'descricao',
        'DADOS ESTOQUE_UNID. COMPRA': 'unidade',
        'DADOS MARGENS_P. CUSTO': 'p_custo',
    })
    cols_keep = ['cod', 'ean', 'depto', 'grupo', 'descricao', 'p_custo']
    if 'unidade' in m.columns:
        cols_keep.append('unidade')
    m = m[cols_keep].copy()
    m['cod'] = m['cod'].astype(str).str.strip().str.replace('.0', '', regex=False)
    m['depto'] = m['depto'].apply(fix_encoding)
    m['grupo'] = m['grupo'].apply(fix_encoding)
    m['p_custo'] = pd.to_numeric(m['p_custo'], errors='coerce').fillna(0)
    if 'unidade' not in m.columns:
        m['unidade'] = ''
    m['unidade'] = m['unidade'].fillna('').astype(str).str.strip().str.upper()
    print(f"  ✓ gran_margens: {len(m):,} SKUs cadastrados")
    return m


# ─────────────────────────────────────────────────────────────────────
# Fonte 3: cadastro_equipe (folha CLT classificada)
# ─────────────────────────────────────────────────────────────────────
def carregar_cadastro_equipe() -> pd.DataFrame:
    """Carrega cadastro_equipe.xlsx → matricula + nome + função + total_vencimentos + equipe."""
    path = INPUTS_DIR / 'cadastro_equipe.xlsx'
    if not path.exists():
        raise FileNotFoundError(f"cadastro_equipe.xlsx não encontrado em {path}")
    df = pd.read_excel(path, sheet_name='Cadastro Equipe')
    df = df.dropna(subset=['Equipe']).copy()
    df = df[~df['Nome'].astype(str).str.contains('TOTAL', case=False, na=False)]
    df['matricula'] = df['Matrícula'].astype(str).str.replace('.0', '', regex=False)
    df = df.rename(columns={
        'Nome': 'nome', 'Função': 'funcao',
        'Total Vencimentos (Proventos)': 'vencimentos',
        'Equipe': 'equipe',
    })
    print(f"  ✓ cadastro_equipe: {len(df)} funcionários CLT")
    print(f"    Distribuição: {dict(df['equipe'].value_counts())}")
    return df[['matricula', 'nome', 'funcao', 'vencimentos', 'equipe']]


# ─────────────────────────────────────────────────────────────────────
# Fonte 4: omie_gmpro (faturamento Gran Mesa Pro últimos 30d)
# ─────────────────────────────────────────────────────────────────────
def carregar_gmpro(data_ini: datetime, data_fim: datetime) -> dict:
    """Soma NFs do Omie no período. Retorna {fat, n_nfs}."""
    path = INPUTS_DIR / 'omie_gmpro.xlsx'
    if not path.exists():
        print(f"  ⚠️  omie_gmpro.xlsx não encontrado — GMPro será 0.")
        return {'fat': 0.0, 'n_nfs': 0, 'periodo': f"{data_ini.date()}–{data_fim.date()}"}
    nfs = pd.read_excel(path, sheet_name='NFs Detalhe')
    nfs['Data Emissão'] = pd.to_datetime(nfs['Data Emissão'], dayfirst=True)
    nfs_periodo = nfs[(nfs['Data Emissão'] >= data_ini) & (nfs['Data Emissão'] <= data_fim)]
    fat = float(nfs_periodo['Valor Total (R$)'].sum())
    print(f"  ✓ Omie GMPro {data_ini.date()}–{data_fim.date()}: {len(nfs_periodo)} NFs · R$ {fat:,.2f}")
    return {'fat': fat, 'n_nfs': len(nfs_periodo), 'periodo': f"{data_ini.date()}–{data_fim.date()}"}


# ─────────────────────────────────────────────────────────────────────
# Atribuição por equipe (regra do parametros.json)
# ─────────────────────────────────────────────────────────────────────
def atribuir_equipe(row, regra: dict) -> tuple:
    """Retorna (label, peso_gran_mesa). peso_gh = 1 - peso_gm.
    Ordem de regras (importa):
      1. Lista split_65_35_outros (ex: cód 4324 Galeto)
      2. Setor 'GRAN MESA' → 100% GM
      3. Setor 'GRANEL' → 100% GM (porcionamento da equipe)
      4. Grupo 'FATIADOS' com unidade KG/QUILO → 100% GM
      5. Grupo 'FATIADOS' com outras unidades (UN, PCT...) → 100% GH
      6. Lista padaria_gran_excl_760 → 65/35
      7. Cód 760 → 100% GH
      8. Demais → 100% GH
    """
    cod = str(row.get('cod', '')).strip()
    setor_raiz = str(row.get('setor_raiz', ''))
    grupo = str(row.get('grupo_margens', ''))
    unidade = str(row.get('unidade', '')).upper().strip()

    # 1) Split 65/35 outros (Galeto, etc.) — vem ANTES do setor pra sobrepor a regra default
    split_outros = regra.get('split_65_35_outros', {})
    if isinstance(split_outros, dict) and cod in split_outros.get('codigos', []):
        return ('Split 65/35 outros', split_outros.get('share_gran_mesa', 0.65))

    # 2) Setor GRAN MESA inteiro
    if setor_raiz == 'GRAN MESA':
        return ('Gran Mesa', 1.0)

    # 3) Setor GRANEL — agora 100% Gran Mesa
    if setor_raiz == 'GRANEL':
        return ('Gran Mesa (Granel)', 1.0)

    # 4-5) Grupo FATIADOS — desambigua por unidade
    if grupo == 'FATIADOS':
        unidades_kg = ('QUILO', 'KG')
        if unidade in unidades_kg:
            return ('Gran Mesa (Fatiados kg)', 1.0)
        elif unidade and unidade not in ('NAN', ''):
            # UN, PCT, etc. → fornecedor pronto
            return ('Gran Horti (Fatiados UN)', 0.0)
        else:
            # Sem unidade cadastrada → default seguro = GM (será logado)
            return ('Gran Mesa (Fatiados sem unid)', 1.0)

    # 6) Padaria Gran 65/35 (exceto cód 760)
    padaria_codes = regra.get('padaria_gran_excl_760', {}).get('codigos', [])
    if cod in padaria_codes:
        return ('Gran Mesa 65%', regra['padaria_gran_excl_760']['share_gran_mesa'])

    # 7) Cód 760
    if cod == '760':
        return ('Gran Horti (cód 760)', 0.0)

    # 8) Demais
    return ('Gran Horti', 0.0)


# ─────────────────────────────────────────────────────────────────────
# Pipeline principal
# ─────────────────────────────────────────────────────────────────────
def main(mes_ref: str = None, data_ref: str = None, fonte: str = 'auto'):
    print("\n" + "═" * 70)
    print("  PRODUTIVIDADE GRAN — BUILD DADOS v1")
    print("═" * 70)

    # 1. Parâmetros
    print("\n→ Carregando parâmetros...")
    p = load_parametros()
    fator = p['fator_encargos_clt']
    cmv_gmpro = p['cmv_gmpro_pct']
    custo_diaristas = p['custo_diaristas_gran_mesa']
    janela_dias = p['periodo_analise_dias']
    alerta_crit = p['alerta_custo_margem_critico_pct']
    alerta_warn = p['alerta_custo_margem_warning_pct']

    # 2. Determinar período
    if data_ref:
        fim = datetime.strptime(data_ref, '%Y-%m-%d')
    elif mes_ref:
        m, a = mes_ref.split('/')
        fim = (datetime(int(a), int(m), 1) + pd.offsets.MonthEnd(0)).to_pydatetime()
    else:
        # Mês anterior fechado
        hoje = datetime.now()
        fim = (hoje.replace(day=1) - timedelta(days=1))
    ini = fim - timedelta(days=janela_dias - 1)
    ini = ini.replace(hour=0, minute=0, second=0, microsecond=0)
    fim = fim.replace(hour=23, minute=59, second=59)
    print(f"\n→ Período: {ini.date()} a {fim.date()} ({janela_dias} dias)")

    # 3. Carregar fontes
    print(f"\n→ Carregando KW (fat + qtd) [fonte={fonte}]...")
    vendas = carregar_vendas_kw(ini, fim, fonte=fonte)

    print("\n→ Carregando margens (P. Custo)...")
    margens = carregar_margens()

    print("\n→ Carregando cadastro de equipe (folha CLT)...")
    equipe = carregar_cadastro_equipe()

    print("\n→ Carregando Omie GMPro...")
    gmpro = carregar_gmpro(ini, fim)

    # 4. Cruzar vendas com p_custo (via cod ou ean)
    print("\n→ Cruzando vendas KW com gran_margens...")
    # Deduplica por cod mantendo o primeiro registro (margens pode ter códigos repetidos por revisão)
    margens_dedup = margens.drop_duplicates(subset=['cod'], keep='first')
    margens_cod = margens_dedup.set_index('cod')[['p_custo', 'depto', 'grupo', 'descricao', 'unidade']].to_dict('index')
    n_dups = len(margens) - len(margens_dedup)
    if n_dups > 0:
        print(f"  ℹ️  {n_dups} códigos duplicados em gran_margens — usando primeira ocorrência")

    def get_pcusto(row):
        cod = str(row.get('cod', '') or '').strip()
        if cod and cod in margens_cod:
            m = margens_cod[cod]
            return m['p_custo'], m['depto'], m['grupo'], m.get('descricao'), m.get('unidade', '')
        return 0.0, None, None, None, ''

    res = vendas.apply(lambda r: pd.Series(get_pcusto(r)), axis=1)
    res.columns = ['p_custo', 'depto_margens', 'grupo_margens', 'desc_margens', 'unidade']
    vendas = pd.concat([vendas.reset_index(drop=True), res.reset_index(drop=True)], axis=1)

    # Setor raiz (do depto da gran_margens, mais limpo)
    vendas['setor_raiz'] = vendas['depto_margens'].astype(str).str.split(' / ').str[0]
    # Se margens não tem, usa setor_arius
    vendas.loc[vendas['setor_raiz'] == 'None', 'setor_raiz'] = vendas['setor_arius']

    vendas['cmv'] = vendas['qtd'] * vendas['p_custo']
    vendas['margem'] = vendas['fat'] - vendas['cmv']

    # 5. Atribuir equipe por linha
    print("\n→ Atribuindo equipe por SKU (regra parametros.json)...")
    eq = vendas.apply(lambda r: pd.Series(atribuir_equipe(r, p['regra_atribuicao_equipe'])), axis=1)
    eq.columns = ['equipe_label', 'peso_gm']
    vendas = pd.concat([vendas.reset_index(drop=True), eq.reset_index(drop=True)], axis=1)

    # Log dos casos especiais (transparência)
    fatiados_sem_unid = vendas[vendas['equipe_label'] == 'Gran Mesa (Fatiados sem unid)']
    if len(fatiados_sem_unid) > 0:
        n_skus = fatiados_sem_unid['cod'].nunique()
        fat_total = fatiados_sem_unid['fat'].sum()
        print(f"  ⚠️  {n_skus} SKUs FATIADOS sem unidade cadastrada — mantidos em GM (R$ {fat_total:,.2f}). Atualizar gran_margens.")
    n_galeto = (vendas['equipe_label'] == 'Split 65/35 outros').sum()
    if n_galeto > 0:
        print(f"  ✓ Cód 4324 (Galeto) e similares — split 65/35: {n_galeto} linhas")
    n_granel = (vendas['equipe_label'] == 'Gran Mesa (Granel)').sum()
    if n_granel > 0:
        print(f"  ✓ Setor GRANEL — 100% GM: {n_granel} linhas")
    n_fat_un = (vendas['equipe_label'] == 'Gran Horti (Fatiados UN)').sum()
    if n_fat_un > 0:
        print(f"  ✓ Fatiados UN (prontos do fornecedor) — 100% GH: {n_fat_un} linhas")

    vendas['fat_gm'] = vendas['fat'] * vendas['peso_gm']
    vendas['fat_gh'] = vendas['fat'] * (1 - vendas['peso_gm'])
    vendas['margem_gm'] = vendas['margem'] * vendas['peso_gm']
    vendas['margem_gh'] = vendas['margem'] * (1 - vendas['peso_gm'])

    # 6. Agregados KW
    fat_gm_kw = float(vendas['fat_gm'].sum())
    fat_gh_kw = float(vendas['fat_gh'].sum())
    mar_gm_kw = float(vendas['margem_gm'].sum())
    mar_gh_kw = float(vendas['margem_gh'].sum())

    # Cobertura ARIUS / margens
    n_total = len(vendas)
    n_class = (vendas['p_custo'] > 0).sum()
    fat_total = float(vendas['fat'].sum())
    fat_sem_pcusto = float(vendas.loc[vendas['p_custo'] == 0, 'fat'].sum())
    pct_sem_pcusto = (fat_sem_pcusto / fat_total * 100) if fat_total > 0 else 0

    # 7. GMPro
    fat_gmpro = gmpro['fat']
    mar_gmpro = fat_gmpro * (1 - cmv_gmpro)
    fat_gm_total = fat_gm_kw + fat_gmpro
    mar_gm_total = mar_gm_kw + mar_gmpro

    # 8. Custo pessoal por equipe
    print("\n→ Calculando custo de pessoal por equipe...")
    venc_por_eq = equipe.groupby('equipe')['vencimentos'].sum().to_dict()
    custo_gm_dir_folha = venc_por_eq.get('Gran Mesa', 0) * fator
    custo_gh_dir_folha = venc_por_eq.get('Gran Horti', 0) * fator
    custo_retag = venc_por_eq.get('Retaguarda', 0) * fator
    custo_gm_dir = custo_gm_dir_folha + custo_diaristas

    # Rateio retaguarda pró-rata por faturamento total
    fat_base_rateio = fat_gm_total + fat_gh_kw
    share_gm = (fat_gm_total / fat_base_rateio) if fat_base_rateio > 0 else 0.5
    share_gh = 1 - share_gm
    custo_retag_gm = custo_retag * share_gm
    custo_retag_gh = custo_retag * share_gh
    custo_gm_total = custo_gm_dir + custo_retag_gm
    custo_gh_total = custo_gh_dir_folha + custo_retag_gh

    # 9. KPIs
    def safe_div(a, b):
        return (a / b) if b else 0

    # Margem líquida (após pagar pessoal) — sobra real
    mar_liquida_gm = mar_gm_total - custo_gm_total
    mar_liquida_gh = mar_gh_kw - custo_gh_total
    mar_liquida_total = mar_liquida_gm + mar_liquida_gh

    # Benchmarks vs realidade — status por KPI por equipe
    bench = p.get('benchmarks', {})
    def status_kpi(real, alvo, menor_eh_melhor=True, tolerancia=0.05):
        """Compara real vs alvo. Retorna ACIMA/META/ATENCAO/ABAIXO + cor."""
        if alvo == 0:
            return ('-', 'var(--ink-mute)')
        ratio = real / alvo
        if menor_eh_melhor:
            if real <= alvo * (1 - tolerancia):
                return ('ACIMA DA META', 'var(--verde)')
            if real <= alvo * (1 + tolerancia):
                return ('NA META', 'var(--gran-dourado)')
            if real <= alvo * 1.20:
                return ('LEVE ATENÇÃO', 'var(--amarelo)')
            return ('FORA DA META', 'var(--vermelho)')
        else:  # maior é melhor (margem bruta)
            if real >= alvo * (1 + tolerancia):
                return ('ACIMA DA META', 'var(--verde)')
            if real >= alvo * (1 - tolerancia):
                return ('NA META', 'var(--gran-dourado)')
            if real >= alvo * 0.80:
                return ('LEVE ATENÇÃO', 'var(--amarelo)')
            return ('FORA DA META', 'var(--vermelho)')

    bench_gm = bench.get('gran_mesa', {})
    bench_gh = bench.get('gran_horti', {})

    def calc_status_equipe(bench_eq, fat, custo, margem_bruta_pct, custo_fat_pct, custo_margem_pct):
        return {
            'alvo_margem_bruta_pct': bench_eq.get('margem_bruta_pct', 0),
            'alvo_custo_sobre_fat_pct': bench_eq.get('custo_sobre_fat_pct', 0),
            'alvo_custo_sobre_margem_pct': bench_eq.get('custo_sobre_margem_pct', 0),
            'status_margem_bruta': status_kpi(margem_bruta_pct, bench_eq.get('margem_bruta_pct', 0), menor_eh_melhor=False),
            'status_custo_sobre_fat': status_kpi(custo_fat_pct, bench_eq.get('custo_sobre_fat_pct', 0), menor_eh_melhor=True),
            'status_custo_sobre_margem': status_kpi(custo_margem_pct, bench_eq.get('custo_sobre_margem_pct', 0), menor_eh_melhor=True),
            'tipo_operacao': bench_eq.get('tipo_operacao', ''),
            'fontes': bench_eq.get('fontes', ''),
        }

    bench_status_gm = calc_status_equipe(
        bench_gm,
        fat_gm_total, custo_gm_total,
        safe_div(mar_gm_total, fat_gm_total) * 100,
        safe_div(custo_gm_total, fat_gm_total) * 100,
        safe_div(custo_gm_total, mar_gm_total) * 100,
    )
    bench_status_gh = calc_status_equipe(
        bench_gh,
        fat_gh_kw, custo_gh_total,
        safe_div(mar_gh_kw, fat_gh_kw) * 100,
        safe_div(custo_gh_total, fat_gh_kw) * 100,
        safe_div(custo_gh_total, mar_gh_kw) * 100,
    )

    kpis = {
        'gran_mesa': {
            'fat_total': fat_gm_total,
            'fat_kw': fat_gm_kw,
            'fat_gmpro': fat_gmpro,
            'cmv_total': fat_gm_total - mar_gm_total,
            'margem_total': mar_gm_total,
            'margem_kw': mar_gm_kw,
            'margem_gmpro': mar_gmpro,
            'margem_pct': safe_div(mar_gm_total, fat_gm_total) * 100,
            'margem_liquida': mar_liquida_gm,
            'margem_liquida_pct_sobre_fat': safe_div(mar_liquida_gm, fat_gm_total) * 100,
            'custo_total': custo_gm_total,
            'custo_folha': custo_gm_dir_folha,
            'custo_diaristas': custo_diaristas,
            'custo_retag_rateio': custo_retag_gm,
            'n_funcionarios_clt': int((equipe['equipe'] == 'Gran Mesa').sum()),
            'custo_sobre_fat_pct': safe_div(custo_gm_total, fat_gm_total) * 100,
            'custo_sobre_margem_pct': safe_div(custo_gm_total, mar_gm_total) * 100,
            'margem_sobre_custo_x': safe_div(mar_gm_total, custo_gm_total),
            'fat_por_func': safe_div(fat_gm_total, (equipe['equipe'] == 'Gran Mesa').sum()),
            'margem_por_func': safe_div(mar_gm_total, (equipe['equipe'] == 'Gran Mesa').sum()),
        },
        'gran_horti': {
            'fat_total': fat_gh_kw,
            'fat_kw': fat_gh_kw,
            'fat_gmpro': 0,
            'cmv_total': fat_gh_kw - mar_gh_kw,
            'margem_total': mar_gh_kw,
            'margem_kw': mar_gh_kw,
            'margem_gmpro': 0,
            'margem_pct': safe_div(mar_gh_kw, fat_gh_kw) * 100,
            'margem_liquida': mar_liquida_gh,
            'margem_liquida_pct_sobre_fat': safe_div(mar_liquida_gh, fat_gh_kw) * 100,
            'custo_total': custo_gh_total,
            'custo_folha': custo_gh_dir_folha,
            'custo_diaristas': 0,
            'custo_retag_rateio': custo_retag_gh,
            'n_funcionarios_clt': int((equipe['equipe'] == 'Gran Horti').sum()),
            'custo_sobre_fat_pct': safe_div(custo_gh_total, fat_gh_kw) * 100,
            'custo_sobre_margem_pct': safe_div(custo_gh_total, mar_gh_kw) * 100,
            'margem_sobre_custo_x': safe_div(mar_gh_kw, custo_gh_total),
            'fat_por_func': safe_div(fat_gh_kw, (equipe['equipe'] == 'Gran Horti').sum()),
            'margem_por_func': safe_div(mar_gh_kw, (equipe['equipe'] == 'Gran Horti').sum()),
        },
        'total': {
            'fat_total': fat_gm_total + fat_gh_kw,
            'cmv_total': (fat_gm_total - mar_gm_total) + (fat_gh_kw - mar_gh_kw),
            'margem_total': mar_gm_total + mar_gh_kw,
            'margem_pct': safe_div(mar_gm_total + mar_gh_kw, fat_gm_total + fat_gh_kw) * 100,
            'margem_liquida': mar_liquida_total,
            'margem_liquida_pct_sobre_fat': safe_div(mar_liquida_total, fat_gm_total + fat_gh_kw) * 100,
            'custo_total': custo_gm_total + custo_gh_total,
            'custo_sobre_fat_pct': safe_div(custo_gm_total + custo_gh_total, fat_gm_total + fat_gh_kw) * 100,
            'custo_sobre_margem_pct': safe_div(custo_gm_total + custo_gh_total, mar_gm_total + mar_gh_kw) * 100,
            'n_funcionarios_clt': len(equipe),
        },
    }

    # Faturamento por GRUPO dentro de cada equipe (pra Aba 2)
    print("\n→ Calculando faturamento por grupo por equipe...")
    grupos_gm_df = vendas[vendas['fat_gm'] > 0].groupby('grupo_margens').agg(
        fat=('fat_gm', 'sum')
    ).reset_index().sort_values('fat', ascending=False)
    grupos_gh_df = vendas[vendas['fat_gh'] > 0].groupby('grupo_margens').agg(
        fat=('fat_gh', 'sum')
    ).reset_index().sort_values('fat', ascending=False)

    def grupos_to_list(df, top_n=8):
        # Top N + "Outros"
        if len(df) > top_n:
            top = df.head(top_n)
            outros_fat = df.iloc[top_n:]['fat'].sum()
            top_list = [{'grupo': str(r['grupo_margens']) if r['grupo_margens'] else 'Sem grupo',
                         'fat': float(r['fat'])} for _, r in top.iterrows()]
            top_list.append({'grupo': f'Outros ({len(df)-top_n} grupos)', 'fat': float(outros_fat)})
            return top_list
        return [{'grupo': str(r['grupo_margens']) if r['grupo_margens'] else 'Sem grupo',
                 'fat': float(r['fat'])} for _, r in df.iterrows()]

    grupos_fat = {
        'gran_mesa': grupos_to_list(grupos_gm_df),
        'gran_horti': grupos_to_list(grupos_gh_df),
    }
    print(f"  ✓ {len(grupos_fat['gran_mesa'])} grupos GM · {len(grupos_fat['gran_horti'])} grupos GH")

    # 10. Top SKUs por equipe (top 10 por margem $)
    print("\n→ Calculando Top SKUs por equipe...")
    vendas_agg = vendas.groupby(['cod', 'descricao', 'setor_raiz', 'grupo_margens', 'equipe_label', 'unidade']).agg(
        qtd=('qtd', 'sum'),
        fat=('fat', 'sum'),
        cmv=('cmv', 'sum'),
        margem=('margem', 'sum'),
        fat_gm=('fat_gm', 'sum'),
        fat_gh=('fat_gh', 'sum'),
        margem_gm=('margem_gm', 'sum'),
        margem_gh=('margem_gh', 'sum'),
    ).reset_index()

    def top_skus(df_agg, qtd_col, eq_label):
        out = df_agg.nlargest(10, qtd_col)
        return [
            {
                'cod': str(r['cod']) if pd.notna(r['cod']) else '?',
                'descricao': str(r['descricao'])[:50],
                'setor': str(r['setor_raiz']),
                'grupo': str(r['grupo_margens']),
                'fat': float(r['fat_gm'] if eq_label == 'gm' else r['fat_gh']),
                'margem': float(r[qtd_col]),
                'margem_pct': safe_div(r[qtd_col], r['fat_gm'] if eq_label == 'gm' else r['fat_gh']) * 100,
            }
            for _, r in out.iterrows() if r[qtd_col] > 0
        ]

    top_gm = top_skus(vendas_agg[vendas_agg['margem_gm'] > 0], 'margem_gm', 'gm')
    top_gh = top_skus(vendas_agg[vendas_agg['margem_gh'] > 0], 'margem_gh', 'gh')

    # Sumário do Top 10 (% sobre margem total da equipe)
    soma_top_gm = sum(s['margem'] for s in top_gm)
    soma_top_gh = sum(s['margem'] for s in top_gh)
    top_resumo = {
        'gran_mesa': {
            'soma_top10': soma_top_gm,
            'pct_sobre_margem_total': (soma_top_gm / mar_gm_kw * 100) if mar_gm_kw > 0 else 0,
        },
        'gran_horti': {
            'soma_top10': soma_top_gh,
            'pct_sobre_margem_total': (soma_top_gh / mar_gh_kw * 100) if mar_gh_kw > 0 else 0,
        },
    }

    # 10b. VILÕES da Gran Mesa — combinação ponderada (margem perdida vs média da equipe)
    # Score = "margem potencial perdida" = fat_gm × (margem_média_equipe - margem_atual)/100
    print("\n→ Calculando VILÕES da Gran Mesa (margem perdida vs média da equipe)...")
    margem_pct_ref_gm = (mar_gm_kw / fat_gm_kw * 100) if fat_gm_kw > 0 else 50
    print(f"  Margem média Gran Mesa: {margem_pct_ref_gm:.1f}% (referência)")

    vendas_gm_pos = vendas_agg[vendas_agg['fat_gm'] > 0].copy()

    def calc_vilao_metrics(row):
        fat_gm_v = float(row['fat_gm'])
        margem_gm_v = float(row['margem_gm'])
        margem_pct = (margem_gm_v / fat_gm_v * 100) if fat_gm_v > 0 else 0
        # Margem perdida = quanto a mais a equipe ganharia se esse SKU rodasse com a margem média
        margem_perdida = fat_gm_v * max(0, (margem_pct_ref_gm - margem_pct)) / 100
        # Penalidade extra se margem negativa
        if margem_pct < 0:
            margem_perdida *= 2
        return pd.Series({
            'vilao_score': margem_perdida,
            'margem_pct_gm': margem_pct,
        })

    if len(vendas_gm_pos) > 0:
        vil_metrics = vendas_gm_pos.apply(calc_vilao_metrics, axis=1)
        vendas_gm_pos = pd.concat([vendas_gm_pos, vil_metrics], axis=1)
        viloes_df = vendas_gm_pos.nlargest(8, 'vilao_score')
        viloes_gm = []
        for _, r in viloes_df.iterrows():
            if r['vilao_score'] <= 0:
                continue
            margem_pct_v = float(r['margem_pct_gm'])
            if margem_pct_v < 0:
                diag = 'Vendendo no prejuízo'
                acao = 'DESCONTINUAR'
            elif margem_pct_v < 15:
                diag = f'Margem crítica ({margem_pct_v:.0f}%)'
                acao = 'REVISAR PREÇO'
            elif margem_pct_v < 30:
                diag = f'Margem baixa ({margem_pct_v:.0f}%)'
                acao = 'AVALIAR'
            elif margem_pct_v < margem_pct_ref_gm - 10:
                diag = f'Abaixo da média ({margem_pct_v:.0f}% vs {margem_pct_ref_gm:.0f}% ref)'
                acao = 'OTIMIZAR'
            else:
                diag = 'Performance limitada'
                acao = 'ACOMPANHAR'
            viloes_gm.append({
                'cod': str(r['cod']),
                'descricao': str(r['descricao'])[:50],
                'setor': str(r['setor_raiz']),
                'grupo': str(r['grupo_margens']),
                'unidade': str(r.get('unidade', '')),
                'fat': float(r['fat_gm']),
                'margem': float(r['margem_gm']),
                'margem_pct': margem_pct_v,
                'margem_pct_ref': float(margem_pct_ref_gm),
                'qtd': float(r['qtd']),
                'score': float(r['vilao_score']),
                'diagnostico': diag,
                'acao_sugerida': acao,
            })
    else:
        viloes_gm = []
    print(f"  ✓ {len(viloes_gm)} vilões identificados na Gran Mesa")

    # 10c. MENOS VENDIDOS da Gran Mesa — baixo giro, candidatos a tirar do mix
    print("\n→ Calculando MENOS VENDIDOS da Gran Mesa...")
    limite_giro = p.get('limite_baixo_giro_kg_30d', 5.0)
    unid_prod = set(p.get('unidades_producao', ['QUILO', 'KG']))
    # Filtra SKUs Gran Mesa com qtd < limite (em kg)
    pouco_vendidos_df = vendas_gm_pos[
        (vendas_gm_pos['unidade'].astype(str).str.upper().isin(unid_prod)) &
        (vendas_gm_pos['qtd'] < limite_giro) &
        (vendas_gm_pos['fat_gm'] > 0)
    ].copy()
    pouco_vendidos_df = pouco_vendidos_df.nsmallest(8, 'margem_gm') if len(pouco_vendidos_df) >= 8 else pouco_vendidos_df.sort_values('margem_gm')
    # Simulação de custo de hora — APENAS pra menos vendidos (pra mostrar potencial prejuízo)
    custo_hora_sim = 15.0  # premissa fixa, só pra simulação aqui
    horas_kg_sim = 1.0
    menos_vendidos = []
    for _, r in pouco_vendidos_df.iterrows():
        qtd_v = float(r['qtd'])
        margem_v = float(r['margem_gm'])
        # Simulação: 1h por kg a R$ 15
        custo_h_sim = qtd_v * horas_kg_sim * custo_hora_sim
        margem_apos_h = margem_v - custo_h_sim
        margem_apos_h_pct = (margem_apos_h / float(r['fat_gm']) * 100) if r['fat_gm'] > 0 else 0
        menos_vendidos.append({
            'cod': str(r['cod']),
            'descricao': str(r['descricao'])[:50],
            'grupo': str(r['grupo_margens']),
            'qtd': qtd_v,
            'fat': float(r['fat_gm']),
            'margem': margem_v,
            'margem_pct': float(r['margem_pct_gm']),
            'unidade': str(r['unidade']),
            # Campos de simulação (só pra essa lista)
            'sim_horas_estim': qtd_v * horas_kg_sim,
            'sim_custo_horas': custo_h_sim,
            'sim_margem_apos_horas': margem_apos_h,
            'sim_margem_apos_horas_pct': margem_apos_h_pct,
        })
    print(f"  ✓ {len(menos_vendidos)} produtos com baixo giro (<{limite_giro}kg em 30d)")

    # 11. Lista nominal funcionários
    lista_funcionarios = []
    for _, r in equipe.iterrows():
        custo_ind = r['vencimentos'] * fator
        lista_funcionarios.append({
            'matricula': str(r['matricula']),
            'nome': str(r['nome']),
            'funcao': str(r['funcao']),
            'vencimentos': float(r['vencimentos']),
            'custo_total': float(custo_ind),
            'equipe': str(r['equipe']),
        })
    lista_funcionarios.append({
        'matricula': '—',
        'nome': 'DIARISTAS (obras)',
        'funcao': 'Diaristas (fora da folha)',
        'vencimentos': custo_diaristas,
        'custo_total': custo_diaristas,
        'equipe': 'Gran Mesa',
    })

    # 12. Sensibilidade — pré-calcular cenários
    sensibilidade = {
        'eixo_a_gmpro': [],
        'eixo_b_quadro_gm': [],
        'eixo_c_realocacao': [],
        'eixo_d_migracao': [],  # NOVO: SKUs lucrativos da GH migrando pra GM
    }
    for fat_test in [70295, 100000, 130000, 150000, 200000]:
        mar_test = fat_test * (1 - cmv_gmpro)
        fat_gm_test = fat_gm_kw + fat_test
        mar_gm_test = mar_gm_kw + mar_test
        share_test = fat_gm_test / (fat_gm_test + fat_gh_kw) if (fat_gm_test + fat_gh_kw) > 0 else 0.5
        custo_gm_test = custo_gm_dir + custo_retag * share_test
        sensibilidade['eixo_a_gmpro'].append({
            'fat_gmpro': fat_test,
            'custo_sobre_margem_pct': safe_div(custo_gm_test, mar_gm_test) * 100,
        })
    for n_func in [9, 8, 7, 6]:
        # Estimativa: salário médio de Gran Mesa
        venc_med_gm = venc_por_eq.get('Gran Mesa', 0) / max(1, kpis['gran_mesa']['n_funcionarios_clt'])
        custo_dir_test = (n_func * venc_med_gm * fator) + custo_diaristas
        custo_test = custo_dir_test + custo_retag * share_gm
        sensibilidade['eixo_b_quadro_gm'].append({
            'n_funcionarios': n_func,
            'custo_sobre_margem_pct': safe_div(custo_test, mar_gm_total) * 100,
        })
    for pct in [0, 10, 20, 30]:
        # % do custo Gran Mesa que é realocado pra Gran Horti
        custo_realoc = custo_gm_total * (1 - pct / 100)
        sensibilidade['eixo_c_realocacao'].append({
            'pct_realocado': pct,
            'custo_sobre_margem_pct': safe_div(custo_realoc, mar_gm_total) * 100,
        })

    # Eixo D: migração de SKUs lucrativos da Gran Horti pra Gran Mesa
    # Hipótese Hugo: alguns SKUs hoje atribuídos à Gran Horti foram produzidos pela Gran Mesa
    # Cenário: % do faturamento+margem da Gran Horti migra pra Gran Mesa
    for pct in [0, 5, 10, 15, 20, 25]:
        # X% do fat e margem da Gran Horti volta pra Gran Mesa
        fat_migra = fat_gh_kw * (pct / 100)
        mar_migra = mar_gh_kw * (pct / 100)
        fat_gm_test = fat_gm_total + fat_migra
        mar_gm_test = mar_gm_total + mar_migra
        fat_gh_test = fat_gh_kw - fat_migra
        mar_gh_test = mar_gh_kw - mar_migra
        # Re-rateia retaguarda
        share_test = fat_gm_test / (fat_gm_test + fat_gh_test) if (fat_gm_test + fat_gh_test) > 0 else 0.5
        custo_gm_test = custo_gm_dir + custo_retag * share_test
        custo_gh_test = custo_gh_dir_folha + custo_retag * (1 - share_test)
        sensibilidade['eixo_d_migracao'].append({
            'pct_migracao': pct,
            'custo_sobre_margem_pct_gm': safe_div(custo_gm_test, mar_gm_test) * 100,
            'custo_sobre_margem_pct_gh': safe_div(custo_gh_test, mar_gh_test) * 100,
            'fat_gm': fat_gm_test,
            'mar_gm': mar_gm_test,
        })

    # 13. Alerta de qualidade e nível
    nivel_alerta = 'verde'
    custo_marg_gm = kpis['gran_mesa']['custo_sobre_margem_pct']
    custo_marg_gh = kpis['gran_horti']['custo_sobre_margem_pct']
    if custo_marg_gm >= alerta_crit or custo_marg_gh >= alerta_crit:
        nivel_alerta = 'vermelho'
    elif custo_marg_gm >= alerta_warn or custo_marg_gh >= alerta_warn:
        nivel_alerta = 'amarelo'

    qualidade_dado = {
        'cobertura_pcusto_pct': safe_div(n_class, n_total) * 100,
        'fat_sem_pcusto_pct': pct_sem_pcusto,
        'flag_cobertura': pct_sem_pcusto > 5,  # >5% sem custo é bandeira
        'fonte_kw': 'pkl' if (DATA_DIR / 'base' / 'base_classificada.pkl').exists() else 'csv_fallback',
    }

    # 14. Empacotar
    out = {
        'meta': {
            'gerado_em': datetime.now().isoformat(),
            'periodo_inicio': ini.date().isoformat(),
            'periodo_fim': fim.date().isoformat(),
            'janela_dias': janela_dias,
            'mes_referencia': fim.strftime('%m/%Y'),
        },
        'parametros': p,
        'kpis': kpis,
        'top_skus': {
            'gran_mesa': top_gm,
            'gran_horti': top_gh,
        },
        'top_resumo': top_resumo,
        'viloes_gran_mesa': viloes_gm,
        'menos_vendidos_gran_mesa': menos_vendidos,
        'grupos_fat': grupos_fat,
        'benchmarks': {
            'gran_mesa': bench_status_gm,
            'gran_horti': bench_status_gh,
        },
        'funcionarios': lista_funcionarios,
        'sensibilidade': sensibilidade,
        'nivel_alerta': nivel_alerta,
        'qualidade_dado': qualidade_dado,
        'gmpro': gmpro,
    }

    # 15. Salvar
    out_path = PROD_DIR / 'dados_produtividade.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n✓ Salvo: {out_path}")

    # 16. Print sumário
    print("\n" + "═" * 70)
    print(f"  SUMÁRIO — {fim.strftime('%m/%Y')}")
    print("═" * 70)
    print(f"\n  Faturamento total:    R$ {kpis['total']['fat_total']:>12,.2f}")
    print(f"  Margem total:         R$ {kpis['total']['margem_total']:>12,.2f}  ({kpis['total']['margem_pct']:.1f}%)")
    print(f"  Custo pessoal total:  R$ {kpis['total']['custo_total']:>12,.2f}")
    print(f"\n  KPI mãe (custo/margem):")
    print(f"    Gran Mesa:   {kpis['gran_mesa']['custo_sobre_margem_pct']:>5.1f}%  ({kpis['gran_mesa']['n_funcionarios_clt']} func + diaristas)")
    print(f"    Gran Horti:  {kpis['gran_horti']['custo_sobre_margem_pct']:>5.1f}%  ({kpis['gran_horti']['n_funcionarios_clt']} func)")
    print(f"    Total:       {kpis['total']['custo_sobre_margem_pct']:>5.1f}%")
    print(f"\n  Nível alerta: {nivel_alerta.upper()}")
    if qualidade_dado['flag_cobertura']:
        print(f"  ⚠️  {qualidade_dado['fat_sem_pcusto_pct']:.1f}% do faturamento sem P. Custo cadastrado")
    print()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mes', help='Mês de referência no formato MM/AAAA (ex: 03/2026)')
    parser.add_argument('--data-ref', help='Data de referência (último dia do período) YYYY-MM-DD')
    parser.add_argument('--fonte-kw', choices=['auto','pkl','csv','margens'], default='auto',
                       help='Fonte de fat/qtd. auto=tenta pkl→csv→margens. margens=usa SEMANA1-4 da planilha de margens (modo demo).')
    args = parser.parse_args()
    main(mes_ref=args.mes, data_ref=args.data_ref, fonte=args.fonte_kw)
