from enum import Enum
from uuid import UUID

from packages.events.base import BaseEvent


class DepartmentLifeCycleEvent(BaseEvent):
    id : UUID
    status: Enum

class DepartmentCreatedEvent(DepartmentLifeCycleEvent):
    @property
    def subject(self)-> str:
        return "organization.events.department.created"

class DepartmentUpdatedEvent(DepartmentLifeCycleEvent):
    @property
    def subject(self)-> str:
        return "organization.events.department.updated"

class DepartmentArchivedEvent(DepartmentLifeCycleEvent):
    @property
    def subject(self)-> str:
        return "organization.events.department.archived"
