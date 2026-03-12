---
hide:
  - navigation
  - toc
---

<div class="tx-hero" style="text-align: center; margin-top: 3rem; margin-bottom: 3rem;">
  <h1 class="text-gradient" style="font-size: 2.5rem; font-weight: bold; margin-bottom: 1rem;">aptdata</h1>
  <p style="font-size: 1.25rem; color: var(--md-default-fg-color--light); max-width: 700px; margin: 0 auto;">
    O framework declarativo e extensível para construção de pipelines de dados inteligentes. Validação estrita, roteamento dinâmico e integração nativa com IA.
  </p>
  <div style="margin-top: 2rem;">
    <a href="getting-started/" class="md-button md-button--primary">🚀 Comece Agora</a>
    <a href="https://github.com/strondata/smart-data" class="md-button">🐙 GitHub</a>
  </div>
</div>

---

## Por que escolher o aptdata?

<div class="grid cards" markdown>

-   :material-shield-check: **Type Safety & Contratos**

    Interfaces (`IDataset`, `IComponent`) combinadas com a validação em tempo de execução do **Pydantic**. Saiba exatamente o que entra e sai do seu pipeline antes de ir para produção.

-   :material-puzzle: **Agnóstico a Engines**

    Construa fluxos desacoplados da ferramenta de processamento. Use wrappers para Pandas ou escale nativamente para clusters PySpark sem alterar a arquitetura do fluxo.

-   :material-robot-outline: **Pronto para Agentes (AI Ready)**

    Integração nativa com MCP Server e emissão de telemetria em JSON Lines. Perfeito para ser orquestrado por frameworks como LangChain e agentes autônomos.

-   :material-source-branch: **Roteamento Dinâmico**

    Crie `FlowEdges` condicionais que ramificam a execução baseada em predicados de metadados das saídas anteriores.

</div>

---

## Instalação Rápida

```bash
pip install aptdata
```

### Flexibilidade: Escolha seu Paradigma

Desenvolva da forma que melhor se adapta ao seu time: usando Orientação a Objetos para sistemas complexos ou Decorators para agilidade.

=== "Declarativo (Decorators)"

    ```python
    from aptdata.core.decorators import pandas_component
    import pandas as pd

    @pandas_component("filter_active_users")
    def filter_active_users(df: pd.DataFrame) -> pd.DataFrame:
        """Filtra usuários ativos com sintaxe limpa e direta."""
        return df[df['active'] == True]
    ```

=== "Orientado a Objetos (Core)"

    ```python
    from pydantic.dataclasses import dataclass as pydantic_dataclass
    from aptdata.core import BaseDataset, IDataset, BaseComponent

    @pydantic_dataclass
    class FilterComponent(BaseComponent):
        def validate_inputs(self, inputs: list[IDataset]) -> bool:
            return len(inputs) == 1

        def execute(self, inputs: list[IDataset]) -> list[IDataset]:
            rows = inputs[0].read()
            out = MemoryDataset(uri="memory://filtered")
            out.write([r for r in rows if r.get("active")])
            return [out]
    ```
