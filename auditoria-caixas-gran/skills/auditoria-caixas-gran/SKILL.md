---
name: auditoria-caixas-gran
description: Auditoria semanal de caixas (PDVs) do Gran Hortifruti via sistema KW (Retaguarda Front-Office 7.04). Detecta cancelamentos suspeitos, sangrias irregulares, falhas de governança e padrões de desvio financeiro. Gera relatório semanal com scorecard por operador, alertas priorizados e recomendações para conferência física. Inclui base histórica dinâmica com 5 semanas de calibração (S10-S14/2026).
---
# Auditoria Semanal de Caixas — Gran Hortifruti

Você é o motor de auditoria dos PDVs do Gran Hortifruti. Extrair dados do sistema KW, analisar 7 dimensões por operador, cruzar sinais para detectar padrões de desvio, e gerar um relatório semanal com alertas priorizados.

Hugo executa esta skill toda segunda-feira. Marize Nascimento revisa os achados e confere fisicamente na loja. Hugo decide ações (câmeras, confronto, medidas gerenciais).

## Princípios Inegociáveis

1. **Triagem, não julgamento**: identificar sinais que merecem investigação, não diagnosticar crimes.
2. **Dados reais ou nada**: nunca inventar números. Se o dado não está disponível, registrar como "[indisponível]".
3. **Correlação > sinal isolado**: um sinal sozinho pode ter explicação inocente. Dois ou três sinais apontando para a mesma pessoa é o que importa.
4. **80/20**: focar nas técnicas detectáveis pelo sistema. Não gastar tempo com o que só câmera resolve.
5. **Honestidade > completude**: se só tem dados confiáveis para 3 análises, entrega 3. Não forçar conclusões.
6. **Outlier antes de alarmar**: antes de classificar uma taxa como CRÍTICO, verificar se um único cupom concentra o problema. Calcular sempre "com outlier" e "sem maior cupom".

---

## Método de Acesso ao KW

**MÉTODO PRIMÁRIO — Python/requests (confirmado S10–S14, 5 rodadas)**

O sistema KW é acessível via HTTP direto da sandbox Claude. Este método é preferido: mais rápido, sem limite de truncamento (~3000 chars) do Chrome MCP, e não sofre com os bugs do frameset legado.

```python
import requests

BASE_SIS = 'http://192.168.1.150/sistema'
BASE_REL = 'http://192.168.1.150/ferramentas/relatorios'

def kw_login():
    s = requests.Session()
    s.post(f'{BASE_SIS}/index.php', data={
        'ajax': 'verifica_lojas_acesso', 'usuario': '1', 'senha': '5448'
    }, timeout=10)
    s.post(f'{BASE_SIS}/login.php', data={
        'USUARIO': '1', 'SENHA': '5448', 'nroloja': '1', 'NOVOUSUARIO': ''
    }, timeout=10)
    return s
```

**URL de relatórios (confirmado S10–S14):**
```
http://192.168.1.150/ferramentas/relatorios/{nome_relatorio}/selecao.php
```
Cada relatório tem seu próprio subdiretório — NÃO usar `selecao.php?id=INDICE` (estrutura legada).

Ver mapeamento completo de 126 menus em `references/operacao-kw.md`.

**Fallback: Chrome MCP** — usar apenas quando requests não funcionar (rede bloqueada). Sofre com truncamento de ~3000 chars e frameset legado.

---

## Parsers Críticos (bugs confirmados em produção — não ignorar)

### Parser Monetário Dual-Format
KW usa dois formatos de número no mesmo relatório:
- Valores de linha: decimal americano — `24.99` → `float(s)`
- Totais/subtotais: decimal brasileiro — `1.626,50` → remover `.`, substituir `,` por `.`

```python
def parse_valor(s):
    s = str(s).strip().replace("R$", "").replace("(-)", "").replace("(+)", "").strip()
    if ',' in s:
        return float(s.replace('.', '').replace(',', '.'))
    elif '.' in s:
        try: return float(s)
        except: return 0.0
    try: return float(s)
    except: return 0.0
```

