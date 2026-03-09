# Scaffold Templates

The `smart-data scaffold` command bootstraps a project from a pre-built template.

```bash
smart-data scaffold <project-name> [--template TEMPLATE] [--output DIR]
```

| Option          | Default        | Description                          |
|-----------------|----------------|--------------------------------------|
| `project-name`  | *required*     | Must match `[A-Za-z][A-Za-z0-9_]*`  |
| `--template`/`-t` | `hello-world`  | Template to generate                 |
| `--output`/`-o`   | `.`            | Parent directory for the new project |

---

## Available Templates

### `hello-world` (default)

A minimal pandas pipeline that ingests a JSON file, processes it, and saves
CSV/JSON output.  Great for getting started.

```bash
smart-data scaffold my_project
```

**Generated files:**

```
my_project/
├── data/
│   └── selecao_brasileira.json
├── output/
├── main.py
├── requirements.txt
└── README.md
```

---

### `medallion`

A three-layer Bronze → Silver → Gold data lakehouse pattern.

```bash
smart-data scaffold my_lakehouse --template medallion
```

**Generated files:**

```
my_lakehouse/
├── data/
├── output/
├── bronze.py           # Raw ingestion (CSVReader)
├── silver.py           # Cleaning + PandasTransformer + QualityValidator
├── gold.py             # Aggregation + ParquetWriter
├── smart-data.yaml     # Connector config
├── requirements.txt
└── README.md
```

The Silver layer demonstrates wiring a
:class:`~smart_data.plugins.transform.pandas.PandasTransformer` with a
:class:`~smart_data.plugins.quality.validator.QualityValidator` inside a
:class:`~smart_data.core.workflow.Workflow`.

---

### `rag-ingestion`

An end-to-end Retrieval-Augmented Generation (RAG) ingestion pipeline:
extract → chunk → embed → load.

```bash
smart-data scaffold my_rag_app --template rag-ingestion
```

**Generated files:**

```
my_rag_app/
├── data/
├── pipeline.py         # 4-step Workflow (extract/chunk/embed/load)
├── smart-data.yaml
├── requirements.txt
└── README.md
```

Replace the `embed` step with your chosen embedding provider (OpenAI,
Sentence-Transformers, etc.) and the `load_to_vector_store` step with your
vector database client.

---

### `data-quality-test`

A data quality enforcement pipeline using
:class:`~smart_data.plugins.quality.contract.SchemaContract` and expectations.

```bash
smart-data scaffold my_dq_suite --template data-quality-test
```

**Generated files:**

```
my_dq_suite/
├── data/
├── quality_pipeline.py  # SchemaContract + QualityValidator + Workflow
├── smart-data.yaml
├── requirements.txt
└── README.md
```

Modify the contract columns and expectations to match your dataset, then run:

```bash
python quality_pipeline.py
```

---

## Machine-readable output

All scaffold events are emitted as JSON lines:

```json
{"event": "scaffold.started", "project": "my_project", "template": "medallion", "output": "/..."}
{"event": "scaffold.completed", "project": "my_project", "template": "medallion", "path": "/..."}
```

Error events are written to stderr with `exit code 1`:

```json
{"event": "scaffold.error", "project": "...", "error": "Directory already exists: ..."}
```
