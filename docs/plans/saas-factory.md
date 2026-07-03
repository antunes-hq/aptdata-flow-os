# aptdata como fábrica de micro-SaaS — estratégia rumo a ~$10k MRR

> Documento de estratégia (pesquisa + orquestração multi-agente), **v2 — revisado criticamente**.
> Eixo: o vídeo do **Lucas Montano ("não tem como faturar $10k")**. A conclusão não é "é
> impossível" — é **o gargalo mudou de lugar**. Construir ficou barato (IA). **Reter e
> distribuir, não.** O **aptdata é a linha de montagem, não o produto.**
>
> A v2 pressiona as premissas da v1: corrige claims de concorrência ("sem incumbente" era
> falso nos dois nichos fiscais), reprecifica a margem (impostos/suporte/inadimplência e o
> conflito DeepSeek×LGPD derrubam 85–93% para ~65–80%), expõe a contradição interna do top-3
> com a própria tese (dogfooding + canal próprio), e adiciona o que faltava: **experimentos de
> validação, plano de 90 dias, kill-criteria, pricing/retenção por ideia e registro de
> riscos**. Parecer completo da revisão em `saas-factory-review.md`.

## TL;DR (revisado)

- **Tese (mantida, com emenda):** `MRR ≈ (novos/mês × ticket) ÷ churn`. O jogo é o
  **denominador (churn)** e a **torneira de cima (distribuição)**. Caso Persua (Montano):
  ~211 assinantes / ~€2,2k MRR / **~40% churn** → devia estar em ~€5k. **Emenda:** a v1
  tratava distribuição como "o gargalo" mas a precificava em ~zero. Distribuição em nicho
  que não é o seu custa **meses de tempo do founder** (o CAC real) + **barreira de confiança**
  (em fiscal, o incumbente é o contador humano, não outro app).
- **Economia unitária: boa, não trivial.** Margem operacional realista **~65–80%** (não
  85–93%): a conta da v1 ignorava impostos sobre receita (Simples ~6–15,5%), suporte humano,
  inadimplência/dunning — e o **conflito estrutural**: a margem depende de rotear pro DeepSeek,
  mas o nicho-carro-chefe (dados fiscais/de pacientes) é exatamente onde **não se pode** mandar
  dado cru pra API externa barata sem camada de mascaramento. Ainda assim: 101 clientes B2B a
  $99 = $10k MRR com 1/10 do suporte/churn de 1.000 a $10. A conclusão sobrevive; o número
  da v1 era marketing.
- **Top 3 (reordenado, com condicionais):**
  1. 🥇 **Copiloto fiscal do psicólogo** (Receita Saúde + Carnê-Leão) — retenção regulatória
     real, **mas condicionado a passar no experimento de canal** (§2.1) antes de qualquer
     código. Tem incumbentes (Leoa, contabilidades digitais de saúde, ferramentas gratuitas
     da própria Receita) — o moat é canal + dado, não "ninguém faz".
  2. 🥈 **Validador NF-e da Reforma Tributária (CBS/IBS)** — sobe uma posição: melhor fit
     técnico (core do aptdata, majoritariamente determinístico → margem E compliance), canal
     B2B2C via contadores. Janela de 12–24 meses antes de virar checkbox de ERP.
  3. 🥉 **aptdata white-label pra criadores** — desce: demanda não validada, risco de virar
     consultoria com fatura recorrente, concentração de receita (5 parceiros = perder 1 é
     −20% MRR). Só com pré-venda assinada (§2.1).
- **Regra nova:** nenhuma linha de código de produto antes do experimento de validação da
  ideia **passar nos kill-criteria** (§2.2). "Canal > código" vira processo, não slogan.

---

## 1. A tese aplicada ao Lucas (as 4 travas de valor)

1. **Nicho com dor verificável/regulatória/recorrente.** No BR isso é ouro: obrigação legal =
   dor que não some, ticket que se paga, churn baixo (parar = assumir risco fiscal). 24M
   empresas ativas, <5% usam SaaS.
2. **Dor pessoal / dogfooding.** Aconchego e mindflow provaram que ele constrói melhor o que
   ele (ou a Lilo, ou gente perto) usa todo dia — feedback loop grátis, zero risco de
   validação, narrativa autêntica pra build-in-public.
3. **Distribuição por autoridade/comunidade, não ads.** Todos os casos BR que escalaram foram
   Founder-Led Growth (R$1k→R$13k via comunidade; $0→$70k via YouTube; $0→R$40k via parceria).
   **O canal é o ativo, não o app.**
