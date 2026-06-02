# Extração KW · Caminho B: AnyDesk + Python na SAMSUNG

**Quando usar:** Hugo respondeu "não, estou fora da rede do KW" na pergunta da FASE 2 do `SKILL.md`.

## Pré-requisitos

- Conta AnyDesk acessível.
- Acesso à SAMSUNG (ID `305817889`, senha `TIRAPREÇO`).
- Chrome aberto com KW autenticado na SAMSUNG.
- Python 3.8+ instalado na SAMSUNG.
- Domínio do KW conhecido (ver Fase 4).

**ANTES DE COMEÇAR:** ler `conhecimento/manual_anydesk.md` (manual completo, não-stub).

## Domínio do KW

O domínio é estável. Está armazenado no arquivo `conhecimento/dominio_kw.txt` da skill (uma linha só). Se o arquivo não existir ou estiver vazio:

1. Inspecionar a aba Chrome do KW na SAMSUNG (clicar na URL bar).
2. Copiar o domínio (sem `https://`, sem path).
3. Perguntar Hugo: "Confirmo o domínio do KW como `<X>` antes de prosseguir?"
4. Após confirmar, gravar em `conhecimento/dominio_kw.txt` para evitar redescobrir nas próximas execuções.

Nunca chutar. Domínio errado = todos os requests retornam HTML genérico ou erro 404.

## Workflow

### Fase 1 · Conectar AnyDesk

Seguir `conhecimento/manual_anydesk.md` (Conexão padrão). Se a conexão falhar e Hugo não conseguir resolver fisicamente, **PARAR**.

### Fase 2 · Verificar Chrome e KW na SAMSUNG

1. Tirar screenshot da SAMSUNG via AnyDesk.
2. Confirmar Chrome aberto com aba KW.
3. Confirmar visualmente sessão ativa (nome do usuário visível no canto do KW).

Se a sessão expirou (login screen no Chrome): **PARAR**, pedir Hugo logar manualmente via AnyDesk, retomar.

### Fase 3 · Verificar Python e bibliotecas

Abrir cmd na SAMSUNG (Win+R → cmd → Enter):

```cmd
python --version
```

Aceitar ≥3.8. Se não houver Python:

```cmd
py --version
python3 --version
```

Se nenhum funcionar: **PARAR** e pedir Hugo instalar Python 3.11 (preferência) de https://python.org. Não tentar instalar Python via cmd silenciosamente.

Instalar bibliotecas (em qualquer Python ≥3.8 que tiver respondido):

```cmd
pip install --user requests pandas openpyxl browser-cookie3
```

Se erro de permissão, usar `--user`. Se antivírus bloquear, **PARAR** e avisar Hugo.

### Fase 4 · Descobrir paths e domínio

```cmd
echo %USERNAME%
```

Anotar `<USERNAME>`. Caminho da pasta de trabalho: `C:\Users\<USERNAME>\Downloads\`.

Se a pasta Downloads estiver sincronizada com OneDrive, ela pode estar redirecionada para `C:\Users\<USERNAME>\OneDrive\Downloads\`. Use:

```python
from pathlib import Path
DOWNLOADS = Path.home() / 'Downloads'
DOWNLOADS.mkdir(exist_ok=True)
```

Em vez de hardcoded path. Isso funciona com OneDrive, redirecionamento, e contas corporativas.

### Fase 5 · Script de extração

Criar `C:\Users\<USERNAME>\Downloads\extrair_kw.py` na SAMSUNG. Editar `DOMINIO_KW` e `JANELAS` antes de rodar.

```python
import browser_cookie3, requests, pandas as pd, sys, time
from pathlib import Path

# ============================================================
# CONFIGURAR ANTES DE RODAR
# ============================================================
DOMINIO_KW = 'CONFIRMADO_COM_HUGO'   # ex: 'kw.exemplo.com.br'
JANELAS = [
    ('DD/MM/AAAA', 'DD/MM/AAAA'),
    # adicionar mais se janela total >30 dias (limite KW)
]

# ============================================================
# Pasta de trabalho — robusto a OneDrive
# ============================================================
DOWNLOADS = Path.home() / 'Downloads'
DOWNLOADS.mkdir(exist_ok=True)

URL_CSV = f'http://{DOMINIO_KW}/ferramentas/relatorios/lista_mercadorias_vendidas/selecaocsv.php'
URL_HTML = f'http://{DOMINIO_KW}/ferramentas/relatorios/lista_mercadorias_vendidas/selecao.php'
# v12.7 nota: protocolo é HTTP (não HTTPS) — KW está em rede local na SAMSUNG.
# Default DOMINIO_KW = '192.168.1.150' (IP fixo da retaguarda).

