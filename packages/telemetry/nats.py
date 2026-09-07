from typing import Dict, Any, Optional
from opentelemetry import trace, baggage
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.baggage.propagation import W3CBaggagePropagator
from opentelemetry.context import Context


class NATSHeaderGetterSetter:
    """Helper to read/write string headers for NATS message metadata."""

    def get(self, carrier: Dict[str, str], key: str) -> list[str]:
        val = carrier.get(key)
        return [val] if val else []

    def set(self, carrier: Dict[str, str], key: str, value: str) -> None:
        carrier[key] = value

    def keys(self, carrier: Dict[str, str]) -> list[str]:
        return list(carrier.keys())


getter_setter = NATSHeaderGetterSetter()
trace_propagator = TraceContextTextMapPropagator()
baggage_propagator = W3CBaggagePropagator()


def inject_nats_headers(headers: Dict[str, str], correlation_dict: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    """
    Injects active OpenTelemetry trace context and baggage into NATS header dictionary
    prior to publishing an event.
    """
    if headers is None:
        headers = {}

    trace_propagator.inject(headers, setter=getter_setter)

    if correlation_dict:
        ctx = Context()
        for key, val in correlation_dict.items():
            if val is not None:
                ctx = baggage.set_baggage(key, str(val), context=ctx)
        baggage_propagator.inject(headers, context=ctx, setter=getter_setter)

    return headers


def extract_nats_headers(headers: Dict[str, str]) -> Context:
    """
    Extracts OpenTelemetry trace context and baggage from incoming NATS event headers
    to re-establish parent context upon message consumption.
    """
    if not headers:
        return Context()

    ctx = trace_propagator.extract(headers, getter=getter_setter)
    ctx = baggage_propagator.extract(headers, context=ctx, getter=getter_setter)
    return ctx