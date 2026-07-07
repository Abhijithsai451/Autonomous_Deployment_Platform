# Organization Service API

## Organizations
- `GET /organizations/{slug}` - Get organization by slug
- `PATCH /organizations/{id}` - Update tenant settings (e.g., feature toggles)

## Departments
- `POST /departments` - Create a department within an org
- `GET /organizations/{id}/departments` - List departments for a tenant
- `GET /departments/{id}` - Get specific department details
- `PATCH /departments/{id}` - Rename or reconfigure a department

## Integration Hooks
- `GET /resolve/{resource_id}` - Returns the organization_id and department_id owning the requested asset.