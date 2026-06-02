# Regras de Escopo · Survey Gran Mesa

Define quais SKUs entram no Survey Gran Mesa e como tratam-se itens compartilhados, fornecedores externos e SKUs sem mapping.

## Regra de atribuição em cascata (escopo)

Para cada linha de venda no KW, aplicar:

```
1. SE setor == 'GRAN MESA'                              → escopo (categoria: gran_mesa)
2. SENÃO SE grupo == 'FATIADOS'                         → escopo (categoria: fatiados)
3. SENÃO SE cod ∈ PADARIA_GRAN_CODES (exceto 760)       → escopo (categoria: padaria_gran)
4. SENÃO SE cod == '760'                                → FORA (Gran Horti)
5. SENÃO                                                → FORA
```

Onde `PADARIA_GRAN_CODES = {1, 589, 590, 591, 592, 593, 594, 595, 602, 616, 759, 763, 6424, 6584}`.

Total esperado no escopo: **~134 SKUs** (109 GRAN MESA + 25 FATIADOS + 14 PADARIA, podendo variar levemente conforme ARIUS).

## Padaria Gran no Survey Mesa — diferença vs Produtividade

| Plugin | Tratamento Padaria Gran |
|---|---|
| **produtividade-gran** | Split 65% Gran Mesa / 35% Gran Horti (porque equipe Mesa produz mas equipe Horti coloca em prateleira e atende) |
| **survey-gran-mesa** | **100% Gran Mesa** (faturamento e margem cheios) com tag visual `[split 65/35 no Produtividade]` |

Motivação: o Survey Mesa quer ver o **produto inteiro** (100% do que aquele SKU vendeu), não a fatia operacional. Tag visual deixa claro pra sócia que no Produtividade a contabilização é diferente, evitando confusão entre os dois relatórios.

## GMPro (Omie) — fluxo paralelo

GMPro Omie é lido de `data/produtividade/inputs/omie_gmpro.xlsx` e tratado em fluxo separado:

- **Aba 01**: bloco GMPro segregado com fat, margem, ticket B2B, n° clientes ativos
- **Aba 02**: linha dedicada GMPro no painel comparativo
- **Demais abas**: GMPro **NÃO entra** no heatmap, lift, matriz Margem×Volume, ruptura nem ticket médio (tem dinâmica B2B muito diferente — cupom único de R$ 5k+ distorce tudo)

CMV GMPro padrão: **49%** (margem 51%) — confirmado por Hugo. Configurável em `parametros.json`.

## Fornecedores externos no Mapa de Produção

`Mapa e Producao.xlsx` lista 2 fornecedores externos:

- **FORNECEDOR Mica** — Água de coco (cód 2868, 2867)
- **FORNECEDOR Natural Citrus** — Suco de laranja (cód 2457, 2456)

Tratamento na Aba 07 Bloco B:

- Sub-bloco separado **"Fornecedores Terceirizados"** (não conta em produtividade interna)
- Métricas mostradas: **fat, margem R$/%, share Gran Mesa, ruptura**
- Métricas **NÃO** aplicadas: produtividade kg/hora, perdas físicas internas, atribuição de hora-funcionário

Decisão de continuidade: avaliar trimestralmente se vale renovar parceria com base em margem e sell-through.

## Itens "PRODUCAO" intermediários

A planilha tem 3 itens marcados como insumos intermediários:

- **CARNE MOIDA PRODUCAO** (sem COD)
- **ACEM DESFIADO PRODUCAO** (cód 2002001)
- **FRANGO DESFIADO PRODUCAO** (cód 2002003)

Tratamento:

- Coluna `tipo_item = 'insumo_producao'` na pipeline
- **NÃO** entram nos KPIs de venda (não vendem em PDV — são insumos para outros pratos)
- Atribuídos ao colaborador para fins de carteira (Aba 07 Bloco B), mas com tag visual `[insumo intermediário]`

## Bucket "Não Atribuído"

SKUs cujo COD não está em `Mapa e Producao.xlsx`:

- Categoria `colaborador = 'Não Atribuído'`
- Aparecem na Aba 07 Bloco B em card próprio
- Card mostra alerta vermelho: "X% do fat Gran Mesa sem mapping de colaborador — atualize Mapa e Producao.xlsx"

Bandeira amarela no Headline (Aba 01) se `cobertura_mapping < 95%`.

## Cobertura esperada do Mapa

Hoje: **62 SKUs mapeados** (54 internos + 4 fornecedores + 3 insumos PRODUCAO + 1 Solange/Operação).
Escopo: **~134 SKUs**.
Gap inicial estimado: **~72 SKUs sem mapping** (provavelmente Padaria, Fatiados não cadastrados, e parte de Sucos).

Próximo passo (paralelo à v1): atualizar planilha para fechar gap.

## Path resolution

Mesma convenção dos outros plugins:

```python
def get_data_dir() -> Path:
    if env := os.environ.get('SURVEY_DATA_DIR'):
        return Path(env)
    home_proj = Path.home() / 'Documents' / 'Claude' / 'Projects' / '[GRAN] Survey' / 'data'
    if home_proj.exists():
        return home_proj
    legacy = Path.home() / 'Documents' / 'SurveyGran'
    if legacy.exists():
        return legacy
    raise FileNotFoundError(...)
```

Estrutura de pastas esperada:

```
data/
├── base/
│   └── base_classificada.pkl                ← do survey-gran
├── cadastros/
│   └── export_base_arius.xlsx               ← do survey-gran
├── produtividade/
│   └── inputs/
│       ├── gran_margens.xlsx                ← do produtividade-gran
│       ├── omie_gmpro.xlsx                  ← do produtividade-gran
│       └── parametros.json                  ← do produtividade-gran
└── gran-mesa/
    ├── inputs/
    │   └── Mapa e Producao.xlsx             ← novo, do survey-gran-mesa
    ├── relatorios/
    │   └── Survey_Gran_Mesa_S{NN}_v1.html
    └── ultima_semana_processada.txt
```

## Como ajustar a regra de escopo

Editar `data/produtividade/inputs/parametros.json`:

```json
"regra_atribuicao_equipe": {
  "padaria_gran_excl_760": {
    "codigos": ["1","589","590", "..."]
  }
}
```

E re-rodar `build_dados.py` do Survey Mesa.
