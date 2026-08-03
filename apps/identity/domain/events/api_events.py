from uuid import UUID

from packages.events.base import BaseEvent


class APIKeyLifecycleEvent(BaseEvent):
    id : UUID

class APIKeyCreatedEvent(APIKeyLifecycleEvent):
    @property
    def subject(self) -> str:
        return "identity.events.apiKey.created"

class APIKeyRevokedEvent(APIKeyLifecycleEvent):
    @property
    def subject(self) -> str:
        return "identity.events.apiKey.Revoked"