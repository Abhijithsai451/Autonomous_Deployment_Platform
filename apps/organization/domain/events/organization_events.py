from enum import Enum
from uuid import UUID

from packages.events.base import BaseEvent


class OrganizationLifeCycleEvent(BaseEvent):
    id : UUID
    status: Enum

class OrganizationCreatedEvent(OrganizationLifeCycleEvent):
    @property
    def subject(self)-> str:
        return "organization.events.organization.created"

class OrganizationUpdatedEvent(OrganizationLifeCycleEvent):
    @property
    def subject(self)-> str:
        return "organization.events.organization.updated"

class OrganizationSuspendedEvent(OrganizationLifeCycleEvent):
    @property
    def subject(self)-> str:
        return "organization.events.organization.suspended"

