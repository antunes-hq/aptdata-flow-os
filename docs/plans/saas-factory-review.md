# Parecer — revisão crítica do saas-factory.md (v1 → v2)

> Revisão de estratégia feita contra o estado real do aptdata 0.2.0 (código + planos vivos:
> sync-architecture, observability, aptdata-viz, telegram-orchestration). Este documento é o
> raciocínio por trás das mudanças aplicadas na v2 do `saas-factory.md` — o que discordei, o
> que faltava, e o que a v1 acertou e foi mantido.

## Veredito em uma frase

A tese central da v1 está certa (o gargalo é churn + distribuição, e o aptdata como fábrica é
a jogada correta), mas o documento **vendia a própria tese barato**: precificava a distribuição
em ~zero, inflava a margem com uma conta incompleta, afirmava "sem incumbente" em dois nichos
onde há incumbentes nomeáveis, e não tinha nenhum mecanismo de decisão (validação, gates,
kill-criteria) — era um mapa sem bússola.

---

## As 3 maiores discordâncias

### 1. "Sem incumbente" era falso nos dois nichos fiscais — e o moat proposto não existia

- **B1 (psicólogo):** existe a **Leoa** (automação de Carnê-Leão para profissionais de saúde,
  com funding), contabilidades digitais especializadas em saúde, e — pior — as ferramentas
  **gratuitas** da própria Receita (app Receita Saúde + Carnê-Leão Web), que são exatamente o
  motivo da obrigação de 2025. O incumbente dominante, porém, não é app nenhum: é **"meu
  contador resolve"** (R$150–300/mês, com rosto, CRC e responsabilidade). A v1 tratava a
  obrigação legal só como motor de retenção; ela é também **barreira de entrada contra você**
  — comprador com medo de multa é avesso a fornecedor desconhecido.
- **B3 (CBS/IBS):** todo ERP/emissor é *obrigado* a implementar o layout novo, e o Brasil tem
  uma indústria inteira de tax-tech (Systax, Sovos, Arquivei/Qive, Avalara) que vive disso.
  "95% erram" é uma janela de 12–24 meses, não um vácuo. Além disso, 2026 é ano-teste com
  alíquotas simbólicas — a dor de 2026 é rejeição/retrabalho, não multa; o marketing de
  urgência da v1 estava calibrado pro cenário de 2027+.
- **Consequência na v2:** o moat foi redefinido como **canal + dado + profundidade de workflow**
  (nunca "ninguém faz"), B3 subiu para 🥈 (fit técnico determinístico + canal contador
  multiplicador), C2 desceu para 🥉, e cada ideia ganhou um campo explícito de **"maior motivo
  pra falhar"**.

### 2. O top-3 contradiz a própria tese do documento — e a contradição custa caro

