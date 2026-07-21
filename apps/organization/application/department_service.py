from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from apps.organization.domain.department import Department, DepartmentStatus
from infrastructure.nats.nats_client import EventBus

class DepartmentService:
    def __init__(self, db:Session):
        self.db = db
    async def create_department(self, name: str, description: str, type: str) -> Department:
        department = Department(name=name, description=description,type = type )
        self.db.add(department)
        self.db.commit()
        self.db.refresh(department)
        await EventBus.publish("DepartmentCreated", {"id": str(department.id), "description": str(department.description)})
        return department

    async def update_department_data(self, department_id:UUID, updates:dict)-> Department:
        department = self.db.query(Department).where(Department.id == str(department_id)).first()
        if department:
            for k,v in updates.items():
                setattr(department, k,v)
            self.db.commit()
            self.db.refresh(department)
            await EventBus.publish("DepartmentDataUpdated", {"id":str(department.id)})
        return department

    async def update_department_status(self, department_id: UUID, status: str):
        department = self.db.query(Department).where(Department.id == str(department_id)).first()
        if department:
            department.status = DepartmentStatus(status)
            if department.status == DepartmentStatus.UPDATED:
                self.db.commit()
                await EventBus.publish("DepartmentUpdated", {"id": str(department.id), "status": "UPDATED"})
            if department.status == DepartmentStatus.DELETED:
                self.db.commit()
                await EventBus.publish("DepartmentDeleted", {"id": str(department.id), "status": "DELETED"})
            if department.status == DepartmentStatus.ARCHIVED:
                self.db.commit()
                await EventBus.publish("DepartmentArchived", {"id": str(department.id), "status": "ARCHIVED"})
        else:
            await EventBus.publish("DepartmentNotFound", {"id": str(department.id)})
            raise HTTPException(status_code=404, detail=f"Organization not found with id {department_id}")

