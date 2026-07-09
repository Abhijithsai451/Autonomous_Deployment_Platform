from typing import Any, Optional, Dict


class CortexOpsError(Exception):
    def __init__(self,
                 message: str,
                 error_code: str,
                 status_code: int = 500,
                 details: Optional[Dict[str, Any]] = None,
                 ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}

    def to_dict(self)-> Dict[str,Any]:
        return {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "details": self.details
            }
        }


class NotFoundError(CortexOpsError):
    def __init__(self, message: str = "Resource not found", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=404, error_code="NOT_FOUND", details=details)

class ForbiddenError(CortexOpsError):
    def __init__(self, message: str = "Access denied", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=403, error_code="FORBIDDEN", details=details)

class ConflictError(CortexOpsError):
    def __init__(self, message: str = "Resource conflict", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=409, error_code="RESOURCE_CONFLICT", details=details)