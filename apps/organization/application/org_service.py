from fastapi import HTTPException
from uuid import UUID

from sqlalchemy.orm import Session

from apps.organization.domain.events.organization_events import OrganizationCreatedEvent, OrganizationUpdatedEvent, \
    OrganizationStatusUpdatedEvent, OrganizationNotFoundEvent, OrganizationSuspendedEvent
from apps.organization.domain.organization import Organization, OrgStatus
from apps.organization.domain.outbox import OutboxEvent, OutboxStatus
from apps.organization.infrastructure.org_nats_client import org_nats_client as nats


class OrganizationService:
    def __init__(self, db:Session):
        self.db = db

    def _log_event(self, aggregate_id: UUID, aggregate_type: str,  event_type: str, payload:dict):
        outbox_entry = OutboxEvent(
                aggregate_id=aggregate_id,
                aggregate_type=aggregate_type,
                event_type = event_type,
                payload= payload,
            status = OutboxStatus.PENDING
        )
        self.db.add(outbox_entry)

    async def create_organization(self, name: str, slug: str)-> Organization:
        org = Organization(name= name, slug = slug)
        self.db.add(org)
        self.db.flush()
        event = OrganizationCreatedEvent(id =org.id,status = org.status).subject
        payload = {
            "id": str(org.id),
            "name": org.name,
            "slug": org.slug,
            "status": str(org.status),
            "plan": str(org.plan)
        }
        self._log_event(
            aggregate_id= org.id,
            aggregate_type= "ORGANIZATION",
            event_type = event,
            payload = payload,
        )
        self.db.commit()
        return org

    async def update_organization(self, org_id:UUID, updates: dict):
        org = self.db.query(Organization).where(Organization.id == str(org_id)).first()
        if org:
            for k, v in updates.items():
                setattr(org, k, v)
            event = OrganizationUpdatedEvent(id=org.id, status = org.status).subject
            payload = {
                "id": str(org.id),
                "name": org.name,
                "slug": org.slug,
                "status": str(org.status),
                "plan": str(org.plan)
        }
            self._log_event(
                aggregate_id= org.id,
                aggregate_type= "ORGANIZATION",
                event_type= event,
                payload = payload
            )
            self.db.commit()
            self.db.refresh(org)

    async def update_organization_status(self,org_id: UUID, status: str ):
        org = self.db.query(Organization).where(Organization.id == str(org_id)).first()
        if org:
            org.status = OrgStatus(status)
            event = OrganizationStatusUpdatedEvent(id=org.id, status=org.status).subject
            if org.status == OrgStatus.ACTIVE:
                payload = {
                    "id": str(org.id),
                    "name": org.name,
                    "slug": org.slug,
                    "status": str(org.status),
                    "plan": str(org.plan)
                }
                self._log_event(
                    aggregate_id=org.id,
                    aggregate_type="ORGANIZATION",
                    event_type=event,
                    payload=payload
                )
                self.db.commit()

            if org.status == OrgStatus.ARCHIVED:
                payload = {
                    "id": str(org.id),
                    "name": org.name,
                    "slug": org.slug,
                    "status": str(org.status),
                    "plan": str(org.plan)
                 }
                self._log_event(
                    aggregate_id=org.id,
                    aggregate_type="ORGANIZATION",
                    event_type=event,
                    payload=payload
                )
                self.db.commit()

        else:
            event = OrganizationNotFoundEvent(id = org.id).subject
            payload = {
                "id": str(org.id),
                "error": "Organization not found",
            }
            self._log_event(aggregate_id=org.id, aggregate_type="ORGANIZATION",event_type=event, payload= payload)
            raise HTTPException(status_code=404, detail=f"Organization not found with id {org_id}")

    async def suspend_organization(self, org_id:UUID):
        org = self.db.query(Organization).where(Organization.id == str(org_id)).first()
        if not org:
            event = OrganizationNotFoundEvent(id=org.id).subject
            payload = {
                "id": str(org.id),
                "error": "Organization not found",
            }
            self._log_event(aggregate_id=org.id, aggregate_type="ORGANIZATION", event_type=event, payload=payload)
            raise HTTPException(status_code=404, detail=f"Organization not found with id {org_id}")

        if org:
            org.status = OrgStatus.SUSPENDED
            event = OrganizationSuspendedEvent(id=org.id, status= org.status).subject
            payload = {
                "id": str(org.id),
                "name": org.name,
                "slug": org.slug,
                "status": str(org.status),
                "plan": str(org.plan)
                }
            self._log_event(aggregate_id=org.id, aggregate_type="ORGANIZATION", event_type=event, payload=payload)
            self.db.commit()

