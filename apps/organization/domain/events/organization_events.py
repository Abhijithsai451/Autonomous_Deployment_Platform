from enum import Enum
from uuid import UUID

from packages.events.base import BaseEvent


class OrganizationLifeCycleEvent(BaseEvent):
    id : UUID

class OrganizationCreatedEvent(OrganizationLifeCycleEvent):
    status: Enum
    @property
    def subject(self)-> str:
        return "organization.events.organization.created"

class OrganizationStatusUpdatedEvent(OrganizationLifeCycleEvent):
    status: Enum
    @property
    def subject(self)-> str:
        return "organization.events.organization.status_updated"

class OrganizationUpdatedEvent(OrganizationLifeCycleEvent):
    status: Enum
    @property
    def subject(self)-> str:
        return "organization.events.organization.updated"

class OrganizationSuspendedEvent(OrganizationLifeCycleEvent):
    status: Enum
    @property
    def subject(self)-> str:
        return "organization.events.organization.suspended"

class OrganizationNotFoundEvent(OrganizationLifeCycleEvent):
    @property
    def subject(self)-> str:
        return "organization.events.organization.not_found"