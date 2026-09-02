import time
from abc import ABC, abstractmethod
from dataclasses import field, dataclass
from typing import Any, Dict, Optional

from apps.agent_runtime.infrastructure.struct_logger import struct_logger as logger


@dataclass
class ToolInput:
    """
    Standardized Wrapper for parameters passed into a tool execution
    """
    parameters: Dict[str, Any] = field(default_factory=dict)
    context_metadata: Dict[str, Any] = field(default_factory = dict)

@dataclass
class ToolOutput:
    """Standardized wrapper for data returned from a tool execution."""
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_duration_ms: float = 0.0


class BaseTool(ABC):
    name: str = "base_tool"
    description: str = "Abstract base tool implementation"
    version: str = "1.0.0"

    def execute(self, tool_input: ToolInput) -> ToolOutput:
        """
        Public execution wrapper. Measures latency and catches unhandled tool exceptions
        so tool failures never crash the entire Agent execution loop.
        """
        start_time = time.perf_counter()
        logger.info(
            "Executing tool",
            tool_name=self.name,
            tool_version=self.version,
        )

        try:
            raw_result = self._run(tool_input.parameters)
            duration_ms = (time.perf_counter() - start_time) * 1000

            return ToolOutput(
                success=True,
                result=raw_result,
                execution_duration_ms=round(duration_ms, 2),
            )

        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "Tool execution failed",
                tool_name=self.name,
                error=str(exc),
            )

            return ToolOutput(
                success=False,
                error=str(exc),
                execution_duration_ms=round(duration_ms, 2),
            )

    @abstractmethod
    def _run(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Core tool execution logic implemented by concrete tools.
        Must accept a dictionary of parameters and return a dictionary result.
        """
        pass

    def get_schema(self) -> Dict[str, Any]:
        """
        Returns metadata schema for LLM function calling registration.
        """
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
        }