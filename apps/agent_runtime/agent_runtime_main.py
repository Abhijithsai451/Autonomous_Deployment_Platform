import asyncio
from apps.agent_runtime.infrastructure.agent_runtime_nats_client import agent_nats_client as nats
from apps.agent_runtime.infrastructure.outbox_publisher import agent_outbox_publisher
from apps.agent_runtime.infrastructure.struct_logger import struct_logger as logger

"""
 1. Initiating the Nats Server.  - Done
 2. Create a Task to send to the orchestrator
 3. Create the LangGraph with agent loops to create the architecture of agents to run the tasks 
 4. Create composio interface 
 5. Create the tools to push code to github, deploy code to kubernetes, 
 """

async def main():
    logger.info("Initializing the Agent Runtime Daemon ....")

    await nats.initialize()
    logger.info("NATS Core Messaging is successfully initialized for Agent Runtime Service")


if __name__ == "__main__":
    asyncio.run(main())