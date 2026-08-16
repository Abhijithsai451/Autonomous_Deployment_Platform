from uuid import UUID

from packages.events.base import BaseEvent


class ServiceAccountLifecycleEvent(BaseEvent):
    id : UUID
    client_id : str

class ServiceAccountCreatedEvent(ServiceAccountLifecycleEvent):
    @property
    def subject(self)-> str:
        return "identity.events.serviceAccount.created"

class ServiceAccountUpdatedEvent(ServiceAccountLifecycleEvent):
    @property
    def subject(self)-> str:
        return "identity.events.serviceAccount.updated"

class ServiceAccountDeletedEvent(ServiceAccountLifecycleEvent):
    @property
    def subject(self)-> str:
        return "identity.events.serviceAccount.deleted"