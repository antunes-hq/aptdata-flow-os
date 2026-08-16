# F1.3 — Browser Grant HTTP Adapter

## WorkPacket

```text
O quê: criar o boundary HTTP framework-neutral para trocar Browser Session Grant por sessão de navegador
Por quê: permitir deep link seguro no Telegram sem expor CAPTURE_TOKEN ou segredo de infraestrutura
Quem: Flow OS Control Plane; framework web entra como adapter posterior
Quando: após F1.2c verified
Onde: aptdata/auth + aptdata/delivery + tests
Como: request/response puros, redeem one-shot, cookie HttpOnly, headers de segurança e deep-link contextual
Quanto: offline/local; zero rede; zero produção
```

## Descoberta obrigatória

O aptdata atual não possui FastAPI/Starlette nem servidor HTTP do Control Plane no core. Não adicionar framework web obrigatório nesta fatia.

Implementar contratos puros que possam ser montados depois em FastAPI, Starlette, Flask ou ASGI.

## Contrato

Criar um adapter com operação equivalente a:

```python
class BrowserGrantHttpAdapter:
    def redeem_access_request(
        self,
        request: BrowserGrantHttpRequest,
    ) -> BrowserGrantHttpResponse: ...
```

### Request

```text
method
path
query: mapping
headers: mapping
remote_address opcional
```

### Response

```text
status_code
headers
body
session metadata opcional — nunca raw grant
```

## Fluxo de troca

```text
GET /access/<opaque-grant>
  → extrair grant uma única vez
  → store.redeem(grant, workspace/run esperado)
  → gerar cookie browser_session_id
  → resposta 303 para /universe/<workspace>/<project>/<run>
  → apagar grant da URL
```

Em erro:

```text
400 grant ausente/malformado
401 grant inválido/expirado/revogado
403 contexto ou scope incompatível
405 método não permitido
```

O corpo de erro deve ser curto, estável e nunca incluir:

```text
raw grant
hash do grant
CAPTURE_TOKEN
FLOW_MCP_TOKEN
stack trace
```

## Segurança obrigatória

A resposta de troca deve incluir:

```text
Cache-Control: no-store
Pragma: no-cache
Referrer-Policy: no-referrer
X-Content-Type-Options: nosniff
Set-Cookie: browser_session_id=<opaque-session>; Path=/; HttpOnly; Secure configurável; SameSite=Lax; Max-Age=<ttl>
```

Regras:

- grant é consumido mesmo se a resposta de redirect for repetida;
- redirect remove o grant da URL;
- `Secure=True` por default no modo production; configurável somente por policy explícita;
- o adapter nunca imprime ou loga a URL completa;
- não aceitar grant via `Referer`, body ou header alternativo nesta fatia;
- workspace/project/run esperados vêm de configuração/route assinada, nunca de confiança cega no query;
- `approval:respond`, deploy e scopes mutáveis ficam fora do grant read-only;
- `run:read`, `flow:read`, `artifact:read` são os scopes default permitidos;
- qualquer scope mutável é rejeitado pelo adapter.

## Integração com o store

Reusar:

```text
BrowserSessionGrantStore.redeem
BrowserSessionResponse / SessionCookie
```

Não duplicar hashing, TTL, revogação ou validação de sessão.

## Critérios de aceite

```text
1. request válida retorna 303
2. resposta tem Set-Cookie HttpOnly
3. resposta tem Secure conforme policy
4. resposta tem no-store/no-referrer/nosniff
5. Location não contém o grant
6. segundo request com mesmo grant falha 401
7. grant ausente/malformado retorna 400
8. grant expirado/revogado/inválido retorna 401 sem segredo
9. contexto incorreto retorna 403
10. método diferente de GET retorna 405
11. scope mutável é rejeitado
12. body de erro não contém raw grant/hash/stack trace
13. URL completa não é logada
14. testes não usam rede, FastAPI, Starlette ou credenciais
15. aptdata/mcp/server.py e Nuvem não são tocados
```

## Fora de escopo

```text
servidor HTTP real
FastAPI/Starlette dependency
Telegram Bot API
emissão de grant via bot
deploy/VPS
My Universe frontend
OAuth/OIDC
CSRF completo de sessão autenticada
```

## Evidência obrigatória

```text
focused pytest
full pytest
ruff
diff/escopo
commit SHA
```

## Executor

Executor free. Implementar em `/home/strondinha/lab/bora-hq/aptdata-flow-os`.

Commit focado:

```text
feat(auth): add browser grant HTTP boundary
```

O parent faz a verificação independente antes de alterar o ledger para `verified`.
