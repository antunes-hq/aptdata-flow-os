from pathlib import Path
from typing import TYPE_CHECKING

from aptdata.core.dataset import IDataset
from aptdata.core.system import BaseComponent, IContext
from aptdata.plugins.local_fs import CSVReader
from aptdata.plugins.transform.pandas import PandasTransformComponent

if TYPE_CHECKING:
    import pandas as pd

# Caminho para os dados raw mockados. Em um ambiente real
# isso viria de configuração ou Secret
MOCK_DATA_PATH = Path(__file__).parent.parent / "data" / "raw" / "matches_mock.csv"


class IngestMatchDataComponent(BaseComponent):
    """Bronze component: Reads mock CSV and pushes to memory.
    No strict validation."""

    def validate_inputs(self, inputs: list[IDataset]) -> bool:
        return True

    def execute(self, inputs: list[IDataset]) -> list[IDataset]:
        # Utiliza o leitor nativo do framework (CSVReader)
        # zero I/O de pandas aqui. O CSVReader já gera o Dataset InMemory.
        reader = CSVReader(str(MOCK_DATA_PATH))
        out_ds = reader.read()
        return [out_ds]

class CleanMatchDataComponent(PandasTransformComponent):
    """Silver component: Cleans and standardises types.
    Expects data to comply with SilverMatchModel on output via BaseFlow contract."""

    def transform(self, df: "pd.DataFrame", context: IContext) -> "pd.DataFrame":
        context.logger.info("Iniciando limpeza da camada Silver")

        # Pure pandas logic: drop duplicates, nulls on crucial fields, fillna etc.
        df_cleaned = df.dropna(subset=['match_id']).copy()
        df_cleaned['home_goals'] = df_cleaned['home_goals'].fillna(0).astype(int)
        df_cleaned['away_goals'] = df_cleaned['away_goals'].fillna(0).astype(int)

        # Ensure only the fields required by the contract are passed,
        # plus maybe 'date'.
        columns = [
            'match_id', 'home_team', 'away_team', 'home_goals', 'away_goals', 'date'
        ]
        return df_cleaned[columns]


class AggregateTeamStatsComponent(PandasTransformComponent):
    """Gold component: Aggregates total goals by team."""

    def transform(self, df: "pd.DataFrame", context: IContext) -> "pd.DataFrame":
        import pandas as pd
        context.logger.info("Iniciando agregação da camada Gold")

        home_stats = df.groupby('home_team').agg(
            total_goals_scored=('home_goals', 'sum'),
            matches_played=('match_id', 'count')
        ).reset_index().rename(columns={'home_team': 'team'})

        away_stats = df.groupby('away_team').agg(
            total_goals_scored=('away_goals', 'sum'),
            matches_played=('match_id', 'count')
        ).reset_index().rename(columns={'away_team': 'team'})

        combined = pd.concat([home_stats, away_stats], ignore_index=True)
        gold_stats = combined.groupby('team').sum().reset_index()
        return gold_stats
