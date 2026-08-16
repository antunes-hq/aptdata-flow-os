# F1.2c — Browser Session Grant

## WorkPacket

```text
O quê: implementar grant temporário de sessão de navegador para abrir um run autorizado
Por quê: permitir acompanhamento via browser sem enviar CAPTURE_TOKEN ou segredo de infraestrutura
Quem: Flow OS Control Plane/local SDK; browser é consumidor autorizado
Quando: terceira fatia da F1.2
Onde: aptdata/auth + aptdata/delivery + tests
Como: token opaco hash-only, TTL, one-shot, scopes, workspace/run binding e troca por sessão
Quanto: offline/local; zero rede; zero tokens reais
```

## Escopo

Implementar um serviço local/testável de grants:

- `BrowserSessionGrant` com identificador opaco retornado uma única vez;
- armazenamento somente do hash do grant;
- `workspace_id`, `project_id`, `run_id`, `scopes`, `telegram_user_id` opcional;
- TTL configurável com default seguro;
- criação;
- troca one-shot por sessão autorizada;
- validação/obtenção de sessão por `session_id`;
- expiração;
- revogação explícita de grant e sessão;
- sessão com `session_id` opaco e expiração;
- validação de workspace/run/scope no servidor;
- cookie/header recomendado em estrutura de resposta, sem servidor HTTP ainda;
- erros determinísticos e sem vazamento do valor bruto.

## Fora de escopo

- deploy/VPS;
- alteração da Nuvem atual;
- migração do `CAPTURE_TOKEN`;
- Telegram Bot API;
- OAuth/OIDC;
- FastAPI/Starlette obrigatório;
- browser real;
- MCP;
- produção.

## Contrato mínimo

```python
class BrowserSessionGrantStore:
    def issue(*, workspace_id, project_id, run_id, scopes,
              telegram_user_id=None, ttl_seconds=None) -> str: ...
    def redeem(raw_grant, *, workspace_id, run_id=None, required_scopes=()) -> BrowserSession: ...
    def get_session(session_id, *, workspace_id, run_id=None,
                    required_scopes=()) -> BrowserSession: ...
    def revoke(raw_grant) -> bool: ...
    def revoke_session(session_id) -> bool: ...
```

`BrowserSession` deve expor somente metadados seguros:

```text
session_id
workspace_id
project_id
run_id
scopes
created_at
expires_at
```

Regras:

- raw grant tem entropia criptográfica e não é persistido;
- persistência usa SHA-256/HMAC do grant;
- `redeem` com grant válido consome o grant imediatamente;
- segunda troca falha;
- grant expirado falha;
- workspace diferente falha;
- run diferente, quando informado, falha;
- scope ausente falha;
- grant revogado falha;
- sessão inexistente falha;
- sessão expirada falha;
- sessão revogada falha;
- `get_session` revalida workspace/run/scopes no servidor;
- comparações de segredo usam comparação constante;
- `repr`, exceções e logs nunca mostram raw grant;
- nenhum segredo de provider entra no objeto.

## Persistência

Pode usar SQLite stdlib ou store in-memory com interface. Se SQLite for escolhido:

- tabela versionada;
- índice por hash;
- timestamps UTC ISO ou epoch consistente;
- `redeem` atômico para garantir one-shot;
- testes de fechar/reabrir;
- nenhum valor bruto do grant na base.

## Critérios de aceite

```text
1. issue retorna grant opaco não vazio
2. store não contém o grant bruto
3. redeem válido retorna sessão com escopo/contexto correto
4. redeem repetido falha
5. grant expirado falha
6. workspace mismatch falha
7. run mismatch falha
8. scope ausente falha
9. revoke impede redeem
10. get_session rejeita sessão expirada
11. get_session rejeita sessão revogada
12. revoke_session funciona
13. tokens/grants não aparecem em repr/erro/log capturado
14. dois grants para o mesmo run são independentes
15. SQLite/in-memory persiste e reabre, se aplicável
16. testes não usam rede nem credenciais reais
17. nenhum arquivo da Nuvem, MCP server ou produção é tocado
```

## Evidência obrigatória

```text
focused pytest
full pytest
ruff
path/diff scope
commit SHA
```

## Executor

Executor free do pool. Implementar em `/home/strondinha/lab/bora-hq/aptdata-flow-os`. Fazer commit focado:

```text
fix(auth): validate redeemed browser sessions
```

O parent vai verificar independentemente antes de marcar `verified`.