4. **Retenção como feature.** O *unfair advantage escondido do aptdata*: já traz `gamification`
   (streak+xp), `habits/quickwins` e `observability` (telemetria de churn). Hábito, gancho e
   sinal de churn já são primitivas do framework.

### 1.1 O que a tese subestima (emendas da v2)

- **O CAC é tempo, e tempo tem preço.** Os casos de FLG que escalaram eram founders **dentro
  do nicho** (a comunidade já era deles). O canal do Lucas hoje é **dev pt-BR** — não
  psicólogos, não contadores. Construir audiência num nicho alheio custa 3–6 meses de
  conteúdo/comunidade **antes do primeiro real de MRR**. Esse custo não aparecia na conta da v1.
- **Barreira de confiança em fiscal/regulatório.** A mesma força que segura o churn
  (obrigação legal) torna o comprador avesso a risco: errar o imposto é pior do que pagar
  caro. O incumbente do B1 não é um app — é **"meu contador resolve"** (R$150–300/mês, com
  rosto e CRC). Um SaaS de dev desconhecido precisa de prova social emprestada (contador
  parceiro, CRP, influenciador do nicho) pra ser sequer considerado.
- **Suporte em nicho regulatório é proporcional à ansiedade, não ao ticket.** Época de IRPF =
  pico de tickets; um erro fiscal = cliente furioso + risco reputacional + possível
  responsabilidade (ver §7). Suporte humano não é opcional nem gratuito nesses nichos.
- **Contradição interna do top-3 da v1:** as travas #2 (dogfooding) e #3 (canal próprio) são
  critérios da tese — e **B1 e B3 falham nos dois** (Lucas não é psicólogo nem emite NF-e em
  volume; o canal dele é dev). O único bloco que passa nos 4 critérios é o A (dogfooding) e
  o A2 em particular (o comprador é dev = a audiência que ele já tem). A v2 não inverte o
  ranking por isso (o bloco A tem teto de ticket e churn pior), mas **exige o experimento de
  canal como pedágio** antes de B1/B3 — é o mecanismo que compensa a trava violada.

**Evitar:** "mais um app" horizontal (comoditizado pela IA); otimizar produto antes de ter canal
(**canal identificado > uma linha de código**); espalhar-se em N produtos ao mesmo tempo
(**fábrica é paralela no back-end; distribuição é serial no front-end**); nicho sem disposição a
pagar; **construir antes de validar** (novo — §2.1).

> **Em uma frase (revisada):** a vantagem do Lucas não é "construir rápido" (todo mundo com IA
> tem isso agora); é construir rápido O QUE JÁ FOI VALIDADO barato, num nicho BR de dor
> recorrente, e distribuir por um canal que ele controla **ou aluga de um parceiro com rosto no
> nicho** — com retenção embutida via gamification/telemetria do próprio framework.

---

## 2. Ideias — top 3 + shortlist

### Top 3 (ranking v2: distribuição × retenção × fit aptdata × risco de validação × confiança)

**🥇 B1 — Copiloto fiscal do psicólogo (agenda + Receita Saúde + Carnê-Leão + IRPF)**
Retenção regulatória (obrigação desde 2025 → parar = risco fiscal, o oposto do problema do
Persua); distribuição segmentável (~547k profissionais, grupos/CRPs/contadores acháveis em
semanas); fit forte (orquestração de 3–4 sub-tarefas + **trilha auditável via
`observability`/run_id = comprovação fiscal nativa**). Ticket R$39–79 × churn baixo →
~150–250 assinantes = $10k.
*Correções da v2:* **há incumbentes** — Leoa (automação de Carnê-Leão pra profissionais de
saúde, com funding), contabilidades digitais especializadas em saúde, e as ferramentas
**gratuitas** da própria Receita (Receita Saúde app + Carnê-Leão Web). O diferencial precisa
ser o *workflow completo* (agenda→recibo→carnê→IRPF) + preço abaixo do contador, não "ninguém
faz". **Maior motivo pra falhar:** o psicólogo já resolve com o contador ou com o app grátis
do governo, e não confia dado de paciente + fiscal a um SaaS novo — ou seja, falha por
**confiança/canal**, não por produto. Por isso é 🥇 *condicional*: só passa a produto se o
experimento de canal (§2.1) bater a meta.
*Atenção LGPD:* recibos carregam CPF/nome de **pacientes** (terceiros, contexto de saúde) —
dado sensível. Ver §3 (gap LGPD) e §7.

