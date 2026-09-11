from packages.messaging.nats.event_bus import EventBus

agent_nats_client = EventBus(service = "agent_runtime")