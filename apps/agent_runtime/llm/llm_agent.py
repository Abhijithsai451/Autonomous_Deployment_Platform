from typing import Any, Dict, List
from apps.agent_runtime.domain.agent_contract import BaseAgent, AgentContext, AgentResult, AgentExecutionStatus, AgentError
from apps.agent_runtime.infrastructure.struct_logger import struct_logger as logger
from apps.agent_runtime.llm.base_client import BaseLLMClient, LLMMessage
from apps.agent_runtime.tools.tool_registry import global_tool_registry



class ReActLLMAgent(BaseAgent):
    """
    ReAct (Reasoning + Acting) Agent Engine.
    Iteratively calls the LLM, executes requested tools, feeds back results, and returns output.
    """

    def __init__(self, llm_client: BaseLLMClient, max_iterations: int = 5):
        self.llm_client = llm_client
        self.max_iterations = max_iterations

    async def execute_async(self, context: AgentContext) -> AgentResult:
        system_prompt = (
            "You are a helpful automation agent. Analyze the user's task, select appropriate "
            "tools from the provided functions, execute them, and return a structured final summary."
        )

        messages: List[LLMMessage] = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=str(context.input_data)),
        ]

        tool_schemas = global_tool_registry.get_all_schemas()

        for iteration in range(self.max_iterations):
            logger.info("ReAct Loop Iteration", iteration=iteration + 1, run_id=str(context.run_id))

            response = await self.llm_client.generate(messages=messages, tools=tool_schemas)

            # Case A: Model issued a final answer without tools
            if not response.tool_calls:
                messages.append(LLMMessage(role="assistant", content=response.content))
                return AgentResult(
                    status=AgentExecutionStatus.COMPLETED,
                    output_data={"answer": response.content, "iterations": iteration + 1},
                )

            # Case B: Model requested one or more tool executions
            messages.append(
                LLMMessage(
                    role="assistant",
                    content=response.content,
                    tool_calls=response.tool_calls,
                )
            )

            for tool_call in response.tool_calls:
                logger.info("Executing Tool Request", tool_name=tool_call.tool_name, tool_call_id=tool_call.id)
                tool_output = global_tool_registry.execute_tool(
                    tool_name=tool_call.tool_name,
                    parameters=tool_call.arguments,
                    context_metadata={"run_id": str(context.run_id)},
                )

                # Feed execution result back to conversation context
                messages.append(
                    LLMMessage(
                        role="tool",
                        tool_call_id=tool_call.id,
                        content=str(tool_output.result if tool_output.success else tool_output.error),
                    )
                )

        return AgentResult(
            status=AgentExecutionStatus.FAILED,
            error=AgentError(
                code="MAX_ITERATIONS_EXCEEDED",
                message=f"Agent failed to settle on a final answer within {self.max_iterations} iterations.",
            ),
        )