import pandas as pd
from pathlib import Path

from aptdata.core.decorators import component, pandas_component
from aptdata.core.context import IContext
from aptdata.core.dataset import IDataset
from aptdata.plugins.local_fs import CSVReader

MOCK_DATA_PATH = Path(__file__).parent / "data" / "raw" / "matches_mock.csv"

@component("ingest_match_data")
def ingest_match_data(inputs: list[IDataset], context: IContext) -> list[IDataset]:
    """Bronze Layer: Ingest raw data."""
    context.logger.info("Ingesting raw data from CSV (Bronze)")
    reader = CSVReader(str(MOCK_DATA_PATH))
    out_ds = reader.read()
    return [out_ds]


@pandas_component("clean_match_data")
def clean_match_data(df: pd.DataFrame, context: IContext) -> pd.DataFrame:
    """Silver Layer: Clean and validate data."""
    context.logger.info("Starting cleaning in Silver layer")

    # Pure pandas logic: drop duplicates, nulls on crucial fields, fillna etc.
    df_cleaned = df.dropna(subset=['match_id']).copy()

    if 'home_goals' in df_cleaned.columns:
        df_cleaned['home_goals'] = df_cleaned['home_goals'].fillna(0).astype(int)
    if 'away_goals' in df_cleaned.columns:
        df_cleaned['away_goals'] = df_cleaned['away_goals'].fillna(0).astype(int)

    columns = [col for col in ['match_id', 'home_team', 'away_team', 'home_goals', 'away_goals', 'date'] if col in df_cleaned.columns]
    return df_cleaned[columns]


@pandas_component("aggregate_player_stats")
def aggregate_player_stats(df: pd.DataFrame, context: IContext) -> pd.DataFrame:
    """Gold Layer: Aggregates total goals by team."""
    context.logger.info("Starting aggregation in Gold layer")

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
