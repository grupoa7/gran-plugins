# Benchmark CEASA-BA

Fonte oficial de preço de atacado da praça de Salvador. É a âncora externa que expõe
preço inflado ("fornecedor X está N% acima da referência da semana"). Hugo confia nesta
fonte (Salvador-específica) mais que na base federal PROHORT — e está certo: preço de FLV
varia por região (clima, logística, tributo).

- URL: https://www.ba.gov.br/sde/boletim-informativo-ceasa
- Publicação: PDF, **~3x/semana e atual**.
- Colunas: PRODUTO · UNIDADE · PROCEDÊNCIA · MÍNIMO · **MAIS COMUM** · MÁXIMO · SITUAÇÃO.
- Usamos **MAIS COMUM** (preço modal — melhor que média/mín/máx).
- Cobertura: ~90 commodities (frutas/hortaliças/ovos) = os KVIs de maior giro. Itens fora
  do boletim caem na mediana entre fornecedores. **Aplicar só onde houver match** (KVIs).

## ⚠️ Como pegar o boletim do dia (importante)
O `web_fetch` da página de listagem pode retornar uma **versão em cache** desatualizada,
e o nome do PDF mais recente **não é previsível**. Por isso:

1. Navegue a listagem **AO VIVO** com o Chrome MCP (`navigate` + `get_page_text`), pegue
   o link do boletim do topo (data mais recente).
2. Baixe/leia esse PDF.
3. Parseie com `parse_ceasa.parse_boletim_pdf(caminho)` (ou `parse_boletim_texto` se você
   já tem o texto).

> Lição registrada (22/05/2026): um único `web_fetch` da listagem mostrou série travada em
> 13/03 — era cache. A fonte estava atual. Nunca concluir defasagem de um fetch só.

## Saída do parser
`{'data', 'itens':[{prod, unidade, procedencia, comum, comum_kg, situacao}]}`
- `comum_kg`: preço modal normalizado para R$/kg (None para itens por peça, ex CENTO/DÚZIA).
- `situacao`: EST=estável · FIR=firme · FRA=fraco · ENT=entrando. Dá o humor do mercado
  mesmo que o boletim esteja 1-2 dias atrasado.

## Uso na cotação
Para os KVIs cobertos, comparar o vencedor da semana contra `comum_kg`. Se o melhor
fornecedor ainda está bem acima do CEASA-BA, é sinal de que a praça toda subiu (situação
FIR) ou de que vale rotacionar/buscar. Casar nome do boletim → COD é uma camada de
equivalência menor (≤90 itens) — fazer sob demanda para os itens de maior giro.
