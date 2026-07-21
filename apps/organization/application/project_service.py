from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session
from apps.organization.domain.project import Project, ProjectStatus
from infrastructure.nats.nats_client import EventBus


class ProjectService:

    def __init__(self, db:Session):
        self.db = db

    async def create_projects(self,org_id: UUID,name: str, description: str, lifecycle: str )-> Project :
        project = Project(organization_id=org_id, name=name, description=description, lifecycle=lifecycle)
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        await EventBus.publish("ProjectCreated", {"id": str(project.id), "description":str(project.description)})
        return project

    async def update_project_data(self, project_id: UUID,updates: dict )-> Project:
        project = self.db.query(Project).where(Project.id == str(project_id)).first()
        if project:
            for k,v in updates.items():
                attr_name = "project_metadata" if k == "metadata" else k
                if hasattr(project, attr_name):
                    setattr(project, attr_name, v)
            self.db.commit()
            self.db.refresh(project)
            await EventBus.publish("ProjectDataUpdated", {"id": str(project.id)})
        return project

    async def update_project_status(self, project_id:UUID, status: str):
        project = self.db.query(Project).where(Project.id == str(project_id)).first()
        if project:
            project.status = ProjectStatus(status)
            if project.status == ProjectStatus.UPDATED:
                self.db.commit()
                await EventBus.publish("ProjectUpdated", {"id": str(project.id), "status": "UPDATED"})
            if project.status == ProjectStatus.DELETED:
                self.db.commit()
                await EventBus.publish("ProjectDeleted", {"id": str(project.id), "status": "DELETED"})
            if project.status == ProjectStatus.ARCHIVED:
                self.db.commit()
                await EventBus.publish("ProjectArchived",{"id": str(project.id), "status": "ARCHIVED"})
        else:
            await EventBus.publish("ProjectNotFound", {"id": str(Project.id)})
            raise HTTPException(status_code=404, detail=f"Organization not found with id {project_id}")

