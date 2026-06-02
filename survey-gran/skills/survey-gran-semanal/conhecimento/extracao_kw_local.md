# Extração KW · Caminho A: Chrome MCP local (v2 — calibrado em S18/2026)

**Quando usar:** Hugo está na rede local da loja Gran (Wi-Fi/cabo do prédio). Confirmação automática: tentar fetch para `http://192.168.1.150/sistema/principal.php` — se 200, está na rede.

## Endpoint correto (CRÍTICO — calibrado em S18/2026)

```
http://192.168.1.150/ferramentas/relatorios/lista_mercadorias_vendidas/selecaocsv.php?dataproc_i=DD%2FMM%2FAAAA&dataproc_f=DD%2FMM%2FAAAA&slct_pdv=&cupom=&slct_tributacao=&a_partir_de=&ean=&csv=1&offset=&hpagina=
```

**Pontos de atenção:**
- `http` (não `https`) — IP local
- **SEM** prefix `/sistema/` no path do endpoint (path antigo `/sistema/ferramentas/...` retorna 404)
- `&csv=1` é o que faz a saída ser tabela exportável
- Saída: **HTML com `<table>`** (não CSV puro). Encoding `windows-1252`.

## Workflow operacional via Chrome MCP

### Fase 0 · Sanity check de rede + autenticação

```javascript
// 1. Conferir conectividade + autenticação
const r = await fetch('http://192.168.1.150/sistema/principal.php', {credentials: 'include'});
const url = r.url;
// Se url terminou em /index.php OU body.innerText contém "Autenticação" → não logado
```

Se não logado: **PARAR** e pedir Hugo logar manualmente no Chrome (não preencher senha programaticamente).

### Fase 1 · Definir janela

- `ultima_data_base` = última data em `base_classificada.pkl` (ou `.parquet`).
- `inicio` = `ultima_data_base + 1 dia` (em formato DD/MM/AAAA).
- `fim` = última terça-feira anterior a hoje.
- **Particionar em janelas de 15 dias máximo** (NÃO 30 dias — calibrado: mensal estoura timeout silenciosamente, retorna HTML vazio).

### Fase 2 · Fetch via JavaScript no Chrome

```javascript
const BASE = 'http://192.168.1.150/ferramentas/relatorios/lista_mercadorias_vendidas/selecaocsv.php';
const url = BASE + '?dataproc_i=' + encodeURIComponent(ini)
          + '&dataproc_f=' + encodeURIComponent(fim)
          + '&slct_pdv=&cupom=&slct_tributacao=&a_partir_de=&ean=&csv=1&offset=&hpagina=';

const r = await fetch(url, {credentials: 'include'});
const buf = await r.arrayBuffer();
const text = new TextDecoder('windows-1252').decode(buf);  // CRÍTICO: latin1, não utf-8

const doc = new DOMParser().parseFromString(text, 'text/html');
const tables = doc.querySelectorAll('table');
if (tables.length === 0) {
  // HTML vazio = janela sem dados OU timeout silencioso
  return {janela, status: 'vazio', mb: (buf.byteLength/1048576).toFixed(2)};
}
const rows = tables[tables.length-1].querySelectorAll('tr');
const header = Array.from(rows[0].querySelectorAll('th, td')).map(c => c.textContent.trim());
const dataRows = Array.from(rows).slice(1).map(tr => Array.from(tr.querySelectorAll('td')).map(td => td.textContent.trim()));
```

**Header esperado** (9 colunas):
```
Codigo EAN; Descrição; Pdv; Cupom; Hora; Quantidade; Valor; Tributação; Data
```

### Fase 3 · Agregar e disparar download

```javascript
// Agregar todas as janelas em uma string CSV (separator ;)
const sep = ';';
const csv = [header.join(sep), ...allRows.map(r => r.join(sep))].join('\n');
window.__BASE_CSV__ = csv;

// Disparar download programático
const blob = new Blob([csv], {type: 'text/csv;charset=utf-8'});
const a = document.createElement('a');
a.href = URL.createObjectURL(blob);
a.download = `${ini.replace(/\//g,'-')}_a_${fim.replace(/\//g,'-')}.csv`;
document.body.appendChild(a);
a.click();
setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
```

Arquivo cai em `~/Downloads/`.

### Fase 4 · Mover de Downloads para `incoming/` via Finder

`~/Downloads/` NÃO está montado no sandbox do Cowork. Usar `mcp__computer-use` (Finder em tier full):

```
1. open_application Finder
2. cmd+shift+g → "~/Downloads"
3. left_click no arquivo (linha do CSV)
4. cmd+c
5. cmd+shift+g → "~/Documents/Claude/Projects/[GRAN] Survey/data/extracoes/incoming/"
6. cmd+alt+v  (move, não copy)
7. validar via bash: ls /sessions/.../incoming/
```

### Fase 5 · Validação de volume

| PDVs ativos | Linhas/dia | Cupons/dia | Fat/dia |
|---|---|---|---|
| 1 PDV (101 ou 102 sozinho) | 600–1.000 | 150–250 | R$ 7k–13k |
| 2 PDVs (101+102) | 1.000–1.700 | 240–360 | R$ 11k–19k |
| 3 PDVs | 1.200–1.800 | 280–400 | R$ 14k–21k |

**PDV 103 é esporádico por padrão operacional** — não gerar alerta se ausente. Alerta apenas se TODOS os 3 estiverem ausentes em dia útil.

PARAR se:
- ≥3 dias consecutivos zerados (e não são feriados)
- Faturamento total < 60% do mínimo esperado
- Header da tabela diferente do esperado

## Tratamento de erros

| Erro | O que fazer |
|---|---|
| Status ≠ 200 | PARAR, verificar conectividade |
| Redirect para `/index.php` | PARAR, pedir Hugo logar |
| `tables.length === 0` em janela mensal | RETRY com janela quinzenal |
| Encoding com caracteres ��� | Confirmar `TextDecoder('windows-1252')` |
| Total da janela vazio mas datas existem na base antiga | KW deletou histórico — fazer backup pkl/parquet, abrir ticket SUPORTE KW |

## Detecção automática de gap KW (NOVO — calibrado em S18/2026)

Antes de cada rodada, comparar `df_old["Data"].min()` (de backup) com `df_new["Data"].min()` (re-extração):

```python
if df_new['Data'].min() > df_old['Data'].min() + pd.Timedelta(days=30):
    print(f'⚠️  KW PERDEU DADOS: backup tinha desde {df_old["Data"].min().date()}, '
          f'KW retorna desde {df_new["Data"].min().date()}. '
          f'Restaurando de backup. Abrir ticket SUPORTE KW.')
    # Mesclar OLD (antes do cutoff) + NEW (a partir do cutoff)
```

## Endpoint legado (DEPRECATED — não usar)

O skill v0.12 e anteriores tinha `https://<DOMINIO>/sistema/ferramentas/relatorios/lista_mercadorias_vendidas/selecaocsv.php` com `browser_cookie3`. **Esse caminho NÃO funciona** porque:
1. KW está em IP local (192.168.1.150), não domínio HTTPS
2. Path `/sistema/` retorna 404 para o endpoint
3. `browser_cookie3` requer Python no Mac com pandas+requests, frágil e exige config

Substituído por Chrome MCP (este documento).
