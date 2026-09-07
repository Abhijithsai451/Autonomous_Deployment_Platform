from contextlib import contextmanager
from typing import Any, Dict, Generator, Optional
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode, Span
import structlog


def get_current_tracer(name: str = "cortexops-tracing") -> trace.Tracer:
    return trace.get_tracer(name)


@contextmanager
def start_agent_span(
    name: str,
    attributes: Optional[Dict[str, Any]] = None,
    tracer_name: str = "cortexops-agent-runtime",
) -> Generator[Span, None, None]:
    """
    Context manager to start an OpenTelemetry span, record exceptions gracefully,
    and automatically attach trace context to log statements.
    """
    tracer = get_current_tracer(tracer_name)
    attrs = attributes or {}

    with tracer.start_as_current_span(name) as span:
        for key, val in attrs.items():
            if val is not None:
                span.set_attribute(key, str(val) if isinstance(val, (dict, list)) else val)

        span_context = span.get_span_context()
        if span_context.is_valid:
            trace_id = format(span_context.trace_id, "032x")
            span_id = format(span_context.span_id, "016x")
            structlog.contextvars.bind_contextvars(trace_id=trace_id, span_id=span_id)

        try:
            yield span
            span.set_status(Status(StatusCode.OK))
        except Exception as exc:
            # Record exception telemetry on span
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, description=str(exc)))
            raise