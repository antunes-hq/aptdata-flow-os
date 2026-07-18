# Plano de Limpeza de PRs — strondata/smart-data (aptdata)

> Gerado em 2026-06-30. **Somente plano** — nenhuma alteração foi executada em PRs, branches remotos ou main.
> Convenção do repo: publicado, tudo via branch+PR, **nunca commit direto na main**.
> **Auth:** `gh` não instalado e sem token no ambiente. Toda LEITURA aqui foi via API pública não autenticada.
> A EXECUÇÃO (fechar/mergear PR, deletar branch remoto) exige `gh auth login` ou `GH_TOKEN` — marcado com 🔑 abaixo.

## Panorama

- **28 PRs abertos**, quase todos gerados por frota de agentes autônomos (autor `Lucasa22`), fortemente duplicados.
- main HEAD = `3d323f3`. **Só o #65 está calculado como `mergeable=True`** porque é o único cujo base já é a main atual.
- Todos os outros 27 voltam `mergeable=None` / `mergeable_state=unknown`: foram abertos sobre bases antigas (`155b575`, `051ec63`, `9abd108`, `0aecdbc`, `341cb32`) e o GitHub não recomputou — na prática **vão conflitar entre si**, porque os grupos duplicados tocam os MESMOS arquivos (`aptdata/mcp/server.py`, `aptdata/cli/commands/mesh_cmd.py`, `.github/workflows/*.yml`, `poetry.lock`, `pyproject.toml`).
- Problema estrutural (bate com o "3 registros divergentes" da memória): o mesmo agente QA/DX foi implementado em **4 diretórios diferentes** entre PRs — `aptdata/qa/`, `aptdata/agents/`, `aptdata/plugins/qa/`, `aptdata/cli/commands/agents/`. E CHORE-002 (hygiene) x CHORE-003 (QA/DX) se sobrepõem quase por completo.

**Resumo numérico:** 28 abertos → **fechar 17**, **manter/revisar 11**.

---

## 1. Triagem por tema

### 1a. QA/DX — CHORE-003 (8 PRs) → manter **#63**, fechar 7
Mesmo agente QA/DX reimplementado em locais divergentes. #63 é o mais completo e recente: 757 insersões, 9 arquivos, inclui os dois workflows (`code-hygiene.yml` + `pr-review.yml`), comando CLI dedicado (`qa_agent_cmd.py`) e o agente em `aptdata/qa/` (local canônico, mesmo do #33).

| PR | branch | ins/arq | local do agente | decisão |
|----|--------|---------|-----------------|---------|
| **#63** | chore/qa-dx-agent-003-…5483865 | 757/9 | `aptdata/qa/` | **MANTER** (mais completo + recente) |
| #62 | feat/continuous-code-hygiene-…4038 | 330/5 | `cli/commands/agents/` | fechar (subconjunto, local divergente) |
| #61 | qa-dx-agent-…788346 | 747/8 | `aptdata/plugins/qa/` | fechar (quase-dup do #63, local divergente) |
| #58 | feature/chore-003-…513050 | 488/5 | `aptdata/agents/` | fechar |
| #56 | chore/qa-dx-agent-…233522 | 446/7 | `aptdata/agents/` | fechar |
| #53 | chore/qa-dx-agent-…247481 | 539/5 | `aptdata/agents/` | fechar |
| #51 | feature/qa-dx-agent-…345499 | 437/4 | `aptdata/plugins/qa/` | fechar |
| #33 | chore/qa-dx-agent-…343871 | 530/6 | `aptdata/qa/` | fechar (mesmo local do #63 mas menor/mais antigo; tem `scripts/post_qa_review.py` único — ver §4) |

**Fechar:** #62 #61 #58 #56 #53 #51 #33.

### 1b. Code hygiene — CHORE-002 (5 PRs) → manter **#45**, fechar 4
Mesmo scanner de hygiene em locais divergentes. #45 é o único com **testes** (`tests/test_hygiene.py`) e coloca a lógica em `aptdata/core/hygiene.py` (local mais sensato que `agents/qa.py` ou `plugins/qa/`).

