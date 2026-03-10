import pytest
import pandas as pd
from aptdata.core.dataset import DataContractError
from aptdata.plugins.dataset import InMemoryDataset
from aptdata.core.context import ExecutionContext

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from domain.models import SilverMatchModel
from components.soccer_components import CleanMatchDataComponent
from flows.soccer_flows import SilverFlow
from system import SoccerMedallionSystem

def test_system_dependency_injection():
    """Testa se o sistema sobe corretamente com as dependencias e os fluxos"""
    system = SoccerMedallionSystem(system_id="test_system")
    system.setup()

    assert len(system._flows) == 3
    assert system._flows[0].flow_id == "soccer_bronze_flow"
    assert system._flows[1].flow_id == "soccer_silver_flow"
    assert system._flows[2].flow_id == "soccer_gold_flow"

def test_pydantic_validation_fail_fast(monkeypatch):
    """Força um schema errado na camada Silver (output_contract) para testar a validação."""
    flow = SilverFlow(flow_id="test_silver")
    flow.compile() # Instancia o componente

    # Cria um payload "sujo" e "incorreto", que simula uma saida de um componente
    # ou um dataframe que não segue o contrato
    invalid_data = pd.DataFrame([
        # Missing home_goals and away_goals which are required ints in SilverMatchModel
        {"match_id": "123", "home_team": "Team A", "away_team": "Team B", "date": "2023-10-01"}
    ])
    ds = InMemoryDataset(uri="memory://test")
    ds.write(invalid_data.to_dict(orient="records"))

    # O component de limpeza passaria batido nisso (ja q fillna faria zero), mas para forçar erro de contrato,
    # vamos injetar um erro manipulando o dataframe que o Clean component recebe e forçando ele
    # a devolver algo faltante

    # PydanticDataset is wrapped around the execution.
    # CleanMatchDataComponent cleans and adds missing goals.
    # Let's mock `transform` to return an invalid dataframe intentionally
    component = flow._nodes["CleanMatchDataComponent"].component

    def bad_transform(self_obj, df, context):
        return pd.DataFrame([{"match_id": "123", "home_team": "Team A"}]) # Missing away_team, goals, date

    # Monkeypatch the specific class's transform method
    monkeypatch.setattr(CleanMatchDataComponent, "transform", bad_transform)

    with pytest.raises(DataContractError):
        flow.run([ds])

def test_full_pipeline_with_mocked_io(monkeypatch):
    """Mock the ingest component to test the full pipeline in milliseconds."""

    from components.soccer_components import IngestMatchDataComponent

    def mocked_execute(self, inputs):
        df = pd.DataFrame([
            {"match_id": "1", "home_team": "A", "away_team": "B", "home_goals": 2, "away_goals": 1, "date": "2023-01-01"},
            {"match_id": "2", "home_team": "C", "away_team": "A", "home_goals": 0, "away_goals": 3, "date": "2023-01-02"},
        ])
        ds = InMemoryDataset(uri="memory://test")
        ds.write(df.to_dict(orient="records"))
        return [ds]

    monkeypatch.setattr(IngestMatchDataComponent, "execute", mocked_execute)

    system = SoccerMedallionSystem(system_id="mocked_pipeline")
    system.run() # Should succeed without errors and very fast
