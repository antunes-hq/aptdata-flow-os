# Servidor MCP (Integração IA)

O `aptdata` inclui um servidor [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) embutido. Ele transforma agentes de IA (como Claude Desktop, Copilot, Devin) em Engenheiros de Dados autônomos. Em vez de apenas gerar código estático, a IA consegue descobrir conexões, auditar contratos de schema e executar pipelines diretamente contra sua infraestrutura, sem estourar o limite de *tokens* de contexto.

---

## Visão Geral

Baseado no [FastMCP](https://github.com/jlowin/fastmcp), o servidor expõe a infraestrutura do framework através de **Ferramentas (Tools)** (ações que modificam estado ou extraem dados ativamente) e **Recursos (Resources)** (estado de leitura, como esquemas e relatórios).

```mermaid
graph LR
    A["🤖 Agente IA\n(Claude / Copilot)"]
    S["aptdata mcp-start"]
    T["🛠 Tools\nrun_flow(flow_id)\nget_pipeline_lineage(...)"]
    R["📄 Resources\nquality://reports/.../latest\ngovernance://rules"]

    A -- "Protocolo MCP" --> S
    S --> T
    S --> R
```

---

## Iniciando o Servidor

Para habilitar a integração MCP, instale o grupo opcional `ai`:
```bash
pip install "aptdata[ai]"
```

=== "Transporte Stdio (Default)"
    Utilizado pela maioria dos clientes de desktop (Claude Desktop, Cline, Continue.dev). A comunicação ocorre via *standard input/output*.
    ```bash
    aptdata mcp-start
    ```

=== "Transporte SSE"
    Ideal para integrações baseadas na web (HTTP Server-Sent Events). O servidor inicia localmente na porta `8000`.
    ```bash
    aptdata mcp-start --transport sse
    ```

---

## Ferramentas (Tools) Expostas

A IA possui acesso nativo aos seguintes comandos:

| Ferramenta (Tool) | Assinatura | Descrição |
|---|---|---|
| `run_flow` | `(flow_id: str)` | Executa um sistema registrado no *Registry* e retorna o status. |
| `list_registered_systems` | `()` | Lista todos os sistemas orquestráveis disponíveis. |
| `list_available_plugins` | `()` | Lista adaptadores e conectores de infraestrutura instalados. |
| `get_plugin_schema` | `(plugin_name: str)` | Retorna o schema Pydantic exato exigido por um componente. Elimina alucinações da IA na hora de gerar código. |
| `preview_dataset` | `(plugin: str, **reader_config)` | Instancia o reader com a config informada e retorna as primeiras 5 linhas reais para a IA inspecionar os dados. |
| `list_agents` | `()` | Lista os agentes registrados no `agents.yaml` (id, tipo, capabilities, enabled). |
| `dispatch` | `(prompt: str, hint: str \| None)` | Roteia um prompt pelo Router e envia ao agente escolhido. |
| `get_pipeline_lineage` | `(flow_id: str)` | Retorna a árvore de dependência (DAG) e a linhagem de colunas. **Placeholder:** hoje devolve um grafo ilustrativo fixo. |

---

## Recursos (Resources) Expostos

Recursos funcionam como URIs internas para o agente consumir contexto sob demanda.

| Padrão URI | Retorno para a IA |
|---|---|
| `schema://datasets/{name}` | JSON Schema (Tipagem) para o dataset informado. |
| `quality://reports/{workflow}/latest`| Último relatório de qualidade (QualityReport) com contagem de erros e regras falhas. |
| `governance://rules` | Lista de Regras de Negócios registradas no catálogo. |

> **Nota:** os resources de schema/quality/governance (e a tool
> `get_pipeline_lineage`) hoje retornam **payloads mock** que definem o
> contrato (ver `aptdata/mcp/server.py`) — os stores reais ainda não foram
> plugados. Trate os dados como ilustrativos.

---

## Configurando no Claude Desktop

Adicione o servidor `aptdata` ao arquivo de configuração do Claude Desktop:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "aptdata": {
      "command": "aptdata",
      "args": ["mcp-start", "--transport", "stdio"]
    }
  }
}
```

Após reiniciar o aplicativo, o agente será capaz de entender seu banco de dados e rodar seus fluxos de forma autônoma.
