from uuid import UUID
from packages.events.base import BaseEvent

class UserLifecycleEvent(BaseEvent):
    id: UUID
    keycloak_user_id: UUID
class UserCreatedEvent(UserLifecycleEvent):
    @property
    def subject(self)-> str:
        return "identity.events.user.created"

class UserInvitedEvent(UserLifecycleEvent):
    @property
    def subject(self)-> str:
        return "identity.events.user.invited"

class UserActivatedEvent(UserLifecycleEvent):
    @property
    def subject(self)-> str:
        return "identity.events.user.activated"

class UserDisabledEvent(UserLifecycleEvent):
    @property
    def subject(self)-> str:
        return "identity.events.user.disabled"

class UserLoggedInEvent(UserLifecycleEvent):
    @property
    def subject(self)-> str:
        return "identity.events.user.loggedIn"

class UserLoggedOutEvent(UserLifecycleEvent):
    @property
    def subject(self)-> str:
        return "identity.events.user.loggedOut"

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