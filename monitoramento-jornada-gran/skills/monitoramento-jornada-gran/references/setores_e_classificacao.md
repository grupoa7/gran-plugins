# Setores e Classificação — Skill Monitoramento de Jornada (v3)

Cadastro mestre dos colaboradores baseado nas escalas reais. **A escala é a fonte de verdade**.

---

## Setores cadastrados (9)

| Setor | Restrito? | Razão |
|---|---|---|
| ENCARREGADOS | ✅ Sim | Líderes operacionais — não podem descansar em horário de pico |
| OPERADOR DE LOJA | ✅ Sim | Atendem cliente direto — fluxo alto 11-13h e 16-19:30 |
| OPERADOR DE CAIXAS | ✅ Sim | Mesma razão de loja, função crítica |
| ASG | ❌ Não | Área de apoio |
| COZINHA | ❌ Não | Produção |
| SUPRIMENTOS | ❌ Não | Backoffice |
| MANOBRISTA | ❌ Não | **v3 (09/05/2026): saiu dos restritos por decisão do Hugo** |
| LOGÍSTICA | ❌ Não | Backoffice |
| ESTAGIÁRIAS | ❌ Não | Regime especial |

**3 setores restritos** = janela proibida 11h-13h e 16h-19:30 aplicável.

---

## Cadastro de colaboradores — Mai/2026

### ENCARREGADOS (2)
- Alyne Bittencourt
- Silvio Rouzan

### OPERADOR DE LOJA (3)
- Jilney Alves
- Joelison Frois
- Luciene Dias

### OPERADOR DE CAIXAS (2)
- Robson Santos
- Grasiela Conceição

### ASG (1)
- Jair Nascimento

### COZINHA (5)
- Joselene Costa, Fernanda Mascarenhas, Emanuele Maciel, Magno Oliveira, Solange Alves

### SUPRIMENTOS (4)
- Elissandro Nascimento, Robert Ferreira, Luis Guilherme
- Emilly Brito ⚠️ **SUSPENSA** (modalidade alternativa)

### MANOBRISTA (1)
- **Jamilton Ribeiro** ← v3: setor confirmado, mas sem regra restrita

### LOGÍSTICA (1)
- **Daniel Pereira** ← v3: setor confirmado conforme escala

### ESTAGIÁRIAS (1)
- Alana

**Total ativos no monitoramento: 19** (= 20 da escala − 1 suspensa).

---

## Mapeamento nome RHID ↔ nome escala

| Nome no RHID | Nome na escala |
|---|---|
| Alyne Bittencoutrt Meireles | Alyne Bittencourt |
| Daniel Santos Pereira | Daniel Pereira |
| Elissandro Nascimento Oliveira | Elisssandro Nascimento (typo PDF) |
| Emanuele Maciel de Jesus | Emanuele Maciel |
| EMILLY DE JESUS BRITO | Emilly Brito (suspensa) |
| Fernanda Santos Mascarenhas | Fernanda Mascarenhas |
| Grasiela dos Santos Conceição | Grasiela Conceição |
| Jair Nascimento de Sena | Jair Nascimento |
| Jamiltton de Oliveira Ribeiro Santos | Jamilton Ribeiro |
| Jilney de Jesus Alves | Jilney Alves |
| Joelison Frois Nogueira Piton | Joelison Frois |
| Joselene de Jesus Costa | Joselene Costa |
| Luciene Dias Santos | Luciene Dias |
| Luis Guilherme de Jesus Viana | Luis Guilherme |
| Magno Virginnio Barbosa de Oliveira | Magno Oliveira |
| Robert dos Santos Ferreira | Robert Ferreira |
| Robson Santos da Silva | Robson Santos |
| Silvio Rouzan Pereira da Silva | Silvio Rouzan |
| Solange Alves dos Santos | Solange Alves |

**Match não encontrado:**
- **Alana** está na escala mas não foi encontrada no RHID — verificar nome ou regime

**Match a remover:**
- **Josemaria Maximiana dos Santos** — saiu, RHID ainda lista como ativa

---

## Códigos da escala mensal

| Código | Significado |
|---|---|
| `HH:MM às HH:MM` | Jornada prevista do dia |
| `F` | Folga regular (semanal) |
| `FF` | Folga feriado |
| `FD` | Folga domingo |
| `Férias` | Período de férias |
| `BH` | Banco de horas |
| `X` | Inativo |
| `Rescisão` | Pós-demissão |

---

## Mudanças v3 (09/05/2026)
- Confirmado: Daniel Pereira = LOGÍSTICA, Jamilton Ribeiro = MANOBRISTA (escala vence)
- MANOBRISTA SAIU dos setores restritos — não aplica mais regra "janela proibida"
- Sandro entra em rota de tratativa RH separada (ver heuristicas_suspeitos.md)
