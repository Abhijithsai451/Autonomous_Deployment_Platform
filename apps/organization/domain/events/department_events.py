from enum import Enum
from uuid import UUID

from packages.events.base import BaseEvent


class DepartmentLifeCycleEvent(BaseEvent):
    id : UUID

class DepartmentCreatedEvent(DepartmentLifeCycleEvent):
    status: Enum
    @property
    def subject(self)-> str:
        return "organization.events.department.created"

class DepartmentArchivedEvent(DepartmentLifeCycleEvent):
    status: Enum
    @property
    def subject(self)-> str:
        return "organization.events.department.archived"

class DepartmentDeletedEvent(DepartmentLifeCycleEvent):
    status: Enum
    @property
    def subject(self)-> str:
        return "organization.events.department.deleted"


class DepartmentUpdatedEvent(DepartmentLifeCycleEvent):
    status: Enum
    @property
    def subject(self)-> str:
        return "organization.events.department.updated"

class DepartmentNotFoundEvent(DepartmentLifeCycleEvent):
    @property
    def subject(self)-> str:
        return "organization.events.department.not_found"