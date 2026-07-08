# Organization Service API

## Organizations
- `GET /organizations/{id}`: Fetch tenant details.
- `PATCH /organizations/{id}`: Update tenant configuration.

## Projects
- `POST /projects`: Create a new project.
- `GET /projects`: List projects.
- `GET /projects/{id}`: Get project details.
- `PATCH /projects/{id}`: Update project.
- `DELETE /projects/{id}`: Delete/Archive project.

## Departments
- `POST /departments`: Establish a new functional unit.
- `GET /departments`: List all sub-units for an org.
- `GET /departments/{id}`: Get department details.
- `PATCH /departments/{id}`: Update department configuration.
- `DELETE /departments/{id}`: Archive a department.

## Resource Resolution
- `GET /resolve/department/{resource_id}`: Verify department ownership of a resource.