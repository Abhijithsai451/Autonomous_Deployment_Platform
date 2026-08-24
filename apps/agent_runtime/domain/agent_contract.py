from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID


class AgentExecutionStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"


@dataclass
class AgentError:
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    retryable: bool = False


@dataclass
class AgentContext:
    run_id: UUID
    agent_id: UUID
    task_id: UUID
    workflow_instance_id: UUID
    input_data: Dict[str, Any]
    configuration: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    status: AgentExecutionStatus
    output_data: Optional[Dict[str, Any]] = None
    error: Optional[AgentError] = None
    execution_duration_ms: float = 0.0


class BaseAgent:
    """
    Abstract contract for all execution units within the Agent Runtime.
    """
    def execute(self, context: AgentContext) -> AgentResult:
        raise NotImplementedError("Agents must implement their own execute logic.")