# ADR 001: Revisão Arquitetural do Core e Simplificação de Fluxos (DX)

**Status:** Proposed
**Data:** 2024-05-20 (Atual)
**Contexto:** Spike Técnico - Developer Experience (DX) & Automação de Core

## 1. Contexto e Problema

O `aptdata` foi desenhado com base em três abstrações universais (`ISystem`, `IFlow`, `IComponent`) guiadas pelo princípio de design Contract-First via Pydantic (`IDataset`). Contudo, ao analisar os fluxos implementados na pasta `examples/` (especificamente `01_soccer_medallion`), notou-se que a Developer Experience (DX) está prejudicada por excesso de boilerplate e vazamento de responsabilidades transversais para o código do usuário.

Os principais gargalos mapeados são:

* **Boilerplate de Dataset:** Componentes (`BaseComponent`) precisam instanciar manualmente objetos `InMemoryDataset`, manipular listas de entrada de forma verbosa (e.g. `for ds in inputs: data = ds.read()`) e repacotar os resultados (e.g. `out_ds.write(cleaned_records)`).
* **Governança Manual (Lineage & Quality):** O rastreamento de linhagem e a emissão de métricas (`LineageGraph`, `QualityValidator`) estão sendo invocados de forma manual e mockada nos métodos `on_complete` do `BaseSystem` ou espalhados dentro do `execute` dos componentes.
* **Vazamento de Engine (Acoplamento):** Apesar de existir o `PandasTransformComponent`, a fronteira entre processamento nativo (Pandas/Spark) e a orquestração core do framework apresenta atrito, forçando o usuário a se preocupar com I/O de infraestrutura ao invés de focar na lógica de transformação de dados.
* **Inicialização Verbosa:** A instanciação de `BaseSystem` e `BaseFlow` exige muita configuração imperativa explícita, quando poderia ser inferida de metadados ou abstraída em *factories*.

O objetivo desta revisão é garantir que o framework permaneça agnóstico a engines, mantendo contratos estritos com Pydantic, porém simplificando radicalmente o uso diário através da inversão de controle para requisitos transversais.

## 2. Decisões Arquiteturais Propostas

Para mitigar a dívida técnica de DX sem quebrar a filosofia SOLID, propomos as seguintes mudanças arquiteturais:

### 2.1. Refatoração das Abstrações Base (Factories e Decorators)

* **Decorators Inteligentes (`@component` / `@pandas_component`):** Expandir a funcionalidade dos decorators funcionais atuais para encapsular totalmente a lógica de `InMemoryDataset`. O decorator deve realizar o `.read()` nas entradas e o `.write()` nas saídas, entregando e recebendo tipos primitivos (listas de dicts, dataframes) do usuário.
* **Injeção de Dependência Automática:** O `IContext` deve ser injetado de forma opcional por introspecção de assinatura, evitando que o usuário precise declará-lo se não for utilizá-lo (ex: logging).

```python
# Como deve ser (Declarativo e Limpo)
@pandas_component("aggregate_player_stats")
def aggregate_player_stats(df: pd.DataFrame) -> pd.DataFrame:
    # Foco 100% no negócio
    return aggregate_player_stats_logic(df)
```

### 2.2. Automação de Transação de Dados (Contract-First nativo)

* **Validação Transparente via Pydantic:** Se um componente ou fluxo definir um `output_contract` (modelo Pydantic), a camada base (`BaseComponent` ou o decorator) deve interceptar o output bruto (lista de dicionários) e rodar o `Model.model_validate()` automaticamente.
* Isso garante que a validação de esquema não suje o método `execute()` do componente. Se os dados não respeitarem o contrato, o framework lança a exceção antes mesmo de criar o `IDataset` de saída.

### 2.3. Governança Invisível via Event Bus (Hooks / Callbacks)

* **Hooks de Ciclo de Vida:** Introduzir hooks padrão (e.g., `pre_execute`, `post_execute`, `on_success`, `on_failure`) na classe `BaseComponent` e gerenciados por um Event Bus no `BaseSystem`.
* **Lineage Automático:** Ao invés do usuário preencher a linhagem no `on_complete` do sistema, o framework capturará as arestas do fluxo durante a compilação do `IFlow` e registrará os nós `LineageNode` via `post_execute` interceptando a URI dos `IDataset` gerados.
* **Captura de Qualidade:** Qualquer `QualityValidator` atrelado a um componente deve rodar em um hook de validação pré/pós-execução, isolando a regra de negócio da verificação de integridade da infraestrutura.

### 2.4. Avaliação Core vs. Plugins (Isolamento de Engine)

* O **Core** (`aptdata.core`) passará a ser estritamente focado em orquestração, I/O abstrato (`IDataset`), contratos Pydantic e Injeção de Dependências.
* Qualquer dependência de Pandas, PySpark ou banco de dados relacional deve residir exclusivamente nos pacotes `aptdata.plugins.*`.
* Em ambientes onde a engine não está instalada, as classes de plugin correspondentes devem levantar `ImportError` de forma amigável no momento da instanciação, e nunca quebrar a importação global do core.

## 3. Trade-offs e Consequências

* **Positivo:** Redução massiva de código boilerplate nos projetos dos usuários (examples provam a economia de dezenas de linhas de I/O em troca de decorators puros).
* **Positivo:** Governança (Lineage, Data Quality) será padronizada, consistente e independente de esquecimentos do engenheiro de dados, pois ocorrerá "por debaixo dos panos".
* **Negativo/Atenção:** A mágica gerada por decorators e hooks pode dificultar o debugging caso ocorram erros de *type hinting* ou contratos divergentes. Será necessário um tratamento de exceções robusto e detalhado, reportando exatamente onde a validação Pydantic ou introspecção falhou.
* **Atenção (Performance):** A automação de `InMemoryDataset` e validação Pydantic em *loops tight* pode adicionar pequeno overhead. Como mitigação, utilizaremos operações otimizadas (ex: desempacotamento de dicionários e validação em batch do Pydantic) ao invés de instanciar objetos individuais para cada linha quando tratamos `DataFrames` ou coleções massivas.

## 4. Próximos Passos

1. Atualizar as classes de suporte (`aptdata.core.decorators`) para implementar a injeção oculta de `IDataset`.
2. Incluir lógica de Event Bus no `BaseFlow` para emissão automática de linhagem.
3. Refatorar os examples (`01_soccer_medallion`) para utilizar a nova API reduzida e atestar a melhoria em DX.
