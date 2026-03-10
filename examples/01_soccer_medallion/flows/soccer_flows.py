from aptdata.core.system import BaseFlow

from components.soccer_components import (
    IngestMatchDataComponent,
    CleanMatchDataComponent,
    AggregateTeamStatsComponent,
)
from domain.models import SilverMatchModel, GoldTeamStatsModel

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
        self.add_component(AggregateTeamStatsComponent, output_contract=GoldTeamStatsModel)
