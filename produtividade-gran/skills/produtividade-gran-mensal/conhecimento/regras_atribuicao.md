# Regras de Atribuição por Equipe

Definidas em `parametros.json` no campo `regra_atribuicao_equipe`. Editar lá pra mudar.

## Lógica de cascata (ordem importa)

```
PARA cada SKU vendido no KW:

  1. SE setor raiz == 'GRAN MESA' → 100% Gran Mesa
     (109 SKUs. Cobre refeições, sucos, hortaliças higienizadas,
      frutas higienizadas, molhos, sobremesas, hortaliças prontas)

  2. SENÃO SE grupo == 'FATIADOS' → 100% Gran Mesa
     (25 SKUs. Subgrupo de Frios & Laticínios. Queijos fatiados
      e similares finalizados na cozinha)

  3. SENÃO SE cod ∈ {1, 589, 590, 591, 592, 593, 594, 595,
                     602, 616, 759, 763, 6424, 6584}
     → 65% Gran Mesa + 35% Gran Horti
     (14 SKUs do grupo PADARIA GRAN, exceto cód 760.
      Pães e salgados de produção própria. Splittados porque
      a equipe Gran Mesa produz, mas a equipe Gran Horti
      coloca em prateleira e atende)

  4. SENÃO SE cod == '760' → 100% Gran Horti
     (PAO DELICIA GRAN KG — exceção pedida pelo Hugo)

  5. SENÃO → 100% Gran Horti
     (todos os demais setores: Mercearia, Hortifruti,
      Bebidas, Frios, Carnes, Congelados, Padaria não-Gran,
      Granel, Bazar, Sazonais, Embalagens)
```

## Faturamento Omie (Gran Mesa Pro)

**100% atribuído à Gran Mesa.** É a UN B2B de refeições coletivas, emite NF pelo CNPJ Gran Realizacoes (39.303.338/0001-58). Aparece separado do KW.

CMV padrão: 49% (margem 51%) — confirmado por Hugo.

## Custo Pessoal por Equipe

### Custo direto
- Soma do `Total Vencimentos` × `fator_encargos_clt (1.55)` dos funcionários CLT classificados como aquela equipe na planilha `cadastro_equipe.xlsx`.

### Diaristas
- R$ 2.000/mês fixo, **100% Gran Mesa**.

### Retaguarda (rateio)
- 4 funcionários classificados como "Retaguarda" na planilha.
- Custo total da retaguarda é dividido entre Gran Mesa e Gran Horti **pró-rata pelo faturamento total** de cada equipe (incluindo GMPro pra Gran Mesa).

## Como ajustar a regra

Editar `data/produtividade/inputs/parametros.json`:

```json
"regra_atribuicao_equipe": {
  "padaria_gran_excl_760": {
    "codigos": ["1","589","590", "..."],
    "share_gran_mesa": 0.65,    ← muda aqui pra ajustar split
    "share_gran_horti": 0.35
  },
  ...
}
```

E re-rodar `build_dados.py`.

## Funcionários "fronteira"

Funcionários que tocam atividades de mais de uma equipe (ex: alguém que finaliza padaria 50% do tempo e tira pedido de cliente os outros 50%) **não são tratados em v1**. Hugo classifica binariamente: Gran Mesa OU Gran Horti OU Retaguarda. Veja a aba Sensibilidade Eixo C para investigar essa hipótese de mistura.

## Próximas iterações (v2+)

- Suportar `peso_gm` parametrizável por funcionário individual (ex: João = 50% Gran Mesa, 50% Gran Horti)
- Ler horas trabalhadas por área via timesheet (granularidade real ao invés de classificação binária)
- Detectar e alertar quando regra de SKU mudar mês a mês (ex: novo grupo "Padaria Gran" criado)
