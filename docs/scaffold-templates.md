# Scaffold Templates

A CLI `aptdata scaffold` gera um esqueleto de projeto a partir de templates pré-configurados (Architectural Patterns), acelerando o desenvolvimento e garantindo padronização.

```bash
aptdata scaffold <project-name> [--template TEMPLATE] [--output DIR]
```

| Opção | Default | Descrição |
|---|---|---|
| `project-name` | *(obrigatório)* | Nome do projeto (apenas letras, números e underscores) |
| `--template`, `-t` | `hello-world` | Nome do template a ser gerado |
| `--output`, `-o` | `.` | Diretório de destino |

---

## Templates Disponíveis

=== "hello-world (Default)"

    Pipeline minimalista em Pandas. Lê um JSON, aplica uma transformação simples e salva um CSV. Ideal para testes iniciais.

    ```bash
    aptdata scaffold meu_projeto
    ```

    **Arquivos Gerados:**
    ```text
    meu_projeto/
    ├── data/
    │   └── selecao_brasileira.json
    ├── main.py
    └── requirements.txt
    ```

=== "medallion"

    Padrão de arquitetura Data Lakehouse em três camadas: **Bronze** (Raw) → **Silver** (Clean) → **Gold** (Agregado).

    ```bash
    aptdata scaffold meu_lakehouse --template medallion
    ```

    ```mermaid
    flowchart LR
        Bronze["🥉 Bronze\nIngestão Raw"]
        Silver["🥈 Silver\nLimpeza + Qualidade"]
        Gold["🥇 Gold\nAgregação + Parquet"]

        Bronze --> Silver --> Gold
    ```

=== "rag-ingestion"

    Pipeline de ingestão ponta-a-ponta para Retrieval-Augmented Generation (RAG).

    ```bash
    aptdata scaffold rag_app --template rag-ingestion
    ```

    ```mermaid
    flowchart LR
        Extract["1️⃣ Extract\n(Docs Brutos)"]
        Chunk["2️⃣ Chunk\n(Divisão)"]
        Embed["3️⃣ Embed\n(Vetorização)"]
        Load["4️⃣ Load\n(Vector Store)"]

        Extract --> Chunk --> Embed --> Load
    ```

=== "data-quality-test"

    Pipeline focado em governança, utilizando `SchemaContract` e *Expectations* rigorosas para barrar dados sujos (`QualityValidator`).

    ```bash
    aptdata scaffold dq_suite --template data-quality-test
    ```

=== "job-wheel"

    Template focado em portabilidade. Cria um projeto empacotável como um Python Wheel (`.whl`), com metadados `pyproject.toml` configurados para entry-points de CLI.

    ```bash
    aptdata scaffold my_job --template job-wheel
    ```

=== "docker-compose-app"

    Serviço conteinerizado pronto para orquestração. Inclui `Dockerfile` otimizado para Python e `docker-compose.yml` para infraestrutura anexada.

    ```bash
    aptdata scaffold my_service --template docker-compose-app
    ```

=== "viz-panel"

    Painel web **fino** com o design system aptdata (sem build, sem CDN):
    cards de agentes com badges de status (dot + texto — cor nunca carrega o
    estado sozinha), consumindo uma API de leitura no padrão do aptdata-viz
    (`/api/agents`, `/api/health`). `assets/tokens.css` é a fonte única de
    design (claro + escuro), com paleta validada para daltonismo/contraste.

    ```bash
    aptdata scaffold meu_painel --template viz-panel
    ```

    **Arquivos Gerados:**
    ```text
    meu_painel/
    ├── assets/
    │   ├── tokens.css        # fonte única de design (claro+escuro)
    │   └── components.css    # card, tile, badge, tabela
    ├── index.html            # cliente fino (configure API_BASE)
    └── README.md
    ```

=== "dashboard"

    Dashboard sem build: stat tiles, gráfico de barras em **SVG puro** (barras
    finas, topo arredondado na baseline, label direto seletivo, tooltip no
    hover, 1 série sem legenda) e **tabela acessível** dos mesmos dados —
    tudo renderizado de um `data.json` (zero lógica no frontend). Compartilha
    os MESMOS tokens do `viz-panel`.

    ```bash
    aptdata scaffold meu_dash --template dashboard
    ```

    **Arquivos Gerados:**
    ```text
    meu_dash/
    ├── assets/
    │   ├── tokens.css
    │   └── components.css
    ├── data.json             # contrato de dados (edite; o front só renderiza)
    ├── index.html
    └── README.md
    ```

---

## Mesh CLI (Orquestração de Artefatos)

O subcomando `aptdata mesh` orquestra infraestrutura local descrita em arquivos `mesh.yaml` encontrados dentro do projeto.

```bash
# Lista todos os componentes mesh
aptdata mesh list [--dir DIR] [--json]

# Constrói o componente (Wheel ou Docker Image)
aptdata mesh build COMPONENT

# Executa o artefato final
aptdata mesh run COMPONENT [--dry-run]
```

### Tipos de Componentes Suportados

| Tipo (`type` no mesh.yaml) | Ação `build` | Ação `run` |
|---|---|---|
| `job-wheel` | `pip wheel .` | Invoca o *entrypoint* do wheel gerado |
| `docker-compose-app` | `docker compose build` | `docker compose up` |

---

!!! tip "Saídas Machine-Readable"
    Todas as ações de scaffolding e mesh emitem JSON Lines estruturados (`.model_dump_json()`), facilitando a automação de logs CI/CD ou integração com o [Servidor MCP](mcp.md). Falhas críticas saem em `stderr` com *exit code* `1`.
