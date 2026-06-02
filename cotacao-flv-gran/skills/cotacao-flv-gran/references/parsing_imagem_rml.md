# Parsing de Tabela em Imagem (RML e fotos de WhatsApp)

Tabelas que chegam como **imagem/print** não têm parser de script confiável. Você
(Claude) lê a imagem por visão e transcreve para um CSV que o motor consome igual aos
demais. Isso é mais confiável que OCR automático para grades densas.

## Procedimento
1. Abra a imagem (Read tool). Leia com cuidado, categoria por categoria.
2. Para cada item, capture: **descrição como está escrita**, **unidade/embalagem**, **preço**.
3. Grave em CSV com colunas exatamente: `desc,unidade,preco`.
4. Carregue com `parsers.carregar_csv_fornecedor(caminho, "RML")`.

## Regras de transcrição (críticas)
- **Preço 0,00 ou em branco = NÃO COTADO.** Não inclua a linha (ou deixe preço vazio).
  Nunca chute um preço.
- **Unidade fiel ao que dá pra normalizar**:
  - Por kg → `KG`. Por peça → `UND`. Bandeja → `BDJ`. Maço → `MC`.
  - Caixa/saca com peso → `CX 20KG`, `SC 25KG`, `CX 9KG` (o motor divide pelo peso).
  - Cento → `CENTO`.
- **Ofertas em amarelo**: são preço promocional válido — transcreva o preço amarelo
  (não o riscado). Pode anotar na descrição se houver dúvida.
- Não invente itens que não estão na imagem. Honestidade > completude.

## Formato do CSV (exemplo)
```
desc,unidade,preco
Banana prata kg,KG,4.00
Abacate breda cx 20kg,CX 20KG,70.00
Abacaxi graudo und,UND,5.00
Kiwi cat1 imp cx 9kg,CX 9KG,200.00
```

## Dica de match
Use a descrição **como o fornecedor escreve** (ex: "Abobora jacarezinho", não "Abóbora
jacaré"), porque o dicionário guarda a grafia do fornecedor naquela coluna. Itens que
não casarem aparecem em `nao_casados` para você confirmar e enriquecer o dicionário.
