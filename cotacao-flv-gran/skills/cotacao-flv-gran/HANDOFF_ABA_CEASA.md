# Handoff — Aperfeiçoar a Aba 02 "Inteligência CEASA"

> Ler junto com a memória `project-cotacao-flv` (preferências de design do Hugo) e o
> `DESENHO_SKILL_COTACAO_FLV.md`. A **aba 01 Cotação está FECHADA (V1 aprovada)** — não mexer
> nela sem pedido. Este handoff é só para a aba 02.

## Como gerar/ver o relatório
```
cd cotacao-flv/scripts
python3 cotar.py --semana "2026-W21" --periodo "12 a 18 mai" \
  --contagem "<uploads>/Pedido FLV 2105.xlsx" \
  --donofrio "<uploads>/Tabela Donofrio.rtf" \
  --shimizu "<uploads>/Consulta Produto ATUALIZADO 16-05.pdf" \
  --docemel "<uploads>/TABELA 0% SEMANA 21..pdf" \
  --rml "../dados/teste_semana_2105/rml_transcrito.csv" \
  --out "../dados/teste_semana_2105/saidas"
```
Abre `dados/teste_semana_2105/saidas/mapa_decisao.html`, aba "02 Inteligência CEASA".
A renderização da aba está em `scripts/outputs.py` (procurar `tab-ceasa`). NÃO recriar do zero;
melhorar o que existe.

## Dados disponíveis (já prontos, passados a gerar_mapa_html)
- `ceasa_series` = {produto: {serie:[(data,preco_kg)], atual, min, max, media, tend_pct, dir, sit, n}}
  — 80 itens, 13 semanas (trimestre, 20/02→22/05/2026). Fonte: `dados/ceasa_historico/ceasa_trimestre.json`.
- `ceasa_atual` = boletim mais recente por produto (preço + situação firme/estável/fraco).
- `ceasa_datas` = 13 datas do trimestre.
- Captura de novos boletins: ver [[reference-ceasa-ba-boletim]] (método DecompressionStream via Chrome MCP).

## O que a aba 02 JÁ TEM hoje
1. KPIs do mercado (itens monitorados, em alta, em queda, semanas).
2. Rankings "maiores altas" e "maiores quedas" do trimestre, com mini-sparklines SVG.
3. "Foco na sua cesta" — itens da compra da semana que casam com a série CEASA.
4. Distribuição de situação de mercado.
5. **Gráfico de linha interativo** — `<select>` (64 itens) + SVG (eixo tempo × preço, marcadores semanais). Funciona.
6. Bloco "A confirmar" — agora vazio (CEASA 100% resolvido via dicionário de exceções).

## O que provavelmente vale aperfeiçoar (validar com Hugo, aba a aba, 80/20)
- **Diagramação/clareza** no padrão que fechamos na cotação (limpo, lê em segundos, PT claro).
- **Enquadramento de NEGOCIAÇÃO**: o Hugo quer o CEASA como "munição" — deixar explícito por item
  o quanto o preço de mercado subiu/caiu e o que isso significa pra comprar/pressionar agora.
- **Sazonalidade / janela de compra**: usar o trimestre pra sinalizar "tende a cair → segure / subir → antecipe".
- Conectar à cesta do Gran por **impacto econômico** (giro × preço), não só variação %.

## O que NÃO dá pra fazer agora (Fase 2 — honesto)
- **Comportamento do fornecedor ao longo do tempo** (quem vive acima do mercado, quem faz creep):
  precisa de várias semanas de histórico de cotação acumulado (`historico_precos.csv`). Hoje só há 1 semana
  real de preços de fornecedor. Isso preenche rodada a rodada — não force agora.

## Lembrar
- Identidade Survey, JetBrains Mono nos números, zero inglês.
- Cabeçalho de tabela NÃO-sticky.
- Nunca chutar match/conversão — perguntar e gravar exceção.
- Iterar aba por aba, validando antes de avançar.
