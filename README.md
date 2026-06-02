# gran-plugins

Marketplace pessoal de skills do Grupo A7 para uso no Cowork mode (Claude Desktop).

## Para que serve

Distribui as skills operacionais do Gran Hortifruti entre os dois PCs do Hugo (pessoal = dev, escritorio = producao 24/7). Edita aqui, da push, e os dois PCs se atualizam.

## Como adicionar este marketplace ao Cowork

Em qualquer PC com Cowork instalado:

1. Abra o Cowork
2. Configuracoes -> Plugins -> Adicionar marketplace
3. Cole a URL do repo: `https://github.com/<seu-usuario>/gran-plugins`
4. Os plugins listados aparecem na loja, prontos pra instalar

## Plugins disponiveis

| Plugin | Versao | Onde roda | Descricao |
|---|---|---|---|
| passagem-turno-avaliacao | 0.1.0 | Escritorio | Avalia cards Pipefy, rituais diario+semanal |
| (em breve) survey-gran | - | Escritorio | Survey semanal de vendas |
| (em breve) survey-gran-mesa | - | Escritorio | Survey semanal Gran Mesa |
| (em breve) produtividade-gran | - | Escritorio | Custo de pessoal vs margem |
| (em breve) auditoria-caixas-gran | - | Escritorio | Auditoria semanal de caixas KW |
| (em breve) painel-guerra-diario | - | Escritorio | Painel diario operacional |
| (em breve) monitoramento-jornada-gran | - | Escritorio | Monitoramento de jornada RHID |
| (em breve) cotacao-flv-gran | - | Escritorio | Cotacao FLV via WhatsApp |
| (em breve) triagem-whatsapp-compras | - | Escritorio | Triagem do WhatsApp da Compras |

## Estrutura

```
gran-plugins/
├── .claude-plugin/
│   └── marketplace.json       <- catalogo de plugins
├── README.md
├── .gitignore
└── <nome-do-plugin>/
    ├── .claude-plugin/
    │   └── plugin.json        <- metadados do plugin
    └── skills/
        └── <nome-da-skill>/
            ├── SKILL.md       <- prompt + roteador da skill
            ├── references/
            ├── templates/
            └── scripts/
```

## Importante: dados e arquivos sensiveis NUNCA entram no repo

O `.gitignore` ja bloqueia:

- `data/` em qualquer plugin (logs, CSVs, planilhas de runtime)
- `*.xlsx`, `*.csv` (dados reais)
- `credentials.json`, `.env` (tokens, senhas)
- `snapshots/` (dumps de sistemas)
- `*.archive-*.md` (versoes arquivadas)

Esses arquivos ficam em pastas locais de cada PC OU em Dropbox sincronizado, NUNCA no Git.

## Workflow dev -> prod

1. Edita uma skill no PC pessoal (dev)
2. Roda local pra validar
3. Bumpa versao no `plugin.json` da skill afetada
4. Bumpa versao no `marketplace.json`
5. `git commit -m "skill X v0.2.0: <mudanca>"`
6. `git push`
7. No PC do escritorio: Cowork -> Plugins -> Update -> a skill nova entra em producao
