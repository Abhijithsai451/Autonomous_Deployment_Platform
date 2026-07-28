from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from apps.organization.domain.department import Department, DepartmentStatus
from apps.organization.infrastructure.org_nats_client import org_nats_client as nats


class DepartmentService:
    def __init__(self, db:Session):
        self.db = db
    async def create_department(self, org_id: UUID, name: str, description: str, type: str) -> Department:
        department = Department(organization_id=org_id, name=name, description=description, type=type)
        self.db.add(department)
        self.db.commit()
        self.db.refresh(department)
        await nats.publish("DepartmentCreated", {"id": str(department.id), "description": str(department.description)})
        return department

    async def update_department_data(self, department_id:UUID, updates:dict)-> Department:
        department = self.db.query(Department).where(Department.id == str(department_id)).first()
        if department:
            for k,v in updates.items():
                attr_name = "department_metadata" if k == "metadata" else k
                if hasattr(department, attr_name):
                    setattr(department, attr_name, v)
            self.db.commit()
            self.db.refresh(department)
            await nats.publish("DepartmentDataUpdated", {"id":str(department.id)})
        return department

    async def update_department_status(self, department_id: UUID, status: str):
        department = self.db.query(Department).where(Department.id == str(department_id)).first()
        if department:
            department.status = DepartmentStatus(status)
            if department.status == DepartmentStatus.UPDATED:
                self.db.commit()
                await nats.publish("DepartmentUpdated", {"id": str(department.id), "status": "UPDATED"})
            if department.status == DepartmentStatus.DELETED:
                self.db.commit()
                await nats.publish("DepartmentDeleted", {"id": str(department.id), "status": "DELETED"})
            if department.status == DepartmentStatus.ARCHIVED:
                self.db.commit()
                await nats.publish("DepartmentArchived", {"id": str(department.id), "status": "ARCHIVED"})
        else:
            await nats.publish("DepartmentNotFound", {"id": str(department.id)})
            raise HTTPException(status_code=404, detail=f"Organization not found with id {department_id}")

