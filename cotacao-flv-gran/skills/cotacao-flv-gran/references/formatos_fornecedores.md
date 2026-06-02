# Formatos de Tabela por Fornecedor

Cada fornecedor manda num formato próprio, mas **estável semana a semana**. Por isso
cada um tem um adaptador. Formato heterogêneo entre fornecedores, consistente no mesmo.

| Fornecedor | Canal | Formato | Parser |
|---|---|---|---|
| **D'onofrio** | entrega | Texto WhatsApp / RTF — categorias + "Item R$: X,XX UNID" | `parse_donofrio` |
| **Shimizu** | entrega | PDF — Nome \| Preço CX \| **Preço KG/UND** (a última é a usada) | `parse_shimizu` |
| **Doce Mel** | entrega | PDF — Cód \| Descrição \| UN \| **Preço KG** \| Preço CX | `parse_docemel` |
| **RML** | busca | **Imagem** (grade densa, ofertas em amarelo) | visão → CSV |
| **Hortimix** | busca | PDF "Tabela Restaurante" — grade densa 2 colunas (Nome \| Unid \| R$) | `parse_hortimix` |
| **Boa Citrus** | busca | Texto WhatsApp / RTF — "Item — caixa com NNkg: R$ X,XX" (preço POR CAIXA) | `parse_boacitrus` |

## Pontos de atenção por fornecedor

- **Shimizu**: a coluna "Preço Venda KG OU UND" é o preço final por kg/un. A embalagem
  no nome (ex: "CX 20 KG") é só descrição — **não é divisor de preço.** Por isso o parser
  fixa `unidade="KG/UND"`.
- **Doce Mel**: tem código próprio do produto (ex `002.023`) — guardado em `cod_fornecedor`,
  útil pra match determinístico futuro. Usamos a coluna **Preço KG**.
- **D'onofrio**: unidade vem no fim da linha (KG/UNI/BDJ). Linhas sem "R$:" são cabeçalho
  de categoria — ignoradas.
- **RML**: imagem → ver `parsing_imagem_rml.md`.
- **Hortimix** (cadastrado 25/05): tabela "Restaurante" com ~250 itens, muitos fora de FLV
  (temperos, castanhas, ovos, polpas) que ficam em `nao_casados` por design — só entra o que
  está no cadastro do Gran. **Atenção:** o offset das colunas MUDA entre as páginas do PDF
  (pág.1 tem coluna separadora vazia, pág.2 não), por isso o parser ancora na célula de
  **preço** e lê unidade/nome à esquerda dela. O bloco "POLPAS 1KG" é prefixado com `POLPA `
  para não casar com a fruta fresca homônima. `FALTA` / `R$ -` / vazio = não cotado.
- **Boa Citrus** (cadastrado 25/05): citrus + abacate. Preço vem **POR CAIXA** no corpo do
  WhatsApp ("caixa com 24kg: R$ 30,00"); o parser passa o preço da caixa + `unidade="CX NNKG"`
  e o motor divide pelo peso → R$/kg. Não usar o "/kg aproximado" do texto (arredondado).
  Laranja = SKU único (pega a mais barata). Itens genéricos (laranja/lima/limão/pocan) exigem
  decisão de variedade do Gran — manter em revisão até a compradora confirmar.

## Como o casamento funciona (item → COD Gran)
O dicionário (`dados/dicionario_equivalencia_oficial.xlsx`) tem uma coluna de descrição POR
fornecedor. O parser normaliza a descrição (minúsculas, sem acento, espaçamento de
unidade) e busca o COD. Match exato primeiro; fallback conservador por contenção.
Itens não casados aparecem em `nao_casados` — Claude/Hugo confirmam e o dicionário
engorda (auto-melhoria).

## Adicionar um fornecedor novo (ex: os ~10 do CEASA)
1. Se a tabela é digital e tem formato estável → escrever um parser novo em `parsers.py`
   no mesmo padrão (devolve `{desc, unidade, preco}`).
2. Se é imagem/foto → transcrever por visão para CSV e usar `carregar_csv_fornecedor`.
3. Adicionar uma coluna de descrição do fornecedor no dicionário (ou casar na rodada).
4. Definir o canal: novos fornecedores do CEASA = **busca** (editar `CANAL_BUSCA` em
   `flv_lib.py` se for outro nome além de Micael/RML).

## Normalização de unidade → R$/kg ou R$/un
Feita em `engine.normalizar_preco` usando a unidade Gran do SKU:
- Item Gran em **QUILO**: caixa/saca com peso (CX 20KG) → preço/peso; já-por-kg → direto.
- Item Gran em **UNIDADE**: CENTO → /100; por unidade/bandeja → direto; caixa de contagem
  desconhecida → não comparável (fica de fora, com nota).
A banda de sanidade (último custo) pega erros grosseiros de unidade.
