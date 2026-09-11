import logging
import os
import atexit
from typing import Optional
from opentelemetry import trace, metrics, _logs
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter

class TelemetryProvider:
    """
    Central telemetry provider configuring OpenTelemetry SDK tracing and Metrics exporters pointing
    toward the central OpenTelemetry Collector.
    """
    def __init__(self,
                 service_name: str,
                 service_version: str = "1.0.0",
                 otlp_endpoint: Optional[str]=None,
                 environment: str = "production"
                 ):
        self.service_name = service_name
        self.service_version = service_version
        self.otlp_endpoint = otlp_endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT","http://localhost:4317")
        self.environment = environment
        self._resource = Resource.create(
            {
            SERVICE_NAME: self.service_name,
            SERVICE_VERSION: self.service_version,
            "deployment-environment": self.environment,
            }
        )
        self._setup_tracing()
        self._setup_metrics()
        self._setup_logging()

    def _setup_tracing(self):
        tracer_provider = TracerProvider(resource= self._resource)
        exporter = OTLPSpanExporter(endpoint = self.otlp_endpoint, insecure = True)

        span_processor = BatchSpanProcessor(exporter)
        tracer_provider.add_span_processor(span_processor)

        trace.set_tracer_provider(tracer_provider)
        self.tracer = trace.get_tracer(self.service_name, self.service_version)

        atexit.register(tracer_provider.shutdown)

    def _setup_metrics(self):
        metric_exporter = OTLPMetricExporter(endpoint = self.otlp_endpoint, insecure = True)
        reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=15000)

        meter_provider = MeterProvider(resource=self._resource, metric_readers = [reader])
        metrics.set_meter_provider(meter_provider)
        self.meter = metrics.get_meter(self.service_name, self.service_version)

        atexit.register(meter_provider.shutdown)

    def _setup_logging(self):
        log_exporter = OTLPLogExporter(endpoint=self.otlp_endpoint, insecure=True)

        logger_provider = LoggerProvider(resource=self._resource)
        logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
        _logs.set_logger_provider(logger_provider)

        handler = LoggingHandler(logger_provider=logger_provider)
        logging.getLogger().addHandler(handler)

        atexit.register(logger_provider.shutdown)

def init_telemetry(service_name: str, environment: str = "production")-> TelemetryProvider:
    """Helper Function to initialize OpenTelemetry SDk across services_events"""
    return TelemetryProvider(service_name, environment=environment)



