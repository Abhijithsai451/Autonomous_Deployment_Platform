from datetime import datetime, timezone
from typing import Any, Dict
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class BaseEvent(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1

    @property
    def event_name(self) -> str:
        return self.__class__.__name__

    @property
    def subject(self) -> str:
        raise NotImplementedError("Subclasses must define a target subject.")

    def to_payload(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")