| PR | branch | ins/arq | destaque | decisão |
|----|--------|---------|----------|---------|
| **#45** | chore-002-continuous-hygiene-…964868 | 562/7 | `core/hygiene.py` + `tests/test_hygiene.py` | **MANTER** (tem testes + local canônico) |
| #57 | feat/chore-002-code-hygiene-…107626 | 658/7 | `aptdata/agents/qa.py` | fechar (maior mas sem teste, local divergente) |
| #55 | chore/continuous-code-hygiene-…398494 | 261/8 | `plugins/qa/llm_agent.py` + `hygiene_report.md` (artefato) | fechar |
| #52 | chore-002-code-hygiene-…388847 | 452/6 | `cli/commands/lint_cmd.py` | fechar |
| #47 | feature/code-hygiene-automation-…435517 | 451/6 | `core/hygiene.py` | fechar (mesmo local do #45, sem teste) |

**Fechar:** #57 #55 #52 #47.
⚠️ **#45 e #63 se sobrepõem** em `code-hygiene.yml`, `mesh_cmd.py` e `mcp/server.py`. Não dá pra mergear os dois cegamente. **Recomendação:** tratar CHORE-002+CHORE-003 como UMA entrega — mergear #63 primeiro, depois rebasear #45 e manter só o delta de `core/hygiene.py`+testes que não colidir. Se der muito atrito, fechar os dois e reabrir um único PR deliberado.

### 1c. Docs / DevPortal (9 PRs) → manter **#40**, salvar 3, fechar 5
Estes **não** são todos duplicados puros — vários tocam arquivos diferentes. #40 ("phases 3-5 modernization") é o carro-chefe: 540 ins, adiciona logo/favicon SVG, termynal, CSS custom, mermaid theming.

| PR | branch | ins/arq | conteúdo | decisão |
|----|--------|---------|----------|---------|
| **#40** | docs-evolution-mermaid-premium-…901477 | 540/11 | assets + CSS + termynal + governance/index | **MANTER** como base visual. ⚠️ remove `.cache/plugin/social/manifest.json` (artefato de build, não versionar) |
| #50 | docs-evolution-…636346 | 138/5 | **tradução API ref → pt-BR** + notebook | **SALVAR** (conteúdo único; cherry-pick, não fechar) |
| #42 | docs-evolution-…829346 | 188/7 | README + contributing + `transform-engines.md` | **SALVAR** (conteúdo único) |
| #34 | chore-004-docs-agent-prompt-…535404 | 39/1 | `docs/prompts/docs-agent.md` (prompt do agente) | **SALVAR** (não é doc de produto; útil pro guardrail §5) |
| #64 | docs-evolution-…585893 | 22/6 | reescrita concisa (architecture/config/getting-started) | fechar (subset) |
| #60 | docs-evolution-…911917 | 34/7 | reescrita concisa (mesmos arquivos + mkdocs) | fechar (subset) |
| #59 | docs-evolution-…007162 | 9/1 | só getting-started | fechar (trivial, subset do #40) |
| #54 | docs-evolution-…606629 | 87/7 | mexe em `poetry.lock`/`pyproject.toml` p/ docs | fechar (arriscado, subset) |
| #46 | docs-evolution-…176014 | 44/3 | architecture/diys/getting-started | fechar (subset) |

**Fechar:** #64 #60 #59 #54 #46. **Salvar (manter aberto p/ cherry-pick):** #50 #42 #34.

### 1d. Outros (isolados) — avaliar 1 a 1
| PR | tema | ins/arq | decisão |
|----|------|---------|---------|
| **#65** | agents-core (adapter OpenClaw) | +1888/16 | **PRIORIDADE** — ver §2 |
| #49 | SparkExecutor + UDPTelemetryListener | 131/4 | manter/avaliar (feature única) |
| #29 | 01_soccer_medallion (exemplo + contratos) | 157/9 vs main (6 commits) | manter/avaliar (projeto-exemplo único) |
| #28 | script de teste CLI e2e + Makefile | 120/4 | manter (infra de teste útil) |
| #27 | cobertura de teste do PluginManager.load_module | 24/1 | manter (pequeno, útil, baixo risco) |
| #48 | "Architectural Analysis" | **0/0** | **FECHAR** — PR VAZIO, sem arquivos |

**Fechar:** #48.

---

## 2. #65 agents-core — PRIORIDADE (tratamento à parte)

