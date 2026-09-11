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


class ProjectLifeCycleEvent(BaseEvent):
    id : UUID


class ProjectCreatedEvent(ProjectLifeCycleEvent):
    status: Enum
    @property
    def subject(self)-> str:
        return "organization.events.project.created"

class ProjectUpdatedEvent(ProjectLifeCycleEvent):
    status: Enum
    @property
    def subject(self)-> str:
        return "organization.events.project.updated"

class ProjectArchivedEvent(ProjectLifeCycleEvent):
    status: Enum
    @property
    def subject(self)-> str:
        return "organization.events.project.archived"

class ProjectSuspendedEvent(ProjectLifeCycleEvent):
    status: Enum
    @property
    def subject(self)-> str:
        return "organization.events.project.suspended"

class ProjectNotFoundEvent(ProjectLifeCycleEvent):
    @property
    def subject(self)-> str:
        return "organization.events.project.suspended"
