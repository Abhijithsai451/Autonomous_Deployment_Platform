import contextvars
from typing import Optional

_correlation_id_var = contextvars.ContextVar[Optional[str]]("correlation_id", default=None)
_causation_id_var = contextvars.ContextVar[Optional[str]]("causation_id", default=None)
_tenant_id_var = contextvars.ContextVar[Optional[str]]("tenant_id", default=None)
class RequestContext:
    @staticmethod
    def set(
            correlation_id: Optional[str] = None,
            causation_id: Optional[str] = None,
            tenant_id: Optional[str] = None,
    ) -> None:
        if correlation_id:
            _correlation_id_var.set(correlation_id)
        if causation_id:
            _causation_id_var.set(causation_id)
        if tenant_id:
            _tenant_id_var.set(tenant_id)

    @staticmethod
    def get_correlation_id() -> Optional[str]:
        return _correlation_id_var.get()

    @staticmethod
    def get_causation_id() -> Optional[str]:
        return _causation_id_var.get()

    @staticmethod
    def get_tenant_id() -> Optional[str]:
        return _tenant_id_var.get()

    @staticmethod
    def clear() -> None:
        _correlation_id_var.set(None)
        _causation_id_var.set(None)
        _tenant_id_var.set(None)
