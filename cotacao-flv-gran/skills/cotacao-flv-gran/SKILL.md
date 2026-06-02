---
name: cotacao-flv-gran
description: >-
  Cotação FLV do Gran Hortifruti — compara tabelas semanais dos fornecedores em
  R$/kg, faz cherry-picking por item, expõe preço inflado vs mediana e CEASA-BA,
  gera Mapa de Decisão + Pedidos prontos pro WhatsApp. TAMBÉM dispara automaticamente
  o pedido de tabela pros fornecedores nas seg+qua de madrugada via WhatsApp Desktop,
  com retentativas horárias e arquivamento das respostas. Use SEMPRE que Hugo
  mencionar cotação, cotar, /cotar, /cotacao-disparar, /cotacao-status, /cotacao-arquivar,
  pedido de tabela, ronda de fornecedores, compra FLV, CEASA, mapa de decisão, pedido
  por fornecedor, cherry-picking, fornecedor mais barato, creep de fornecedor, ou
  decidir de quem comprar cada item de hortifruti na semana. Também ajustes em
  parsing, exclusão por item, alertas, entregáveis, templates de mensagens, contatos
  ou scheduled task. NÃO use para previsão de demanda, NPS, CRM, receptivo, survey
  ou auditoria.
---

# Cotação Inteligente FLV — Gran Hortifruti

Esta skill cobre **dois fluxos**:

1. **Decisão de compra** (`/cotar`) — compara tabelas dos fornecedores, faz
   cherry-picking item por item, gera o Mapa de Decisão e os pedidos prontos
   pro WhatsApp. Detalhes abaixo.
2. **Ronda de pedido de tabela** (madrugada Seg+Qua) — dispara automaticamente
   ping de "manda a tabela?" pros fornecedores via WhatsApp Desktop e arquiva
   as respostas. **Roteiro completo em `RONDA_PEDIDO_TABELA.md`.**

Regras canônicas em `references/regras_negocio.md` — leia antes de rodar
qualquer cotação.

## Os dois problemas que esta skill mata

1. **Indisponibilidade** — nunca depender de fonte única. Cherry-picking + canais.
2. **Preço inflado** — creep de cliente cativo e margem ruim escondida no pacote.
   Combatidos comparando todos lado a lado e rotacionando.

## Comando `/cotar` (decisão de compra)

Fluxo de uma rodada (operado pelo Hugo). Siga em ordem, validando cada etapa:

1. **Reunir entradas** da pasta da semana **no projeto** (`<projeto>/entradas/semana-AAAA-Www/`):
   - Tabelas dos fornecedores (qualquer formato).
   - `BI do Gran` (aba `APOIO PEDIDO`) — **base oficial da demanda**:
     a MÉDIA FINAL (col BA) é a média diária ponderada; giro semanal = MÉDIA FINAL × 7.
     O BI também dá custo (P.CUSTO), preço (P.ATUAL), curva e fornecedor atual. Hugo
     envia o BI na conversa a cada rodada.
   - Os DADOS mutáveis (dicionários, exceções, feedback, histórico CEASA) ficam em
     `<projeto>/dados/`; as SAÍDAS em `<projeto>/cotacoes/semana-AAAA-Www/`.
2. **Parsear cada tabela** → `references/formatos_fornecedores.md`.
   - Formatos digitais (texto/PDF): use os parsers em `scripts/parsers.py`.
   - Tabela em **imagem** (ex: RML): transcreva por visão para CSV seguindo
     `references/parsing_imagem_rml.md`. Nunca chute preço; 0,00 = não cotado.
3. **Buscar o benchmark CEASA-BA** (KVIs de maior giro) → `references/benchmark_ceasa.md`.
4. **Rodar a cotação**: `python scripts/cotar.py --semana AAAA-Www --projeto <projeto>
   --bi <BI Gran.xlsx> --donofrio ... --shimizu ... [...] --out <projeto>/cotacoes/semana-AAAA-Www`.
5. **Resolver as incertezas do CEASA**: abra `perguntar_ceasa.json`, pergunte ao
   Hugo, grave em `dados/dicionario_excecoes_ceasa.csv` e rode `cotar.py` de novo.
6. **Revisar os alertas** com o Hugo: `CONFERIR`, `NEGOCIAR`, `FONTE ÚNICA`,
   `sem cotação`.
7. **Entregar**: `mapa_decisao.html` + pedidos por fornecedor.

## Comandos da ronda de pedido de tabela

- `/cotacao-disparar` — Roda um slot da ronda (3h, 4h, 5h, 6h, 7h de Seg/Qua).
  **Roteiro completo em `RONDA_PEDIDO_TABELA.md`.**