**🥈 B3 — Validador de NF-e da Reforma Tributária (CBS/IBS)** *(subiu de 🥉)*
É o **core técnico do aptdata** (`quality/`, `governance/rules`, contratos de schema) quase sem
adaptação → menor esforço, maior fit. E o motor de validação é **determinístico** (regras, não
LLM) — o que resolve de uma vez margem E compliance (dado fiscal nem passa por API de LLM
externa). Ticket B2B R$49–149, churn baixo (conformidade contínua + regras que mudam todo ano
até 2033 = retenção estrutural). Canal: contadores/ERPs pequenos (B2B2C) — 1 contador = 30–200
CNPJs, o multiplicador de distribuição mais barato da lista.
*Correções da v2:* "sem incumbente" era **falso** — todo ERP/emissor (Omie, Bling, Tiny,
ContaAzul, emissores gratuitos) é *obrigado* a implementar o layout CBS/IBS, e tax-techs
(Systax, Sovos, Arquivei/Qive, Avalara) vivem disso. A janela real é **12–24 meses** no
segmento que os ERPs atendem mal (micro/pequeno + contador de bairro), antes de validação
virar checkbox. E 2026 é ano-teste (alíquotas simbólicas ~0,9%+0,1%): a dor em 2026 é
**rejeição de nota/retrabalho**, não multa — o marketing de urgência precisa refletir isso;
a dor vira existencial de 2027 em diante (cronograma até 2033 = anuidade de retenção).
**Maior motivo pra falhar:** o ERP do cliente entrega validação "boa o suficiente" de graça
antes de você ter canal — corrida contra o roadmap alheio. Mitigação: vender pro **contador**
(que atende clientes multi-ERP e responde pelo erro), não pro emissor final.

**🥉 C2 — aptdata white-label pra criadores (SaaS + comunidade)** *(desceu de 🥈)*
Ataca a trava #1 (distribuição) terceirizando-a pro criador que já tem audiência, e é a única
ideia que usa o aptdata pelo que ele é (fábrica). Poucos parceiros (R$500–2k/mês) chegam a
$10k.
*Por que desceu:* (a) **demanda não validada** — "criador quer white-label" é hipótese; o que
criador quer é revenue share com zero trabalho, o que transforma o Lucas em **dev shop do
parceiro** (consultoria com fatura recorrente, não produto); (b) **concentração**: 5 parceiros
= perder 1 é −20% MRR, e audiência de criador é volátil; (c) cada parceiro é uma mini-venda
enterprise (negociação, customização, suporte em cascata — o parceiro promete pro público
dele e quem entrega é você). **Maior motivo pra falhar:** o segundo parceiro exige o dobro de
customização do primeiro e a "fábrica" vira atelier. Só avança com **pré-venda assinada**
(≥2 LOIs com valor e escopo fechado — §2.1) e template de escopo inegociável.

### 2.1 Experimentos de validação (antes de qualquer código de produto)

Custo-alvo por experimento: **≤ R$500 e ≤ 3 semanas**. O que se compra: evidência de canal +
disposição a pagar. Formato: landing (1 dia com o próprio aptdata/scaffold) + tráfego manual.

| Ideia | Experimento (3 semanas) | Sinal de PASSA | Sinal de MATA |
|---|---|---|---|
| **B1 psicólogo** | (1) 10 entrevistas (recrutar em grupos de psicólogos/Instagram/CRP); (2) landing com **preço visível** + waitlist, divulgada por 2–3 psicólogos-parceiros micro; (3) **concierge**: fazer o Carnê-Leão de 5 psicólogos na mão por 1 mês, cobrando R$49 piloto | ≥30 waitlist orgânica; ≥3/10 entrevistados topam pagar no piloto; concierge renova pro 2º mês | <15 waitlist com divulgação ativa; entrevistas convergem em "meu contador resolve" ou "uso o app da Receita"; ninguém paga o piloto |
| **B3 CBS/IBS** | (1) 10 conversas com contadores de PME; (2) oferta manual: "relatório de diagnóstico CBS/IBS das notas dos seus clientes" (rodar as regras à mão/script, entregar PDF); (3) 1 post técnico (a Reforma dá autoridade barata) | ≥2 contadores pagam pelo diagnóstico ou assinam intenção; contadores confirmam que o ERP dos clientes não cobre | contadores dizem que o ERP já resolve; ninguém paga nem de graça quer o relatório |
| **C2 white-label** | DM direto pra 20 criadores com **mockup concreto** (1 tela do produto com a marca deles) + proposta de escopo fechado; pedir **LOI com valor** | ≥2 LOIs assinadas com setup fee aceito | respostas só de "revenue share, sem investimento"; pedidos de customização já na conversa de venda |
| **A1/A3 dogfooding** | já validado por uso próprio — vitrine de build-in-public, não aposta de MRR | n/a (é marketing da fábrica) | n/a |

