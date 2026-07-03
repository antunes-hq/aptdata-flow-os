# aptdata como fábrica de micro-SaaS — estratégia rumo a ~$10k MRR

> Documento de estratégia (pesquisa + orquestração multi-agente). Eixo: o vídeo do
> **Lucas Montano ("não tem como faturar $10k")**. A conclusão não é "é impossível" — é
> **o gargalo mudou de lugar**. Construir ficou barato (IA). **Reter e distribuir, não.**
> O **aptdata é a linha de montagem, não o produto.**

## TL;DR

- **Tese:** `MRR ≈ (novos/mês × ticket) ÷ churn`. O Lucas domina a produção (constrói rápido,
  barato, com aptdata). O jogo é o **denominador (churn)** e a **torneira de cima (distribuição)**.
  Caso Persua (Montano): ~211 assinantes / ~€2,2k MRR / **~40% churn** → devia estar em ~€5k. A
  feature não muda essa conta; retenção e canal mudam.
- **A economia unitária é trivial; a aquisição é o problema.** Com o **roteamento do aptdata**
  (DeepSeek default → Claude só quando precisa), a margem bruta fica **85–93%** em qualquer preço
  ≥$20. **101 clientes B2B a $99 = $10k MRR** com 1/10 do suporte/churn de 1.000 a $10.
- **Top 3 (nichos de retenção estrutural + distribuição):**
  1. 🥇 **Copiloto fiscal do psicólogo** (Receita Saúde + Carnê-Leão) — obrigação legal desde 2025, ~547k profissionais, churn regulatório.
  2. 🥈 **aptdata white-label pra criadores** — terceiriza a distribuição pro parceiro que já tem audiência (modelo que fez R$1k→R$13k no BR).
  3. 🥉 **Validador NF-e da Reforma Tributária (CBS/IBS)** — regra nova de jan/2026, ~95% erram; é o core técnico do aptdata quase sem adaptação (melhor timing).

---

## 1. A tese aplicada ao Lucas (as 4 travas de valor)

1. **Nicho com dor verificável/regulatória/recorrente.** No BR isso é ouro: obrigação legal = dor
   que não some, ticket que se paga, churn baixo (parar = assumir risco fiscal). 24M empresas ativas,
   <5% usam SaaS.
2. **Dor pessoal / dogfooding.** Aconchego e mindflow provaram que ele constrói melhor o que ele (ou
   a Lilo, ou gente perto) usa todo dia — feedback loop grátis, zero risco de validação, narrativa
   autêntica pra build-in-public.
3. **Distribuição por autoridade/comunidade, não ads.** Todos os casos BR que escalaram foram
   Founder-Led Growth (R$1k→R$13k via comunidade; $0→$70k via YouTube; $0→R$40k via parceria). **O
   canal é o ativo, não o app.**
4. **Retenção como feature.** O *unfair advantage escondido do aptdata*: já traz `gamification`
   (streak+xp), `habits/quickwins` e `observability` (telemetria de churn). Hábito, gancho e sinal de
   churn já são primitivas do framework.

**Evitar:** "mais um app" horizontal (comoditizado pela IA); otimizar produto antes de ter canal
(**canal identificado > uma linha de código**); espalhar-se em N produtos ao mesmo tempo
(**fábrica é paralela no back-end; distribuição é serial no front-end**); nicho sem disposição a pagar.

> **Em uma frase:** a vantagem do Lucas não é "construir rápido" (todo mundo com IA tem isso agora);
> é **construir rápido O QUE ELE JÁ VALIDA no próprio uso, num nicho BR de dor recorrente, e
> distribuir por um canal que ele controla — com retenção embutida via gamification/telemetria do
> próprio framework.**

---

## 2. Ideias — top 3 + shortlist

### Top 3 (ranking: distribuição × retenção × fit aptdata × risco de validação)