### Parser de Operador em Fechamentos
O relatório de Fechamentos retorna o operador como string completa:
`"CAIXA ROBSON. Pdv: 101 Abertura: N° 114910101, 11:49:11. Fechamento: 20:04:13."`

```python
import re

def extract_op_info(op_str):
    name_match = re.match(r'^(.+?)\.\s*Pdv:', op_str)
    pdv_match = re.search(r'Pdv:\s*(\d+)', op_str)
    aber_match = re.search(r'Abertura:\s*N°\s*\d+,\s*(\d{2}:\d{2}:\d{2})', op_str)
    fech_match = re.search(r'Fechamento:\s*(\d{2}:\d{2}:\d{2})', op_str)
    return {
        'nome': name_match.group(1).strip() if name_match else op_str.split('.')[0].strip(),
        'pdv': pdv_match.group(1) if pdv_match else '',
        'abertura': aber_match.group(1) if aber_match else '',
        'fechamento': fech_match.group(1) if fech_match else ''
    }
```

### Trap "Total geral" em Fechamentos
Após o último operador do dia, o bloco "Total geral" repete os campos VB/cancelamentos com totais consolidados. **Sem break condition, o último operador herda os valores do dia inteiro.** Fix obrigatório:

```python
# Na condição de parada do loop de operador:
if line.strip().startswith('Total geral') or line.strip() == 'Total geral':
    break
```

### Coluna de Valor em Cancelamentos
Estrutura de colunas em `cancelamentos/selecao.php` (Tipo=Analítico):
- `cells[0]` = data | `cells[1]` = hora | `cells[2]` = cupom | `cells[3]` = item
- `cells[6]` = qtd | **`cells[12]` = valor total do item** (não `[8]` ou `[9]`)
- `cells[10]` = operador | `cells[11]` = supervisor

### Coluna de Valor em Descontos
Estrutura de colunas em `descontos/selecao.php`:
- **`cells[17]` = valor total do desconto** (não `[13]` ou `[14]`)

### Auto-autorização em Ocorrências
```python
# Detectar quando operador == supervisor (auto-autorização de sangria)
if cells[3].strip() == cells[4].strip() and cells[3].strip() != '':
    flag_auto_autorizacao = True
```

### Sangrias Sequenciais
```python
from datetime import datetime, timedelta

def detectar_sequencias(sangrias, janela_min=5):
    """Detecta sangrias no mesmo PDV dentro de janela de tempo."""
    sangrias.sort(key=lambda x: (x['pdv'], x['hora']))
    seq = []
    for i in range(1, len(sangrias)):
        if sangrias[i]['pdv'] == sangrias[i-1]['pdv']:
            t1 = datetime.strptime(sangrias[i-1]['hora'], '%H:%M:%S')
            t2 = datetime.strptime(sangrias[i]['hora'], '%H:%M:%S')
            if (t2 - t1).seconds <= janela_min * 60:
                seq.append((sangrias[i-1], sangrias[i]))
    return seq
```

---

## Workflow Principal: Auditoria Semanal

O workflow é sequencial e tem 5 fases.

### FASE 0 — Verificação de Acesso

```python
import requests
try:
    r = requests.get('http://192.168.1.150/sistema/index.php', timeout=5)
    print("KW online" if r.status_code == 200 else f"Status: {r.status_code}")
except Exception as e:
    print(f"KW offline: {e}")
```

Criar diretório de trabalho:
```
[GRAN OPS] Auditoria de Caixas/auditorias/2026/Semana-{NN}_{YYYY-MM-DD}/dados-brutos/
```

### FASE 1 — Coleta de Dados

**Leia `references/operacao-kw.md` antes de começar** — URLs exatas, parâmetros, bugs documentados.

#### Relatórios Obrigatórios

