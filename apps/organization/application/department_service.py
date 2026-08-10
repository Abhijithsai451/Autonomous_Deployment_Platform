from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from apps.organization.domain.department import Department, DepartmentStatus
from apps.organization.domain.events.department_events import DepartmentCreatedEvent, DepartmentUpdatedEvent, \
    DepartmentDeletedEvent, DepartmentArchivedEvent, DepartmentNotFoundEvent
from apps.organization.domain.outbox import OutboxEvent, OutboxStatus


class DepartmentService:
    def __init__(self, db:Session):
        self.db = db
    def _log_event(self, aggregate_id: UUID, aggregate_type: str,  event_type: str, payload:dict):
        outbox_entry = OutboxEvent(
                aggregate_id=aggregate_id,
                aggregate_type=aggregate_type,
                event_type = event_type,
                payload= payload,
            status = OutboxStatus.PENDING
        )
        self.db.add(outbox_entry)
    async def create_department(self, org_id: UUID, name: str, description: str, type: str) -> Department:
        department = Department(organization_id=org_id, name=name, description=description, type=type)
        self.db.add(department)
        self.db.flush()
        event = DepartmentCreatedEvent(id = department.id, status = department.status).subject
        payload = {
            "id": str(department.id),
            "organization_id": str(org_id),
            "name": department.name,
            "type": str(department.type),
            "status": str(department.status),
        }
        self._log_event(
                        aggregate_id=department.id,
                        aggregate_type="DEPARTMENT",
                        event_type=event,
                        payload = payload,
        )
        self.db.commit()
        self.db.refresh(department)
        return department

    async def update_department_data(self, department_id:UUID, updates:dict):
        department = self.db.query(Department).where(Department.id == str(department_id)).first()
        if department:
            for k,v in updates.items():
                attr_name = "department_metadata" if k == "metadata" else k
                if hasattr(department, attr_name):
                    setattr(department, attr_name, v)
            event = DepartmentUpdatedEvent(id = department.id, status = department.status).subject
            payload = {
                "id": str(department.id),
                "organization_id": str(department.organization_id),
                "name": department.name,
                "type": str(department.type),
                "status": str(department.status),
            }
            self._log_event(
                aggregate_id=department.id,
                aggregate_type="DEPARTMENT",
                event_type=event,
                payload=payload,
            )
            self.db.commit()
            self.db.refresh(department)


    async def update_department_status(self, department_id: UUID, status: str):
        department = self.db.query(Department).where(Department.id == str(department_id)).first()
        if department:
            department.status = DepartmentStatus(status)
            if department.status == DepartmentStatus.DELETED:
                event = DepartmentDeletedEvent(id=department.id, status=department.status).subject
                payload = {
                    "id": str(department.id),
                    "organization_id": department.organization_id,
                    "name": department.name,
                    "type": str(department.type),
                    "status": str(department.status),
                }
                self._log_event(
                    aggregate_id=department.id,
                    aggregate_type="DEPARTMENT",
                    event_type=event,
                    payload=payload,
                )
                self.db.commit()
            if department.status == DepartmentStatus.ARCHIVED:
                event = DepartmentArchivedEvent(id=department.id, status=department.status).subject
                payload = {
                    "id": str(department.id),
                    "organization_id": department.organization_id,
                    "name": department.name,
                    "type": str(department.type),
                    "status": str(department.status),
                }
                self._log_event(
                    aggregate_id=department.id,
                    aggregate_type="DEPARTMENT",
                    event_type=event,
                    payload=payload,
                )
                self.db.commit()
        else:
            event = DepartmentNotFoundEvent(id=department.id).subject
            payload = {
                "id": str(department.id),
                "Error": "Department Not Found"
            }
            self._log_event(
                aggregate_id=department.id,
                aggregate_type="DEPARTMENT",
                event_type=event,
                payload=payload,
            )
            raise HTTPException(status_code=404, detail=f"Organization not found with id {department_id}")