**Disciplina:** os experimentos de B1 e B3 podem rodar **em paralelo** (públicos diferentes);
o produto escolhido é o que passar melhor. Se ambos matarem, o fallback é A2 (copiloto dev
indie — único com canal já existente) com expectativa de ticket menor.

### 2.2 Kill-criteria (quando desistir — definir ANTES de começar)

- **Pré-código (validação):** qualquer linha "MATA" da tabela acima → arquivar a ideia e
  documentar o porquê (o registro é ativo da fábrica).
- **Pós-lançamento (por produto):**
  - Churn mensal > 8% após 3 meses de ajustes de onboarding → o nicho não retém; matar ou pivotar.
  - Ativação < 40% (signup → "aha" na 1ª sessão) após 2 iterações de onboarding → proposta de valor não comunica.
  - CAC-tempo > 4h de founder por cliente no mês 3 (sem tendência de queda) → canal não escala; trocar canal ou matar.
  - < 30 clientes pagantes no dia 90 (B1/B3) → sem tração; voltar pro funil de ideias.
- **Regra anti-falácia do custo afundado:** a decisão de matar é tomada contra estes números,
  não contra o apego. A fábrica só faz sentido se matar barato for rotina.

### Shortlist completa (por bloco)

- **A. Dogfooding (menor risco de validação, teto de ticket):** A1 Aconchego Pro (casa/casal,
  começa pela Lilo) · A2 copiloto de dev indie / gerente de ecossistema (é o `aptdata-viz`
  virando produto — melhor como open-core/lead-gen, **e é o fallback com canal pronto**) ·
  A3 mindflow-for-teams (journaling com RAG + insight).
- **B. Regulatório BR (ticket alto, churn baixo, barreira de confiança):** B1 psicólogo ⭐ ·
  B2 calendário fiscal do Simples (alerta WhatsApp; contador como canal — bom *wedge* barato
  pra construir a relação com contadores que o B3 precisa) · B3 NF-e CBS/IBS ⭐ · B4 simulador
  MEI→ME (isca de funil, não MRR) · B5 LGPD pra MEI (wizard).
- **C. Comunidade/criador (distribuição embutida, concentração):** C1 copiloto de WhatsApp
  por vertical único (agente vertical retém 3–5×) · C2 white-label pra criadores ⭐ · C3
  segunda-opinião de nicho (cuidado com compliance em financeiro).

---

## 3. O aptdata como fábrica de SaaS (design + fluxo)

