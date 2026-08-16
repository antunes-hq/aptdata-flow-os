# F1.5 — Browser Session Consumer Bridge

## Problema

F1.4 redime o grant no Control Plane, mas o cookie não era consumido pela PWA:

```text
central.srv → cookie host-only → redirect flow.srv → PWA pede CAPTURE_TOKEN
```

Isso autentica o redirect, mas não o My Universe.

## Contrato

```text
Cookie: browser_session_id=<opaque session id>
Domain: .srv1723096.hstgr.cloud
Path: /
HttpOnly; Secure; SameSite=Lax

flow-capture GET /cloud:
  aceita browser_session_id + sessão válida + scope flow:read
  rejeita cookie inválido/expirado/revogado/contexto errado
  mantém CAPTURE_TOKEN para escrita e demais endpoints

PWA:
  tenta GET /cloud com credentials=same-origin sem ler cookie
  se sucesso, entra em modo read-only browser
  se falha, mantém onboarding/token legado
  nunca persiste browser_session_id
  nunca envia CAPTURE_TOKEN via browser grant
```

## Não-goals

- não transformar browser session em CAPTURE_TOKEN;
- não permitir `/capture`, `/pending`, `/ack` ou `POST /cloud` via browser session;
- não expor sessão no localStorage/frontend;
- não alterar flow.db;
- não enviar Telegram nesta fatia;
- não deployar sem gate independente.

## Critérios de aceite

1. Cookie Domain é configurável e não altera o padrão atual quando ausente.
2. `GET /cloud` com sessão válida e `flow:read` retorna cloud JSON.
3. Sessão inválida, expirada, revogada, workspace errado ou sem scope retorna 401.
4. Browser session não autoriza escrita nem endpoints de inbox.
5. PWA carrega `/cloud` com credentials sem acessar cookie HttpOnly.
6. PWA não grava browser session em localStorage.
7. Sem cookie válido, fluxo legado de token continua funcionando.
8. Testes offline cobrem os critérios; nenhum segredo real é usado.
9. SDK, flow-capture e PWA têm testes/build verdes.
10. Deploy só após verificação independente e smoke browser real.

## Evidência obrigatória

```text
arquivos + diff
focused tests
full suites/build
lint/config
commits e SHAs
smoke real: link → 303 → PWA carrega cloud em read-only
risco residual e rollback
```

## Estado

```text
Status: in_progress
SDK commit: pendente
Server commit: pendente
PWA commit: pendente
Deploy: pendente
Smoke browser: pendente
```

## Rollback

```text
remover a rota de leitura por browser session
remover o fallback de credentials na PWA
restaurar a referência anterior do SDK
manter CAPTURE_TOKEN legado intacto
```