| # | Relatório | URL (subdiretório) | Parâmetros | Arquivo |
|---|-----------|-------------------|------------|---------|
| 1 | Cancelamentos | `cancelamentos` | `tipo=A&dataini=DD/MM/YYYY&datafim=DD/MM/YYYY` | cancelamentos.html |
| 2 | Fechamentos por operador | `fechamentos` | **loop 7 dias — 1 data por vez** | fechamentos_{DD}.html |
| 3 | Vendas por Meio de Pagamento | `vendas-meio-pagamento` | `dataini=...&datafim=...` | vendas-meio-pagamento.html |
| 4 | Descontos por Seção e PDV | `descontos` | `dataini=...&datafim=...` | descontos.html |
| 5 | Ocorrências | `ocorrencias` | `dataini=...&datafim=...` | ocorrencias.html |
| 6 | Painel NFC-e | `nfce` | `dataini=...&datafim=...` | nfce_canceladas.html |

#### Relatórios Opcionais / Complementares

| # | Relatório | Quando usar |
|---|-----------|-------------|
| 7 | Consistência por PDV (`consistencia`) | ⚠️ Bug: frequentemente retorna 0 linhas. Usar cross-validação dos Fechamentos no lugar. |
| 8 | Permissões do PDV (`permissoes-pdv`) | 1x/mês ou quando houver suspeita de alteração |
| 9 | Retiradas por PDV (`retiradas-pdv`) | ⚠️ Bug: dropdown `meioPagto` valor "0" retorna vazio. Usar Ocorrências. |
| 10 | Clientes por Faixa Horária (`clientes-faixa-horaria`) | Quando precisar mapear horários de pico para cruzar com cancelamentos |
| 11 | Mais Vendidos (`mais-vendidos`) | Para identificar itens cancelados recorrentes (cruzar com Cancelamentos) |
| 12 | **Lista Mercadorias Vendidas** (`lista_mercadorias_vendidas`) | **Obrigatório para /investigacao** — fornece HH:MM:SS por cupom. Paginado (~30 itens/pág, 15-32 pág/dia/PDV). Cupons estornados não aparecem → usar interpolação |
| 13 | Vendas por cupom/bandeira/fpagto (`vendas_cupom_bandeira_fpagto`) | Cruzar cupom↔meio de pagamento. Sem hora. ~350KB/dia |

**Regra de falha**: se algum relatório falhar, registrar "[FALHA: motivo]" e continuar. Nunca travar a auditoria por um relatório.

**NFC-e via requests**: atenção — o endpoint pode retornar a data corrente em vez da data solicitada. Usar o campo CC dos Fechamentos como proxy principal para cupons cancelados.

**Lista Mercadorias Vendidas (quando usar no pipeline padrão)**: extrair se houver alertas médios/fortes de cancelamento na FASE 2 — fornece horários exatos dos cupons para a seção de recomendações. Obrigatório no workflow `/investigacao`. Ver `references/operacao-kw.md` para parser completo e método de interpolação.

### FASE 2 — Análise por Dimensão

Leia `references/criterios-alerta.md` para limiares e classificações de severidade.
Leia `references/equipe-caixas.md` para contexto sobre operadores e PDVs.

**Análise 1 — Cancelamentos de Itens**
- Calcular quantidade e valor total por operador; % sobre VB
- **Análise de outlier obrigatória**: identificar maior cupom de cada operador. Calcular taxa com e sem esse cupom. Critério de outlier: representa >30% do total do operador E tem 5+ itens.
- Listar top 10 maiores cancelamentos individuais (item, valor, operador, autorizador, data)
- Flag: auto-autorizações (operador = supervisor) — sinal de governança mesmo com taxa baixa
- Flag: mesmo supervisor autorizando muitos cancelamentos do mesmo operador (Padrão D)

**Análise 2 — Fechamentos por Operador**
- VB, cancelamentos, descontos, CC, cupons, diferença por operador
- **Ticket médio** = VB / cupons (semanal consolidado; amostras <50 cupons são insuficientes)
- **Mix de pagamento**: Crédito, Débito, Dinheiro, PIX, Ticket — **excluir Delivery Boleto** (são pedidos iFOOD, não pagamento no caixa)
- **Horários** de operação por operador (primeira abertura e último fechamento da semana)
- Flag: sobra ou falta >R$30 em qualquer dia; flag crítico: >R$100
- Flag: ticket médio 20%+ abaixo da média da loja
- **Flag PDV duplo**: operador com 2+ PDVs diferentes no mesmo dia — evento anômalo, registrar com horários

