# OpenAPI Generation Standards

Rules for generating OpenAPI 3.0.3 specifications from source code.

## File Location

Place the generated spec at `docs/openapi.yaml` within the target service directory.

## Required Fields

| Field | Requirement |
|-------|-------------|
| `openapi` | Must be `"3.0.3"` |
| `info.title` | Service name derived from directory or module name |
| `info.version` | `"1.0.0"` or extracted from project metadata |
| `info.description` | Brief service description including workflow and issue key |
| `servers` | At least one entry (localhost for dev) |
| `paths` | All detected REST endpoints |

## Path Object Rules

For each endpoint:

| Field | Rule |
|-------|------|
| `summary` | From function docstring first line, or function name |
| `operationId` | Function name (camelCase) |
| `tags` | Derived from router prefix or module name |
| `parameters` | Path params from URL pattern, query params from function signature |
| `requestBody` | Required for POST/PUT/PATCH; schema from Pydantic model or DTO |
| `responses` | At minimum `200` with description; add `4xx`/`5xx` from error handlers |

## Schema Generation

- Extract from Pydantic `BaseModel` subclasses (Python)
- Extract from DTO/record classes (Java)
- Extract from TypeScript interfaces/classes in `dto/` directories
- Map language types to JSON Schema types:

| Language Type | JSON Schema Type |
|---------------|-----------------|
| `str` / `String` | `string` |
| `int` / `Integer` / `long` | `integer` |
| `float` / `double` / `Decimal` | `number` |
| `bool` / `boolean` | `boolean` |
| `list` / `List` / `Array` | `array` |
| `dict` / `Map` / `object` | `object` |
| `Optional[X]` | `X` with `nullable: true` |
| `datetime` / `Date` | `string` with `format: date-time` |
| `UUID` | `string` with `format: uuid` |

## Required vs Optional

- Fields without a default value and not wrapped in `Optional` are required
- Add them to the `required` array on the schema object
- Fields with defaults or `Optional` are not required

## Validation

Before writing the file, verify:
1. YAML is syntactically valid
2. All `$ref` references resolve to defined schemas
3. All path parameters in the URL appear in the `parameters` list
4. No duplicate `operationId` values
5. Response codes are valid HTTP status codes
