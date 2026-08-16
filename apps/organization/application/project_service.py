from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from apps.organization.domain.events.project_events import ProjectCreatedEvent, ProjectUpdatedEvent, \
    ProjectSuspendedEvent, ProjectArchivedEvent, ProjectNotFoundEvent
from apps.organization.domain.outbox import OutboxEvent, OutboxStatus
from apps.organization.domain.project import Project, ProjectStatus


class ProjectService:

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
    async def create_projects(self,org_id: UUID,name: str, description: str, lifecycle: str )-> Project :
        project = Project(organization_id=org_id, name=name, description=description, lifecycle=lifecycle)
        self.db.add(project)
        self.db.flush()
        event = ProjectCreatedEvent(id = project.id, status = project.status).subject
        payload = {
            "id": str(project.id),
            "organization_id": str(project.organization_id),
            "name": project.name,
            "lifecycle": str(project.lifecycle),
            "status": str(project.status),
        }
        self._log_event(aggregate_id=project.id,
                        aggregate_type="PROJECT",
                        event_type=event,
                        payload = payload
                        )

        self.db.commit()
        self.db.refresh(project)
        return project

    async def update_project_data(self, project_id: UUID,updates: dict )-> Project:
        project = self.db.query(Project).where(Project.id == str(project_id)).first()
        if project:
            for k,v in updates.items():
                attr_name = "project_metadata" if k == "metadata" else k
                if hasattr(project, attr_name):
                    setattr(project, attr_name, v)
            event = ProjectUpdatedEvent(id=project.id, status=project.status).subject
            payload = {
                "id": str(project.id),
                "organization_id": str(project.organization_id),
                "name": project.name,
                "lifecycle": str(project.lifecycle),
                "status": str(project.status),
            }
            self._log_event(aggregate_id=project.id,
                            aggregate_type="PROJECT",
                            event_type=event,
                            payload=payload
                            )
            self.db.commit()
            self.db.refresh(project)

    async def update_project_status(self, project_id:UUID, status: str):
        project = self.db.query(Project).where(Project.id == str(project_id)).first()
        if project:
            project.status = ProjectStatus(status)
            if project.status == ProjectStatus.DELETED:
                event = ProjectSuspendedEvent(id=project.id, status=project.status).subject
                payload = {
                    "id": str(project.id),
                    "organization_id": str(project.organization_id),
                    "name": project.name,
                    "lifecycle": str(project.lifecycle),
                    "status": str(project.status),
                }
                self._log_event(aggregate_id=project.id,
                                aggregate_type="PROJECT",
                                event_type=event,
                                payload=payload
                                )
                self.db.commit()

            if project.status == ProjectStatus.ARCHIVED:
                event = ProjectArchivedEvent(id=project.id, status=project.status).subject
                payload = {
                    "id": str(project.id),
                    "organization_id": str(project.organization_id),
                    "name": project.name,
                    "lifecycle": str(project.lifecycle),
                    "status": str(project.status),
                }
                self._log_event(aggregate_id=project.id,
                                aggregate_type="PROJECT",
                                event_type=event,
                                payload=payload
                                )
                self.db.commit()

        else:
            event = ProjectNotFoundEvent(id=project_id).subject
            payload = {
                "id": str(project_id),
                "Error": "Project not found with id {project_id}"
            }
            self._log_event(
                aggregate_id=project_id,
                aggregate_type="PROJECT",
                event_type=event,
                payload=payload
            )
            raise HTTPException(status_code=404, detail=f"Organization not found with id {project_id}")