**🥇 B1 — Copiloto fiscal do psicólogo (agenda + Receita Saúde + Carnê-Leão + IRPF)**
Retenção regulatória (obrigação desde 2025 → parar = risco fiscal, o oposto do problema do Persua);
distribuição segmentável (547k profissionais, grupos/CRPs/contadores acháveis em semanas); fit forte
(orquestração de 3–4 sub-tarefas + **trilha auditável via `observability`/run_id = comprovação fiscal
nativa** que ninguém no nicho tem). Ticket R$39–79 × churn baixo → ~150–250 assinantes = $10k.

**🥈 C2 — aptdata white-label pra criadores (SaaS + comunidade)**
Ataca a trava #1 (distribuição) de frente, terceirizando-a pro criador que já tem audiência. É a
única ideia que **usa o aptdata pelo que ele é** (fábrica): você não constrói 1 SaaS, constrói o
gerador e vende a capacidade. `gamification` embutido mantém a comunidade engajada (interesse
alinhado). Poucos parceiros (R$500–2k/mês) chegam a $10k. Risco: dependência do canal → 3–5 parceiros,
não 1.

**🥉 B3 — Validador de NF-e da Reforma Tributária (CBS/IBS)**
Melhor timing da lista (regra nova jan/2026, ~95% erram, sem incumbente). É o **core técnico do
aptdata** (`quality/`, `governance/rules`, contratos de schema) quase sem adaptação → menor esforço,
maior fit. Ticket B2B R$49–149, churn baixo (conformidade contínua). Canal: contadores/ERPs pequenos
(B2B2C). Ressalva: exige acurácia fiscal — validar regras com contador parceiro antes de vender.

### Shortlist completa (por bloco)

- **A. Dogfooding (menor risco):** A1 Aconchego Pro (casa/casal, começa pela Lilo) · A2 copiloto de
  dev indie / gerente de ecossistema (é o `aptdata-viz` virando produto — melhor como open-core/lead-gen)
  · A3 mindflow-for-teams (journaling com RAG + insight).
- **B. Regulatório BR (ticket alto, churn baixo):** B1 psicólogo ⭐ · B2 calendário fiscal do Simples
  (alerta WhatsApp; contador como canal) · B3 NF-e CBS/IBS ⭐ · B4 simulador MEI→ME (isca de funil, não
  MRR) · B5 LGPD pra MEI (wizard).
- **C. Comunidade/criador (distribuição embutida):** C1 copiloto de WhatsApp por vertical único
  (agente vertical retém 3–5×) · C2 white-label pra criadores ⭐ · C3 segunda-opinião de nicho (cuidado
  com compliance em financeiro).

---

## 3. O aptdata como fábrica de SaaS (design + fluxo)

**Regra de ouro** (herda da telegram-orchestration): nenhuma lógica de orquestração, roteamento,
conversa, observabilidade ou viz vive dentro de um produto. O produto é **config + Flows/Components de
nicho**. Tudo que é infra é o núcleo, versionado 1x. (Não recriar a dor dos "3 registros divergentes".)

**Duas camadas:**

| Dimensão | Reusado (núcleo, 1x → custo fixo) | Muda por produto (config/flows → custo marginal) |
|---|---|---|
| Orquestração | `core/` System·Flow·Component; Router; ProjectRunner | os Flows/Components do nicho (a lógica de valor) |
| Registry | motor `AgentRegistry.from_yaml` | o `agents.yaml` do produto (agentes, skills, modelos) |
| Roteamento | algoritmo prefix/skill/llm/default | bloco `routing:` (thresholds, guardrails) do nicho |
| Conversa/UX | `ConversationEngine` (política + guardrails) | prompts, persona, copy dos cards |
| Interface | transporte Telegram fino + `viz` | branding, subdomínio, quais views ligar |
| Telemetria | `Observer` + store + `run_id` | nada — herda de graça; filtra por `tenant` |
| Dados | `DatasetPlugin`/`plugins/` | o schema/fonte do cliente (o dado é o moat) |
| Deploy | Docker+Traefik+TLS, `aptdata setup` | labels/subdomínio + copy do onboarding |

