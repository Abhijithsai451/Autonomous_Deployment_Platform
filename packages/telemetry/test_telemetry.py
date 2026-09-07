from packages.telemetry.provider import init_telemetry

# Initialize Telemetry
telemetry = init_telemetry(service_name="cortexops-agent-runtime", environment="local")

tracer = telemetry.tracer
meter = telemetry.meter

# Emit test span
with tracer.start_as_current_span("test_init_span") as span:
    span.set_attribute("test.status", "ok")
    print("OpenTelemetry SDK successfully initialized and emitted test span.")