from uuid import UUID

from packages.events.base import BaseEvent


class UserLifecycleEvent(BaseEvent):
    id: UUID
    keycloak_user_id: UUID

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




