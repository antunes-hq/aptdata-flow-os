# aptdata

O **aptdata** é um framework declarativo e extensível para construção de pipelines de dados inteligentes em Python. Ele fornece um sistema de contratos robusto baseado em três abstrações universais — **Component**, **Flow**, e **System** — garantindo que você construa, teste e componha pipelines com total confiança.

---

## Principais Funcionalidades

<div class="grid cards" markdown>

-   :material-file-document-check-outline: **Design Contract-First**

    Interfaces puras em Python (`@dataclass + ABC`) para comportamento explícito.

-   :material-shield-check: **Validação Pydantic**

    Type safety em tempo de execução sem custo adicional.

-   :material-source-branch: **Fluxos Condicionais**

    Estrutura `FlowEdge` com predicados opcionais para ramificações dinâmicas.

-   :material-tag-multiple: **Componentes Direcionados por Metadados**

    A classe `ComponentMeta` carrega o tipo (*kind*), *tags*, chave de roteamento condicional e atributos extras.

-   :material-puzzle: **Registro de Plugins (Registry)**

    Adapters de terceiros registram implementações concretas de `ISystem` pelo nome.

-   :material-console: **CLI Estruturada e JSON Lines**

    Resultados emitidos em JSON Lines (`.model_dump_json()`), ideal para orquestradores.

-   :material-monitor-dashboard: **Dashboard Interativo (TUI)**

    Um dashboard no terminal construído com Textual para monitoramento em tempo real.

</div>

---

## Visão Rápida (Quick Look)

=== "Object-Oriented (Core)"

    ```python
    from pydantic.dataclasses import dataclass as pydantic_dataclass
    from aptdata.core import BaseDataset, IDataset, BaseComponent

    @pydantic_dataclass
    class MemoryDataset(BaseDataset):
        def __post_init__(self): self._data = None
        def read(self): return self._data
        def write(self, data): self._data = data

    @pydantic_dataclass
    class FilterComponent(BaseComponent):
        """Mantém apenas registros onde 'active' é verdadeiro."""

        def validate_inputs(self, inputs: list[IDataset]) -> bool:
            return len(inputs) == 1

        def execute(self, inputs: list[IDataset]) -> list[IDataset]:
            rows = inputs[0].read()
            out = MemoryDataset(uri="memory://filtered")
            out.write([r for r in rows if r.get("active")])
            return [out]
    ```

=== "Declarative (Decorators)"

    ```python
    from aptdata.core.decorators import pandas_component
    import pandas as pd

    @pandas_component("filter_active_users")
    def filter_active_users(df: pd.DataFrame) -> pd.DataFrame:
        """Mantém apenas usuários ativos usando a API simplificada."""
        return df[df['active'] == True]
    ```

---

## Navegação

- 🚀 [Getting Started](getting-started.md) — Instalação e criação do seu primeiro sistema
- 🏛 [Architecture](architecture.md) — Entenda o design `I*` → `Base*`
- ⚙️ [Transform Engines](transform-engines.md) — Wrappers para Pandas & PySpark
- ✅ [Data Quality](quality.md) — Contratos de schema e expectations
- 🏗 [Governance](governance.md) — Linhagem, catálogo e classificação
- 🧩 [Scaffold Templates](scaffold-templates.md) — Bootstrapping rápido de projetos
- 📡 [Telemetry](telemetry.md) — Integração com OpenTelemetry
- 🤖 [MCP Server](mcp.md) — Integração nativa com Agentes de IA
- ⚙️ [Configuration](configuration.md) — Arquivos de configuração YAML
- 📖 [API Reference](api/core.md) — Documentação completa das classes
- 📋 [Changelog](changelog.md) — Histórico de versões
