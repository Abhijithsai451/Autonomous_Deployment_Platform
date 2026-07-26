from fastapi import HTTPException
from typing import Optional, List
from uuid import UUID

from sqlalchemy.orm import Session

from apps.workflow.domain.workflow_blueprints import WorkflowBlueprint
from infrastructure.nats.nats_client import EventBus


class BlueprintService:
    def __init__(self, db:Session):
        self.db = db

    async def create_blueprint(self, name: str, definition: dict, description: Optional[str] = None,
                               version: int =1)-> WorkflowBlueprint:
        existing = (
            self.db.query(WorkflowBlueprint).filter(WorkflowBlueprint.name == name, WorkflowBlueprint.version == version).first()
        )
        if existing:
            raise HTTPException(status_code=400, detail = f"Blueprint '{name}' with version {version} already exists")
        blueprint = WorkflowBlueprint(
            name=name,
            description=description,
            version=version,
            definition=definition,
            is_active=True
        )
        self.db.add(blueprint)
        self.db.commit()
        self.db.refresh(blueprint)

        await EventBus.publish("BlueprintCreated",
                               {"id": str(blueprint.id), "name": blueprint.name, "version": blueprint.version})
        return blueprint

    async def get_blueprints(self, limit: int = 100, offset: int = 0) -> List[WorkflowBlueprint]:
        return self.db.query(WorkflowBlueprint).offset(offset).limit(limit).all()

    async def get_blueprint_by_id(self, blueprint_id: UUID) -> WorkflowBlueprint:
        blueprint = self.db.query(WorkflowBlueprint).filter(WorkflowBlueprint.id == blueprint_id).first()
        if not blueprint:
            raise HTTPException(status_code=404, detail=f"Blueprint not found with id {blueprint_id}")
        return blueprint

    async def update_blueprint(self, blueprint_id: UUID, updates: dict) -> WorkflowBlueprint:
        blueprint = await self.get_blueprint_by_id(blueprint_id)

        if "definition" in updates and blueprint.definition != updates["definition"]:
            pass

        for k, v in updates.items():
            if hasattr(blueprint, k):
                setattr(blueprint, k, v)

        self.db.commit()
        self.db.refresh(blueprint)
        await EventBus.publish("BlueprintUpdated", {"id": str(blueprint.id), "name": blueprint.name})
        return blueprint

    async def update_blueprint_status(self, status):
        pass


