# Recovery de pkl com StringDtype incompatível (último recurso)

## Quando usar

`pd.read_pickle()` falha com `NotImplementedError` mencionando `<StringDtype(storage='python', na_value=nan)>` ou `NDArrayBacked.__setstate__`.

**Causa**: o pkl foi salvo com versão de pandas onde StringDtype tinha `na_value` parameter; versão atual rejeita. `NDArrayBacked` é Cython type (immutable) — não dá para monkey-patch direto.

## Solução: capturar blocks + reconstruir DataFrame manualmente

```python
import pandas as pd
import pickle
import numpy as np
from pandas.core.arrays.string_ import StringArray, StringDtype
from pandas.core.arrays.datetimes import DatetimeArray
from pandas._libs.arrays import NDArrayBacked

# 1. Patch StringDtype.__init__ para aceitar na_value sem erro
_orig_sd_init = StringDtype.__init__
StringDtype.__init__ = lambda s, storage=None, na_value=None: _orig_sd_init(s, storage=storage)

# 2. Subclasses tolerantes
class _CompatStrArr(StringArray):
    def __setstate__(self, state):
        if isinstance(state, tuple) and len(state) == 2:
            dt, arr = state
            arr_obj = np.asarray(arr, dtype=object)
            if arr_obj.ndim == 2 and arr_obj.shape[0] == 1:
                arr_obj = arr_obj.ravel()
            NDArrayBacked.__init__(self, arr_obj, StringDtype(storage='python'))
            return
        super().__setstate__(state)

class _CompatDateArr(DatetimeArray):
    def __setstate__(self, state):
        if isinstance(state, tuple) and len(state) == 2:
            dt, arr = state
            arr_ns = arr.astype('datetime64[ns]') if arr.dtype != np.dtype('datetime64[ns]') else arr
            if arr_ns.ndim == 2 and arr_ns.shape[0] == 1:
                arr_ns = arr_ns.ravel()
            NDArrayBacked.__init__(self, arr_ns, np.dtype('datetime64[ns]'))
            return
        super().__setstate__(state)

# 3. Capturar blocks + axes via monkey-patch (REVERTER ao final!)
_blocks, _axes = [], []

import pandas._libs.internals as internals_mod
_ORIG_UB = internals_mod._unpickle_block
def _capture_ub(values, placement, ndim):
    _blocks.append({'values': values, 'placement': placement})
    return _ORIG_UB(values, placement, ndim)

import pandas.core.indexes.base as idx_mod
_ORIG_NEW = idx_mod._new_Index
def _capture_new(*a, **k):
    o = _ORIG_NEW(*a, **k); _axes.append(o); return o

internals_mod._unpickle_block = _capture_ub
idx_mod._new_Index = _capture_new

class CompatUnpickler(pickle.Unpickler):
    def find_class(self, m, n):
        c = super().find_class(m, n)
        if c is StringArray: return _CompatStrArr
        if c is DatetimeArray: return _CompatDateArr
        return c

# 4. Load (vai falhar no BlockManager mas captura tudo)
try:
    with open('base_historica.pkl', 'rb') as f:
        CompatUnpickler(f).load()
except Exception:
    pass

# 5. RESTAURAR monkey-patches (CRÍTICO — senão polui pickle.dump)
internals_mod._unpickle_block = _ORIG_UB
idx_mod._new_Index = _ORIG_NEW

# 6. Reconstruir DataFrame manualmente
cols = next(list(a) for a in _axes if len(a) == 12)  # ajustar 12 = nº colunas esperado
data = {}
for b in _blocks:
    p = b['placement']
    p_idx = list(range(p.start, p.stop, p.step or 1)) if isinstance(p, slice) else list(p)
    v = b['values']
    raw = v._ndarray if hasattr(v, '_ndarray') else v
    if raw.ndim == 2:
        if raw.shape[0] == 1:
            data[cols[p_idx[0]]] = raw.ravel()
        else:
            for j, cp in enumerate(p_idx):
                data[cols[cp]] = raw[j]
    else:
        data[cols[p_idx[0]]] = raw

df = pd.DataFrame(data)
df['Data'] = pd.to_datetime(df['Data'])
for c in ['Codigo EAN','DESCRICAO','Hora','TRIB.','fonte','DEPARTAMENTO_legado']:
    if c in df.columns:
        df[c] = df[c].astype(str)

# 7. Salvar como pkl LIMPO + parquet (backup portável)
df.to_pickle('base_historica.pkl')
df.to_parquet('base_historica.parquet', engine='pyarrow', compression='snappy')
```

## Validação

Aplicado em S18/2026 com sucesso: 752.394 linhas, 12 colunas (incluindo `ano_mes` derivada), datas 09/09/2024 → 28/04/2026, fat R$ 10,14M.
