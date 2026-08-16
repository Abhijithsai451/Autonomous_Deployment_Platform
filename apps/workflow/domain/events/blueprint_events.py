from uuid import UUID

from packages.events.base import BaseEvent


class BlueprintLifeCycleEvent(BaseEvent):
    pass


class BlueprintCreatedEvent(BlueprintLifeCycleEvent):
    id: UUID
    @property
    def subject(self)->str:
        return "workflow.events.blueprint.created"

class BlueprintAlreadyExists(BlueprintLifeCycleEvent):
    name : str
    @property
    def subject(self)-> str:
        return "workflow.events.blueprint.already_exists"

class BlueprintUpdateEvent(BlueprintCreatedEvent):
    id: UUID
    @property
    def subject(self)-> str:
        return "workflow.events.blueprint.updated"
