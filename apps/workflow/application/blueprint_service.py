from typing import Optional, List
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from apps.workflow.domain.events.blueprint_events import BlueprintAlreadyExists, BlueprintCreatedEvent, \
    BlueprintUpdateEvent
from apps.workflow.domain.outbox import OutboxEvent, OutboxStatus
from apps.workflow.domain.workflow_blueprints import WorkflowBlueprint

class BlueprintService:
    def __init__(self, db: Session):
        self.db = db

    def _log_event(self, aggregate_id:Optional[UUID], aggregate_type: str, event_type: str, payload: dict):
        outbox_entry = OutboxEvent(
            aggregate_id=aggregate_id,
            aggregate_type=aggregate_type,
            event_type=event_type,
            payload=payload,
            status=OutboxStatus.PENDING
        )
        self.db.add(outbox_entry)

    def create_blueprint(self,  name: str, definition: dict, description: Optional[str] = None,
        version: int = 1 ) -> WorkflowBlueprint:
        existing = (
            self.db.query(WorkflowBlueprint)
            .filter( WorkflowBlueprint.name == name, WorkflowBlueprint.version == version)
            .first()
        )
        if existing:
            self._log_event(
                aggregate_type="BLUEPRINT",
                event_type=BlueprintAlreadyExists(name=name).subject,
                payload={
                "name": name,
                "error": f"Blueprint with the name {name} already exists"
            })
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f"Blueprint '{name}' with version {version} already exists"
            )

        blueprint = WorkflowBlueprint(
            name=name,
            description=description,
            version=version,
            definition=definition,
            is_active=True
        )
        self.db.add(blueprint)
        self.db.flush()
        self._log_event(
            aggregate_id=blueprint.id,
            event_type=BlueprintCreatedEvent(id = blueprint.id).subject,
            payload={
                "id": str(blueprint.id),
                "name": blueprint.name,
                "version": blueprint.version,
                "is_active": blueprint.is_active
            }
        )
        self.db.commit()
        self.db.refresh(blueprint)
        return blueprint

    def get_blueprints(self, limit: int = 100, offset: int = 0) -> List[WorkflowBlueprint]:
        return self.db.query(WorkflowBlueprint).offset(offset).limit(limit).all()

    def get_blueprint_by_id(self, blueprint_id: UUID) -> WorkflowBlueprint:
        blueprint = self.db.query(WorkflowBlueprint).filter(WorkflowBlueprint.id == blueprint_id).first()
        if not blueprint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail=f"Blueprint not found with id {blueprint_id}"
            )
        return blueprint

    def update_blueprint(self, blueprint_id: UUID, updates: dict) -> WorkflowBlueprint:
        blueprint = self.get_blueprint_by_id(blueprint_id)

        for k, v in updates.items():
            if hasattr(blueprint, k):
                setattr(blueprint, k, v)


        self._log_event(
           aggregate_id=blueprint.id,
            event_type= BlueprintUpdateEvent(id=blueprint_id).subject,
            payload={
                "id": str(blueprint.id),
                "name": blueprint.name,
                "version": blueprint.version,
                "is_active":blueprint.is_active,
            }
        )

        self.db.commit()
        self.db.refresh(blueprint)
        return blueprint