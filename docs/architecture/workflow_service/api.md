# Workflow Service API

## Blueprints
- `POST /blueprints`: Register a new workflow definition.
- `GET /blueprints`: List blueprints.
- `PATCH /blueprints/{id}`: Update blueprint metadata.

## Execution APIs
- `POST /instances`: Trigger a new workflow instance.
- `GET /instances`: List workflow instances.
- `GET /instances/{id}`: Get instance status.
- `POST /instances/{id}/pause`: Pause execution.
- `POST /instances/{id}/resume`: Resume execution.
- `POST /instances/{id}/cancel`: Cancel execution.
- `POST /instances/{id}/retry`: Retry failed instance.
- `POST /instances/{id}/signal`: Signal external data into workflow.

## Task APIs
- `GET /tasks/{id}`: Get task details.
- `GET /instances/{id}/tasks`: List tasks for an instance.
- `POST /tasks/{id}/retry`: Retry specific task.
- `POST /tasks/{id}/cancel`: Cancel specific task.

## Timeline
- `GET /instances/{id}/timeline`: Fetch execution history.