**Custo marginal de um SaaS ≈** escrever `product.yaml` + `agents.yaml` + os Flows do domínio. O
nascimento reusa e estende o `cli/scaffold.py`:

```
aptdata new-saas <nome> --template <nicho> --tenant-mode <single|multi>
  → product.yaml · agents.yaml(+routing) · flows/domain.py · <nome>.project.yaml
    · prompts/ · branding/ · Dockerfile+compose+labels Traefik · .env.example
```

**Multi-tenancy (2 eixos):** por **PRODUTO** = 1 container + subdomínio Traefik/TLS (padrão do
painel/Aconchego já em produção); por **CLIENTE** = `tenant_id` de 1ª classe no store (reusa o esquema
`events/runs` da observability + um `TenantContext` no `ExecutionContext`). Escala promovível:
shared → db-per-tenant → container-per-tenant, trocando só o resolver de conexão.

**Auth e Billing = plugins do núcleo por flag**, nunca reimplementados por produto. Auth resolve
`request → tenant_id`; Billing (Stripe) **consome a telemetria por tenant como fonte de uso** (nada de
contador paralelo); eventos de billing entram no mesmo EventBus → `viz`/alertas os enxergam de graça.

**Fluxo:** `idea → new-saas → build (só o de nicho) → deploy (container+Traefik) → operate
(Telegram/web → auth→tenant → ConversationEngine → Router → Flows do nicho sobre dados do tenant →
observability+billing por run_id/tenant_id) → retain (viz por tenant, alertas, learning-loop, o dado
vira moat)`. Uma costura só (MCP): mesmo cérebro pra Telegram, web e IA.

### Gaps a fechar (o que falta pra ser fábrica)

| # | Gap | Estado | Reaproveita |
|---|---|---|---|
| **P0** | **Tenancy (`tenant_id` 1ª classe)** | inexistente | esquema events/runs da observability + `RunContext`→`TenantContext` |
| **P0** | **Template de produto + `aptdata new-saas`** | scaffold só gera hello-world | estender `cli/scaffold.py` + padrão Docker/Traefik |
| P1 | **Auth** (resolver `req→tenant_id`) | não há | `plugins/manager.py` + `config/secrets` |
| P1 | **Billing** (Stripe plugin) | inexistente | telemetria por tenant como fonte de uso |
| P1–P2 | ConversationEngine / observability / viz **em produção + `tenant_id`** | PLANEJADOS (docs/plans) | executar os 3 planos vivos + 1 dimensão `tenant_id` |

**Caminho crítico:** `Tenancy (P0)` desbloqueia o lado do cliente (auth→billing→viz/obs por tenant);
`Template/new-saas (P0)` desbloqueia o lado da criação. O "operate/retain" já está ~80% desenhado nos
3 planos vivos (observability, aptdata-viz, telegram-orchestration) — a fábrica é **executá-los +
costurar tenant/auth/billing por cima**, não reinventar.

---

## 4. Custos, IA e economia unitária

**Infra fixa ≈ R$0 marginal** (VPS já paga; auth/email/analytics em free tier até milhares de users).
O gasto variável real é **inference + taxa de payment**. O aptdata **substitui de graça** o que sangra
num SaaS de IA: orquestração (vs LangChain/LangGraph), telemetria de LLM (vs LangSmith/Helicone) e o
roteador barato→caro (vs OpenRouter/Portkey). Essa é a vantagem de custo.

**Custo de IA por usuário (blended, roteamento ~80% DeepSeek + 20% Sonnet):** **~$1,47/mês** (usuário
médio). O mesmo usuário custa **$0,18 no DeepSeek vs $6,60 no Sonnet — 36×**. Redutores que ele já usa:
prompt caching (~0,1× o input), Batch API (−50%), e o roteamento.

**Economia unitária (quantos clientes pra $10k):**

