from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Tracer
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

def init_tracer(service_name: str, otlp_endpoint: str= "http://localhost:4317")-> Tracer:
    """Initializes global OpenTelemetry tracing for a given microservice."""
    provider = TracerProvider()
    # In production, OTLPSpanExporter points to your Jaeger/OpenTelemetry collector
    processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint))
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    return trace.get_tracer(service_name)

def inject_trace_context()-> dict:
    """Extracts the current trace context and converts it to the dictionary headers"""
    headers = {}
    TraceContextTextMapPropagator().inject(headers)
    return headers

