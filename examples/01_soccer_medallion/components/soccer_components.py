import os
from aptdata.core.system import BaseComponent, IContext
from aptdata.core.dataset import IDataset
from aptdata.plugins.dataset import InMemoryDataset
from aptdata.plugins.transform.pandas import PandasTransformComponent


class IngestMatchDataComponent(BaseComponent):
    """Bronze component: Reads mock CSV and pushes to memory without strict validation."""

    def validate_inputs(self, inputs: list[IDataset]) -> bool:
        return True

    def execute(self, inputs: list[IDataset]) -> list[IDataset]:
        import pandas as pd

        filepath = os.path.join(
            os.path.dirname(__file__), "..", "data", "raw", "matches_mock.csv"
        )
        # Note: I/O is contained entirely here on the edge (Ingestion)
        df = pd.read_csv(filepath)

        out_ds = InMemoryDataset(uri="memory://bronze_matches")
        out_ds.write(df.to_dict(orient="records"))
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
        return df_cleaned[['match_id', 'home_team', 'away_team', 'home_goals', 'away_goals', 'date']]


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
