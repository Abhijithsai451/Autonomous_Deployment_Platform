from apps.agent_runtime.domain.agents import Agent


class EchoAgent:
    """Deterministic agent implementation for Phase 1."""
    async def run(self, agent: Agent, input_data: dict) -> dict:
        echo_res = agent.run_agent()
        message = input_data.get("message") or input_data.get("payload", {}).get("message", "Phase 1 Complete")
        return {
            "result": "completed",
            "echo_message": message,
            "agent_response": echo_res
        }