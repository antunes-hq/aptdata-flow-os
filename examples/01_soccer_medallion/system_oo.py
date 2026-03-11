import os
import sys

from aptdata.core.system import BaseSystem, IContext
from aptdata.telemetry import TelemetryProvider

sys.path.insert(0, os.path.dirname(__file__))

from flows.soccer_flows import (
    BronzeFlow,
    GoldFlow,
    SilverFlow,
)


class SoccerMedallionSystem(BaseSystem):
    name = "soccer_medallion_pipeline"

    def setup(self):
        # Configuração de telemetria e observabilidade nativa do aptdata
        self.telemetry = TelemetryProvider.get_instance()

        # Observabilidade via Event Bus nativo
        def log_event(event):
            print(f"[{event.timestamp.isoformat()}] [{event.event_type}] {event.component_id} -> {event.status}")

        self._context.event_bus.subscribe("on_success", log_event)
        self._context.event_bus.subscribe("on_failure", log_event)

        # Registro de flows
        self.register_flow(BronzeFlow(flow_id="soccer_bronze_flow"))
        self.register_flow(SilverFlow(flow_id="soccer_silver_flow"))
        self.register_flow(GoldFlow(flow_id="soccer_gold_flow"))

    def on_complete(self, context: IContext):
        context.logger.info("Execução do sistema finalizada.")

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)

    system = SoccerMedallionSystem(system_id="medallion_system_01")
    system.run()
