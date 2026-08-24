from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from apps.agent_runtime.infrastructure.database import agent_db_session, agent_runtime_db_client
from apps.agent_runtime.infrastructure.struct_logger import struct_logger as logger

router = APIRouter(tags=["Health"])

@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    return {"status": "ok"}


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check(db: AsyncSession = Depends(agent_db_session)):
    try:
        is_alive = agent_runtime_db_client.check_health()
        if not is_alive:
            raise Exception("Database ping returned unexpected response.")
        return {"status": "ready", "database": "connected"}
    except Exception as exc:
        logger.error("Readiness check failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not_ready", "database": "disconnected"}
        )