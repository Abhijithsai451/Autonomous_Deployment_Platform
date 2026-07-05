from typing import TypeVar, Generic, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.platform.models import WorkflowModel

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
        result = await self.session.execute(select(Workflow))