| Preço/mês | Clientes p/ $10k | Margem bruta/usuário (payment ~5% + IA $1,47) | Margem % |
|---|---|---|---|
| $10 | 1.000 | ~$7,73 | 77% |
| $29 | **345** | ~$25,78 | 89% |
| $99 (B2B) | **101** | ~$92,28 | 93% |

**O risco central:** IA é custo variável descolado da receita flat. Um power user de $29/mês rodando
**só no Sonnet** custa ~$33 → **prejuízo de ~$6**. Com roteamento (DeepSeek): $0,91 → 93% margem. **O
roteamento do aptdata não é otimização — é o que separa lucro de prejuízo.** Mitigar com quota por
plano + `task_budget`/`effort` baixo nos agentes.

**Conclusão:** $10k é **trivial na margem** e **difícil na aquisição**. Vá de **poucos clientes de
ticket médio-alto** (minimiza a superfície de aquisição/retenção).

**Stack recomendada (indie BR):** Supabase/Clerk auth (50k MAU grátis) · **Stripe** (USD) / **Asaas
+ Pix** (BRL, ~R$1 fixo) / Paddle-Lemon (MoR 5% se vender B2B gringo sem lidar com fiscal) · Resend
email · PostHog self-host.

---

## 5. Go-to-market + retenção (o gargalo da tese)

Como indie sem caixa de ads, canal = **orgânico**: build-in-public (X/threads — documentar a "fábrica
de micro-SaaS" *é* o conteúdo), YouTube dev pt-BR (autoridade → leads B2B), e **entrar fundo em 1
comunidade/nicho** por vez. CAC ≈ tempo. LTV ~$310 ($29/mês) a ~$1.100 (B2B $99) → regra CAC < LTV/3.
Ads só depois de LTV provado.

**Alavancas de retenção** (onde a grana vive): (1) onboarding até o "aha" na 1ª sessão; (2) **dado que
gruda** (histórico/memória = custo de sair); (3) **hábito/gatilho recorrente** (notificação Telegram,
relatório semanal — padrão que ele já usa); (4) nicho estreito; (5) dogfooding como prova viva.

---

## 6. Recomendação executiva

1. **Escolher UM produto pra distribuir** (serial). Recomendado: **🥇 B1 (psicólogo)** — retenção
   regulatória + distribuição segmentável + fit forte. Alternativa de maior alavanca-de-canal: 🥈 C2
   (white-label pra criadores).
2. **Antes de codar:** identificar o canal dos primeiros 100 (grupos/CRPs/contadores pra B1;
   parceiros-criadores pra C2). Canal > código.
3. **No aptdata (a fábrica), em paralelo:** fechar os 2 gaps P0 — **tenancy (`tenant_id`)** e
   **template `aptdata new-saas`** — que transformam o núcleo 0.2.0 em fábrica. Auth/billing (P1) na
   sequência, reusando a telemetria por tenant.
4. **Executar os 3 planos vivos** (observability, aptdata-viz, telegram-orchestration) — eles já são o
   "operate/retain" da fábrica.
5. **Dogfoodar** com A1/A3 (Aconchego Pro / mindflow) como vitrine e estudo de caso do build-in-public.

> Regra final: a fábrica só compensa se **cada micro-SaaS custa quase nada pra manter vivo** (e custa,
> graças à VPS + aptdata) — o barato de rodar existe pra sustentar experimentação até **um** acertar a
> distribuição.

---

*Fontes: tese do vídeo (Montano/Persua); ideias regulatórias BR (@fabianocarvalhojr); casos de
distribuição BR (microsaas.com.br / substack); métricas de churn/MRR por segmento (vibrantsnap,
ideaproof, softwareseni); agentes verticais (superannotate, actgsys); preços de IA (Claude/DeepSeek/
OpenAI/Gemini docs); payment (Stripe/Asaas/Paddle); auth (Clerk/Supabase). Detalhamento nas seções de
pesquisa (ideias/design/custos).*
