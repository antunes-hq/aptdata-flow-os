"""Scaffold command — generates plug-and-play project templates."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import typer

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _emit(payload: dict, *, error: bool = False) -> None:
    """Emit *payload* as a single JSON line to stdout or stderr."""
    line = json.dumps(payload, default=str)
    if error:
        print(line, file=sys.stderr, flush=True)
    else:
        print(line, flush=True)


def _validate_project_name(name: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name))


# ---------------------------------------------------------------------------
# hello-world template (unchanged from original)
# ---------------------------------------------------------------------------


def _render_main(project_name: str) -> str:
    return f"""from __future__ import annotations

from pathlib import Path
from time import perf_counter

import pandas as pd


def ingest(json_path: Path) -> pd.DataFrame:
    return pd.read_json(json_path)


def process(dataframe: pd.DataFrame) -> pd.DataFrame:
    processed = dataframe.copy()
    processed["idade"] = pd.to_numeric(processed["idade"], errors="coerce")
    processed["jogos_selecao"] = pd.to_numeric(
        processed["jogos_selecao"], errors="coerce"
    )
    processed["gols_selecao"] = pd.to_numeric(
        processed["gols_selecao"], errors="coerce"
    )
    processed["participacoes_copa"] = pd.to_numeric(
        processed["participacoes_copa"], errors="coerce"
    )

    processed["taxa_gols"] = (
        (processed["gols_selecao"] / processed["jogos_selecao"]).fillna(0).round(3)
    )
    processed["indice_experiencia"] = (
        processed["jogos_selecao"] + (processed["participacoes_copa"] * 5)
    )
    return processed.sort_values(
        by=["indice_experiencia", "taxa_gols"], ascending=[False, False]
    ).reset_index(drop=True)


