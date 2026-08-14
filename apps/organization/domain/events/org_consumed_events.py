from packages.events.base import BaseEvent


class DepartmentLifeCycleEvent(BaseEvent):
    id : UUID
    status: Enum

class DepartmentCreatedEvent(DepartmentLifeCycleEvent):
    @property
    def subject(self)-> str:
        return "organization.events.department.created"