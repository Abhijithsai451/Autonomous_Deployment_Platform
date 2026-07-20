from uuid import UUID

from sqlalchemy.orm import Session

from apps.organization.domain.project import Project
from infrastructure.nats.nats_client import EventBus


class ProjectService:
    def __init__(self, db:Session):
        self.db = db

    async def create_projects(self,name: str, description: str, lifecycle: str )-> Project :
        project = Project(name=name, description=description, lifecycle=lifecycle)
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        await EventBus.publish("ProjectCreated", {"id": str(project.id), "description":str(project.description)})
        return project

    async def update_project_status(self, project_id:UUID, status: str):
        project = self.db.query(Project).where(Project.id == str(project_id)).first()
        if project:
