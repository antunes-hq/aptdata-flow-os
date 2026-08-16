# F1.2a — Event Envelope + Durable Outbox

## WorkPacket

```text
O quê: criar o contrato mínimo de eventos e outbox para notificar Telegram/navegador sem perder estado
Por quê: separar estado canônico da entrega e impedir notificações silenciosas ou duplicadas
Quem: Flow OS kernel; Telegram/browser são consumidores posteriores
Quando: primeira fatia executável da F1.2
Onde: aptdata-flow-os/aptdata/events + aptdata/delivery + tests
Como: envelope versionado + SQLite outbox idempotente + testes de contrato
Quanto: zero provider externo; zero token; offline/local
```

## Escopo

Implementar somente:

- `FlowEvent` serializável e versionado;
- `OutboxMessage` persistente em SQLite;
- idempotência por `event_id` + `channel`;
- estados `pending`, `sent`, `failed`;
- retry seguro sem duplicar mensagem;
- leitura de mensagens pendentes;
- marcação de entrega com timestamp e erro sanitizado;
- testes determinísticos.

## Fora de escopo

- Telegram API;
- Browser Session Grant;
- OAuth;
- deploy/VPS;
- alteração da Nuvem;
- MCP público;
- qualquer segredo.

## Contrato `FlowEvent`

Campos obrigatórios:

```text
event_id
schema_version
event_type
workspace_id
project_id
run_id
severity
human_summary
created_at
```

Campos opcionais:

```text
flow_definition_id
stage_id
next_action
evidence_refs
metadata
```

Regras:

- `event_id` é fornecido pelo produtor ou gerado pelo SDK;
- `created_at` é timezone-aware UTC;
- payload não contém secrets;
- `metadata` é JSON serializável;
- evento é imutável depois de publicado.

## Contrato `OutboxMessage`

```text
message_id
event_id
channel
status
attempts
payload_json
created_at
sent_at
last_error
```

Regras:

- unique `(event_id, channel)`;
- `enqueue` repetido retorna o registro existente;
- somente `pending` e `failed` podem ser reclamados;
- `claim_pending` incrementa attempts de maneira transacional;
- `mark_sent` é idempotente;
- erro armazenado é limitado e não inclui tokens;
- nenhuma chamada de rede ocorre dentro do storage.

## Critérios de aceite

```text
1. evento válido round-tripa JSON sem perder campos
2. evento inválido falha com erro determinístico
3. enqueue cria uma mensagem pending
4. enqueue repetido não duplica
5. claim retorna pending e incrementa attempts
6. mark_sent muda para sent e registra sent_at
7. mark_failed registra erro sanitizado
8. mensagem sent não volta para pending
9. dois canais para o mesmo evento são independentes
10. storage sobrevive ao fechamento/reabertura SQLite
11. testes não usam rede nem tokens
12. pacote não altera aptdata/mcp/server.py nem Nuvem
```

## Evidência requerida

```text
pytest command + stdout
ruff check command + stdout
git diff --stat
git commit SHA
paths changed
```

O ledger só pode marcar `verified` depois da verificação no workspace pai.

## Executor

Executor free do pool. Não usar Claude Code, OpenCode ou qualquer CLI paga. O implementador deve fazer commit próprio somente dos arquivos desta task e retornar o SHA.