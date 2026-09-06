from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from apps.agent_runtime.domain.agents import Agent, AgentStatus


class AgentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, agent_id: UUID)-> Optional[Agent]:
        return self.db.query(Agent).filter(Agent.id == agent_id).first()

    def get_by_slug(self, slug: str)-> Optional[Agent]:
        return self.db.query(Agent).filter(Agent.slug == slug).first()

    def list_active(self)-> list[Agent]:
        return self.db.query(Agent).filter(Agent.status=="ACTIVE").all()

    def create(self, agent_id: UUID, name)-> Optional[Agent]:
        agent = Agent(id=agent_id, name=name, status=AgentStatus.ACTIVE)
        self.db.add(agent)
        return agent