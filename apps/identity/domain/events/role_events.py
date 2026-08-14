from uuid import UUID
from packages.events.base import BaseEvent


class RoleLifecycleEvent(BaseEvent):
    id : UUID

class RoleCreatedEvent(RoleLifecycleEvent):
    @property
    def subject(self)-> str:
        return "identity.events.role.created"

class RoleAssignedToUserEvent(RoleLifecycleEvent):
    user_id: UUID
    @property
    def subject(self)-> str:
        return "identity.events.role.assignedToUser"

class RoleRemovedFromUserEvent(RoleLifecycleEvent):
    user_id: UUID
    @property
    def subject(self)-> str:
        return "identity.events.role.removedFromUser"

