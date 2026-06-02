# Manual RHID e Escala — Skill Monitoramento de Jornada

Resumo operacional do RHID e da escala mensal pro Claude executar a skill. Manual completo em `[A7] Fábrica de Skills/Manual_RHID_e_Escala_v3.md`.

---

## Acesso ao RHID

```
URL: https://www.rhid.com.br/v2/#/login
Email: rhid@grupoa7.com.br  (em .env como RHID_USER)
Senha: rhid@12345            (em .env como RHID_PASS)
Tipo: usuário/senha. Sem 2FA.
```

**NUNCA** logar credenciais em mensagens visíveis ou commits.

### Tratamento de sessão expirada

Quando aparece modal "Tempo de sessão expirado, faça login novamente":
1. Clicar OK
2. Os campos email/senha geralmente já vêm preenchidos pelo gerenciador do navegador
3. Clicar Entrar (talvez 2x)
4. Aguardar 5s redirect pra `/dashboard`

A skill deve detectar esse modal antes de qualquer ação crítica.

---

## Fluxo principal — gerar Cartão de Ponto da semana

### Passo 1 — Login
```
1. mcp__Claude_in_Chrome__tabs_context_mcp({ createIfEmpty: true })
2. navigate → https://www.rhid.com.br/v2/#/login
3. Aguardar 3s
4. Detectar modal sessão expirada → clicar OK se houver
5. Clicar Entrar (campos pré-preenchidos)
6. Aguardar 5s redirect
```

### Passo 2 — Configurar Cartão de Ponto

```
1. navigate → https://www.rhid.com.br/v2/#/processamento_folha
2. Aguardar 3s
3. Setar datas via JS:
     document.querySelectorAll('input[type=date]')[0].value = 'YYYY-MM-DD'  // quarta anterior
     document.querySelectorAll('input[type=date]')[1].value = 'YYYY-MM-DD'  // terça
     ds[0].dispatchEvent(new Event('change',{bubbles:true}))
     ds[1].dispatchEvent(new Event('change',{bubbles:true}))
4. Funcionários: deixar em "Ativos" (radio padrão) — NÃO mudar pra Todos exceto pra reconciliação histórica
5. Empresa: deixar VAZIO (puxa Gran + GRSM juntos)
6. Clicar campo "Formato de Saída" → escolher HTML
7. Clicar Processar
8. Aguardar 10-15s
9. Modal "Dados enviados pra cálculo: N pessoas" → clicar OK
```

### Passo 3 — Capturar GUID e abrir relatório

```
1. navigate → https://www.rhid.com.br/v2/#/list_process
2. Aguardar 3s
3. Capturar GUID do primeiro item da tabela (Cartão de ponto mais recente):
     const link = document.querySelector('table tbody tr:first-child a[ng-click]')
     const guid = link.getAttribute('ng-click').match(/'([a-f0-9-]+)'/)[1]
4. Criar nova aba e navegar pra:
     https://www.rhid.com.br/v2/reporthtml.html#/html/{guid}
5. Aguardar 8s pelo render completo
```

### Passo 4 — Extrair os N cartões

**Descoberta crítica:** todos os cartões já estão no DOM (mais de 100 tables) — não precisa iterar via clique no `>`.

```javascript
const allTables = Array.from(document.querySelectorAll('table'));
const cartoes = [];
for (let i = 0; i < allTables.length; i++) {
  const t = allTables[i];
  const txt = t.textContent.replace(/\s+/g,' ').trim();
  // Anchor: tabela com 1 linha contendo só "Nome do funcionário: X"
  if (txt.startsWith('Nome do funcion') && t.querySelectorAll('tr').length === 1) {
    const m = txt.match(/Nome do funcion[^:]*:\s*(.+)$/);
    const nome = m ? m[1].trim() : '?';
    // Tabela de dados: próxima com "Total Trabalhado"
    let principal = null;
    for (let j = i+1; j < Math.min(i+5, allTables.length); j++) {
      if (allTables[j].textContent.includes('Total Trabalhado')) {
        principal = allTables[j]; break;
      }
    }
    if (principal) {
      const rows = Array.from(principal.querySelectorAll('tr')).map(tr =>
        Array.from(tr.querySelectorAll('td,th')).map(c => c.textContent.trim())
      );
      cartoes.push({nome, rows});
    }
  }
}
window.__cartoes = cartoes;
```

**Estrutura de cada cartão:**
- `rows[0]` = cabeçalho (DIA, Previsto, ENT.1, SAÍ.1, ENT.2, SAÍ.2, ENT.3, SAÍ.3, ...)
- `rows[1..N]` = um por dia da semana (DD/MM/AAAA - DOM/SEG/...)
- `rows[N+1]` = TOTAIS