**Regra de ouro** (herda da telegram-orchestration): nenhuma lógica de orquestração, roteamento,
conversa, observabilidade ou viz vive dentro de um produto. O produto é **config + Flows/Components
de nicho**. Tudo que é infra é o núcleo, versionado 1x. (Não recriar a dor dos "3 registros
divergentes".)

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
`request → tenant_id`; Billing (Stripe/Asaas) **consome a telemetria por tenant como fonte de uso**
(nada de contador paralelo); eventos de billing entram no mesmo EventBus → `viz`/alertas os
enxergam de graça. **Dunning faz parte do plugin Billing desde o dia 1** (ver gap abaixo) — no BR,
falha de cobrança recorrente em cartão é rotina; recuperar 5–9% do MRR é feature, não luxo.

**Realidade de transporte (emenda v2):** o núcleo conversacional hoje fala **Telegram** — ótimo
pra dev/dogfooding, **errado pros nichos B**: psicólogo e contador vivem no **WhatsApp** e no
navegador. A fábrica precisa de (a) onboarding self-service **web** (signup → pagamento →
primeiro valor sem falar com humano) e (b) um transporte WhatsApp (Cloud API tem custo por
conversa e template aprovado — orçar) ou e-mail transacional como gancho de hábito. Sem isso,
o "operate/retain" desenhado nos planos vivos não alcança o usuário-alvo.

**Fluxo:** `idea → experimento (§2.1) → new-saas → build (só o de nicho) → deploy
(container+Traefik) → operate (web/WhatsApp/Telegram → auth→tenant → ConversationEngine → Router
→ Flows do nicho sobre dados do tenant → observability+billing por run_id/tenant_id) → retain
(viz por tenant, alertas, learning-loop, o dado vira moat)`. Uma costura só (MCP): mesmo cérebro
pra todos os transportes e IA.

### Gaps a fechar (o que falta pra ser fábrica) — revisado

| # | Gap | Estado | Reaproveita / nota |
|---|---|---|---|
| **P0** | **Tenancy (`tenant_id` 1ª classe)** | inexistente | esquema events/runs da observability + `RunContext`→`TenantContext` |
| **P0** | **Template de produto + `aptdata new-saas`** | scaffold só gera hello-world | estender `cli/scaffold.py` + padrão Docker/Traefik |
| **P0\*** | **LGPD/dados sensíveis** (mascaramento pré-LLM, criptografia at-rest, base legal, DPA, política de retenção) | inexistente | `mask_telemetry_value` (telemetry) é a semente do masking; P0\* = bloqueante **antes do primeiro cliente de B1/B3**, não do template |
| P1 | **Auth** (resolver `req→tenant_id`) | não há | `plugins/manager.py` + `config/secrets` |
| P1 | **Billing + dunning** (Stripe/Asaas plugin, retry de cobrança, e-mails de recuperação) | inexistente | telemetria por tenant como fonte de uso |
| P1 | **Backup/DR testado** | VPS única = ponto único de falha | dump SQLite/volumes → storage externo diário + **teste de restore mensal**; perder dado fiscal de cliente = fim do produto |
| P1 | **Onboarding self-service web** (signup→pagamento→aha sem humano) | inexistente (fluxo atual é Telegram/dev) | viz/FastAPI como base do web app fino |
| P1–P2 | ConversationEngine / observability / viz **em produção + `tenant_id`** | PLANEJADOS (docs/plans) | executar os 3 planos vivos + 1 dimensão `tenant_id` |
| P2 | **Transporte WhatsApp** (ou e-mail como gancho) | inexistente | mesma interface fina do transporte Telegram (telegram-orchestration §6) |
| P2 | **Export de dados / offboarding** | inexistente | LGPD (portabilidade) + confiança de entrada ("consigo sair") reduz fricção de venda |
| P2 | Status page / termos de uso com limitação de responsabilidade | inexistente | template jurídico 1x, reusado por produto (§7) |

**Caminho crítico:** `Tenancy (P0)` desbloqueia o lado do cliente (auth→billing→viz/obs por
tenant); `Template/new-saas (P0)` desbloqueia o lado da criação; `LGPD (P0*)` desbloqueia
**vender** pros nichos B. O "operate/retain" já está ~80% desenhado nos 3 planos vivos
(observability, aptdata-viz, telegram-orchestration) — a fábrica é **executá-los + costurar
tenant/auth/billing por cima**, não reinventar. Backup/DR e dunning entram como P1 porque a
fábrica promete "custa quase nada manter vivo" — e produto sem backup nem recuperação de
cobrança não está vivo, está com sorte.

---

## 4. Custos, IA e economia unitária (revisado)

**Infra fixa ≈ R$0 marginal** (VPS já paga; auth/email/analytics em free tier até milhares de
users). O gasto variável real é **inference + payment + impostos + suporte**. O aptdata
**substitui de graça** o que sangra num SaaS de IA: orquestração (vs LangChain/LangGraph),
telemetria de LLM (vs LangSmith/Helicone) e o roteador barato→caro (vs OpenRouter/Portkey).
Essa vantagem de custo é real e permanece.

**Custo de IA por usuário (blended, roteamento ~80% DeepSeek + 20% Sonnet):** **~$1,47/mês**
(usuário médio). O mesmo usuário custa **$0,18 no DeepSeek vs $6,60 no Sonnet — 36×**. Redutores
que ele já usa: prompt caching (~0,1× o input), Batch API (−50%), e o roteamento.

**⚠️ O conflito DeepSeek × LGPD (novo na v2):** a margem acima assume rotear 80% do tráfego
pra DeepSeek. Mas nos nichos B o payload contém **CPF de paciente, rendimento, dados fiscais**
— transferência internacional de dado pessoal/sensível pra provedor sem os requisitos da LGPD é
risco jurídico E de venda (o contador/psicólogo pergunta "pra onde vai meu dado?"). Três saídas,
em ordem de preferência: (1) **desenhar o flow pra LLM nunca ver PII** — núcleo determinístico
(B3 é quase todo regra) + masking (`mask_telemetry_value` como semente) antes de qualquer
chamada; (2) rotear payload sensível pra provedor com contrato adequado (Claude/Bedrock/
Vertex) e aceitar margem menor nesses flows; (3) modelo local pra classificação simples. O
roteamento do aptdata ganha uma dimensão nova: **rotear por sensibilidade do dado, não só por
custo**.

**O que a conta da v1 ignorava (por usuário/mês, ticket $29):**

| Item | v1 | v2 (realista) |
|---|---|---|
| Payment (gateway) | ~5% ($1,45) | ~5% ($1,45); Pix/Asaas menor, cartão recorrente + retries maior |
| IA | $1,47 | $1,47–3,00 (mix com flows sensíveis fora do DeepSeek) |
| **Impostos sobre receita** | — | **Simples serviço ~6–15,5%** (~$1,75–4,50) |
| **Suporte humano** | — | ~5–10% do MRR em nicho regulatório (pico no IRPF); ~$1,50–3,00 amortizado |
| **Inadimplência/refund** | — | ~3–5% (mitigável com dunning + Pix + anual) |
| Margem resultante | ~89% | **~65–78%** |

**Economia unitária (quantos clientes pra $10k) — margem revisada:**

| Preço/mês | Clientes p/ $10k | Margem v1 | Margem v2 realista |
|---|---|---|---|
| $10 | 1.000 | 77% | ~55–65% (suporte come ticket baixo) |
| $29 | **345** | 89% | **~65–78%** |
| $99 (B2B) | **101** | 93% | **~75–83%** |

**O risco central (mantido):** IA é custo variável descolado da receita flat. Um power user de
$29/mês rodando **só no Sonnet** custa ~$33 → **prejuízo**. Com roteamento: $0,91 → margem
saudável. **O roteamento do aptdata não é otimização — é o que separa lucro de prejuízo.**
Mitigar com quota por plano + `task_budget`/`effort` baixo nos agentes. **Adendo v2:** o
melhor mitigador é arquitetural — quanto mais o produto for **regra determinística com LLM só
na borda** (B3), menos essa exposição existe.

**Outros dois pontos honestos:** (a) **o primeiro cliente custa 10× o centésimo** — onboarding
manual, pedidos custom, confiança construída a mão; a margem de regime só chega com ~30+
clientes; (b) **descasamento cambial** — custo de IA em USD, receita em BRL: alta do dólar
comprime margem sem você tocar em nada. Precificar com folga ou indexar plano anual.

**Conclusão (mantida, recalibrada):** $10k é **bom negócio na margem** (65–80%, não 85–93%) e
**difícil na aquisição**. Vá de **poucos clientes de ticket médio-alto** (minimiza a superfície
de aquisição/retenção).

**Stack recomendada (indie BR):** Supabase/Clerk auth (50k MAU grátis) · **Stripe** (USD) /
**Asaas + Pix** (BRL, ~R$1 fixo, sem chargeback no Pix) / Paddle-Lemon (MoR 5% se vender B2B
gringo sem lidar com fiscal) · Resend email · PostHog self-host.

---

## 5. Go-to-market, pricing e retenção (o gargalo da tese)

Como indie sem caixa de ads, canal = **orgânico**: build-in-public (X/threads — documentar a
"fábrica de micro-SaaS" *é* o conteúdo), YouTube dev pt-BR (autoridade → leads B2B), e **entrar
fundo em 1 comunidade/nicho** por vez. CAC ≈ tempo — **e o §1.1 precifica esse tempo**: em nicho
alheio, os primeiros 100 clientes custam meses de presença antes da primeira venda; por isso o
experimento (§2.1) valida o canal ANTES do produto. LTV ~$310 ($29/mês) a ~$1.100 (B2B $99) →
regra CAC < LTV/3. Ads só depois de LTV provado.

### 5.1 Pricing & packaging por ideia (novo na v2)

| | B1 psicólogo | B3 CBS/IBS | C2 white-label |
|---|---|---|---|
| **Modelo** | **Trial 14d com onboarding assistido** (não freemium: free tier em fiscal = suporte sem receita + sinal de pouca seriedade) | **Diagnóstico gratuito como isca** (1 relatório) → assinatura de monitoramento contínuo | **Setup fee + mensalidade com piso** (nunca só revenue share — piso protege do parceiro que não divulga) |
| **Âncora de preço** | contra o **contador** (R$150–300/mês), não contra apps: "R$59 e seu carnê nunca atrasa" | contra a **multa/retrabalho** e a hora do contador | contra o custo de o criador desenvolver do zero |
| **Planos** | R$39 (solo) / R$59 (agenda+recibo+carnê) / R$99 (multi-consultório) | R$49/CNPJ → R$149 (multi-CNPJ) · **plano contador** (painel com N clientes, preço por lote) | R$1–2k/mês + setup R$3–5k, contrato **anual** |
| **Anual** | 2 meses grátis — **fecha antes de maio** (ver cliff abaixo) | anual com desconto — alinha com o ciclo fiscal | obrigatório (protege da volatilidade do criador) |
| **Parceiro** | **contador que atende psicólogos** = canal + prova social + retenção (quem paga indicado pelo contador não cancela sem falar com o contador) | **o contador É o cliente** (B2B2C) — plano de revenda com margem pro contador | n/a (o parceiro é o canal) |

### 5.2 Retenção por ideia (novo na v2)

- **B1 — o cliff de maio:** o risco específico do nicho é churn sazonal — entregou o IRPF em
  abril/maio, cancela. Antídotos: (a) valor **mensal**, não anual (recibo Receita Saúde e
  carnê-leão são obrigações *mensais* — o produto certo lembra e resolve todo mês, não só na
  declaração); (b) plano anual fechado no Q1; (c) **dado que gruda**: histórico fiscal +
  agenda = custo de sair; (d) relatório mensal "sua vida fiscal em dia" (gancho de hábito,
  padrão que o Lucas já usa).
- **B3 — a Reforma é uma assinatura por natureza:** regras mudam todo ano até 2033; retenção =
  **monitoramento contínuo + alerta de mudança de regra** (nunca vender como validador
  one-shot). O plano contador amarra retenção dupla: o contador não cancela porque os clientes
  dele dependem do painel.
- **C2 — retenção do parceiro = sucesso do parceiro:** QBR trimestral com números (o `viz` por
  tenant é literalmente isso), playbook de lançamento pro criador, e contrato anual. Se o
  produto do parceiro não vende, o churn é dele — o piso mensal compra tempo, não imunidade.
- **Alavancas gerais (mantidas da v1):** (1) onboarding até o "aha" na 1ª sessão; (2) dado que
  gruda; (3) hábito/gatilho recorrente (notificação, relatório semanal); (4) nicho estreito;
  (5) dogfooding como prova viva.

---

## 6. Sequenciamento — primeiros 90 dias (produto: B1, condicionado ao experimento)

> Se o experimento matar B1 e aprovar B3, o mesmo esqueleto vale trocando entrevistas de
> psicólogos por contadores e o concierge por diagnóstico de notas. **Gates nas semanas 3, 6
> e 13** — cada um com kill-criteria explícito (§2.2).

| Semanas | Foco | Entregável / gate |
|---|---|---|
| **1–3** | **Validação (zero código de produto).** 10 entrevistas; landing com preço + waitlist; recrutar 2–3 psicólogos-parceiros e 1 contador de saúde; iniciar concierge com 5 pilotos pagos (R$49) | **GATE 1:** critérios do §2.1. Falhou → roda B3; passou → segue |
| **4–6** | **Wedge mínimo.** UM job só: recibo Receita Saúde + lançamento no Carnê-Leão automatizados (o resto continua concierge/manual). Fechar os 2 gaps P0 da fábrica (tenancy + `new-saas`) usando o próprio B1 como primeiro template. Masking LGPD no flow (P0\*) | **GATE 2:** 5 pilotos usando o wedge sem intervenção manual em ≥70% dos casos; NPS verbal positivo. Falhou → mais 2 semanas de iteração, depois decide |
| **7–10** | **Piloto pago.** 10→25 clientes via parceiros + grupos; onboarding self-service web mínimo (signup→Pix/cartão→primeiro recibo); dunning básico; backup diário + teste de restore; termos de uso com limitação de responsabilidade | 25 pagantes; ativação ≥40%; churn dos pilotos = 0 |
| **11–13** | **Lançamento público.** Waitlist + build-in-public (a série "fábrica" começa aqui — o making-of é o marketing); plano contador-parceiro no ar; instrumentar telemetria de churn (observability por tenant) | **GATE 3 (dia 90):** ≥30 pagantes e churn <8% → escalar canal. Abaixo disso → §2.2 decide |
| *paralelo (fábrica)* | Executar os 3 planos vivos (observability → viz → conversation) com `tenant_id`; B1 é o cliente de teste de tudo | fábrica validada com 1 produto real, não hello-world |

**Por que assim:** o wedge nas semanas 4–6 força a fábrica a nascer do produto (template
extraído de caso real, não especulado) — o inverso de construir a fábrica primeiro e caçar
produto depois. E o concierge das semanas 1–3 gera o insumo mais valioso: o **processo manual
documentado** que os Flows vão automatizar.

---

## 7. Registro de riscos (novo na v2 — o que a v1 ignorava)

| Risco | Severidade | Mitigação |
|---|---|---|
| **Responsabilidade fiscal**: o produto erra um recibo/validação, cliente é autuado, culpa o SaaS | alta (B1/B3) | ToS com limitação de responsabilidade + "não é aconselhamento contábil"; contador parceiro revisa as regras (B3: *nenhuma* regra vai pra produção sem validação de contador); trilha auditável (`observability`/run_id) como prova do que foi feito; seguro E&O quando faturar |
| **LGPD / dado sensível de terceiros** (CPF+contexto de saúde de *pacientes* no B1) | alta | gap P0\* do §3: masking pré-LLM, criptografia at-rest, minimização, DPA, retenção definida; **nunca** dado sensível cru em API sem contrato adequado (§4) |
| **Dependência de canal de terceiro** (C2: audiência do criador; B1/B3: o contador-parceiro) | média-alta | C2: mínimo 3–5 parceiros + contrato anual + piso; B1/B3: parceiro é *acelerador*, canal próprio (conteúdo no nicho) cresce em paralelo desde a semana 1 |
| **Concentração de receita** (101 clientes B2B; 5 parceiros) | média | monitorar % do MRR nos top-5 clientes; nenhum >10% (C2 viola isso por design — por isso desceu) |
| **Corrida contra roadmap de ERP** (B3) | média | janela 12–24 meses: vender pro contador multi-ERP, não pro emissor; profundidade (cronograma 2026–2033) vs checkbox do ERP |
| **Sazonalidade fiscal** (pico de suporte no IRPF; cliff de churn em maio) | média | §5.2; provisionar suporte extra no Q1–Q2; anual fechado antes de maio |
| **Key-person**: canal E operação = Lucas | média | fábrica reduz o lado operação (por design); o canal não tem mitigação barata — é o custo do modelo indie, admitir e monitorar |
| **Câmbio** (custo IA em USD, receita BRL) | baixa-média | folga na precificação; núcleo determinístico reduz exposição |
| **Plataforma de transporte** (política/custo do WhatsApp API; Telegram fora do perfil do nicho) | baixa-média | transporte é camada fina por design (telegram-orchestration) — trocar transporte não toca o cérebro |

---

## 8. Recomendação executiva (revisada)

1. **Rodar os experimentos de validação de B1 e B3 em paralelo, JÁ (§2.1)** — ≤3 semanas,
   ≤R$500 cada, kill-criteria escritos antes. O vencedor vira o produto único a distribuir
   (serial). Empate técnico → B1 (ticket direto, nicho mais quente); duplo fracasso → A2 com
   expectativa recalibrada.
2. **Antes de codar produto:** o experimento É a identificação do canal dos primeiros 100
   (grupos/CRPs/contadores pra B1; contadores pra B3). Canal > código — agora com gate formal.
3. **No aptdata (a fábrica), em paralelo:** fechar os 2 gaps P0 — **tenancy** e **template
   `new-saas`** — *extraindo-os do produto vencedor* (semanas 4–6 do §6), e o **P0\* LGPD**
   antes do primeiro cliente pagante de nicho B. Auth/billing+dunning/backup-DR (P1) na
   sequência.
4. **Executar os 3 planos vivos** (observability, aptdata-viz, telegram-orchestration) com a
   dimensão `tenant_id` — eles são o "operate/retain" da fábrica; o produto vencedor é o
   cliente de teste real de todos.
5. **Dogfoodar** com A1/A3 como vitrine e estudo de caso do build-in-public — e tratar a
   própria série "construindo a fábrica" como o ativo de marketing que alimenta o funil de
   TODOS os produtos.
6. **Revisar este documento no dia 90** contra os gates do §6 — estratégia sem data de
   revisão é opinião.

> Regra final (mantida, com adendo): a fábrica só compensa se **cada micro-SaaS custa quase
> nada pra manter vivo** — e "vivo" inclui backup testado, cobrança que se recupera sozinha e
> compliance de dado. O barato de rodar existe pra sustentar experimentação até **um** acertar
> a distribuição; e experimentação barata inclui **matar barato** (§2.2).

---

*Fontes: tese do vídeo (Montano/Persua); ideias regulatórias BR (@fabianocarvalhojr); casos de
distribuição BR (microsaas.com.br / substack); métricas de churn/MRR por segmento (vibrantsnap,
ideaproof, softwareseni); agentes verticais (superannotate, actgsys); preços de IA (Claude/DeepSeek/
OpenAI/Gemini docs); payment (Stripe/Asaas/Paddle); auth (Clerk/Supabase). Detalhamento nas seções
de pesquisa (ideias/design/custos). **v2:** concorrência B1/B3 (Leoa, contabilidades digitais de
saúde, tax-techs Systax/Sovos/Arquivei, roadmaps de ERPs — checar estado atual antes do GATE 1,
mercado se move), cronograma da Reforma Tributária (LC 214/2025, alíquotas-teste 2026), LGPD
(arts. 5º/11 — dado sensível; cap. V — transferência internacional). Claims de concorrência
marcados como "a verificar" devem ser confirmados nas entrevistas do §2.1.*
