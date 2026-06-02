"""
Pipeline de Consolidação · Survey Gran
========================================

Consolida nova extração na base histórica, re-classifica todo o histórico,
e prepara a base para o gerador HTML.

Uso:
    python pipeline_consolidacao.py

Lê:
    ~/Documents/Claude/Projects/[GRAN] Survey/data/cadastros/export_base_arius.xlsx
    ~/Documents/Claude/Projects/[GRAN] Survey/data/cadastros/kvi.xlsx
    ~/Documents/Claude/Projects/[GRAN] Survey/data/extracoes/incoming/*.csv  (novas)
    ~/Documents/Claude/Projects/[GRAN] Survey/data/base/base_historica.pkl   (se existir)

Salva:
    ~/Documents/SurveyGran/base/base_historica.pkl  (atualizada)
    ~/Documents/SurveyGran/base/base_classificada.pkl
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Resolver paths absolutos no Mac
import os
# Estrutura unificada — dados ficam dentro do projeto Cowork [GRAN] Survey/
# Override via env: SURVEY_DATA_DIR=/path/customizado python pipeline_consolidacao.py
HOME = Path.home()
DEFAULT_ROOT = HOME / "Documents" / "Claude" / "Projects" / "[GRAN] Survey" / "data"
LEGACY_ROOT = HOME / "Documents" / "SurveyGran"  # fallback se houver instalação antiga
ENV_ROOT = os.environ.get("SURVEY_DATA_DIR")
if ENV_ROOT:
    ROOT = Path(ENV_ROOT)
elif DEFAULT_ROOT.exists() or not LEGACY_ROOT.exists():
    ROOT = DEFAULT_ROOT
else:
    ROOT = LEGACY_ROOT  # mantém retrocompatibilidade se base antiga existir
CADASTROS = ROOT / "cadastros"
INCOMING = ROOT / "extracoes" / "incoming"
PROCESSED = ROOT / "extracoes" / "processed"
BASE_DIR = ROOT / "base"

for d in [CADASTROS, INCOMING, PROCESSED, BASE_DIR]:
    d.mkdir(parents=True, exist_ok=True)

ARIUS_FILE = CADASTROS / "export_base_arius.xlsx"
KVI_FILE = CADASTROS / "kvi.xlsx"
BASE_FILE = BASE_DIR / "base_historica.pkl"
BASE_CLAS_FILE = BASE_DIR / "base_classificada.pkl"
BASE_PARQUET = BASE_DIR / "base_historica.parquet"        # v12.7: backup portável
BASE_CLAS_PARQUET = BASE_DIR / "base_classificada.parquet"
BACKUP_DIR = BASE_DIR / "backup"                          # v12.7: snapshots semanais
BACKUP_DIR.mkdir(parents=True, exist_ok=True)


def parse_brnum(x):
    if pd.isna(x):
        return None
    try:
        return float(str(x).replace(',', '.'))
    except Exception:
        return None


def clean(x):
    s = str(x).strip()
    if s.endswith('.0'):
        s = s[:-2]
    return s


def carregar_csv_extracao(path):
    for enc in ['utf-8', 'utf-8-sig', 'windows-1252']:
        try:
            df = pd.read_csv(path, sep=';', encoding=enc, dtype=str)
            print(f"  Carregado {path.name} (encoding {enc}): {len(df):,} linhas")
            return df, enc
        except Exception:
            continue
    raise ValueError(f"Não consegui ler {path}")


def normalizar_extracao(df):
    # Renomeações primeiro (cobrir variações de header do KW)
    rename_map = {
        'Descrição': 'DESCRICAO',
        'Descricao': 'DESCRICAO',
        'Tributação': 'TRIB.',
        'Tributacao': 'TRIB.',
        'PDV': 'Pdv',
        'pdv': 'Pdv',
        'cod_pdv': 'Pdv',
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    # Validar colunas obrigatórias antes de qualquer parsing
    must_have = {'Codigo EAN', 'Pdv', 'Cupom', 'Hora', 'Quantidade', 'Valor', 'Data'}
    faltam = must_have - set(df.columns)
    if faltam:
        raise ValueError(
            f'CSV mal-formado. Faltam colunas: {faltam}. '
            f'Vistas: {sorted(df.columns)}. '
            'Verificar se o endpoint do KW mudou ou se o encoding corrompeu o header.'
        )

    df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y')
    df['Valor'] = df['Valor'].apply(parse_brnum)
    df['Quantidade'] = df['Quantidade'].apply(parse_brnum)
    df['Pdv'] = df['Pdv'].astype(int)
    df['Cupom'] = df['Cupom'].astype(int)

    if 'DESCRICAO' not in df.columns:
        df['DESCRICAO'] = ''
    if 'TRIB.' not in df.columns:
        df['TRIB.'] = ''
    if 'DEPARTAMENTO_legado' not in df.columns:
        df['DEPARTAMENTO_legado'] = None
    if 'fonte' not in df.columns:
        df['fonte'] = 'kw_incremental'

    cols = ['Codigo EAN', 'DESCRICAO', 'Pdv', 'Cupom', 'Hora',
            'Quantidade', 'Valor', 'TRIB.', 'Data',
            'DEPARTAMENTO_legado', 'fonte']
    return df[cols]


def classificar_em_cascata(base, arius, kvi):
    base['ean_clean'] = base['Codigo EAN'].apply(clean)
    base['desc_norm'] = base['DESCRICAO'].astype(str).str.strip().str.upper()
    arius['ean_clean'] = arius['EAN'].apply(clean)
    arius['cod_clean'] = arius['Código'].apply(clean)
    arius['desc_norm'] = arius['Descrição'].astype(str).str.strip().str.upper()
    kvi['cod_clean'] = kvi['COD'].apply(clean)

    def split_dept(x):
        parts = [p.strip() for p in str(x).split('/')]
        return pd.Series({
            'setor':    parts[0] if len(parts) > 0 else 'N/A',
            'subgrupo': parts[1] if len(parts) > 1 else 'N/A',
        })

    arius_expanded = arius.join(arius['DEPARTAMENTO'].apply(split_dept))
    lk_ean  = arius_expanded.drop_duplicates('ean_clean').set_index('ean_clean')[
        ['setor', 'subgrupo', 'Descrição', 'Código']]
    lk_cod  = arius_expanded.drop_duplicates('cod_clean').set_index('cod_clean')[
        ['setor', 'subgrupo', 'Descrição', 'Código']]
    lk_desc = arius_expanded.drop_duplicates('desc_norm').set_index('desc_norm')[
        ['setor', 'subgrupo', 'Descrição', 'Código']]

    all_arius_descs = sorted(arius_expanded['desc_norm'].dropna().unique())
    kw_descs = base['desc_norm'].dropna().unique()
    prefix_map = {}
    for kwd in kw_descs:
        if kwd in lk_desc.index:
            continue
        cands = [ad for ad in all_arius_descs if ad.startswith(kwd)]
        if len(cands) == 1:
            prefix_map[kwd] = cands[0]
    print(f"  Casamento por prefixo único: {len(prefix_map)} mapeados")

    def match_row(r):
        ean = r['ean_clean']
        desc = r['desc_norm']
        if ean in lk_ean.index:
            a = lk_ean.loc[ean]
            return 'EAN', a['setor'], a['subgrupo'], a['Descrição'], a['Código']
        if ean in lk_cod.index:
            a = lk_cod.loc[ean]
            return 'Código', a['setor'], a['subgrupo'], a['Descrição'], a['Código']
        if desc in lk_desc.index:
            a = lk_desc.loc[desc]
            return 'Desc exata', a['setor'], a['subgrupo'], a['Descrição'], a['Código']
        if desc in prefix_map:
            a = lk_desc.loc[prefix_map[desc]]
            return 'Prefixo', a['setor'], a['subgrupo'], a['Descrição'], a['Código']
        return 'N/A', 'N/A', 'N/A', r['DESCRICAO'], None

    print(f"  Aplicando classificação a {len(base):,} linhas...")
    matched = base.apply(match_row, axis=1, result_type='expand')
    matched.columns = ['metodo_match', 'setor', 'subgrupo', 'desc_oficial', 'cod_arius']
    v = pd.concat([base, matched], axis=1)
    v['cod_arius_str'] = v['cod_arius'].apply(lambda x: clean(x) if pd.notna(x) else None)

    kvi_by_cod = kvi.drop_duplicates('cod_clean').set_index('cod_clean')[['KVI', 'CURVA']]
    v = v.merge(kvi_by_cod, left_on='cod_arius_str', right_index=True, how='left')
    v['KVI'] = v['KVI'].fillna('-')
    v['CURVA'] = v['CURVA'].fillna('-')
    return v


def main():
    print("=" * 70)
    print("PIPELINE CONSOLIDAÇÃO · Survey Gran")
    print("=" * 70)

    if not ARIUS_FILE.exists():
        print(f"❌ Cadastro ARIUS não encontrado: {ARIUS_FILE}")
        return 1
    if not KVI_FILE.exists():
        print(f"❌ Tabela KVI não encontrada: {KVI_FILE}")
        return 1

    print(f"\nCadastros:")
    print(f"  ARIUS: {ARIUS_FILE}")
    print(f"  KVI:   {KVI_FILE}")

    arius = pd.read_excel(ARIUS_FILE)
    kvi = pd.read_excel(KVI_FILE, sheet_name='PRECIFICAÇÃO', header=1)
    print(f"  ARIUS: {len(arius):,} SKUs · KVI: {len(kvi):,} classificados")

    base_existente = _carregar_base_existente()  # v12.7: fallback pkl→parquet

    incoming_csvs = sorted(INCOMING.glob("*.csv"))
    if not incoming_csvs:
        print(f"\nNenhum CSV em {INCOMING}")
        if base_existente is None:
            print("E não há base histórica. Nada a fazer.")
            return 1
        df_concat = base_existente
    else:
        print(f"\n{len(incoming_csvs)} CSV(s) em incoming/")
        novos_dfs = []
        for csv_path in incoming_csvs:
            df, enc = carregar_csv_extracao(csv_path)
            df_norm = normalizar_extracao(df)
            print(f"    {csv_path.name}: {len(df_norm):,} linhas · "
                  f"{df_norm['Data'].min().date()} → {df_norm['Data'].max().date()} · "
                  f"R$ {df_norm['Valor'].sum():,.2f}")
            novos_dfs.append(df_norm)

        if base_existente is not None:
            df_concat = pd.concat([base_existente] + novos_dfs, ignore_index=True)
            antes = len(df_concat)
            df_concat = df_concat.drop_duplicates(
                subset=['Data', 'Pdv', 'Cupom', 'Hora', 'Codigo EAN', 'Valor'],
                keep='first').reset_index(drop=True)
            depois = len(df_concat)
            print(f"\n  Dedupe: {antes:,} → {depois:,} ({antes - depois:,} removidas)")
        else:
            df_concat = pd.concat(novos_dfs, ignore_index=True)

        df_concat = df_concat.sort_values('Data').reset_index(drop=True)

    # v12.7: backup snapshot semanal ANTES de sobrescrever (preserva versão anterior)
    _backup_snapshot()

    # v12.7: detectar gap KW (KW deletou histórico antigo). Só faz sentido se há nova
    # extração + base anterior — se primeira execução ou re-classificação sem incoming, pula
    teve_extracao = bool(incoming_csvs)
    if base_existente is not None and teve_extracao:
        _detectar_gap_kw(base_existente, df_concat)

    print(f"\nSalvando base histórica acumulada...")
    df_concat.to_pickle(BASE_FILE)
    try:
        df_concat.to_parquet(BASE_PARQUET, engine='pyarrow', compression='snappy')
        print(f"  + parquet portável salvo")
    except Exception as e:
        print(f"  (parquet skip: {e})")
    print(f"  {len(df_concat):,} linhas · {df_concat['Data'].min().date()} → {df_concat['Data'].max().date()} · "
          f"R$ {df_concat['Valor'].sum():,.2f}")

    if incoming_csvs:
        for csv_path in incoming_csvs:
            destino = PROCESSED / f"{datetime.now():%Y-%m-%d}_{csv_path.name}"
            csv_path.rename(destino)

    print(f"\nRe-classificando histórico completo...")
    base_classificada = classificar_em_cascata(df_concat, arius, kvi)

    cobertura = (base_classificada['metodo_match'] != 'N/A').sum() / len(base_classificada) * 100
    fat_coberto = (base_classificada[base_classificada['metodo_match'] != 'N/A']['Valor'].sum()
                   / base_classificada['Valor'].sum() * 100)
    print(f"  Cobertura linhas: {cobertura:.1f}% · Cobertura fat: {fat_coberto:.1f}%")

    if fat_coberto < 95:
        print(f"\n⚠️  ALERTA: cobertura abaixo de 95%. Cadastro ARIUS desatualizado.")

    primeira_data = base_classificada['Data'].min()
    delta = (primeira_data.weekday() - 2) % 7
    inicio_global = primeira_data - pd.Timedelta(days=delta)
    base_classificada['sem_id_global'] = (
        (base_classificada['Data'] - inicio_global).dt.days // 7 + 1)

    base_classificada.to_pickle(BASE_CLAS_FILE)
    try:
        base_classificada.to_parquet(BASE_CLAS_PARQUET, engine='pyarrow', compression='snappy')
    except Exception:
        pass
    print(f"\nBase classificada salva: {len(base_classificada):,} linhas · "
          f"{base_classificada['sem_id_global'].nunique()} semanas")

    print(f"\n{'=' * 70}")
    print("Consolidação concluída.")
    print(f"{'=' * 70}\n")
    return 0


# v12.7: helpers de robustez ===================================================

def _carregar_base_existente():
    """Tenta pkl primeiro, fallback para parquet (mais portável entre versões pandas)."""
    if BASE_FILE.exists():
        try:
            df = pd.read_pickle(BASE_FILE)
            df['Data'] = pd.to_datetime(df['Data'])
            print(f"\nBase histórica (pkl): {len(df):,} linhas · "
                  f"{df['Data'].min().date()} → {df['Data'].max().date()}")
            return df
        except Exception as e:
            print(f"\n⚠️  pkl falhou ({type(e).__name__}). Tentando parquet...")
    if BASE_PARQUET.exists():
        try:
            df = pd.read_parquet(BASE_PARQUET)
            df['Data'] = pd.to_datetime(df['Data'])
            print(f"\nBase histórica (parquet): {len(df):,} linhas · "
                  f"{df['Data'].min().date()} → {df['Data'].max().date()}")
            return df
        except Exception as e:
            print(f"⚠️  parquet falhou ({type(e).__name__}).")
    print(f"\nPrimeira execução ou pkl/parquet ilegíveis: base será criada do zero")
    return None


def _detectar_gap_kw(base_old, base_concat):
    """v12.7: alerta se KW perdeu dados antigos. Calibrado em S18/2026 quando KW
    deletou silenciosamente set/2024-abr/2025."""
    if base_old is None or len(base_old) == 0:
        return
    old_min = pd.to_datetime(base_old['Data']).min()
    new_min = pd.to_datetime(base_concat['Data']).min()
    if new_min > old_min + pd.Timedelta(days=30):
        print(f"\n⚠️  ALERTA — KW pode ter perdido dados antigos:")
        print(f"     Base anterior tinha desde {old_min.date()}")
        print(f"     Base atual começa em {new_min.date()}")
        print(f"     Diferença: {(new_min - old_min).days} dias")
        print(f"     Recomendo: abrir ticket SUPORTE KW + restaurar de backup em {BACKUP_DIR}")


def _backup_snapshot():
    """v12.7: snapshot semanal antes de sobrescrever — protege contra perda silenciosa."""
    from datetime import datetime
    if not BASE_FILE.exists():
        return
    snap_dir = BACKUP_DIR / datetime.now().strftime('%Y-%m-%d')
    snap_dir.mkdir(parents=True, exist_ok=True)
    import shutil
    for f in [BASE_FILE, BASE_CLAS_FILE, BASE_PARQUET, BASE_CLAS_PARQUET]:
        if f.exists():
            shutil.copy2(f, snap_dir / f.name)
    # Manter só 8 últimos snapshots (~2 meses)
    snaps = sorted(BACKUP_DIR.iterdir())
    for old in snaps[:-8]:
        if old.is_dir():
            shutil.rmtree(old)
    print(f"\n  Backup snapshot salvo em {snap_dir.name}")


if __name__ == '__main__':
    import sys
    sys.exit(main())