- Estado: `mergeable=True`, `mergeable_state=unstable`, 4 commits, +1888/-1, 16 arquivos. Base já é a main atual (`3d323f3`) — **não precisa rebase**.
- `unstable` = mergeável, mas **CI falhando**. Checks no head `8f71e55`:
  - ✅ Integration / E2E / Plugin tests (3.10/3.11/3.12) → todos **success**
  - ⏭️ "Full test suite + coverage" → **skipped**
  - ❌ **Lint (ruff)** → **failure**
  - ❌ **CLI tests (Python 3.12)** → **failure**; CLI 3.10/3.11 → **cancelled** (fail-fast por causa do 3.12)
- **Para destravar:** rodar localmente `ruff check aptdata/` (corrigir lint) e a suíte de CLI tests em 3.12; corrigir e dar push no mesmo branch. É bloqueio de qualidade, não de conflito.
- **Branch órfão possivelmente relevante:** `fix/ci-lint-tests-17074594136311155205` existe no remoto sem PR aberto — pode conter exatamente o fix de ruff/CLI. Checar antes de reescrever do zero.

### Mudanças locais não commitadas (working tree em `feat/agents-core` = branch do #65)
591 linhas não commitadas: `aptdata/agents/base.py` (+19), `cli_agents.py` (+266), `openclaw.py` (+357).
- Adicionam: `adapter_type` no `AgentSpec` (telegram/internal/http), campos de token Telegram, `_TelegramPollingMixin`, e reescrevem `OpenClawAgent` em 3 modos + `ClaudeCodeAgent`/`OpenCodeAgent`.
- **Onde encaixar:** é continuação natural do #65 (mesmo tema, mesmo branch). Recomendo **commitar no #65** como commit(s) adicional(is) — mas SÓ depois de corrigir o item abaixo, senão entra defeito factual no PR de prioridade.
- 🚩 **CORREÇÃO OBRIGATÓRIA de docstring/arquitetura** em `openclaw.py`: a versão não commitada afirma que cada worker OpenClaw roda um "Gateway em loopback na **porta 18789**", que **não existe `/api/chat`**, e marca o modo HTTP como "BROKEN by design". Isso está **factualmente errado**: o OpenClaw real é **Node**, expõe um **`/ws` (WebSocket) real** e roda nas **portas 48330-48333**. Antes de commitar no #65:
  1. corrigir o docstring do módulo e da classe (portas 48330-48333, transporte `/ws` real, é Node e não Go);
  2. reavaliar se o modo `openclaw_http` deve mesmo ser "broken by design" ou se o transporte correto é WebSocket `/ws` (provavelmente um 4º modo `openclaw_ws` ou substituir o http);
  3. só então `git add` + commit + push no branch `feat/agents-core`.
- Alternativa: se a correção for grande, virar **PR separado** encadeado sobre o #65 já mergeado — mas o mais simples é consertar e incluir no #65.

---

## 3. Ordem de execução (concreta e reversível)

Pré-requisito de execução: 🔑 `gh auth login` (ou exportar `GH_TOKEN`). Sem isso, só leitura.

1. **#65 primeiro (destravar prioridade):**
   - `ruff check aptdata/` local → corrigir; rodar CLI tests 3.12 local → corrigir.
   - Checar `fix/ci-lint-tests-…155205` (pode já ter o fix).
   - Corrigir o docstring de `openclaw.py` (portas 48330-48333, `/ws`, Node) → `git add aptdata/agents/{base,cli_agents,openclaw}.py` → commit → `git push lucas feat/agents-core`.
   - Confirmar CI verde → 🔑 mergear #65.
2. **Fechar duplicados com comentário** (reversível: fechar ≠ deletar; reabre a qualquer momento). 🔑 Para cada PR abaixo, comentar "fechando como duplicado de #<mantido>; conteúdo consolidado lá" e fechar:
   - QA/DX: #62 #61 #58 #56 #53 #51 #33 → apontar p/ **#63**
   - Hygiene: #57 #55 #52 #47 → apontar p/ **#45**
   - Docs: #64 #60 #59 #54 #46 → apontar p/ **#40**
   - Vazio: #48 → fechar sem substituto
   - (comando por PR: `gh pr close <n> -c "duplicado de #<x>"`)