- `/cotacao-status` — Snapshot agregado da rodada de hoje (quem disparou, quem
  respondeu, formatos recebidos).
- `/cotacao-arquivar` — Varredura manual de respostas pendentes (caso Hugo
  queira rodar fora do horário automático).

Scripts envolvidos:
- `scripts/enviar_pedido.py` — CLI: `listar`, `registrar-disparo`,
  `registrar-erro`, `marcar-tabela-externa`, `checar-preview`, `status`,
  `candidatos-desativar`.
- `scripts/arquivar_resposta.py` — CLI: `listar-pendentes`, `registrar-resposta`,
  `resposta-audio`, `registrar-audio`, `classificar-conteudo`,
  `listar-arquivos`.
- `scripts/envio_lib.py` — Lógica compartilhada (calendário, manifest, anti-spam,
  detecção de tabela no preview).
- `scripts/relatorio_rodada.py` — Relatório agregado da rodada.

## Os dois entregáveis (decisão de compra)

- **Mapa de Cotação** (`mapa_decisao.html`) — relatório desktop, identidade Survey Gran
  (claro/creme + verde + dourado, JetBrains Mono nos números), 5 abas: Matriz de Cotação,
  Inteligência CEASA, Mercado & Decisão, Vendas & Perdas, Alertas.
- **Pedidos por Fornecedor** (`pedidos_whatsapp/*.txt`) — 1 por fornecedor, formato
  WhatsApp: blocos/emojis, **sem %, sem centavos, sem parênteses**, cabe em 1 envio.

## Regras inegociáveis (resumo — detalhe em references/regras_negocio.md)

1. **Cherry-picking por item**, nunca por pacote de fornecedor.
2. **Exclusão por item**: fornecedor ruim para um item não vence aquele item, mesmo
   mais barato (defesa de disponibilidade). Mantida em `dados/exclusoes.csv`.
3. **Canais**: só Micael e RML são *busca* (CEASA); todos os demais *entregam*.
4. **Âncoras**: mediana entre fornecedores + CEASA-BA (KVIs) + último custo do BI
   como banda de sanidade (pega erro de embalagem / preço > 2x).
5. **Dado real ou nada.** Preço 0,00/vazio = não cotado, nunca vence.
6. **A skill não prevê demanda** — usa a MÉDIA FINAL (col BA) do BI × 7 como base.

## Auto-melhoria

- Dicionário (`dados/dicionario_equivalencia_oficial.xlsx`) engorda a cada rodada
  com itens novos que você casar.
- Histórico (`dados/.../historico_precos.csv`) acumula preço por
  item×fornecedor×semana — base do creep/desvio a partir da 2ª rodada.
- Notas de parsing em `references/notas_operacionais.md`.

## Mapa de arquivos

```
cotacao-flv-gran/
├── SKILL.md                       (este roteador)
├── RONDA_PEDIDO_TABELA.md         (roteiro do disparo automático Seg+Qua madrugada)
├── HANDOFF_ABA_CEASA.md           (contexto histórico de troca de aba)
├── scripts/
│   ├── flv_lib.py                 (dicionário, BI/demanda, normalização, banda sanidade)
│   ├── parsers.py                 (adaptadores: D'onofrio, Shimizu, Doce Mel, CSV/RML)
│   ├── parse_ceasa.py             (parser do boletim CEASA-BA)
│   ├── engine.py                  (casamento, normalização, cherry-picking)
│   ├── outputs.py                 (Mapa HTML + Pedidos WhatsApp)
│   ├── cotar.py                   (orquestrador do /cotar)
│   ├── envio_lib.py               (lib compartilhada da ronda de pedido)
│   ├── enviar_pedido.py           (CLI do disparo)
│   ├── arquivar_resposta.py       (CLI do arquivamento de respostas)
│   ├── relatorio_rodada.py        (relatório agregado da ronda)
│   ├── revisao.py                 (camada de revisão crítica do Mapa)
│   ├── decisao.py / ceasa_temporal.py / registrar_pesagem.py (utilitários)
├── references/                    (regras, formatos, parsing imagem, benchmark, notas)
├── templates/
│   ├── fornecedores.json          (roster com canais, grupos, telefones, envio_automatico)
│   ├── mensagens_pedido.json      (templates inicial vs retentativa por slot)
│   ├── embalagens.json            (peso/embalagem por SKU)
│   └── config.py                  (constantes)
└── dados/                         (dicionário, cadastros, semanas, histórico, exclusões — vivem no PROJETO)
```

Regra de ouro: **cada ajuste toca UM arquivo.** Conteúdo editável (mensagens,
parâmetros) fica em `templates/`; lógica fica em `scripts/`; regras em `references/`.
