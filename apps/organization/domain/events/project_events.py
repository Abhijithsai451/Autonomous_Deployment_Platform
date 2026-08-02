from enum import Enum
from uuid import UUID

from packages.events.base import BaseEvent


class ProjectLifeCycleEvent(BaseEvent):
    id : UUID
    status: Enum

class ProjectCreatedEvent(ProjectLifeCycleEvent):
    @property
    def subject(self)-> str:
        return "organization.events.project.created"

class ProjectArchivedEvent(ProjectLifeCycleEvent):
    @property
    def subject(self)-> str:
        return "organization.events.project.archived"

class ProjectSuspendedEvent(ProjectLifeCycleEvent):
    @property
    def subject(self)-> str:
        return "organization.events.project.suspended"