3. **Consolidar QA/Hygiene:** rebasear **#63** na main, resolver, 🔑 mergear. Depois rebasear **#45** sobre a main nova, manter só delta de `core/hygiene.py`+testes que não colide com #63; mergear ou fechar se virar redundante.
4. **Docs:** rebasear **#40**, remover `.cache/plugin/social/manifest.json`, mergear. Cherry-pick o conteúdo único de **#50** (pt-BR), **#42** (README/transform-engines) e **#34** (prompt) — mergear individualmente ou consolidar num PR "docs-consolidado".
5. **Isolados:** revisar e decidir #49, #29, #28, #27 individualmente (não são urgentes).
6. **Higiene de branches (§4)** por último, só depois que cada PR correspondente estiver fechado/mergeado.

**Reversibilidade:** fechar PR preserva o branch e o diff; nada se perde até deletar o branch remoto (passo 6). Não deletar branch de PR que ainda contenha conteúdo único não cherry-pickado.

---

## 4. Higiene de git / branches

### Branches remotos SEM PR aberto (candidatos a deletar após confirmar merge/abandono) 🔑
- `copilot/fix-flowchart-syntax`
- `copilot/implement-plugins-ecosystem`
- `docs-evolution-8390564041959816046`
- `docs-evolution-theme-modernization-8088324244489629830`
- `docs/adr-001-revisao-arquitetural-core-8611048766059122414`
- `fix/ci-lint-tests-17074594136311155205` → **NÃO deletar ainda** — pode ter o fix de CI do #65 (§2)
- `qa-fixes-feature/qa-dx-agent-10495899374624345499`
- `refactor-soccer-medallion-15966167423209595213`
- `jules-7272914940660133706-e77a37b6` (só em `origin`)

Verificar antes de deletar: `git branch -r --merged lucas/main` lista os já integrados (deleção segura). Para cada não-merged, `git log lucas/main..lucas/<branch> --oneline` mostra se tem trabalho único.

### ⚠️ NÃO deletar
- `gh-pages` — é o site de docs publicado.
- `main` — default.
- Qualquer branch de PR que ainda estiver aberto ou com conteúdo único pendente de cherry-pick (#50, #42, #34, #45, #29, #49, #28, #27).

### Risco de perder trabalho ao fechar
- Conteúdo ÚNICO a preservar antes de fechar/deletar: #50 (tradução pt-BR), #42 (transform-engines/README), #34 (prompt docs-agent), #33 (`scripts/post_qa_review.py`), #45 (`tests/test_hygiene.py`). Cherry-pick/consolidar ANTES de deletar os branches.
- Duplicados puros (subconjuntos, mesmos arquivos, versões mais antigas): sem perda — o conteúdo já existe no PR mantido.

### Dois remotes apontam pro MESMO repo
`lucas` (SSH) e `origin` (HTTPS) → ambos `strondata/smart-data`. Não é problema, mas escolher um só como canônico evita confusão de branches espelhados. Sugestão: manter `lucas` (SSH, push) e usar só ele.

---

## 5. Guardrail — impedir a frota de reabrir duplicado

O padrão dos branches (`chore/qa-dx-agent-<random>`, `docs-evolution-<random>`) mostra que cada agente gera um sufixo aleatório e ignora PR existente. Recomendações (barata → robusta):

1. **Convenção de branch por ticket, sem sufixo aleatório:** `chore/CHORE-003` (não `chore/qa-dx-agent-10729...`). Um ticket = um branch = um PR.
2. **Checar antes de abrir:** o agente deve rodar `gh pr list --search "CHORE-003 in:title state:open"` (ou label) e, se existir, **fazer push no branch existente** em vez de abrir novo.
3. **Label por ticket** (`chore-003`, `docs`, `hygiene`) + regra: 1 PR aberto por label.
4. **CODEOWNERS / branch protection na main** exigindo review humano — impede merge autônomo mesmo se o PR abrir.
5. Reaproveitar o **prompt do #34** (`docs/prompts/docs-agent.md`) para embutir essas regras no próprio agente.

---

## Apêndice — dados coletados (via API pública, 2026-06-30)

CI do #65 (head `8f71e55`): Integration/E2E/Plugin 3.10-3.12 = success; Full suite+coverage = skipped; **Lint(ruff) = failure**; **CLI tests 3.12 = failure**, 3.10/3.11 = cancelled.

Bases dos PRs (por que `mergeable=None`): #65 base `3d323f3` (=main, único atualizado); demais em `155b575`/`051ec63`/`9abd108`/`0aecdbc`/`341cb32` (bases antigas → recompute pendente → conflitos prováveis).
