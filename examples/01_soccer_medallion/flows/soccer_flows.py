from components.soccer_components import (
    AggregateTeamStatsComponent,
    CleanMatchDataComponent,
    IngestMatchDataComponent,
)
from domain.models import GoldTeamStatsModel, SilverMatchModel

from aptdata.core.system import BaseFlow


class BronzeFlow(BaseFlow):
    def build(self):
        # I/O boundary
        self.add_component(IngestMatchDataComponent)


class SilverFlow(BaseFlow):
    def build(self):
        # Component with contract
        self.add_component(CleanMatchDataComponent, output_contract=SilverMatchModel)


class GoldFlow(BaseFlow):
    def build(self):
        # Aggregation component with contract
        self.add_component(
            AggregateTeamStatsComponent, output_contract=GoldTeamStatsModel
        )
