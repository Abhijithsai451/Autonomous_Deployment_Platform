from apps.organization.domain.department import Department
from infrastructure.nats.nats_client import EventBus


async def create_department(self, name: str, description: str, type: str) -> Department:
    department = Department(name=name, description=description,type = type )
    self.db.add(department)
    self.db.commit()
    self.db.refresh(department)
    await EventBus.publish("DepartmentCreated", {"id": str(department.id), "description": str(department.description)})
    return department

