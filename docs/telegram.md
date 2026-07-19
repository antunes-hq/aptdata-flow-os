# Telegram — conversa fluida com o ecossistema

O canal Telegram é um **transporte fino** sobre o
`ConversationEngine`: ele só renderiza cards e botões — toda decisão de rota,
threshold e estado de conversa vive no aptdata
(`docs/plans/telegram-orchestration.md`).

## Setup em 3 passos

1. **Crie o bot** com o [@BotFather](https://t.me/BotFather) e exporte o
   token (o aptdata **nunca** grava o token em arquivo):

    ```bash
    export TELEGRAM_BOT_TOKEN="123456:ABC-DEF..."
    ```

2. **Rode o wizard** — ele valida o token (`getMe`), pergunta o chat id e
   grava o bloco `transports:` no `agents.yaml` (só o *nome* da env var):

    ```bash
    aptdata setup
    aptdata setup --check --json   # confere tudo (CI-friendly)
    ```

3. **Suba o bot** (long-polling, sem dependência extra):

    ```bash
    aptdata telegram
    ```

## Como a conversa funciona

Cada mensagem vira um turno do engine, com a política do bloco `routing:` do
`agents.yaml`:

| Você manda | O bot responde |
|---|---|
| `/ondina arruma o header` | despacho direto + resposta inline |
| `mexer no frontend` (match forte) | despacho direto |
| texto ambíguo (match médio / LLM) | card `🧭 agente · skill · conf` + botões **✅ Confirmar** / **→ trocar de agente** |
| sem sinal nenhum | pergunta de esclarecimento |
| `/hermez deploy` (capability guardada) | **sempre** pede confirmação — deploy/ssh/docker ignoram confiança |
| `continua` | reusa o último agente da sessão (multi-turno) |

Sessões seguem o chat (`tg-<chat_id>`) e persistem em
`~/.aptdata/sessions`. Cada decisão, confirmação (`permission.requested` /
`permission.resolved`) e dispatch entra no
[traço de observabilidade](observability.md) — visível no
`aptdata obs tail`, no painel `aptdata studio` (SSE ao vivo) e na TUI.

## Configuração

| Onde | O quê |
|------|-------|
| env `TELEGRAM_BOT_TOKEN` | token do bot (obrigatório; nome da var configurável com `--token-env`) |
| `agents.yaml → transports.telegram.chat_id` | chat/grupo padrão |
| `agents.yaml → routing:` | thresholds (`dispatch_above`) e `guarded_capabilities` |
