import time
from contextlib import contextmanager
from typing import Generator, Optional
from opentelemetry.trace import Span

from packages.telemetry.context.correlation import bind_correlation_context
from packages.telemetry.metrics import metrics_registry
from packages.tracing.spans import start_agent_span
from packages.logging.structured_logs import struc_logger as logger


class AgentObservability:
    @staticmethod
    @contextmanager
    def trace_agent_run(
        agent_id: str,
        agent_type: str,
        tenant_id: Optional[str] = None,
        workflow_instance_id: Optional[str] = None,
        agent_run_id: Optional[str] = None,
    ) -> Generator[Span, None, None]:
        """
        Context manager wrapping an entire agent run:
        Binds context, creates OTel spans, and injects trace keys into structlog.
        """
        with bind_correlation_context(
            tenant_id=tenant_id,
            workflow_instance_id=workflow_instance_id,
            agent_run_id=agent_run_id,
            agent_id=agent_id,
        ):
            with start_agent_span(
                name=f"agent.run.{agent_type}",
                attributes={
                    "agent.id": agent_id,
                    "agent.type": agent_type,
                    "workflow.instance_id": workflow_instance_id,
                },
            ) as span:
                yield span

    @staticmethod
    def record_metrics(
        agent_type: str,
        status: str,
        duration: float,
        provider: str = "openai",
        model: str = "gpt-4o",
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ) -> None:
        """
        Records execution counters, duration histograms, and token usage
        using low-cardinality label rules.
        """
        # Record agent execution run
        metrics_registry.record_agent_run(
            agent_type=agent_type,
            status=status,
            duration=duration,
        )

        # Record LLM token metrics if LLM was called
        total_tokens = prompt_tokens + completion_tokens
        if total_tokens > 0:
            metrics_registry.record_llm_call(
                provider=provider,
                model=model,
                status=status,
                duration=duration,
                tokens=total_tokens,
            )