def save(dataframe: pd.DataFrame, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "selecao_brasileira_processada.csv"
    json_path = output_dir / "selecao_brasileira_processada.json"
    dataframe.to_csv(csv_path, index=False)
    dataframe.to_json(json_path, orient="records", force_ascii=False, indent=2)
    return csv_path, json_path


def run_pipeline() -> None:
    root = Path(__file__).resolve().parent
    input_path = root / "data" / "selecao_brasileira.json"
    output_dir = root / "output"

    started = perf_counter()
    dataframe = ingest(input_path)
    processed = process(dataframe)
    csv_path, json_path = save(processed, output_dir)
    elapsed = perf_counter() - started

    print(
        {{
            "project": "{project_name}",
            "status": "completed",
            "input_records": len(dataframe),
            "output_records": len(processed),
            "csv_output": str(csv_path),
            "json_output": str(json_path),
            "elapsed_seconds": round(elapsed, 4),
        }}
    )


if __name__ == "__main__":
    run_pipeline()
"""


def _render_readme(project_name: str) -> str:
    return f"""# {project_name}

Pipeline dummy (hello-world) com pandas para executar ingestão →
processamento → salvamento de dados da seleção brasileira.

## Como executar

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Estrutura

- `data/selecao_brasileira.json`: dataset dummy de entrada
- `main.py`: pipeline ponta a ponta
- `output/`: artefatos gerados (`.csv` e `.json`)
"""


SAMPLE_INPUT = """[
  {"nome": "Alisson", "posicao": "Goleiro", "idade": 31,
   "jogos_selecao": 63, "gols_selecao": 0, "participacoes_copa": 2},
  {"nome": "Marquinhos", "posicao": "Zagueiro", "idade": 31,
   "jogos_selecao": 85, "gols_selecao": 6, "participacoes_copa": 2},
  {"nome": "Bruno Guimaraes", "posicao": "Meio-campo", "idade": 28,
   "jogos_selecao": 31, "gols_selecao": 1, "participacoes_copa": 1},
  {"nome": "Vinicius Junior", "posicao": "Atacante", "idade": 25,
   "jogos_selecao": 35, "gols_selecao": 5, "participacoes_copa": 1},
  {"nome": "Rodrygo", "posicao": "Atacante", "idade": 25,
   "jogos_selecao": 30, "gols_selecao": 7, "participacoes_copa": 1}
]
"""


def _scaffold_hello_world(project_name: str, project_dir: Path) -> None:
    """Generate hello-world pandas project scaffold."""
    (project_dir / "data").mkdir(parents=True, exist_ok=True)
    (project_dir / "output").mkdir(parents=True, exist_ok=True)

    (project_dir / "requirements.txt").write_text("pandas>=2.0\n", encoding="utf-8")
    (project_dir / "README.md").write_text(
        _render_readme(project_name), encoding="utf-8"
    )
    (project_dir / "main.py").write_text(_render_main(project_name), encoding="utf-8")
    (project_dir / "data" / "selecao_brasileira.json").write_text(
        SAMPLE_INPUT, encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# medallion template
# ---------------------------------------------------------------------------

_MEDALLION_BRONZE = '''\
"""Bronze layer — raw ingestion."""
from __future__ import annotations

from pathlib import Path

from aptdata.plugins.dataset import InMemoryDataset
from aptdata.plugins.local_fs import CSVReader


def ingest(source_path: str) -> InMemoryDataset:
    reader = CSVReader(path=source_path)
    return reader.read()


if __name__ == "__main__":
    dataset = ingest("data/raw.csv")
    print(f"Ingested {len(dataset)} records from bronze layer.")
'''

_MEDALLION_SILVER = '''\
"""Silver layer — cleaning and quality validation."""
from __future__ import annotations

from aptdata.core.workflow import Workflow
from aptdata.plugins.transform import PandasTransformer
from aptdata.plugins.quality import (
    EnforcementMode,
    ExpectColumnToNotBeNull,
    QualityValidator,
)


def clean_data(df):
    """Drop duplicates and fill missing numeric values with zero."""
    return df.drop_duplicates().fillna(0)


transformer = PandasTransformer("clean_data", clean_data)
validator = QualityValidator(
    expectations=[ExpectColumnToNotBeNull("id")],
    enforcement=EnforcementMode.WARN,
)

workflow = Workflow("silver")
workflow.add_step(transformer.transform)
workflow.add_step(validator.validate)


def process(dataset):
    return workflow.execute(dataset)


if __name__ == "__main__":
    from bronze import ingest
    bronze_data = ingest("data/raw.csv")
    silver_data = process(bronze_data)
    print(f"Silver layer: {len(silver_data)} records processed.")
'''

_MEDALLION_GOLD = '''\
"""Gold layer — aggregation and serving."""
from __future__ import annotations

from aptdata.plugins.dataset import InMemoryDataset
from aptdata.plugins.local_fs import ParquetWriter


def aggregate(dataset: InMemoryDataset) -> InMemoryDataset:
    records = dataset.read()
    # Example: keep only non-null id records
    filtered = [r for r in records if r.get("id")]
    result = InMemoryDataset(uri="memory://gold", schema_metadata={})
    result.write(filtered)
    return result


def save(dataset: InMemoryDataset, output_path: str) -> None:
    writer = ParquetWriter(path=output_path)
    writer.write(dataset)


if __name__ == "__main__":
    from silver import process
    from bronze import ingest
    dataset = aggregate(process(ingest("data/raw.csv")))
    save(dataset, "output/gold.parquet")
    print(f"Gold layer: {len(dataset)} records saved.")
'''

_MEDALLION_YAML = """\
project: {project_name}
template: medallion

connectors:
  bronze:
    type: csv
    path: data/raw.csv
  silver:
    type: memory
  gold:
    type: parquet
    path: output/gold.parquet

quality:
  enforcement: WARN
  expectations:
    - column: id
      type: not_null
"""

_MEDALLION_REQUIREMENTS = """\
aptdata
pandas>=2.2
pyarrow>=15.0
"""

_MEDALLION_README = """\
# {project_name} — Medallion Architecture

A Bronze -> Silver -> Gold data lakehouse pipeline built with aptdata.

## Layers

| Layer  | File        | Purpose                        |
|--------|-------------|--------------------------------|
| Bronze | `bronze.py` | Raw ingestion from CSV         |
| Silver | `silver.py` | Cleaning + quality validation  |
| Gold   | `gold.py`   | Aggregation and Parquet output |

## Quick Start

```bash
pip install -r requirements.txt
python bronze.py   # ingest raw data
python silver.py   # clean and validate
python gold.py     # aggregate and save
```
"""


def _scaffold_medallion(project_name: str, project_dir: Path) -> None:
    """Generate medallion (Bronze/Silver/Gold) project scaffold."""
    (project_dir / "data").mkdir(parents=True, exist_ok=True)
    (project_dir / "output").mkdir(parents=True, exist_ok=True)

    (project_dir / "bronze.py").write_text(_MEDALLION_BRONZE, encoding="utf-8")
    (project_dir / "silver.py").write_text(_MEDALLION_SILVER, encoding="utf-8")
    (project_dir / "gold.py").write_text(_MEDALLION_GOLD, encoding="utf-8")
    (project_dir / "aptdata.yaml").write_text(
        _MEDALLION_YAML.format(project_name=project_name), encoding="utf-8"
    )
    (project_dir / "requirements.txt").write_text(
        _MEDALLION_REQUIREMENTS, encoding="utf-8"
    )
    (project_dir / "README.md").write_text(
        _MEDALLION_README.format(project_name=project_name), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# rag-ingestion template
# ---------------------------------------------------------------------------

_RAG_PIPELINE = '''\
"""RAG ingestion pipeline — extraction -> chunking -> embeddings -> vector store."""
from __future__ import annotations

from aptdata.core.workflow import Workflow


def extract(data):
    """Step 1: Extract raw text from source documents."""
    if isinstance(data, list):
        return [{"text": str(r), "id": i} for i, r in enumerate(data)]
    return data


def chunk(data):
    """Step 2: Split documents into smaller chunks."""
    if not isinstance(data, list):
        return data
    chunks = []
    for record in data:
        text = record.get("text", "")
        if not text:
            continue
        for i, start in enumerate(range(0, len(text), 512)):
            chunks.append(
                {"chunk_id": f"{record['id']}-{i}", "text": text[start : start + 512]}
            )
    return chunks


def embed(data):
    """Step 3: Generate embeddings (replace with your embedding provider)."""
    if not isinstance(data, list):
        return data
    return [
        {"chunk_id": r["chunk_id"], "text": r["text"], "embedding": [0.0] * 384}
        for r in data
    ]


def load_to_vector_store(data):
    """Step 4: Load embedded chunks into a vector store."""
    print(f"Loading {len(data)} chunks into vector store...")
    return data


workflow = Workflow("rag_ingestion")
workflow.add_step(extract)
workflow.add_step(chunk)
workflow.add_step(embed)
workflow.add_step(load_to_vector_store)


if __name__ == "__main__":
    source_docs = [
        {"content": "aptdata is a framework for building smart data pipelines."},
        {"content": "It supports RAG ingestion, quality checks, and governance."},
    ]
    result = workflow.execute(source_docs)
    print(f"RAG ingestion complete: {len(result)} chunks indexed.")
'''

_RAG_YAML = """\
project: {project_name}
template: rag-ingestion

pipeline:
  steps:
    - name: extract
      type: text_extraction
    - name: chunk
      type: text_splitter
      chunk_size: 512
    - name: embed
      type: embeddings
      model: text-embedding-3-small
    - name: load
      type: vector_store
      backend: chroma
"""

_RAG_REQUIREMENTS = """\
aptdata
openai>=1.0
chromadb>=0.4
"""

_RAG_README = """\
# {project_name} — RAG Ingestion Pipeline

An end-to-end Retrieval-Augmented Generation ingestion pipeline.

## Steps

1. **Extract** — load raw documents from source
2. **Chunk** — split documents into overlapping text chunks
3. **Embed** — generate vector embeddings via an embedding model
4. **Load** — persist embeddings to a vector store

## Quick Start

```bash
pip install -r requirements.txt
python pipeline.py
```
"""


def _scaffold_rag_ingestion(project_name: str, project_dir: Path) -> None:
    """Generate RAG ingestion project scaffold."""
    (project_dir / "data").mkdir(parents=True, exist_ok=True)

    (project_dir / "pipeline.py").write_text(_RAG_PIPELINE, encoding="utf-8")
    (project_dir / "aptdata.yaml").write_text(
        _RAG_YAML.format(project_name=project_name), encoding="utf-8"
    )
    (project_dir / "requirements.txt").write_text(_RAG_REQUIREMENTS, encoding="utf-8")
    (project_dir / "README.md").write_text(
        _RAG_README.format(project_name=project_name), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# data-quality-test template
# ---------------------------------------------------------------------------

_DQ_PIPELINE = '''\
"""Data quality test pipeline — load data, apply contract + expectations, alert."""
from __future__ import annotations

from aptdata.core.workflow import Workflow
from aptdata.plugins.quality import (
    ColumnClassification,
    ColumnContract,
    EnforcementMode,
    ExpectColumnToNotBeNull,
    ExpectColumnValuesToBeUnique,
    QualityValidator,
    SchemaContract,
)

# Define the schema contract for your dataset.
contract = SchemaContract(
    name="example_contract",
    version="1.0.0",
    owner="data-team",
    columns=[
        ColumnContract(name="id", dtype="int64", nullable=False, pii=False),
        ColumnContract(
            name="email",
            dtype="str",
            nullable=False,
            pii=True,
            classification=ColumnClassification.PII,
        ),
        ColumnContract(name="amount", dtype="float64", nullable=True),
    ],
    enforcement=EnforcementMode.ABORT,
)

# Build quality validator from contract expectations.
validator = QualityValidator(
    expectations=[
        ExpectColumnToNotBeNull("id"),
        ExpectColumnValuesToBeUnique("id"),
        ExpectColumnToNotBeNull("email"),
    ],
    enforcement=contract.enforcement,
    name="contract_validator",
)

workflow = Workflow("data_quality_test")
workflow.add_step(validator.validate)


def run_quality_check(data):
    """Run quality checks on *data* and return it if all checks pass."""
    try:
        return workflow.execute(data)
    except ValueError as exc:
        print(f"[ALERT] Quality check failed: {exc}")
        raise


if __name__ == "__main__":
    import pandas as pd

    sample_data = pd.DataFrame(
        {
            "id": [1, 2, 3],
            "email": ["a@example.com", "b@example.com", "c@example.com"],
            "amount": [100.0, 200.0, None],
        }
    )
    result = run_quality_check(sample_data)
    print(f"Quality check passed for {len(result)} records.")
'''

_DQ_YAML = """\
project: {project_name}
template: data-quality-test

contract:
  name: example_contract
  version: 1.0.0
  owner: data-team
  enforcement: ABORT
  columns:
    - name: id
      dtype: int64
      nullable: false
      pii: false
    - name: email
      dtype: str
      nullable: false
      pii: true
      classification: PII
    - name: amount
      dtype: float64
      nullable: true

expectations:
  - column: id
    type: not_null
  - column: id
    type: unique
  - column: email
    type: not_null
"""

_DQ_REQUIREMENTS = """\
aptdata
pandas>=2.2
"""

_DQ_README = """\
# {project_name} — Data Quality Test Pipeline

A data quality enforcement pipeline using aptdata schema contracts
and expectations.

## Features

- **Schema contracts** — declare expected dtypes, nullability, and PII
- **Expectations** — validate not-null, uniqueness, range, and regex
- **Enforcement modes** — ABORT (raise), WARN (log), or TAG (annotate)

## Quick Start

```bash
pip install -r requirements.txt
python quality_pipeline.py
```

## Enforcement Modes

| Mode  | Behaviour                               |
|-------|-----------------------------------------|
| ABORT | Raise ValueError on first failure       |
| WARN  | Log warning and continue                |
| TAG   | Annotate dataset metadata and continue  |
"""


def _scaffold_data_quality_test(project_name: str, project_dir: Path) -> None:
    """Generate data-quality-test project scaffold."""
    (project_dir / "data").mkdir(parents=True, exist_ok=True)

    (project_dir / "quality_pipeline.py").write_text(_DQ_PIPELINE, encoding="utf-8")
    (project_dir / "aptdata.yaml").write_text(
        _DQ_YAML.format(project_name=project_name), encoding="utf-8"
    )
    (project_dir / "requirements.txt").write_text(_DQ_REQUIREMENTS, encoding="utf-8")
    (project_dir / "README.md").write_text(
        _DQ_README.format(project_name=project_name), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# job-wheel template
# ---------------------------------------------------------------------------

_JOB_WHEEL_PYPROJECT = """\
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "{project_name}"
version = "0.1.0"
description = "aptdata job executor — packaged as a Python wheel."
requires-python = ">=3.10"
dependencies = [
    "aptdata",
]

[project.scripts]
{project_name}-job = "{project_name}.job:main"

[tool.setuptools.packages.find]
where = ["src"]
"""

_JOB_WHEEL_JOB = '''\
"""Job executor entry-point for {project_name}."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path


def run(config: dict) -> dict:
    """Execute the job logic.

    Replace this stub with your actual processing logic.
    """
    started = time.perf_counter()
    print(
        json.dumps(
            {{"event": "job.started", "job": "{project_name}", "config": config}}
        ),
        flush=True,
    )

    # --- your logic here ---

    elapsed = round(time.perf_counter() - started, 4)
    result = {{
        "event": "job.completed",
        "job": "{project_name}",
        "elapsed_seconds": elapsed,
    }}
    print(json.dumps(result), flush=True)
    return result


def main() -> None:
    """CLI entry-point (installed via pyproject.toml [project.scripts])."""
    config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    config: dict = (
        json.loads(config_path.read_text())
        if config_path and config_path.exists()
        else {{}}
    )
    run(config)


if __name__ == "__main__":
    main()
'''

_JOB_WHEEL_MESH_YAML = """\
component: {project_name}
type: job-wheel
version: "0.1.0"

build:
  backend: wheel
  source: src/

run:
  entrypoint: "{project_name}-job"
  args: []
"""

_JOB_WHEEL_MAKEFILE = """\
.PHONY: build install clean run

build:
\tpip wheel . -w dist/ --no-deps

install:
\tpip install dist/{project_name}-*.whl

clean:
\trm -rf dist/ build/ src/{project_name}.egg-info/

run:
\t{project_name}-job
"""

_JOB_WHEEL_README = """\
# {project_name} — Job Wheel

An aptdata job executor packaged as a Python wheel for portable execution.

## Structure

```
{project_name}/
├── src/
│   └── {project_name}/
│       ├── __init__.py
│       └── job.py          # Job logic + CLI entry-point
├── pyproject.toml          # Packaging metadata
├── mesh.yaml               # Component descriptor
├── Makefile
└── README.md
```

## Quick Start

```bash
# Build the wheel
make build

# Install locally
make install

# Run the job
{project_name}-job [config.json]
```

## mesh.yaml

Describes this component to the aptdata mesh orchestrator:

```yaml
component: {project_name}
type: job-wheel
```

Run via the mesh CLI:

```bash
aptdata mesh run {project_name}
```
"""


def _scaffold_job_wheel(project_name: str, project_dir: Path) -> None:
    """Generate job-wheel project scaffold."""
    src_pkg = project_dir / "src" / project_name
    src_pkg.mkdir(parents=True, exist_ok=True)

    (src_pkg / "__init__.py").write_text(
        f'"""Job package for {project_name}."""\n', encoding="utf-8"
    )
    (src_pkg / "job.py").write_text(
        _JOB_WHEEL_JOB.format(project_name=project_name), encoding="utf-8"
    )
    (project_dir / "pyproject.toml").write_text(
        _JOB_WHEEL_PYPROJECT.format(project_name=project_name), encoding="utf-8"
    )
    (project_dir / "mesh.yaml").write_text(
        _JOB_WHEEL_MESH_YAML.format(project_name=project_name), encoding="utf-8"
    )
    (project_dir / "Makefile").write_text(
        _JOB_WHEEL_MAKEFILE.format(project_name=project_name), encoding="utf-8"
    )
    (project_dir / "README.md").write_text(
        _JOB_WHEEL_README.format(project_name=project_name), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# docker-compose-app template
# ---------------------------------------------------------------------------

_DOCKER_COMPOSE_APP_PY = '''\
"""Application service entry-point for {project_name}."""
from __future__ import annotations

import json
import os
import time


def main() -> None:
    """Run the application service."""
    port = int(os.getenv("APP_PORT", "8080"))
    env = os.getenv("APP_ENV", "development")

    print(
        json.dumps({{
            "event": "app.started",
            "service": "{project_name}",
            "port": port,
            "env": env,
        }}),
        flush=True,
    )

    try:
        # --- your service logic here ---
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(
            json.dumps({{"event": "app.stopped", "service": "{project_name}"}}),
            flush=True,
        )


if __name__ == "__main__":
    main()
'''

_DOCKER_COMPOSE_DOCKERFILE = """\
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

ENV APP_PORT=8080
ENV APP_ENV=production

EXPOSE 8080

CMD ["python", "app.py"]
"""

_DOCKER_COMPOSE_YML = """\
version: "3.9"

services:
  {project_name}:
    build: .
    container_name: {project_name}
    ports:
      - "8080:8080"
    environment:
      APP_PORT: "8080"
      APP_ENV: "development"
    volumes:
      - ./data:/app/data
    restart: unless-stopped

  # Add more services below, e.g.:
  # db:
  #   image: postgres:15
  #   environment:
  #     POSTGRES_DB: mydb
  #     POSTGRES_USER: user
  #     POSTGRES_PASSWORD: password
"""

_DOCKER_COMPOSE_MESH_YAML = """\
component: {project_name}
type: docker-compose-app
version: "0.1.0"

build:
  compose_file: docker-compose.yml

run:
  service: {project_name}
  command: "docker compose up"
"""

_DOCKER_COMPOSE_REQUIREMENTS = """\
aptdata
"""

_DOCKER_COMPOSE_README = """\
# {project_name} — Docker Compose Application

An aptdata application scaffold using Docker Compose for multi-service orchestration.

## Structure

```
{project_name}/
├── data/                   # Mounted data directory
├── app.py                  # Main application service
├── Dockerfile              # Container image definition
├── docker-compose.yml      # Service orchestration
├── mesh.yaml               # Component descriptor
├── requirements.txt
└── README.md
```

## Quick Start

```bash
# Build and start all services
docker compose up --build

# Run in background
docker compose up -d

# Stop services
docker compose down
```

## mesh.yaml

Describes this component to the aptdata mesh orchestrator:

```yaml
component: {project_name}
type: docker-compose-app
```

Run via the mesh CLI:

```bash
aptdata mesh run {project_name}
```

## Adding Services

Edit `docker-compose.yml` to add more services (databases, caches, etc.)
and update `mesh.yaml` accordingly.
"""


def _scaffold_docker_compose_app(project_name: str, project_dir: Path) -> None:
    """Generate docker-compose-app project scaffold."""
    (project_dir / "data").mkdir(parents=True, exist_ok=True)

    (project_dir / "app.py").write_text(
        _DOCKER_COMPOSE_APP_PY.format(project_name=project_name), encoding="utf-8"
    )
    (project_dir / "Dockerfile").write_text(
        _DOCKER_COMPOSE_DOCKERFILE, encoding="utf-8"
    )
    (project_dir / "docker-compose.yml").write_text(
        _DOCKER_COMPOSE_YML.format(project_name=project_name), encoding="utf-8"
    )
    (project_dir / "mesh.yaml").write_text(
        _DOCKER_COMPOSE_MESH_YAML.format(project_name=project_name), encoding="utf-8"
    )
    (project_dir / "requirements.txt").write_text(
        _DOCKER_COMPOSE_REQUIREMENTS, encoding="utf-8"
    )
    (project_dir / "README.md").write_text(
        _DOCKER_COMPOSE_README.format(project_name=project_name), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# design-system templates (viz-panel / dashboard)
# ---------------------------------------------------------------------------
# Fonte única de design: os dois templates projetam os MESMOS tokens
# (paleta validada com o método dataviz — CVD/contraste checados; os slots
# claros abaixo de 3:1 exigem labels diretos ou tabela, que os templates têm).

_DESIGN_TOKENS_CSS = """\
/* tokens.css — fonte única de design (não edite por template; edite aqui) */
:root {
  --page: #f9f9f7;
  --surface-1: #fcfcfb;
  --text-primary: #0b0b0b;
  --text-secondary: #52514e;
  --text-muted: #898781;
  --grid: #e1e0d9;
  --baseline: #c3c2b7;
  --border: rgba(11, 11, 11, 0.10);
  --series-1: #2a78d6;  /* blue   */
  --series-2: #1baf7a;  /* aqua   — <3:1 no claro: exige label/tabela */
  --series-3: #eda100;  /* yellow — idem */
  --series-4: #008300;  /* green  */
  --status-good: #0ca30c;
  --status-warning: #fab219;
  --status-serious: #ec835a;
  --status-critical: #d03b3b;
  --radius: 12px;
  --radius-s: 8px;
  --gap: 14px;
  --font: system-ui, -apple-system, "Segoe UI", sans-serif;
}
@media (prefers-color-scheme: dark) {
  :root {
    --page: #0d0d0d;
    --surface-1: #1a1a19;
    --text-primary: #ffffff;
    --text-secondary: #c3c2b7;
    --grid: #2c2c2a;
    --baseline: #383835;
    --border: rgba(255, 255, 255, 0.10);
    --series-1: #3987e5;
    --series-2: #199e70;
    --series-3: #c98500;
    --series-4: #008300;
  }
}
"""

_DESIGN_COMPONENTS_CSS = """\
/* components.css — peças do design system (card, tile, badge, tabela) */
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--page); color: var(--text-primary);
  font-family: var(--font);
}
.wrap { max-width: 1000px; margin: 0 auto; padding: 28px 20px 80px; }
header h1 { font-size: 24px; margin: 0; letter-spacing: -0.4px; }
header .sub { color: var(--text-muted); font-size: 13px; margin: 4px 0 0; }

.tiles { display: flex; gap: var(--gap); flex-wrap: wrap; margin: 20px 0; }
.tile {
  flex: 1; min-width: 150px; background: var(--surface-1);
  border: 1px solid var(--border); border-radius: var(--radius);
  padding: 14px 16px;
}
.tile .label { color: var(--text-muted); font-size: 12px; }
.tile .value { font-size: 28px; font-weight: 700; margin-top: 2px; }
.tile .delta { font-size: 12px; color: var(--text-secondary); }

.card {
  background: var(--surface-1); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 16px; margin: 14px 0;
}
.grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: var(--gap);
}

/* status: sempre dot + TEXTO (cor nunca carrega o estado sozinha) */
.badge {
  display: inline-flex; align-items: center; gap: 6px; font-size: 12px;
  font-weight: 600; padding: 3px 9px; border-radius: 999px;
  border: 1px solid var(--border); color: var(--text-secondary);
}
.badge .dot { width: 8px; height: 8px; border-radius: 50%; }
.badge.good .dot { background: var(--status-good); }
.badge.warning .dot { background: var(--status-warning); }
.badge.critical .dot { background: var(--status-critical); }
.badge.muted .dot { background: var(--text-muted); }

.tag {
  font-size: 11px; padding: 2px 8px; border-radius: var(--radius-s);
  border: 1px solid var(--border); color: var(--text-secondary);
}

table { width: 100%; border-collapse: collapse; font-size: 13px; }
th {
  text-align: left; color: var(--text-muted); font-weight: 600;
  border-bottom: 1px solid var(--baseline); padding: 6px 8px;
}
td { border-top: 1px solid var(--grid); padding: 6px 8px; }
td.num { text-align: right; font-variant-numeric: tabular-nums; }

.empty { color: var(--text-muted); text-align: center; padding: 40px; }
"""

_VIZ_PANEL_HTML = """\
<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<meta name="color-scheme" content="dark light" />
<title>{project_name} · painel</title>
<link rel="stylesheet" href="assets/tokens.css" />
<link rel="stylesheet" href="assets/components.css" />
</head>
<body>
<div class="wrap">
  <header>
    <h1>{project_name}</h1>
    <p class="sub">Painel fino — consome uma API de leitura (padrão aptdata-viz);
      zero lógica de negócio no frontend.</p>
  </header>

  <div class="tiles" id="tiles"></div>
  <div class="grid" id="grid"><div class="empty">carregando…</div></div>
</div>

<script>
// Aponte para a sua API (ex.: http://localhost:4570 do `aptdata viz`).
const API_BASE = '';
const $ = s => document.querySelector(s);
const api = p => fetch(API_BASE + p).then(r => r.json());
const esc = s => String(s).replace(/[&<>"]/g,
  m => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}}[m]));

// status: classe de badge + TEXTO — cor nunca carrega o estado sozinha
function statusLabel(h) {{
  const map = {{up: ['good', 'up'], down: ['critical', 'down'],
               disabled: ['muted', 'off'], unknown: ['warning', '?']}};
  const [cls, label] = map[h] || map.unknown;
  return `<span class="badge ${{cls}}"><span class="dot"></span>${{esc(label)}}</span>`;
}}

function tiles(agents, health) {{
  const up = Object.values(health).filter(h => h === 'up').length;
  const enabled = agents.filter(a => a.enabled).length;
  $('#tiles').innerHTML = [
    ['agentes', agents.length], ['habilitados', enabled], ['up agora', up],
  ].map(([label, value]) =>
    `<div class="tile"><div class="label">${{label}}</div>` +
    `<div class="value">${{value}}</div></div>`).join('');
}}

async function load() {{
  try {{
    const [a, h] = await Promise.all([api('/api/agents'), api('/api/health')]);
    const agents = a.agents || [];
    const health = h.health || {{}};
    tiles(agents, health);
    if (!agents.length) {{
      $('#grid').innerHTML = '<div class="empty">Registry vazio.</div>';
      return;
    }}
    $('#grid').innerHTML = agents.map(ag => `
      <div class="card">
        <div style="display:flex;justify-content:space-between;align-items:center">
          <strong>${{esc(ag.name || ag.id)}}</strong>
          ${{statusLabel(health[ag.id] || 'unknown')}}
        </div>
        <div style="margin-top:8px;display:flex;gap:6px;flex-wrap:wrap">
          <span class="tag">${{esc(ag.type || '?')}}</span>
          ${{(ag.capabilities || [])
            .map(c => `<span class="tag">${{esc(c)}}</span>`).join('')}}
        </div>
      </div>`).join('');
  }} catch (err) {{
    $('#grid').innerHTML =
      '<div class="empty">API fora do ar — suba com <code>aptdata viz</code> ' +
      'e configure API_BASE.</div>';
  }}
}}
load();
setInterval(load, 15000);
</script>
</body>
</html>
"""

_VIZ_PANEL_README = """\
# {project_name} — painel fino (design system aptdata)

Painel web **sem build e sem CDN** que consome uma API de leitura no padrão
do aptdata-viz (`/api/agents`, `/api/health`). Zero lógica de negócio no
frontend — a API é o contrato.

## Rodando

1. Suba uma API (ex.: `aptdata viz` na porta 4570).
2. Edite `API_BASE` no `index.html` (ex.: `http://localhost:4570`).
3. Sirva a pasta: `python -m http.server 8080` e abra `http://localhost:8080`.

## Design system

- `assets/tokens.css` é a **fonte única** de design (cores/spacing/raio,
  claro+escuro via `prefers-color-scheme`). Edite os tokens, nunca os
  componentes, para retematizar.
- Status usa **dot + texto** (cor nunca carrega o estado sozinha).
- Paleta validada para daltonismo/contraste (método dataviz).
"""

_DASHBOARD_HTML = """\
<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<meta name="color-scheme" content="dark light" />
<title>{project_name} · dashboard</title>
<link rel="stylesheet" href="assets/tokens.css" />
<link rel="stylesheet" href="assets/components.css" />
<style>
  .chart {{ position: relative; }}
  .chart svg {{ display: block; width: 100%; height: auto; }}
  .bar {{ fill: var(--series-1); }}
  .bar:hover {{ opacity: 0.85; }}
  .axis {{ stroke: var(--baseline); stroke-width: 1; }}
  .lbl {{ font: 11px var(--font); fill: var(--text-muted); }}
  .lbl.direct {{ fill: var(--text-secondary); font-weight: 600; }}
  .tip {{
    position: absolute; pointer-events: none; background: var(--surface-1);
    border: 1px solid var(--border); border-radius: var(--radius-s);
    padding: 6px 9px; font-size: 12px; display: none;
  }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>{project_name}</h1>
    <p class="sub" id="subtitle"></p>
  </header>

  <div class="tiles" id="tiles"></div>

  <div class="card chart">
    <h2 id="chart-title" style="font-size:14px;margin:0 0 10px"></h2>
    <svg id="chart" viewBox="0 0 720 260" role="img"></svg>
    <div class="tip" id="tip"></div>
  </div>

  <div class="card">
    <table id="table"></table>
  </div>
</div>

<script>
// Frontend fino: renderiza o que vem de data.json — nada de regra de negócio.
const DEFAULT_DATA = {{
  title: 'Exemplo — troque por data.json',
  tiles: [
    {{label: 'total', value: 128, delta: '+12 na semana'}},
    {{label: 'ok', value: 121}},
    {{label: 'falhas', value: 7}}
  ],
  series: {{
    label: 'Execuções por dia',
    points: [
      {{x: 'seg', y: 14}}, {{x: 'ter', y: 22}}, {{x: 'qua', y: 18}},
      {{x: 'qui', y: 31}}, {{x: 'sex', y: 25}}, {{x: 'sab', y: 9}},
      {{x: 'dom', y: 9}}
    ]
  }}
}};
const $ = s => document.querySelector(s);
const esc = s => String(s).replace(/[&<>"]/g,
  m => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}}[m]));

function tiles(data) {{
  $('#tiles').innerHTML = (data.tiles || []).map(t =>
    `<div class="tile"><div class="label">${{esc(t.label)}}</div>` +
    `<div class="value">${{esc(t.value)}}</div>` +
    (t.delta ? `<div class="delta">${{esc(t.delta)}}</div>` : '')
    + '</div>').join('');
}}

// barras finas, topo arredondado ancorado na baseline, gaps, label direto
// só no máximo (seletivo), hover tooltip por barra — 1 série, sem legenda.
function chart(data) {{
  const pts = (data.series || {{}}).points || [];
  $('#chart-title').textContent = (data.series || {{}}).label || '';
  if (!pts.length) return;
  const W = 720, H = 260, padL = 36, padB = 28, padT = 14;
  const max = Math.max(...pts.map(p => p.y));
  const bw = Math.min(28, (W - padL - 12) / pts.length - 8);
  const x = i => padL + i * ((W - padL - 12) / pts.length) + 4;
  const y = v => padT + (1 - v / max) * (H - padT - padB);
  let svg = `<line class="axis" x1="${{padL}}" y1="${{H - padB}}"` +
            ` x2="${{W - 8}}" y2="${{H - padB}}"/>`;
  pts.forEach((p, i) => {{
    const top = y(p.y), bh = H - padB - top, r = Math.min(4, bh);
    svg += `<path class="bar" data-i="${{i}}" d="M${{x(i)}} ${{H - padB}}` +
      ` v-${{bh - r}} q0,-${{r}} ${{r}},-${{r}} h${{bw - 2 * r}}` +
      ` q${{r}},0 ${{r}},${{r}} v${{bh - r}} z"/>`;
    svg += `<text class="lbl" x="${{x(i) + bw / 2}}" y="${{H - 8}}"` +
      ` text-anchor="middle">${{esc(p.x)}}</text>`;
    if (p.y === max) {{
      svg += `<text class="lbl direct" x="${{x(i) + bw / 2}}" y="${{top - 6}}"` +
        ` text-anchor="middle">${{p.y}}</text>`;
    }}
  }});
  $('#chart').innerHTML = svg;
  const tip = $('#tip');
  $('#chart').addEventListener('mousemove', e => {{
    const bar = e.target.closest('.bar');
    if (!bar) {{ tip.style.display = 'none'; return; }}
    const p = pts[Number(bar.dataset.i)];
    tip.innerHTML = `<strong>${{esc(p.x)}}</strong> · ${{p.y}}`;
    tip.style.display = 'block';
    tip.style.left = (e.offsetX + 14) + 'px';
    tip.style.top = (e.offsetY - 8) + 'px';
  }});
  $('#chart').addEventListener('mouseleave',
    () => {{ tip.style.display = 'none'; }});
}}

// a tabela é a visão acessível dos MESMOS dados (regra de relevo da paleta)
function table(data) {{
  const pts = (data.series || {{}}).points || [];
  $('#table').innerHTML =
    '<thead><tr><th>x</th><th style="text-align:right">valor</th></tr></thead>' +
    '<tbody>' + pts.map(p =>
      `<tr><td>${{esc(p.x)}}</td><td class="num">${{p.y}}</td></tr>`
    ).join('') + '</tbody>';
}}

function render(data) {{
  $('#subtitle').textContent = data.title || '';
  tiles(data); chart(data); table(data);
}}
fetch('data.json').then(r => r.json()).then(render)
  .catch(() => render(DEFAULT_DATA));
</script>
</body>
</html>
"""

_DASHBOARD_DATA_JSON = """\
{
  "title": "Visão geral — edite data.json (o front só renderiza)",
  "tiles": [
    {"label": "total", "value": 128, "delta": "+12 na semana"},
    {"label": "ok", "value": 121},
    {"label": "falhas", "value": 7}
  ],
  "series": {
    "label": "Execuções por dia",
    "points": [
      {"x": "seg", "y": 14}, {"x": "ter", "y": 22}, {"x": "qua", "y": 18},
      {"x": "qui", "y": 31}, {"x": "sex", "y": 25}, {"x": "sab", "y": 9},
      {"x": "dom", "y": 9}
    ]
  }
}
"""

_DASHBOARD_README = """\
# {project_name} — dashboard (design system aptdata)

Dashboard **sem build e sem CDN**: stat tiles, gráfico de barras em SVG puro
e tabela acessível, tudo renderizado de um `data.json` — zero lógica de
negócio no frontend.

## Rodando

```bash
python -m http.server 8080   # nesta pasta
# abra http://localhost:8080 e edite data.json
```

## Contrato do data.json

```json
{{
  "title": "…",
  "tiles": [{{"label": "…", "value": 0, "delta": "…"}}],
  "series": {{"label": "…", "points": [{{"x": "…", "y": 0}}]}}
}}
```

## Design system

- `assets/tokens.css` é a **fonte única** (claro+escuro); edite tokens, não
  componentes.
- Gráfico segue o método dataviz: barras finas com topo arredondado na
  baseline, 1 série (sem legenda — o título nomeia), label direto só no
  máximo, tooltip no hover, e a **tabela** como visão acessível dos mesmos
  dados (paleta validada para daltonismo/contraste).
"""


def _write_design_assets(project_dir: Path) -> None:
    """Projeta os tokens/components compartilhados (fonte única de design)."""
    assets = project_dir / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    (assets / "tokens.css").write_text(_DESIGN_TOKENS_CSS, encoding="utf-8")
    (assets / "components.css").write_text(
        _DESIGN_COMPONENTS_CSS, encoding="utf-8"
    )


def _scaffold_viz_panel(project_name: str, project_dir: Path) -> None:
    """Generate viz-panel project scaffold (thin web panel)."""
    _write_design_assets(project_dir)
    (project_dir / "index.html").write_text(
        _VIZ_PANEL_HTML.format(project_name=project_name), encoding="utf-8"
    )
    (project_dir / "README.md").write_text(
        _VIZ_PANEL_README.format(project_name=project_name), encoding="utf-8"
    )


def _scaffold_dashboard(project_name: str, project_dir: Path) -> None:
    """Generate dashboard project scaffold (tiles + SVG chart + table)."""
    _write_design_assets(project_dir)
    (project_dir / "index.html").write_text(
        _DASHBOARD_HTML.format(project_name=project_name), encoding="utf-8"
    )
    (project_dir / "data.json").write_text(_DASHBOARD_DATA_JSON, encoding="utf-8")
    (project_dir / "README.md").write_text(
        _DASHBOARD_README.format(project_name=project_name), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Template dispatch
# ---------------------------------------------------------------------------

_TEMPLATES: dict[str, tuple[str, object]] = {
    "hello-world": (
        "Gera um projeto dummy pandas (hello-world).",
        _scaffold_hello_world,
    ),
    "medallion": (
        "Gera um projeto Bronze/Silver/Gold (Medallion Architecture).",
        _scaffold_medallion,
    ),
    "rag-ingestion": (
        "Gera um pipeline RAG de ingestão de documentos.",
        _scaffold_rag_ingestion,
    ),
    "data-quality-test": (
        "Gera um pipeline de testes de qualidade de dados.",
        _scaffold_data_quality_test,
    ),
    "job-wheel": (
        "Gera um executor JOB empacotado como Python wheel.",
        _scaffold_job_wheel,
    ),
    "docker-compose-app": (
        "Gera uma aplicação Docker Compose multi-serviço.",
        _scaffold_docker_compose_app,
    ),
    "viz-panel": (
        "Gera um painel web fino (design system aptdata, consome API de leitura).",
        _scaffold_viz_panel,
    ),
    "dashboard": (
        "Gera um dashboard (tiles + gráfico SVG + tabela) sobre um data.json.",
        _scaffold_dashboard,
    ),
}

TEMPLATE_NAMES = list(_TEMPLATES)


# ---------------------------------------------------------------------------
# CLI command
# ---------------------------------------------------------------------------


def scaffold(
    project_name: str = typer.Argument(..., help="Nome do novo projeto."),
    output: Path = typer.Option(
        Path("."),
        "--output",
        "-o",
        dir_okay=True,
        file_okay=False,
        writable=True,
        resolve_path=True,
        help="Diretório onde o scaffold será criado.",
    ),
    template: str = typer.Option(
        "hello-world",
        "--template",
        "-t",
        help=(f"Template a ser gerado. Opções: {', '.join(TEMPLATE_NAMES)}."),
    ),
) -> None:
    """Gera um projeto aptdata a partir de um template."""
    if not _validate_project_name(project_name):
        _emit(
            {
                "event": "scaffold.error",
                "project": project_name,
                "error": (
                    "Project name must start with a letter"
                    " and use only letters, numbers, and '_'."
                ),
            },
            error=True,
        )
        raise SystemExit(1)

    if template not in _TEMPLATES:
        _emit(
            {
                "event": "scaffold.error",
                "project": project_name,
                "error": (
                    f"Unknown template '{template}'."
                    f" Available: {', '.join(TEMPLATE_NAMES)}."
                ),
            },
            error=True,
        )
        raise SystemExit(1)

    target_root = output.resolve()
    project_dir = target_root / project_name

    if project_dir.exists():
        _emit(
            {
                "event": "scaffold.error",
                "project": project_name,
                "error": f"Directory already exists: {project_dir}",
            },
            error=True,
        )
        raise SystemExit(1)

    _emit(
        {
            "event": "scaffold.started",
            "project": project_name,
            "template": template,
            "output": str(project_dir),
        }
    )

    project_dir.mkdir(parents=True, exist_ok=True)
    _, generator = _TEMPLATES[template]
    generator(project_name, project_dir)  # type: ignore[operator]

    _emit(
        {
            "event": "scaffold.completed",
            "project": project_name,
            "template": template,
            "path": str(project_dir),
        }
    )
