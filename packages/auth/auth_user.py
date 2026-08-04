from typing import Optional, List

from pydantic import BaseModel


class AuthUser(BaseModel):
    id: str
    email: Optional[str] = None
    username: Optional[str] = None
    realm_roles: List[str] = []
    client_roles: List[str] = []

    def has_realm_role(self, role: str) -> bool:
        return role in self.realm_roles

    def has_client_role(self, role: str) -> bool:
        return role in self.client_roles
