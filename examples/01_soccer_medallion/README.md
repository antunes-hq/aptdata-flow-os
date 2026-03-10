# Soccer Medallion Scaffold

Um projeto de scaffold demonstrando o poder de separação de responsabilidades (IoC), Pydantic Fail-Fast Data Contracts e injeção de dependência na engine do *aptdata*.

## Princípios
- **Bronze (Ingestion)**: Onde ocorre o I/O. Não há validação rígida de schema.
- **Silver (Clean & Standardise)**: Componentes Pandas recebem DataFrames e devolvem DataFrames. O wrapper de injeção de dependência nativo do *aptdata* garante validação em tempo de execução via `PydanticDataset` no *output_contract*.
- **Gold (Aggregated)**: Outra camada estrita baseada em contratos para modelos de apresentação e Analytics.

## Execução

O framework já resolve as dependências e o *build* declarativo dos *Flows*. Execute o sistema com:

```bash
python examples/01_soccer_medallion/system.py
```
