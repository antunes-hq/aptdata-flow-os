# Primeiros Passos (Getting Started)

## Requisitos
- Python ≥ 3.10
- [Poetry](https://python-poetry.org/) (recomendado) **ou** `pip`

---

## Instalação

=== "Poetry"
    ```bash
    poetry add aptdata
    # Para plugins opcionais:
    poetry add "aptdata[pandas]"
    ```

=== "Pip"
    <div class="termy">
      <span data-ty="input">pip install aptdata</span>
      <span data-ty="progress"></span>
      <span data-ty>Successfully installed aptdata-0.1.0</span>
      <span data-ty></span>
      <span data-ty="input" data-ty-prompt=">"># Para plugins opcionais:</span>
      <span data-ty="input">pip install "aptdata[pandas]"</span>
    </div>

### Dependências Opcionais
- `pandas`: Suporte ao Pandas e `PandasTransformComponent`
- `spark`: Suporte ao PySpark
- `plugins`: Adaptadores REST, PostgreSQL, Parquet I/O
- `ai`: Servidor Model Context Protocol (MCP) para IA
- `all`: Instala tudo

---

## Verificando a Instalação

Rode no terminal:
```bash
aptdata --help
```

Saída esperada (resumida):
```text
Usage: aptdata [OPTIONS] COMMAND [ARGS]...

 Smart Data – declarative data-pipeline framework.

Commands:
  run           Run a registered data pipeline.
  monitor       Open the interactive TUI monitoring dashboard.
  mcp-start     Start the MCP (Model Context Protocol) server.
  scaffold      Gera um projeto aptdata a partir de um template.
  interactive   Launch the interactive wizard mode.
  studio        Launch aptdata studio — the web view of the agent ecosystem.
  schema        Schema utilities for declarative configuration.
  system        Inspect and validate registered systems.
  plugin        Manage and inspect plugins.
  config        Manage declarative YAML configurations.
  telemetry     Inspect OpenTelemetry telemetry status.
  mesh          Orchestrate mesh components (job-wheel, docker-compose-app, …).
  agents        Talk to the multi-agent ecosystem.
  project       Orchestrate projects across agents.
```

---

## Construindo seu Primeiro Sistema

O fluxo lógico de orquestração do framework segue cinco etapas principais:

```mermaid
flowchart LR
    %% Estilos Customizados (Design Premium)
    classDef default fill:#0b132b,stroke:#ff6a00,stroke-width:1px,color:#fff,rx:8px,ry:8px;

    DS["1️⃣ Dataset\nLeitura / Escrita (IDataset)"]
    CO["2️⃣ Component\nTransformação (IComponent)"]
    FL["3️⃣ Flow\nConexões Condicionais (IFlow)"]
    SY["4️⃣ System\nOrquestrador Base (ISystem)"]
    RG["5️⃣ Execução\nCLI ou Plugin Registry"]

    DS --> CO --> FL --> SY --> RG
```

### 1. Criar um Dataset
Um Dataset implementa as operações de leitura e escrita através do contrato `IDataset`. Herdando de `BaseDataset`, você recebe injeção de estado e validação via Pydantic.

```python
from pydantic.dataclasses import dataclass as pydantic_dataclass
from aptdata.core import BaseDataset

@pydantic_dataclass
class MemoryDataset(BaseDataset): # (1)!
    """Dataset em memória para propósitos de teste."""

    def __post_init__(self) -> None: # (2)!
        self._data = None

    def read(self): # (3)!
        return self._data

    def write(self, data) -> None:
        self._data = data
```

1. A herança de `BaseDataset` garante injeção do esquema Pydantic para validação robusta.
2. O método `__post_init__` é o local ideal para definir propriedades mutáveis ou privadas que não devem ser validadas como input do construtor.
3. O método `read()` é onde a lógica de extração real (ex: chamar a API do Pandas ou do Spark) acontece.

### 2. Criar um Componente
Um Componente (implementa `IComponent`) recebe uma lista de *inputs* validados, os processa, e retorna uma lista de *outputs* (permitindo múltiplas saídas ou fluxos paralelos).

```python
from pydantic.dataclasses import dataclass as pydantic_dataclass
from aptdata.core import BaseComponent, ComponentMeta, ComponentKind, IDataset

@pydantic_dataclass
class DoubleComponent(BaseComponent):
    """Duplica todos os valores numéricos da lista."""

    def validate_inputs(self, inputs: list[IDataset]) -> bool:
        return len(inputs) == 1

    def execute(self, inputs: list[IDataset]) -> list[IDataset]:
        data = inputs[0].read()
        out = MemoryDataset(uri="memory://output")
        out.write([x * 2 for x in data])
        return [out]

comp = DoubleComponent(
    component_id="double",
    metadata=ComponentMeta(kind=ComponentKind.TRANSFORM, tags=["math"]),
)
```

!!! tip "Dica de DX"
    Com a API Declarativa (decorators como `@pandas_component`), a instanciação manual do `InMemoryDataset` é feita pelo framework "por debaixo dos panos". Você codifica apenas a função recebendo e devolvendo DataFrames.

### 3. Criar um Fluxo (Flow)
Um Fluxo liga componentes em um Grafo Direcionado. Herdando de `BaseFlow`, as arestas suportam condicionais nativas (`FlowEdge`).

```python
from pydantic.dataclasses import dataclass as pydantic_dataclass
from aptdata.core import BaseFlow, IComponent, IDataset, FlowEdge, FlowNode
from typing import Callable

@pydantic_dataclass
class SimpleFlow(BaseFlow):
    def __post_init__(self) -> None:
        self._nodes: dict[str, FlowNode] = {}
        self._edges: list[FlowEdge] = []
        self._order: list[str] = []

    def add_component(self, c: IComponent) -> None:
        self._nodes[c.component_id] = FlowNode(component=c, flow=self)

    def connect(self, src: str, tgt: str, condition: Callable | None = None) -> None:
        self._edges.append(FlowEdge(source_id=src, target_id=tgt, condition=condition))

    def compile(self) -> None:
        targets = {e.target_id for e in self._edges}
        roots = [cid for cid in self._nodes if cid not in targets]
        queue = list(roots)
        while queue:
            current = queue.pop(0)
            self._order.append(current)
            for e in self._edges:
                if e.source_id == current:
                    queue.append(e.target_id)

    def run(self, inputs: list[IDataset]) -> list[IDataset]:
        outputs = inputs
        for cid in self._order:
            comp = self._nodes[cid].component
            if comp.validate_inputs(outputs):
                outputs = comp.execute(outputs)
        return outputs
```

### 4. Criar e Registrar um Sistema
```python
from pydantic.dataclasses import dataclass as pydantic_dataclass
from aptdata.core import BaseSystem, IFlow
from aptdata.plugins import registry

@pydantic_dataclass
class MySystem(BaseSystem):
    def __post_init__(self) -> None:
        self._flows: list[IFlow] = []

    def register_flow(self, flow: IFlow) -> None:
        self._flows.append(flow)

    def run(self) -> None:
        ds = MemoryDataset(uri="memory://input")
        ds.write([1, 2, 3])
        inputs = [ds]
        for flow in self._flows:
            inputs = flow.run(inputs)

# Registre no Plugin Registry global
registry.register("my_system", MySystem)
```

### 5. Executar via CLI
O `aptdata run` resolve o sistema no **próprio processo**, então o registro
(`registry.register`) precisa estar importável nele — carregue o módulo com
`aptdata plugin load meu_pacote.modulo` (ou use um YAML declarativo com
`aptdata config run`) e execute:

```bash
aptdata run my_system
```

Eventos de ciclo de vida automáticos (`pre_execute`, `on_success`) são emitidos internamente pelo EventBus.

Saída esperada em formato JSON Lines (todo evento carrega `trace_id` — o id
do trace OpenTelemetry quando configurado, `null` caso contrário):
```json
{"event": "pipeline.started", "pipeline": "my_system", "env": "dev", "dry_run": false, "trace_id": null}
{"event": "pipeline.completed", "pipeline": "my_system", "env": "dev", "dry_run": false, "elapsed_seconds": 0.001, "trace_id": null}
```

---

## Opções Úteis da CLI

=== "Execução (Run)"

    | Opção | Default | Descrição |
    |---|---|---|
    | `name` | *(obrigatório)* | Nome do sistema registrado (`registry.register`) |
    | `--env`, `-e` | `dev` | Variável de ambiente alvo da execução |
    | `--dry-run` | `false` | Instancia componentes mas **não** dispara o `run()` |

=== "Monitoramento (TUI)"

    | Opção | Default | Descrição |
    |---|---|---|
    | `--refresh`, `-r` | `1.0` | Intervalo em segundos de auto-atualização do terminal |

---

## Integração MCP com Agentes de IA

O framework inclui um servidor [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) (`aptdata mcp-start`) que permite a agentes de IA (Claude, Copilot, Devin) descobrirem e interagirem com seus pipelines.

Adicione ao `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "aptdata": {
      "command": "aptdata",
      "args": ["mcp-start"]
    }
  }
}
```

Agentes podem consultar metadados com as URIs `schema://datasets/{name}` e chamar tools como `run_flow` sem alucinações de schema.
