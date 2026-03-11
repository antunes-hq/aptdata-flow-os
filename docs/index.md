# aptdata

O **aptdata** é um framework declarativo e extensível para construção de pipelines de dados inteligentes em Python. Ele fornece um sistema de contratos robusto baseado em três abstrações universais — **Component**, **Flow**, e **System** — garantindo que você construa, teste e componha pipelines com total confiança.

---

## Principais Funcionalidades

<div class="grid cards" markdown>

-   :material-file-document-check-outline: __Design Contract-First__

    Interfaces puras em Python (`@dataclass + ABC`) como `IDataset`, `IComponent`, `IFlow` e `ISystem` tornam o comportamento esperado explícito antes de qualquer código concreto ser escrito.

-   :material-shield-check: __Base Classes Validadas por Pydantic__

    `BaseDataset`, `BaseComponent`, `BaseFlow` e `BaseSystem` estendem as interfaces adicionando campos validados pelo Pydantic, oferecendo type safety em tempo de execução sem custo adicional.

-   :material-tag-multiple: __Componentes Direcionados por Metadados__

    A classe `ComponentMeta` carrega o tipo (*kind*), *tags*, chave de roteamento condicional e atributos extras — eliminando a necessidade de inspecionar os componentes internamente.

-   :material-source-branch: __Fluxos Condicionais__

    A estrutura `FlowEdge` suporta predicados opcionais, permitindo que os fluxos ramifiquem dinamicamente com base nas saídas em tempo de execução.

-   :material-puzzle: __Registro de Plugins (Registry)__

    Adapters de terceiros registram implementações concretas de `ISystem` pelo nome. Assim, a CLI consegue descobrir e executá-las sem alterar o código principal.

-   :material-console: __CLI Estruturada e JSON Lines__

    Cada resultado e evento de ciclo de vida é emitido em formato JSON Lines (`.model_dump_json()`), ideal para orquestradores, integração com IA e pipelines de CI/CD.

-   :material-monitor-dashboard: __Dashboard Interativo (TUI)__

    Um dashboard no terminal construído com Textual que permite monitorar o progresso dos fluxos e o consumo de memória em tempo real.

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
