import json
from aptdata.core.system import BaseSystem, IContext
from aptdata.telemetry import TelemetryProvider

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from flows.soccer_flows import (
    BronzeFlow,
    SilverFlow,
    GoldFlow,
)

class SoccerMedallionSystem(BaseSystem):
    name = "soccer_medallion_pipeline"

    def setup(self):
        # Configuração de telemetria e observabilidade nativa do aptdata
        self.telemetry = TelemetryProvider.get_instance()

        # Registro de flows
        self.register_flow(BronzeFlow(flow_id="soccer_bronze_flow"))
        self.register_flow(SilverFlow(flow_id="soccer_silver_flow"))
        self.register_flow(GoldFlow(flow_id="soccer_gold_flow"))

    def on_complete(self, context: IContext):
        # Emissão da linhagem e métricas de execução
        # Here we mock lineage to simulate graph generation as per standard scaffold practice,
        # but in a real system we would retrieve it from `self.get_lineage_graph()`.
        lineage_mock = {
            "nodes": ["bronze", "silver", "gold"],
            "edges": [{"from": "bronze", "to": "silver"}, {"from": "silver", "to": "gold"}]
        }

        context.logger.info("Linhagem exportada", extra={"lineage": lineage_mock})

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)

    system = SoccerMedallionSystem(system_id="medallion_system_01")
    system.run()
