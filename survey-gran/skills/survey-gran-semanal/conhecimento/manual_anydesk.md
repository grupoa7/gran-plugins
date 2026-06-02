# Manual AnyDesk · Survey Gran

Manual completo e consolidado para conexão AnyDesk com a SAMSUNG (servidor remoto que mantém Chrome logado no KW). Não é stub — toda informação operacional fica aqui.

## Acesso

| Item | Valor |
|---|---|
| ID AnyDesk SAMSUNG | `305817889` |
| Senha | `TIRAPREÇO` |
| Sistema operacional | Windows |
| Owner | Hugo (Grupo A7) |
| Propósito | manter Chrome com sessão KW autenticada disponível remotamente |

## Conexão padrão

1. Abrir AnyDesk no Mac do Hugo.
2. Inserir ID `305817889`.
3. Quando solicitado, inserir senha `TIRAPREÇO` (atenção ao Ç).
4. Aguardar handshake (~5-15s típico).
5. Confirmar visualmente: tela da SAMSUNG visível, Chrome aberto com KW na aba.

Se a conexão falhar (timeout, "device offline"):
- Confirmar com Hugo se a SAMSUNG está ligada e online.
- Aguardar 30s e tentar de novo (latência inicial pode dar timeout).
- Se persistir, **PARAR** e pedir Hugo verificar fisicamente.

## Estado preservado entre sessões

A SAMSUNG mantém:
- Chrome aberto com KW logado (geralmente 24-72h até a sessão expirar).
- Pasta `C:\Users\<USERNAME>\Downloads\` com extrações anteriores.
- Estado de scripts Python em `C:\Users\<USERNAME>\Downloads\`.

**Não fechar o Chrome após uso** — Hugo precisa dele logado para próximas extrações.

Se a sessão KW expirou (login screen no Chrome):
- Pedir Hugo logar manualmente via AnyDesk (dentro da própria sessão remota).
- Após login, retomar fluxo.
- Não tentar automatizar login: senhas não são entradas via Cowork por política de segurança.

## Cuidados operacionais

| Risco | Mitigação |
|---|---|
| Sleep mode da SAMSUNG | Hugo deve manter "nunca dormir" no Plano de Energia do Windows. Se dormir, AnyDesk falha — Hugo precisa acordar fisicamente. |
| Mac do Hugo dorme durante extração longa | Manter Mac aberto/cafeinado durante `/survey`. Migração futura para cloud resolve. |
| Conexão AnyDesk cai no meio | Reconectar — o estado Python na SAMSUNG continua. Retomar do ponto. |
| Múltiplas sessões AnyDesk simultâneas | Conflitam. Sempre 1 sessão ativa por vez. |
| Antivírus corporativo na SAMSUNG | Pode bloquear `browser_cookie3` lendo cookies do Chrome. Se acontecer, exportar cookies via DevTools manualmente. |
| Latência alta | Não afeta extração via Python (ela roda local na SAMSUNG). Afeta só interação visual via AnyDesk. |

## Caminhos relevantes na SAMSUNG

```
C:\Users\<USERNAME>\Downloads\           ← scripts Python e CSVs (cache)
C:\Program Files\Google\Chrome\          ← Chrome
%APPDATA%\Local\Google\Chrome\User Data\Default\Network\Cookies  ← cookies (lidos por browser_cookie3)
```

`<USERNAME>` é o usuário Windows da SAMSUNG. Para descobrir:

```cmd
echo %USERNAME%
```

## Verificações antes de iniciar extração

1. Chrome aberto na SAMSUNG? Visível na tela.
2. Aba do KW logada? Olhar canto superior direito — nome do usuário visível.
3. Python disponível? `python --version` retorna ≥3.8.
4. Bibliotecas instaladas? `pip show requests pandas browser_cookie3` lista todas.

Se qualquer um falhar, ler `extracao_kw_anydesk.md` (Fase 0 cobre instalação).

## Transferência de arquivos SAMSUNG → Mac

3 opções, em ordem de preferência:

1. **OneDrive sincronizado** — se a pasta Downloads da SAMSUNG sincroniza com o OneDrive do Hugo, o CSV aparece no Mac em segundos. Verificar uma vez se o sync está ativo.
2. **Clipboard transfer do AnyDesk** — abrir CSV no Notepad da SAMSUNG, Ctrl+A Ctrl+C, colar no Mac. Limite ~10MB de texto, ok pra CSVs até ~100k linhas.
3. **Email/upload manual** — último recurso. Hugo anexa o CSV num email pra si mesmo, baixa no Mac.

Destino final no Mac: `~/Documents/SurveyGran/extracoes/incoming/`. O `pipeline_consolidacao.py` lê dessa pasta automaticamente.
