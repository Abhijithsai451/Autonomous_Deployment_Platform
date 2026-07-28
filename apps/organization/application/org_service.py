from fastapi import HTTPException
from uuid import UUID

from sqlalchemy.orm import Session

from apps.organization.domain.organization import Organization, OrgStatus
from apps.organization.infrastructure.org_nats_client import org_nats_client as nats


class OrganizationService:
    def __init__(self, db:Session):
        self.db = db

    async def create_organization(self, name: str, slug: str)-> Organization:
        org = Organization(name= name, slug = slug)
        self.db.add(org)
        self.db.commit()
        self.db.refresh(org)
        await nats.publish("OrganizationCreated", {"id": str(org.id), "slug": org.slug})
        return org

    async def update_organization(self, org_id:UUID, updates: dict)-> Organization:
        org = self.db.query(Organization).where(Organization.id == str(org_id)).first()
        if org:
            for k, v in updates.items():
                setattr(org, k, v)
            self.db.commit()
            self.db.refresh(org)
            await nats.publish("OrganizationUpdated", {"id": str(org.id)})
        return org

    async def update_organization_status(self,org_id: UUID, status: str ):
        org = self.db.query(Organization).where(Organization.id == str(org_id)).first()
        if org:
            org.status = OrgStatus(status)
            if org.status == OrgStatus.ACTIVE:
                self.db.commit()
                await nats.publish("OrganizationUpdated", {"id": str(org.id), "status": "ACTIVE"})
            if org.status == OrgStatus.ARCHIVED:
                self.db.commit()
                await nats.publish("OrganizationUpdated", {"id": str(org.id),"status": "ARCHIVED"})
        else:
            await nats.publish("OrganizationNotFound", {"id": str(org.id)})
            raise HTTPException(status_code=404, detail=f"Organization not found with id {org_id}")

    async def suspend_organization(self, org_id:UUID):
        org = self.db.query(Organization).where(Organization.id == str(org_id)).first()
        if not org:
            await nats.publish("OrganizationNotFound", {"id": str(org.id)})
            raise HTTPException(status_code=404, detail="Organization not found")

        if org:
            org.status = OrgStatus.SUSPENDED
            self.db.commit()
            await nats.publish("OrganizationSuspended", {"id": str(org.id), "status": "SUSPENDED"})

