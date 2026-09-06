from typing import Type, Dict
from uuid import UUID

from apps.agent_runtime.agents.test_agent import TestAgent
from apps.agent_runtime.domain.agent_contract import BaseAgent
from apps.agent_runtime.domain.agents import Agent, AgentStatus
from apps.agent_runtime.infrastructure.struct_logger import struct_logger as logger
from apps.agent_runtime.repository.agent_repository import AgentRepository


class AgentRegistryError(Exception):
    pass

class AgentRegistry:
    def __init__(self, agent_repo : AgentRepository):
        if isinstance(agent_repo, tuple):
            self.agent_repo = agent_repo[0]
        else:
            self.agent_repo = agent_repo

        self._registry: Dict[str, Type[BaseAgent]] = {
            "test-agent-1": TestAgent,
            "test-agent-2": TestAgent,
            "test-agent-3": TestAgent,
            "test-agent-4": TestAgent,
            "test-agent-5": TestAgent,
            "test-agent-6": TestAgent,
            "test-agent-7": TestAgent,
            "test-agent-8": TestAgent,
            "test-agent-9": TestAgent,
            "test-agent-10": TestAgent,
        }
    def resolve(self, slug: str)-> BaseAgent:
        agent_record: Agent = self.agent_repo.get_by_slug(slug)
        if not agent_record:
            raise AgentRegistryError(f"Agent with Slug {slug} not found in database. ")
        status_value = (
            agent_record.status.value
            if hasattr(agent_record.status, "value")
            else str(agent_record.status)
        )
        if status_value != AgentStatus.ACTIVE:
            raise AgentRegistryError(f"Agent with slug {slug} is  disabled (status = {agent_record.status}")
        agent_cls = self._registry.get(slug)
        if not agent_cls:
            raise AgentRegistryError(f"No Python implementation registered for agent slug '{slug}'.")

        return agent_cls()

    def resolve_by_id(self, agent_id: UUID)-> BaseAgent:
        """
        Loads Agent entity by UUID, checks status and instantiates implementation.
        """
        agent_record : Agent = self.agent_repo.get_by_id(agent_id)
        if not agent_record:
            raise AgentRegistryError(f"Agent with id {agent_id} not found in database. ")
        return self.resolve(agent_record.slug)




