#!/usr/bin/env python3
"""
extrair_cartao.py — Guia pro Claude executar Chrome MCP

Este script NÃO roda standalone. É um manual de execução pra Claude seguir
quando precisar extrair Cartão de Ponto do RHID via Chrome MCP.

Resumo do fluxo: ver references/manual_rhid_e_escala.md (seções "Acesso",
"Fluxo principal — gerar Cartão de Ponto da semana", "Limitação de fetch direto").

================================================================================
RECIPE (Claude segue):
================================================================================

# 1) Setup
mcp__Claude_in_Chrome__tabs_context_mcp({ createIfEmpty: True })

# 2) Login
navigate(url="https://www.rhid.com.br/v2/#/login", tabId=...)
wait(3)
# detectar modal "Sessão expirada" — clicar OK se houver
left_click(coords[botão Entrar], tabId=...)  # campos pré-preenchidos
wait(5)

# 3) Configurar Cartão de Ponto
navigate(url="https://www.rhid.com.br/v2/#/processamento_folha", tabId=...)
wait(3)

# Setar datas
javascript_exec(text=\"\"\"
  (() => {
    const ds = document.querySelectorAll('input[type=date]');
    ds[0].value = '{DATA_INI}';
    ds[1].value = '{DATA_FIM}';
    ds[0].dispatchEvent(new Event('change',{bubbles:true}));
    ds[1].dispatchEvent(new Event('change',{bubbles:true}));
    return ds[0].value + ' a ' + ds[1].value;
  })()
\"\"\", tabId=...)

# Selecionar formato HTML
left_click(coords[Formato de Saída], tabId=...)
wait(1)
left_click(coords[opção HTML], tabId=...)

# Processar
left_click(coords[botão Processar], tabId=...)
wait(15)  # processamento pode demorar 10-15s pra ~20 colab

# Fechar modal "Dados enviados pra cálculo"
left_click(coords[OK do modal], tabId=...)

# 4) Pegar GUID do relatório recém-gerado
navigate(url="https://www.rhid.com.br/v2/#/list_process", tabId=...)
wait(3)
guid = javascript_exec(text=\"\"\"
  (() => {
    const link = document.querySelector('table tbody tr:first-child a[ng-click]');
    const m = link?.getAttribute('ng-click').match(/'([a-f0-9-]+)'/);
    return m ? m[1] : 'no';
  })()
\"\"\", tabId=...)

# 5) Abrir relatório HTML em nova aba
new_tab = tabs_create_mcp()
navigate(url=f"https://www.rhid.com.br/v2/reporthtml.html#/html/{guid}", tabId=new_tab)
wait(8)

# 6) Extrair os N cartões via DOM
javascript_exec(text=\"\"\"
  (() => {
    const allTables = Array.from(document.querySelectorAll('table'));
    const cartoes = [];
    for (let i = 0; i < allTables.length; i++) {
      const t = allTables[i];
      const txt = t.textContent.replace(/\\s+/g,' ').trim();
      if (txt.startsWith('Nome do funcion') && t.querySelectorAll('tr').length === 1) {
        const m = txt.match(/Nome do funcion[^:]*:\\s*(.+)$/);
        const nome = m ? m[1].trim() : '?';
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
    return cartoes.length;
  })()
\"\"\", tabId=new_tab)

# 7) Dump em batches via console (pra ler com read_console_messages)
javascript_exec(text=\"\"\"
  (() => {
    const TAG = 'WK';
    window.__cartoes.forEach((c, idx) => {
      const linhas = [c.nome];
      c.rows.slice(1, 1+7).forEach(row => {
        const compact = [
          row[0], row[2]||'',
          row[4]||'', row[5]||'',
          row[6]||'', row[7]||'',
          row[8]||'', row[9]||''
        ].join('@');
        linhas.push(compact);
      });
      console.log(`${TAG}${idx}#${linhas.join('§')}`);
    });
    return `dumped ${window.__cartoes.length}`;
  })()
\"\"\", tabId=new_tab)

# 8) Ler console em batches de 10-15 cartões
read_console_messages(tabId=new_tab, pattern="^WK([0-9]|1[0-4])#", limit=20)
read_console_messages(tabId=new_tab, pattern="^WK1[5-9]|2[0-9]#", limit=20)
# ... etc

================================================================================
PARSE DOS DADOS PYTHON
================================================================================

Cada linha do dump tem formato:
    NOME§DATA1@PREVISTO@E1@S1@E2@S2@E3@S3§DATA2@...

Parser:
"""

import re
from datetime import datetime


def parse_cartao_dump(linhas_console):
    """
    Recebe lista de strings vindas do console (com tag stripada).
    Cada string: "{idx}#{nome}§{dia1}§{dia2}§..."
    Retorna dict {nome: [{data, previsto, batidas}]}
    """
    cartoes = {}
    for linha in linhas_console:
        # Remover prefixo "{idx}#"
        m = re.match(r"^\d+#(.+)$", linha)
        if not m:
            continue
        body = m.group(1)
        partes = body.split("§")
        if len(partes) < 2:
            continue
        nome = partes[0].strip()
        dias = []
        for p in partes[1:]:
            campos = p.split("@")
            if len(campos) < 2:
                continue
            # campos: [data, previsto, e1, s1, e2, s2, e3, s3]
            data_label = campos[0]  # "29/04/2026 - QUA"
            previsto = campos[1] if len(campos) > 1 else ""
            batidas = (campos[2:8] + ["", "", "", "", "", ""])[:6]
            # Parse de data
            data_match = re.match(r"^(\d{2})/(\d{2})/(\d{4})", data_label)
            if data_match:
                dd, mm, aa = data_match.groups()
                data_iso = f"{aa}-{mm}-{dd}"
            else:
                data_iso = data_label
            dias.append({
                "data": data_iso,
                "data_label": data_label,
                "previsto_rhid": previsto,
                "batidas": batidas,
            })
        cartoes[nome] = dias
    return cartoes


if __name__ == "__main__":
    # Teste com dados da S19
    exemplo = [
        "0#Alyne Bittencoutrt Meireles§29/04/2026 - QUA@07:00-12:30/13:30-15:20@13:14@14:05@15:06@21:13@@§30/04/2026 - QUI@07:00-12:30/13:30-15:20@06:25@12:32@13:10@14:33@@",
    ]
    print(parse_cartao_dump(exemplo))