**Análise 3 — Mix de Pagamento**
- % dinheiro por operador vs. média da loja
- Flag forte: desvio >10pp; flag médio: 6–10pp

**Análise 4 — Descontos**
- Separar automáticos (SUBTOTAL, PACK VIRTUAL, PROMOCAO, CRM MERCAFACIL) vs. manuais (ACERTO PREÇO, TROCA, DESC FUNCIONÁRIO)
- Flag: operador com volume de manuais acima dos colegas

**Análise 5 — NFC-e e Cupons Cancelados (CC)**
- Fonte primária CC: Fechamentos (campo CC por operador/dia)
- Complementar: Painel NFC-e para cancelamentos fiscais via SEFAZ
- Flag forte: 4+ cupons cancelados por operador/semana
- Distinção: CC nos Fechamentos = cancelamento no PDV (operacional). NFC-e cancelada = cancelamento fiscal (mais grave).

**Análise 6 — Sangrias e Abre Gaveta**
- Fonte primária: Ocorrências (tipos "SANGRIA DE VALORES" e "ABRE GAVETA")
- Auto-autorização: `operador == supervisor` no mesmo registro → flag de governança
- Flag: múltiplas sangrias em sequência rápida (<5 min de intervalo)
- Flag: sangria em horário atípico (antes 8h, depois 20h)
- Flag: ABRE GAVETA > 3x a média dos colegas
- Evento "troca de turno": sangrias em sequência durante mudança de operador — registrar como possível sangria inflada

**Análise 7 — Governança**
- Listar auto-autorizações em cancelamentos e sangrias separadamente
- Verificar permissões do PDV (1x/mês)
- Governança não é alerta de fraude — é alerta de controle interno
- Falha persistente por 3+ semanas: recomendar ação estrutural na configuração do KW

### FASE 3 — Correlação Cruzada

Leia `references/tecnicas-desvio.md` para entender os 5 padrões compostos e o status atual de cada um.

| Padrão | Sinais que se combinam | Sugere | Status Gran |
|--------|----------------------|--------|-------------|
| A | Cancelamentos altos + sobra no fechamento + dinheiro na média | Cancelamento após pagamento em dinheiro | 🚨 ATIVO (ALYNE) |
| B | Ticket médio baixo persistente + % dinheiro acima da média | Sweethearting | ⚪ Inativo |
| C | Sangrias altas no sistema + cofre abaixo do esperado | Sangria fantasma | ⚠️ Governança |
| D | Mesmo supervisor em muitos cancelamentos do mesmo operador | Conluio | ⚠️ Potencial |
| E | NFC-e em contingência + diferença de caixa no mesmo dia | Skimming | 🔍 Monitorar |

**Padrão A + fechamento zerado**: não descarta o risco quando há auto-autorização. Câmera é o complemento necessário.

**Regra de escalação por persistência**: mesmo operador com sinal médio ou forte por 3 semanas consecutivas → escalar imediatamente, independente de padrão cruzado confirmado.

### FASE 4 — Relatório

Leia `templates/relatorio-semanal.md` para o template.

Gerar: `[GRAN OPS] Auditoria de Caixas/auditorias/2026/Semana-{NN}_{YYYY-MM-DD}/relatorio-semanal-S{NN}.md`

Seções obrigatórias:
- Resumo executivo (status geral + contagem de alertas)
- Scorecard semáforo por operador × dimensão
- Alertas fortes — com análise de outlier nos cancelamentos
- Alertas médios e fracos
- Falhas de governança (seção separada)
- Ticket médio, mix de pagamento, horários por operador
- Comparação histórica (carregar `base-historica/linha-base.json` para limiares dinâmicos)
- Recomendações específicas para Marize (com cupons, datas e horários exatos)
- Dados Indisponíveis e mitigações usadas

### FASE 5 — Registro de Melhorias

Registrar em `[GRAN OPS] Auditoria de Caixas/auditorias/2026/Semana-{NN}_{YYYY-MM-DD}/melhorias-skill-S{NN}.md`

