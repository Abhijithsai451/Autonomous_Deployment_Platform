from typing import Any, Dict, List, Optional
import json
import openai

from apps.agent_runtime.infrastructure.struct_logger import struct_logger as logger
from apps.agent_runtime.llm.base_client import BaseLLMClient, LLMMessage, LLMResponse, ToolCall

class OpenAILLMClient(BaseLLMClient):
    """OpenAI implementation supporting function schema binding and response parsing."""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.model = model

    async def generate(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.0,
    ) -> LLMResponse:
        formatted_messages = self._format_messages(messages)
        formatted_tools = self._format_tools(tools) if tools else None

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": formatted_messages,
            "temperature": temperature,
        }

        if formatted_tools:
            kwargs["tools"] = formatted_tools
            kwargs["tool_choice"] = "auto"

        try:
            response = await self.client.chat.completions.create(**kwargs)
            choice = response.choices[0]
            message = choice.message

            parsed_tool_calls: List[ToolCall] = []
            if message.tool_calls:
                for tc in message.tool_calls:
                    parsed_tool_calls.append(
                        ToolCall(
                            id=tc.id,
                            tool_name=tc.function.name,
                            arguments=json.loads(tc.function.arguments),
                        )
                    )

            return LLMResponse(
                content=message.content,
                tool_calls=parsed_tool_calls,
                finish_reason=choice.finish_reason,
                total_tokens=response.usage.total_tokens if response.usage else 0,
            )

        except Exception as exc:
            logger.error("OpenAI client completion request failed", error=str(exc))
            raise


    def _format_messages(self, messages: List[LLMMessage]) -> List[Dict[str, Any]]:
        formatted = []
        for msg in messages:
            item: Dict[str, Any] = {"role": msg.role, "content": msg.content or ""}
            if msg.role == "tool" and msg.tool_call_id:
                item["tool_call_id"] = msg.tool_call_id
            if msg.tool_calls:
                item["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.tool_name,
                            "arguments": json.dumps(tc.arguments),
                        },
                    }
                    for tc in msg.tool_calls
                ]
            formatted.append(item)
        return formatted

    def _format_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Wraps tool schemas into OpenAI's function tool specification."""
        openai_tools = []
        for schema in tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": schema["name"],
                    "description": schema.get("description", ""),
                    "parameters": schema.get("parameters", {"type": "object", "properties": {}}),
                },
            })
        return openai_tools