A v1 define 4 travas de valor e duas delas são **dogfooding** (trava #2) e **canal que ele
controla** (trava #3). B1 e B3 violam as duas: Lucas não é psicólogo nem emite NF-e em volume,
e o canal que ele efetivamente controla é **audiência dev pt-BR** — que não compra nenhum dos
dois produtos. Os casos de founder-led growth citados como evidência (R$1k→R$13k etc.) eram
founders **dentro do próprio nicho**, ou seja, a evidência da v1 não transfere para o plano da
v1. Isso não invalida B1/B3 (o bloco A tem teto de ticket e churn pior — o ranking não inverte),
mas significa que o item mais caro do plano é exatamente o que a v1 assumia de graça: construir
canal em nicho alheio custa 3–6 meses de founder antes do primeiro real.

**Consequência na v2:** o pedágio virou mecanismo — **nenhum código de produto antes do
experimento de canal passar** (§2.1: ≤3 semanas, ≤R$500, kill-criteria escritos antes), B1 é
🥇 *condicional*, os experimentos de B1 e B3 rodam em paralelo e o vencedor leva, com A2
(único com canal já existente) como fallback declarado.

### 3. A margem de 85–93% era marketing — e tem um conflito estrutural escondido

A conta da v1 (payment 5% + IA $1,47) omitia: **impostos sobre receita** (Simples serviço,
~6–15,5%), **suporte humano** (que em nicho regulatório escala com a ansiedade do cliente, não
com o ticket — pico no IRPF), **inadimplência/dunning** (cartão recorrente no BR falha como
rotina) e o custo do primeiro cliente (~10× o centésimo). Margem realista: **~65–80%**.

Mais grave que o número: a margem depende de rotear ~80% do tráfego pro **DeepSeek**, mas o
nicho-carro-chefe processa **CPF de pacientes + dados fiscais** — dado sensível (LGPD art. 5º/11)
com transferência internacional problemática, e um deal-breaker comercial ("pra onde vai meu
dado?" é a primeira pergunta do contador). **A estratégia de custo e a estratégia de nicho da
v1 colidiam e o documento não via.** A v2 resolve com hierarquia: (1) núcleo determinístico
com LLM só na borda (B3 é quase todo regra — mais um motivo da subida), (2) masking pré-LLM
(gap P0\* novo, com `mask_telemetry_value` como semente), (3) provedor com contrato adequado
para flows sensíveis, aceitando margem menor. E o roteamento do aptdata ganha uma dimensão:
**rotear por sensibilidade, não só por custo**.

A conclusão da v1 ("$10k é trivial na margem, difícil na aquisição") **sobrevive** com 65–80%
— por isso a discordância é com a honestidade do número, não com a direção.

---

## Discordâncias menores (aplicadas na v2)

- **C2 white-label estava superestimado.** "Terceirizar distribuição" soa elegante, mas o
  modelo real é: cada parceiro é uma mini-venda enterprise, o suporte cascateia pra você, a
  receita concentra (5 parceiros → perder 1 = −20% MRR) e a demanda ("criador quer white-label")
  nunca foi validada — o que criador quer é revenue share com zero trabalho, o que transforma
  a fábrica em dev shop. Desceu pra 🥉 e só avança com ≥2 LOIs assinadas com setup fee.
- **Telegram como interface é fit de dev, não do nicho.** Psicólogo e contador vivem no
  WhatsApp e no navegador. Os planos vivos (telegram-orchestration) acertaram em deixar o
  transporte fino — a v2 adiciona onboarding self-service web (P1) e transporte WhatsApp (P2)
  como gaps nomeados, senão o "operate/retain" não alcança o usuário-alvo.
- **A ordem dos gaps P0 estava certa, mas a lista estava curta pra "fábrica de verdade":**
  faltavam LGPD (P0\* — bloqueante de *venda*, não de template), backup/DR testado (VPS única
  + dado fiscal = roleta), dunning (5–9% do MRR no BR) e export de dados/offboarding. Todos
  entraram na tabela do §3 com prioridade e reuso apontados.
- **Sazonalidade fiscal ignorada:** o nicho B1 tem um **cliff de churn em maio** (entregou o
  IRPF, cancela) e pico de suporte no Q1–Q2. A v2 responde com produto de valor *mensal*
  (recibo/carnê são obrigações mensais), anual fechado antes de maio e provisionamento de
  suporte.

## O que faltava e foi adicionado (novidades da v2)

1. **§2.1 Experimentos de validação** por ideia — landing com preço, entrevistas, concierge
   pago, DMs com mockup — cada um com sinal de PASSA e de MATA.
2. **§2.2 Kill-criteria** pré-código e pós-lançamento (churn >8%/mês após 3 meses, ativação
   <40%, CAC-tempo >4h/cliente, <30 pagantes no dia 90) + regra anti-custo-afundado.
3. **§5.1–5.2 Pricing/packaging e retenção por ideia** — trial (não freemium) no B1, isca de
   diagnóstico no B3, setup fee + piso no C2; âncora contra o contador, plano
   contador-parceiro, anual como arma anti-cliff.
4. **§6 Plano de 90 dias semana a semana** com 3 gates — e a decisão de **extrair a fábrica do
   produto** (tenancy/template nascem do B1 real nas semanas 4–6), não construir fábrica
   especulativa primeiro.
5. **§7 Registro de riscos** — responsabilidade fiscal (ToS, contador valida regra, trilha
   auditável via observability/run_id como *prova*), LGPD, dependência de canal de terceiro,
   concentração, corrida contra roadmap de ERP, sazonalidade, key-person, câmbio.

## O que a v1 acertou (mantido intacto)

- A tese `MRR ≈ novos×ticket ÷ churn` e a leitura do caso Persua (40% churn é o problema, não
  a feature).
- **"O aptdata é a linha de montagem, não o produto"** — a melhor frase do documento e a
  decisão estratégica mais importante.
- A arquitetura de duas camadas (núcleo 1x vs config/flows por produto) e a regra de ouro
  herdada da telegram-orchestration — coerente com o que o código 0.2.0 e os planos vivos
  realmente têm.
- Tenancy + template `new-saas` como os dois P0 de criação — ordem certa, só faltava companhia.
- Billing consumindo a telemetria por tenant como fonte de uso (elegante, evita o contador
  paralelo) e o roteamento barato→caro como vantagem estrutural de custo.
- "Fábrica paralela no back-end, distribuição serial no front-end" — mantido como lei.

## Ressalva epistêmica

Os claims de concorrência da v2 (Leoa, tax-techs, roadmap de ERPs) vêm de conhecimento com
corte em jan/2026 — mercado se move; o §2.1 manda confirmá-los nas entrevistas do GATE 1
antes de qualquer decisão irreversível. O mesmo vale para o cronograma da Reforma (LC 214/2025
e alíquotas-teste de 2026): checar o estado regulatório vigente na semana 1.
