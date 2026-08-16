from enum import Enum
from uuid import UUID
from packages.events.base import BaseEvent


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
