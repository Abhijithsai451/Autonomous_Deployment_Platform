from typing import Dict, Optional, Any, List
from apps.agent_runtime.infrastructure.struct_logger import struct_logger as logger
from apps.agent_runtime.tools.base import BaseTool, ToolOutput, ToolInput
from apps.agent_runtime.tools.local_tools import JSONTransformerTool, TaskReaderTool


class ToolRegistryError(Exception):
    """Custom exception raised when tool resolution or execution fails at the registry level."""
    pass


class ToolRegistry:
    """
    Central registry for managing, resolving, and invoking execution tools.
    """
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        # Register default baseline tools upon initialization
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        """Instantiates and registers default local tools."""
        self.register(JSONTransformerTool())
        self.register(TaskReaderTool())

    def register(self, tool: BaseTool) -> None:
        """Registers a tool instance using its defined name."""
        if not tool.name:
            raise ToolRegistryError("Cannot register a tool without a valid 'name' attribute.")

        self._tools[tool.name] = tool
        logger.info("Tool registered successfully", tool_name=tool.name, tool_version=tool.version)

    def get(self, tool_name: str) -> Optional[BaseTool]:
        """Retrieves a registered tool by its name."""
        return self._tools.get(tool_name)

    def resolve(self, tool_name: str) -> BaseTool:
        """
        Resolves and returns a registered tool by name.
        Raises ToolRegistryError if the tool is not found.
        """
        tool = self.get(tool_name)
        if not tool:
            raise ToolRegistryError(f"Tool '{tool_name}' is not registered in ToolRegistry.")
        return tool

    def execute_tool(self, tool_name: str, parameters: Dict[str, Any],
                     context_metadata: Optional[Dict[str, Any]] = None) -> ToolOutput:
        """
        Safe execution entry point. Resolves tool by name and executes it with input context.
        """
        tool = self.resolve(tool_name)
        tool_input = ToolInput(
            parameters=parameters,
            context_metadata=context_metadata or {}
        )
        return tool.execute(tool_input)

    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """Returns the function-calling schema definitions for all registered tools."""
        return [tool.get_schema() for tool in self._tools.values()]


global_tool_registry = ToolRegistry()