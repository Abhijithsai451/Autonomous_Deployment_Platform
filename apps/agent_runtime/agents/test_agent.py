import time
from typing import Dict, Any
from apps.agent_runtime.domain.agent_contract import BaseAgent, AgentContext, AgentResult, AgentExecutionStatus, AgentError
from apps.agent_runtime.infrastructure.struct_logger import struct_logger as logger


class TestAgent(BaseAgent):
    def execute(self, context: AgentContext)-> AgentResult:
        start_time = time.perf_counter()
        logger.info("Executing TestAgent", run_id = str(context.run_id), task_id = str(context.task_id))
        try:
            action_type = context.input_data.get("action_type", "default")
            if action_type == "fail":
                raise ValueError("Simulated Agent failure requested by input payload. ")

            output_payload: Dict[str, Any]= {
                "message": "TestAgent executed successfully",
                "processed_action": action_type,
                "input_reference": context.input_data.get("input_reference"),
                "echo_payload": context.input_data.get("payload", {}),
            }
            duration_ms = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                status = AgentExecutionStatus.COMPLETED,
                output_data = output_payload,
                execution_duration_ms=duration_ms
            )
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"TestAgent Execution Failed", error = str(exc), run_id = str(context.run_id))
            return AgentResult(
                status=AgentExecutionStatus.FAILED,
                error = AgentError(
                    code = "TEST_AGENT_EXECUTION_FAILED",
                    message = str(exc),
                    retryable=False,
                ),
                execution_duration_ms=round(duration_ms,2)
            )
            