Cada linha de dia tem ~30 colunas. As essenciais (índices podem variar):
- col 0: Data + dia da semana
- col 2: Previsto (ex: "07:00-12:30\n13:30-15:20")
- cols 4-9: ENT.1, SAÍ.1, ENT.2, SAÍ.2, ENT.3, SAÍ.3
- (resto: Total Normais, Total Trabalhado, Intervalo, etc.)

### Passo 5 — Dump pro sandbox

Como `read_console_messages` corta em ~50KB, dump em batches:

```javascript
// Salvar em formato compacto: ${TAG}{idx}#{nome}§{linha1}§{linha2}§...
// Cada linha de dia: data@previsto@ENT.1@SAÍ.1@ENT.2@SAÍ.2@ENT.3@SAÍ.3
const TAG = 'WK';
window.__cartoes.forEach((c, idx) => {
  const linhas = [c.nome];
  c.rows.slice(1, 1+7).forEach(row => {
    const compact = [row[0], row[2]||'', row[4]||'', row[5]||'',
                     row[6]||'', row[7]||'', row[8]||'', row[9]||''].join('@');
    linhas.push(compact);
  });
  console.log(`${TAG}${idx}#${linhas.join('§')}`);
});
```

Ler do console com pattern `^WK{N}#` em batches de 10-15 cartões.

### Passo 6 — Limitação de fetch direto

⚠️ **NÃO tentar** fetch direto em `/v2/customerdb/notify.svc/save_file/?format=...&guid=...`:
- POST retorna 200 vazio
- GET retorna 405

Sempre usar formato HTML que abre em nova aba.

---

## Estrutura da escala mensal (PDF)

A escala vem em PDF tabular. Pra cada mês:
- 9 setores como cabeçalhos (ENCARREGADOS, OPERADOR DE LOJA, etc.)
- 1 linha por colaborador
- 1 célula por dia do mês

Ver `setores_e_classificacao.md` pra códigos (`F`, `FF`, `FD`, `Férias`, `BH`).

### Parser do PDF

A skill usa `pdfplumber` ou `pypdf` pra extrair texto. Estrutura esperada:

```
ENCARREGADOS  01/mai 02/mai 03/mai ...
Alyne Bittencourt  07:40-19:20  06:10-14:30  F  ...
Silvio Rouzan  FF  13:00-21:20  07:40-19:20  ...
```

A célula com `\n` (ex: "07:00-12:30\n13:30-15:20") indica jornada com 2 períodos. Skill normaliza pra entender ENT-SAÍ-ENT-SAÍ.

Implementação no `scripts/parsear_escala.py`.

---

## Cálculo do período da semana

A skill roda toda quarta. O período do relatório é **quarta-anterior até terça**.

```python
import datetime
hoje = datetime.date.today()
# Voltar até a quarta passada
dias_da_quarta = (hoje.weekday() - 2) % 7  # 2 = quarta
if dias_da_quarta == 0: dias_da_quarta = 7
quarta_anterior = hoje - datetime.timedelta(days=dias_da_quarta)
terca = quarta_anterior + datetime.timedelta(days=6)
# período = quarta_anterior a terca
```

Exemplo: se hoje é quarta 13/05/2026 → período = qua 06/05 a ter 12/05.

---

## Tratamento de erros

| Sintoma | Causa | Ação |
|---|---|---|
| Modal "Sessão expirada" | Inatividade | Re-logar |
| "Dados enviados pra cálculo: 0 pessoas" | Filtro errado | Conferir Empresa em branco e Ativos marcado |
| HTML aberto vazio | Render incompleto | Aguardar +5s e re-extrair |
| `read_console_messages > 50KB` | Output muito grande | Dump em batches menores |
| Aba Chrome trava | Patch fetch interceptando | Fechar aba, abrir nova, evitar interceptação fetch |
| GUID não aparece em /list_process | Processamento ainda rodando | Aguardar +10s e refresh |

---

## Outros relatórios úteis (pra rodadas futuras)

- **Relatório de Afastamentos** (`/v2/#/relatorio_afastamentos`) — atestados/férias/licenças por período. Útil pra excluir falta seca quando há justificativa.
- **Relatório de Ocorrências** (`/v2/#/relatorio_ocorrencias`) — eventos genéricos com Tipo de Justificativa.
- **Alterações de Ponto** (`/v2/#/alteracoes_ponto`) — log de batidas inseridas manualmente (importante pra distinguir batida real de correção pelo gestor).

---

**Sempre que algo no RHID mudar, atualizar este arquivo e notificar Hugo.**
