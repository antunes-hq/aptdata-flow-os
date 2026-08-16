# F1.4 — Control Plane HTTP + browser link

## WorkPacket

```text
O quê: montar o Browser Grant HTTP Adapter no flow-viz FastAPI e criar o primeiro caminho de link browser testável
Por quê: sair do core offline e abrir o run no navegador com cookie seguro, sem token de infraestrutura
Quem: flow-viz = Control Plane HTTP; aptdata-flow-os = SDK reutilizado
Quando: após F1.3 verified
Onde: /home/strondinha/lab/bora-hq/visu/labs/flow-viz + contrato neste repo
Como: dependência pública Git do aptdata-flow-os, router FastAPI fino, store SQLite separado
Quanto: local/teste primeiro; sem deploy/VPS nesta task
```

## Arquitetura obrigatória

```text
flow-viz FastAPI
  ├── importa BrowserSessionGrantStore/BrowserGrantHttpAdapter do aptdata-flow-os
  ├── mantém browser-grants.db separado do flow.db
  ├── monta /access/{grant}
  └── não duplica hashing, TTL, redeem ou cookie
```

Não copiar `aptdata/auth` para o flow-viz.

## Dependência

Adicionar dependência instalável do repositório público:

```text
git+https://github.com/antunes-hq/aptdata-flow-os.git
```

A solução deve funcionar em `uv sync`/Docker sem depender do workspace local. Se a forma de dependência precisar de ajuste por Hatch/uv, documentar e testar.

## Endpoint

Criar router FastAPI para:

```text
GET /access/{opaque_grant}
```

O endpoint deve:

- usar store SQLite em `BROWSER_GRANT_DB` (default local seguro, nunca `flow.db`);
- usar workspace configurado por `FLOW_OS_WORKSPACE_ID`;
- resolver o project/run do grant com mecanismo seguro do SDK, sem confiar em query do browser;
- chamar o adapter core ou uma extensão mínima no core, nunca duplicar regras;
- devolver `303`, cookie `HttpOnly`, `Secure` por policy e headers de segurança;
- redirecionar para `FLOW_OS_UNIVERSE_BASE_URL` + `/universe/<workspace>/<project>/<run>`;
- não deixar grant/hash na URL final;
- mapear erros para 400/401/403/405;
- não logar URL, grant, hash ou exceção sensível.

Se F1.3 precisar de uma extensão pequena para resolver contexto dinâmico do grant, alterar o core com teste de regressão e commit separado/focado; não criar lookup inseguro nem fazer `redeem` sem workspace binding.

## Emissão de link

Criar uma função/serviço puro no flow-viz para emitir link somente a partir de contexto explícito do servidor:

```python
issue_browser_link(workspace_id, project_id, run_id, scopes, base_url) -> BrowserLink
```

Regras:

- scopes padrão somente `run:read`, `flow:read`, `artifact:read`;
- rejeita escopo mutável;
- usa `BrowserSessionGrantStore.issue` do SDK;
- nunca loga raw grant;
- retorna URL opaca + expiração + contexto seguro;
- não chama Telegram real nesta task;
- incluir função de formatação de mensagem compatível com o notifier, mas enviar Telegram real fica F1.5.

## Configuração

Adicionar `.env.example`/docs sem valores reais:

```text
BROWSER_GRANT_DB=/data/browser-grants.db
FLOW_OS_WORKSPACE_ID=lucas
FLOW_OS_UNIVERSE_BASE_URL=https://flow.srv1723096.hstgr.cloud
BROWSER_GRANT_SECURE=true
```

Nunca colocar token no repo.

## Testes obrigatórios

- import do SDK via configuração de pacote/ambiente documentada;
- TestClient FastAPI para `GET /access/{grant}` válido → 303;
- cookie e headers presentes;
- URL final limpa;
- segundo uso → 401;
- grant expirado/revogado → 401;
- contexto errado → 403;
- DB separado do flow.db;
- emissão de link read-only;
- scope mutável rejeitado;
- link não contém hash/segredo além do grant opaco;
- sem chamadas reais de Telegram/rede nos testes;
- regressão da suíte existente do flow-viz;
- build Docker ou `docker compose config` se a dependência alterar build.

## Fora de escopo

```text
VPS/deploy real
Telegram Bot API real
OAuth/OIDC
CSRF completo
migração do CAPTURE_TOKEN da Nuvem
alteração da PWA My Universe
MCP público
```

## Evidência e commits

O executor deve retornar comandos e saídas reais, paths e commits.

Commits esperados, pequenos:

```text
feat(control-plane): mount browser grant route
feat(control-plane): add browser link issuer
```

O parent verifica no repo correto e só então atualiza o ledger no aptdata-flow-os.

## Executor

Executar em `/home/strondinha/lab/bora-hq/visu/labs/flow-viz`.
Não tocar em `/home/strondinha/lab/antunes-hq/nuvem` nesta task.
Não tocar no `aptdata-flow-os` além de eventual extensão core estritamente necessária e registrada.