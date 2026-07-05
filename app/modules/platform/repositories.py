from typing import TypeVar, Generic, Optional, List
from uuid import UUID

import Workflow
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.platform.models import WorkflowModel, StatusEnum, TaskModel

T = TypeVar("T")

class BaseRepository(Generic[T]):
    def __init__(self,session: AsyncSession):
        self.session = session

class WorkflowRepository(BaseRepository[WorkflowModel]):
    async def create(self, description: str, context_payload: dict)-> WorkflowModel:
        wf = WorkflowModel(description= description, context_payload = context_payload)
        self.session.add(wf)
        await self.session.flush()
        return wf
    async def get_by_id(self, wf_id: UUID)-> Optional[WorkflowModel]:
        result = await self.session.execute(select(WorkflowModel).where(WorkflowModel.id == wf_id))
        return result.scaler_one_or_none()

    async def update_status(self,wf_id: UUID, status: StatusEnum, temporal_id: Optional[str] = None) -> Optional[WorkflowModel]:
        wf = await self.get_by_id(wf_id=wf_id)
        if wf:
            wf.status = status
            if temporal_id:
                wf.temporal_workflow_id = temporal_id
            await self.session.flush()
        return wf

class TaskRepository(BaseRepository[TaskModel]):
    async def create_task(self, workflow_id : UUID, title: str, assigned_agent: str, depends_on: Optional[UUID]= None)-> TaskModel:
        task = TaskModel(workflow_id=workflow_id, title = title, assigned_agent = assigned_agent, depends_on=depends_on)
        self.session.add(task)
        await self.session.commit()
        return task

    async def get_workflow_tasks(self, workflow_id: UUID)-> List[TaskModel]:
        result = await self.session.execute(select(TaskModel).where(TaskModel.workflow_id == workflow_id))
        return list(result.scalars().all())