# ============================================================
# Capturar cookies — assert que jar não está vazio
# ============================================================
cj = browser_cookie3.chrome(domain_name=DOMINIO_KW)
n_cookies = sum(1 for _ in cj)
if n_cookies == 0:
    sys.exit(
        'COOKIE JAR VAZIO. Causas comuns:\n'
        '  - Chrome aberto e bloqueando leitura (fechar Chrome e reabrir)\n'
        '  - browser_cookie3 desatualizado (pip install -U browser-cookie3)\n'
        '  - Antivírus bloqueando acesso ao SQLite do Chrome\n'
        '  - DOMINIO_KW errado'
    )
print(f'Cookies capturados: {n_cookies}')

session = requests.Session()
session.cookies = cj

# ============================================================
# Teste de autenticação (1 dia, request leve)
# ============================================================
test_dia = JANELAS[0][0]
test_params = {
    'offset': '0', 'hpagina': '1',
    'dataproc_i': test_dia, 'dataproc_f': test_dia,
    'slct_pdv': '', 'cupom': '', 'slct_tributacao': '',
    'a_partir_de': '', 'ean': '',
    'consultar': 'Consultar', 'csv': '',
}
r = session.get(URL_CSV, params=test_params, timeout=60)
if r.status_code != 200:
    sys.exit(f'Status {r.status_code} no teste — sessão expirada ou domínio errado')
if 'login' in r.url.lower() or 'autenticacao' in r.url.lower():
    sys.exit('Redirect para login — Hugo precisa relogar no Chrome')
if r.content[:1] == b'<':
    print('Endpoint /selecaocsv.php retornou HTML — usando /selecao.php paginado em vez disso')
    URL_USE = URL_HTML
    PAGINADO = True
else:
    URL_USE = URL_CSV
    PAGINADO = False
print(f'Auth OK. Endpoint: {URL_USE}')
time.sleep(2)  # leve pause antes de extração real

# ============================================================
# Função de extração com fallback de timeout
# ============================================================
def extrair_janela(ini, fim, timeout=120):
    params = {
        'offset': '0', 'hpagina': '1',
        'dataproc_i': ini, 'dataproc_f': fim,
        'slct_pdv': '', 'cupom': '', 'slct_tributacao': '',
        'a_partir_de': '', 'ean': '',
        'consultar': 'Consultar', 'csv': '',
    }
    try:
        r = session.get(URL_USE, params=params, timeout=timeout)
        r.raise_for_status()
        return r.content
    except requests.Timeout:
        # Partir em duas janelas
        from datetime import datetime, timedelta
        d1 = datetime.strptime(ini, '%d/%m/%Y')
        d2 = datetime.strptime(fim, '%d/%m/%Y')
        meio = d1 + (d2 - d1) // 2
        ini1, fim1 = ini, meio.strftime('%d/%m/%Y')
        ini2 = (meio + timedelta(days=1)).strftime('%d/%m/%Y')
        fim2 = fim
        print(f'Timeout em {ini}-{fim}. Partindo em {ini1}-{fim1} + {ini2}-{fim2}')
        b1 = session.get(URL_USE, params={**params, 'dataproc_i':ini1,'dataproc_f':fim1}, timeout=timeout).content
        b2 = session.get(URL_USE, params={**params, 'dataproc_i':ini2,'dataproc_f':fim2}, timeout=timeout).content
        # Concatenar — segundo CSV sem header
        return b1 + b'\n' + b2.split(b'\n', 1)[1]

# ============================================================
# Loop de janelas
# ============================================================
for ini, fim in JANELAS:
    print(f'\nExtraindo {ini} → {fim}')
    payload = extrair_janela(ini, fim)

    # Detectar encoding: utf-8-sig → utf-8 → windows-1252
    text = None
    for enc in ['utf-8-sig', 'utf-8', 'windows-1252']:
        try:
            cand = payload.decode(enc)
            # Heurística: deve ter 'Codigo EAN' ou similar nas primeiras 500 chars
            if 'EAN' in cand[:500] or 'Pdv' in cand[:500]:
                text = cand
                print(f'  Encoding: {enc}')
                break
        except UnicodeDecodeError:
            continue
    if text is None:
        sys.exit(f'  Não consegui decodificar {ini}-{fim}')

    fname = f'{ini.replace("/","-")}_a_{fim.replace("/","-")}.csv'
    out_cache = DOWNLOADS / fname
    out_cache.write_text(text, encoding='utf-8')
    print(f'  Salvo em cache: {out_cache} ({out_cache.stat().st_size/1024:.1f} KB)')
    time.sleep(2)

print('\nExtração concluída. Próximo: validar e transferir pro Mac (Fase 6).')
```

### Fase 6 · Validação na SAMSUNG (antes de transferir)

```python
import pandas as pd
from pathlib import Path
import sys

DOWNLOADS = Path.home() / 'Downloads'
csvs = sorted(DOWNLOADS.glob('*_a_*.csv'))

