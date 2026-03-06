"""Scaffold command for creating a plug-and-play pandas hello-world project."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import typer


def _emit(payload: dict, *, error: bool = False) -> None:
    """Emit *payload* as a single JSON line to stdout or stderr."""
    line = json.dumps(payload, default=str)
    if error:
        print(line, file=sys.stderr, flush=True)
    else:
        print(line, flush=True)


def _validate_project_name(name: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", name))


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
    processed["jogos_selecao"] = pd.to_numeric(processed["jogos_selecao"], errors="coerce")
    processed["gols_selecao"] = pd.to_numeric(processed["gols_selecao"], errors="coerce")
    processed["participacoes_copa"] = pd.to_numeric(processed["participacoes_copa"], errors="coerce")

    processed["taxa_gols"] = (processed["gols_selecao"] / processed["jogos_selecao"]).fillna(0).round(3)
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

Pipeline dummy (hello-world) com pandas para executar ingestão → processamento → salvamento de dados da seleção brasileira.

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
  {"nome": "Alisson", "posicao": "Goleiro", "idade": 31, "jogos_selecao": 63, "gols_selecao": 0, "participacoes_copa": 2},
  {"nome": "Marquinhos", "posicao": "Zagueiro", "idade": 31, "jogos_selecao": 85, "gols_selecao": 6, "participacoes_copa": 2},
  {"nome": "Bruno Guimaraes", "posicao": "Meio-campo", "idade": 28, "jogos_selecao": 31, "gols_selecao": 1, "participacoes_copa": 1},
  {"nome": "Vinicius Junior", "posicao": "Atacante", "idade": 25, "jogos_selecao": 35, "gols_selecao": 5, "participacoes_copa": 1},
  {"nome": "Rodrygo", "posicao": "Atacante", "idade": 25, "jogos_selecao": 30, "gols_selecao": 7, "participacoes_copa": 1}
]
"""


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
) -> None:
    """Gera um projeto dummy pandas (hello-world) com pipeline de ponta a ponta."""
    if not _validate_project_name(project_name):
        _emit(
            {
                "event": "scaffold.error",
                "project": project_name,
                "error": "Project name must start with a letter and use only letters, numbers, '_' or '-'.",
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

    _emit({"event": "scaffold.started", "project": project_name, "output": str(project_dir)})

    (project_dir / "data").mkdir(parents=True, exist_ok=True)
    (project_dir / "output").mkdir(parents=True, exist_ok=True)

    (project_dir / "requirements.txt").write_text("pandas>=2.0\n", encoding="utf-8")
    (project_dir / "README.md").write_text(_render_readme(project_name), encoding="utf-8")
    (project_dir / "main.py").write_text(_render_main(project_name), encoding="utf-8")
    (project_dir / "data" / "selecao_brasileira.json").write_text(SAMPLE_INPUT, encoding="utf-8")

    _emit(
        {
            "event": "scaffold.completed",
            "project": project_name,
            "path": str(project_dir),
            "entrypoint": str(project_dir / "main.py"),
        }
    )
