# Workflow Service API

## Blueprints
- `POST /blueprints` - Create template
- `GET /blueprints` - List available processes

## Execution
- `POST /instances` - Trigger a workflow
- `GET /instances/{id}` - View live status
- `POST /instances/{id}/signal` - Resume/Signal workflow
- `DELETE /instances/{id}` - Cancel/Terminate

## Monitoring
- `GET /instances?status={status}` - List active/failed workflows