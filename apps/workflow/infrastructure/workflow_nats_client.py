from infrastructure.nats.event_bus import EventBus

workflow_nats_client = EventBus(service="workflow")