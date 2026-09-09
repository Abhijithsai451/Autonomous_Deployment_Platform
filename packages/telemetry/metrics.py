from typing import Dict, Any, Optional
from opentelemetry import metrics

class MetricsRegistry:
    """
    Central registry for CortexOps platform metrics.
    Enforces low-cardinality dimension rules (Prometheus safety).
    """

    def __init__(self, meter_name: str = "cortexops-metrics"):
        self.meter = metrics.get_meter(meter_name)
        self._init_agent_metrics()
        self._init_llm_metrics()
        self._init_tool_metrics()
        self._init_nats_metrics()

    def _init_agent_metrics(self) -> None:
        self.agent_runs_total = self.meter.create_counter(
            name="agent_runs_total",
            description="Total number of agent runs executed",
            unit="1",
        )
        self.agent_runs_failed_total = self.meter.create_counter(
            name="agent_runs_failed_total",
            description="Total number of failed agent runs",
            unit="1",
        )
        self.agent_execution_duration = self.meter.create_histogram(
            name="agent_execution_duration_seconds",
            description="Agent execution latency in seconds",
            unit="s",
        )

    def _init_llm_metrics(self) -> None:
        self.llm_requests_total = self.meter.create_counter(
            name="llm_requests_total",
            description="Total LLM requests issued",
            unit="1",
        )
        self.llm_tokens_total = self.meter.create_counter(
            name="llm_tokens_total",
            description="Total LLM tokens consumed",
            unit="1",
        )
        self.llm_request_duration = self.meter.create_histogram(
            name="llm_request_duration_seconds",
            description="LLM request latency in seconds",
            unit="s",
        )

    def _init_tool_metrics(self) -> None:
        self.tool_calls_total = self.meter.create_counter(
            name="tool_calls_total",
            description="Total tool executions",
            unit="1",
        )
        self.tool_execution_duration = self.meter.create_histogram(
            name="tool_execution_duration_seconds",
            description="Tool execution duration in seconds",
            unit="s",
        )

    def _init_nats_metrics(self) -> None:
        self.events_consumed_total = self.meter.create_counter(
            name="events_consumed_total",
            description="Total NATS events consumed",
            unit="1",
        )
        self.event_processing_duration = self.meter.create_histogram(
            name="event_processing_duration_seconds",
            description="Event processing duration in seconds",
            unit="s",
        )

    def record_agent_run(self, agent_type: str, status: str, duration: float) -> None:

        attributes = {"agent_type": agent_type, "status": status}
        self.agent_runs_total.add(1, attributes)
        if status == "failure":
            self.agent_runs_failed_total.add(1, {"agent_type": agent_type})
        self.agent_execution_duration.record(duration, attributes)

    def record_llm_call(self, provider: str, model: str, status: str, duration: float, tokens: int) -> None:

        attributes = {"provider": provider, "model": model, "status": status}
        self.llm_requests_total.add(1, attributes)
        self.llm_tokens_total.add(tokens, {"provider": provider, "model": model})
        self.llm_request_duration.record(duration, attributes)


# Global Metrics Instance
metrics_registry = MetricsRegistry()