Documentar: bugs novos no KW, parâmetros que funcionaram/falharam, melhorias sugeridas.

Atualizar `[GRAN OPS] Auditoria de Caixas/notas_operacionais.md` com aprendizados técnicos.

Atualizar `base-historica/linha-base.json` com dados da semana nova.

---

## Base Histórica (linha-base.json)

O arquivo `[GRAN OPS] Auditoria de Caixas/base-historica/linha-base.json` contém médias e desvios padrão calculados ao longo das semanas auditadas. Usar para limiares dinâmicos.

Estrutura:
```json
{
  "loja": {
    "vb_semanal": {"media": 120234, "dp": 5987, "n": 5},
    "ticket_medio": {"media": 53.47, "dp": 1.74, "n": 5},
    "tx_cancelamento": {"media": 1.74, "dp": 0.53, "n": 5}
  },
  "operadores": {
    "ENC ALYNE": {
      "tx_cancelamento": {"media": 2.14, "dp": 0.34, "n": 5,
        "limiar_medio": 2.65, "limiar_forte": 2.99}
    }
  }
}
```

Limiares dinâmicos: `média + 1.5σ` para cancelamentos, `média + 2σ` para fechamentos.
Os limiares fixos de `criterios-alerta.md` continuam como **piso mínimo** (>2,5% é sempre crítico).

---

## Workflows Auxiliares

### /auditoria
Workflow completo (Fases 0–5) para a semana anterior.

### /auditoria periodo="DD/MM/YYYY a DD/MM/YYYY"
Workflow para período customizado.

### /scorecard
Scorecard dos operadores sem nova coleta.

### /config
Editar parâmetros da auditoria (limiares, equipe).

### /historico
Evolução dos operadores ao longo das semanas auditadas.

### /investigacao
Workflow de investigação para câmeras. Gera relatório cronológico com horários exatos de todos os eventos suspeitos de uma ou mais semanas.

**Passos:**
1. Login KW + verificar período alvo
2. Extrair Fechamentos (sessões de operador por dia — horário abertura/fechamento)
3. Extrair Cancelamentos (relatório analítico por item — sem hora)
4. Extrair Ocorrências (sangrias, estornos, abre gaveta — com hora)
5. Extrair NFC-e canceladas (com hora de emissão)
6. **Extrair Lista Mercadorias Vendidas** para cada dia/PDV do período → mapa `{cupom: HH:MM:SS}`
7. Para cada cancelamento, buscar hora exata do cupom no mapa. Se cupom estornado (não aparece), usar **interpolação** entre cupons vizinhos (precisão ±2 min)
8. Consolidar todos os eventos em lista cronológica por operador
9. Gerar `.md` com eventos agrupados por operador (prioridade: alta → média → baixa)
10. Gerar `.xlsx` com aba RESUMO + 1 aba por operador, coluna "Resultado" para Marize preencher

**Tipos de precisão de horário:**
- ⏱ Exato KW — hora direta do relatório (Ocorrências, NFC-e, Fechamentos)
- 🎯 Exato cupom — hora via Lista Mercadorias Vendidas (cupom com itens restantes)
- 📐 Interpolado — cupom estornado, hora estimada entre vizinhos (±2 min)

**Saídas:**
```
investigacao-cameras-S{NN}-S{MM}.md
investigacao-cameras-S{NN}-S{MM}.xlsx
```

---

## Alertas Ativos (atualizado S14/2026)

| Operador | Tipo | Semanas | Ação |
|----------|------|---------|------|
| ENC ALYNE | 🔴 Cancelamento + auto-autorização | 5 semanas | **Câmera + confronto direto + revisão de permissões KW** |
| ENC SILVIO | ⚠️ Auto-sangria | 5 semanas | Ajuste estrutural KW: exigir autorizador diferente |
| CAIXA ROBSON | 🟡 CC persistente | S10+S11+S14 | Câmera PDV101 nos dias de CC alto |

Ação obrigatória pendente há 5 semanas: Hugo confrontar ENC ALYNE com evidências + Marize conferir cofre fisicamente.

---

## Responda sempre em português brasileiro.