for csv_path in csvs:
    print(f'\n=== Validando {csv_path.name} ===')
    df = pd.read_csv(csv_path, sep=';', dtype=str, encoding='utf-8')

    # Colunas obrigatórias
    must_have = {'Codigo EAN','Pdv','Cupom','Hora','Quantidade','Valor','Data'}
    faltam = must_have - set(df.columns)
    if faltam:
        sys.exit(f'  FALTAM colunas: {faltam}. Colunas vistas: {list(df.columns)}')

    # PDVs presentes
    pdvs = sorted(df['Pdv'].astype(int).unique())
    print(f'  PDVs: {pdvs}')

    # Volume
    n_lin = len(df)
    n_cup = df.groupby(['Pdv','Cupom']).ngroups
    fat = pd.to_numeric(df['Valor'].str.replace(',','.'), errors='coerce').sum()
    print(f'  Linhas: {n_lin:,}  Cupons: {n_cup:,}  Fat: R$ {fat:,.2f}')

    # Dias presentes vs esperados
    df['Data_dt'] = pd.to_datetime(df['Data'], format='%d/%m/%Y', errors='coerce')
    dias_data = sorted(df['Data_dt'].dt.date.unique())
    print(f'  Dias com registro: {len(dias_data)}')

    # Duplicatas (informativo — pipeline_consolidacao deduplica depois)
    dup = df.duplicated(subset=['Data','Pdv','Cupom','Hora','Codigo EAN','Valor']).sum()
    print(f'  Duplicatas exatas: {dup}')

    # Sanity check: faturamento mínimo razoável
    n_dias = len(dias_data) or 1
    fat_dia = fat / n_dias
    if fat_dia < 8000:
        print(f'  ⚠️  ALERTA: faturamento médio diário R$ {fat_dia:,.2f} abaixo de R$ 8.000 — provavelmente extração incompleta')
```

### Fase 7 · Transferir pro Mac

Ver `manual_anydesk.md` seção "Transferência de arquivos SAMSUNG → Mac".

Destino final no Mac: `~/Documents/SurveyGran/extracoes/incoming/`. Não renomear — manter o padrão `DD-MM-AAAA_a_DD-MM-AAAA.csv` que o `pipeline_consolidacao.py` lê.

### Fase 8 · Validação no Mac (pré-pipeline)

Idêntica à Fase 6, mas adicionar:

- **Dias zerados consecutivos**: se ≥3 dias da janela esperada não aparecem, **PARAR** e perguntar Hugo. Não é feriado se for jan/fev/mar — checar `feriados_2025_2026.md`.
- **Volume esperado por janela** (calibrado com 3 PDVs ativos a partir de 26/01/2026):

| PDVs ativos na janela | Linhas/dia | Cupons/dia | Fat/dia |
|---|---|---|---|
| 2 PDVs (101, 102 — antes de 26/01/2026) | 1.000–1.700 | 240–360 | R$ 11k–19k |
| 3 PDVs (101, 102, 103 — desde 26/01/2026) | 1.200–1.800 | 280–400 | R$ 14k–21k |

Se fora da faixa: alertar Hugo, mas só **PARAR** se total da janela < 60% do mínimo esperado.

### Fase 9 · Continuar fluxo

Voltar ao `SKILL.md`, FASE 3 — rodar `pipeline_consolidacao.py` no Mac.

## Mecanismos de PARAR no Cowork

Quando este caminho exigir que o Cowork pare e pergunte Hugo, **NÃO** usar `print()` simples na sessão remota — o output do Python local na SAMSUNG não chega ao chat do Cowork.

Usar uma das três formas:

1. **AskUserQuestion via Cowork** (preferência) — Cowork pausa e pergunta no chat.
2. **Levantar exceção clara**: `sys.exit('PARAR: <motivo>. Pedir Hugo: <ação>.')` — Cowork captura o erro e expõe.
3. **Salvar marker file**: criar `~/Downloads/PARAR_<motivo>.txt` que sinaliza o estado pra próximas etapas.

## Tratamento de erros (resumo)

| Erro | O que fazer |
|---|---|
| Cookie jar vazio | PARAR. Mensagem com 4 causas comuns. |
| Status ≠ 200 | PARAR. Reportar status e URL. |
| Redirect para login | PARAR. Pedir Hugo relogar via AnyDesk. |
| Response com HTML em vez de CSV | Tentar endpoint alternativo (`selecao.php` paginado). |
| Timeout | Auto-partir janela em 2. Se ainda timeout, PARAR. |
| Encoding falha em todos | PARAR. Salvar bytes brutos pra análise manual. |
| ≥3 dias consecutivos zerados | PARAR. Perguntar Hugo. |
| Faturamento médio < R$ 8k/dia | ALERTAR (não-bloqueante), prosseguir. |
| Faturamento total < 60% esperado | PARAR. Perguntar Hugo. |
| AnyDesk caiu no meio | Reconectar. SAMSUNG mantém estado do Python. |
