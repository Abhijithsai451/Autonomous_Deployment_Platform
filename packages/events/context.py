import contextvars
from typing import Optional
from uuid import uuid4

_correlation_id_var: contextvars.ContextVar[Optional[str]]=contextvars.ContextVar("correlation_id", default=None)
_causation_id_var:  contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("causation_id", default = None)
_tenant_id_var : contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("tenant_id", default = None)

class RequestContext:
    @staticmethod
    def set(
            correlation_id: Optional[str] = None,
            causation_id: Optional[str] = None,
            tenant_id: Optional[str] = None,
    ) -> None:
        _correlation_id_var.set(correlation_id or str(uuid4))
        _causation_id_var.set(causation_id)
        _tenant_id_var.set(tenant_id)

    @staticmethod
    def get_correlation_id() -> str:
        cid = _correlation_id_var.get()
        if not cid:
            cid = str(uuid4())
            _correlation_id_var.set(cid)
        return cid

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
