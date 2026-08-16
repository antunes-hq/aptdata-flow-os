# F1.2b — Telegram Notifier Read-only

## WorkPacket

```text
O quê: consumir FlowEvent/OutboxMessage e entregar notificações Telegram read-only
Por quê: avisar Lucas sobre início, checkpoint, bloqueio e conclusão sem perder eventos ou expor segredos
Quem: Flow OS delivery adapter; Telegram é canal, não fonte de verdade
Quando: segunda fatia da F1.2
Onde: aptdata/delivery/telegram_notifier.py + tests
Como: client injetável, formatter por event_type e worker de uma mensagem por vez
Quanto: zero token real nos testes; rede somente em integração explícita
```

## Escopo

Implementar:

- `TelegramNotifier` com client HTTP injetável;
- formatter de eventos `run.started`, `stage.completed`, `checkpoint`, `approval.required`, `run.blocked`, `run.completed`;
- consumo de `OutboxMessage` claimado;
- sucesso marca `sent`;
- falha marca `failed` com erro sanitizado;
- payload Telegram com `chat_id`, `text` e `disable_web_page_preview`;
- token somente via construção explícita/env no adapter, nunca no payload do evento/log;
- limite de tamanho de mensagem;
- testes offline com fake client.

## Fora de escopo

- polling de updates;
- callbacks de aprovação;
- Browser Session Grant;
- deploy/VPS;
- alteração da Nuvem;
- chamada real à API Telegram nos testes;
- criação de novo `TelegramTransport` de conversa.

## Reuso obrigatório

Reusar o contrato e storage existentes:

```text
aptdata.events.models.FlowEvent
aptdata.delivery.outbox.DurableOutbox
aptdata.transports.telegram (somente convenções/client se compatível)
```

Não duplicar `ConversationEngine`, roteamento ou sessão de conversa.

## Comportamento

```text
claim_pending(channel=telegram)
  → format event
  → client.send_message(chat_id, text, options)
  → mark_sent

HTTP/transport failure
  → mark_failed
  → não levantar para derrubar worker
```

Idempotência vem do outbox. O notifier não deve enfileirar duplicatas.

## Segurança

- token nunca aparece em `FlowEvent`, `OutboxMessage.payload_json`, formatter ou logs;
- `chat_id` vem de configuração explícita;
- texto deve redigir padrões óbvios de bearer/API key;
- mensagens não incluem transcript bruto ou metadata privada desnecessária;
- não usar `--dangerously-skip-permissions` ou CLI Telegram;
- cliente HTTP tem timeout configurável.

## Critérios de aceite

```text
1. run.started gera mensagem humana curta
2. checkpoint inclui próximo passo
3. approval.required inclui ação/risco/expiração sem token
4. run.completed inclui resultado/evidência refs
5. evento desconhecido usa fallback legível
6. mensagem longa é limitada
7. fake client recebe chat_id/text/options corretos
8. sucesso marca outbox sent
9. falha marca outbox failed e retorna resultado estruturado
10. token não aparece em nenhum payload/log capturado
11. testes não usam rede
12. aptdata/transports/telegram.py existente não é reimplementado
```

## Evidência requerida

```text
pytest focused + full suite
ruff focused
git diff --name-only
commit SHA
```

O parent verifica tudo antes de mudar o ledger para `verified`.

## Executor

Executor free do pool. Implementar no path absoluto `/home/strondinha/lab/bora-hq/aptdata-flow-os`. Ler este contrato antes de editar. Fazer commit focado `feat(delivery): add Telegram outbox notifier`.