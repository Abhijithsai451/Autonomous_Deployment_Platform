from packages.telemetry.provider import init_telemetry
from packages.telemetry.nats import inject_nats_headers, extract_nats_headers
from packages.tracing.spans import start_agent_span
from opentelemetry import trace

init_telemetry("cortexops-agent-runtime", "local")

nats_headers = {}

# Simulate Publisher: Inject active trace parent into headers
with start_agent_span("nats.publish", attributes={"nats.subject": "agent.workflow.start"}) as pub_span:
    pub_trace_id = format(pub_span.get_span_context().trace_id, "032x")
    inject_nats_headers(nats_headers, correlation_dict={"agent_run_id": "run-999"})

print("Injected NATS Headers:", nats_headers)

# Simulate Consumer: Extract trace parent from headers
extracted_ctx = extract_nats_headers(nats_headers)

tracer = trace.get_tracer("cortexops-agent-runtime")
with tracer.start_as_current_span("nats.consume", context=extracted_ctx) as sub_span:
    sub_trace_id = format(sub_span.get_span_context().trace_id, "032x")

    # Trace IDs must match across publisher and consumer boundaries
    assert pub_trace_id == sub_trace_id, "Trace ID mismatch across NATS boundary!"
    print("NATS trace propagation verified successfully. Matching Trace ID:", sub_trace_id)