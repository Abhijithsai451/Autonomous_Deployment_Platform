from fastapi import HTTPException
from uuid import UUID

from sqlalchemy.orm import Session

from apps.organization.domain.organization import Organization, OrgStatus
from infrastructure.nats.nats_client import EventBus


class OrganizationService:
    def __init__(self, db:Session):
        self.db = db

    async def create_organization(self, name: str, slug: str, plan: str)-> Organization:
        org = Organization(name= name, slug = slug, plan= plan)
        self.db.add(org)
        self.db.commit()
        self.db.refresh(org)
        await EventBus.publish("OrganizationCreated", {"id": str(org.id), "slug": org.slug})
        return org

    async def update_organization(self, org_id:UUID, updates: dict)-> Organization:
        org = self.db.query(Organization).where(Organization.id == str(org_id)).first()
        if org:
            for k, v in updates.items():
                setattr(org, k, v)
            self.db.commit()
            await EventBus.publish("OrganizationUpdated", {"id": str(org.id)})
        return org

    async def update_organization_status(self,org_id: UUID, status: str ):
        org = self.db.query(Organization).where(Organization.id == str(org_id)).first()
        if org:
            org.status = OrgStatus(status)
            if org.status == OrgStatus.ACTIVE:
                await EventBus.publish("OrganizationUpdated", {"id": str(org.id), "status": "ACTIVE"})
            if org.status == OrgStatus.ARCHIVED:
                await EventBus.publish("OrganizationUpdated", {"id": str(org.id),"status": "ARCHIVED"})
        else:
            await EventBus.publish("OrganizationNotFound", {"id": str(org.id)})
            raise HTTPException(status_code=404, detail=f"Organization not found with id {org_id}")

    async def suspend_organization(self, org_id:UUID)-> Organization:
        org = self.db.query(Organization).where(Organization.id == str(org_id)).first()
        if not org:
            await EventBus.publish("OrganizationNotFound", {"id": str(org.id)})
            raise HTTPException(status_code=404, detail="Organization not found")

        org.status = OrgStatus.SUSPENDED
        if org.status == OrgStatus.ACTIVE:
            await EventBus.publish("OrganizationSuspended", {"id": str(org.id), "status": "SUSPENDED"})




