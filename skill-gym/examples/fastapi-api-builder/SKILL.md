# SKILL.md: fastapi-api-builder

## Identity

- **Skill ID:** `fastapi-api-builder`
- **Version:** `1.0.0`
- **Author:** 4M Labs Research
- **License:** Apache-2.0

## Description

Generate a production-ready FastAPI application from a natural language description of a REST API. The agent must produce valid Python code with proper route definitions, Pydantic models, error handling, and OpenAPI metadata. Outputs are verified by syntax checking, type checking, runtime execution, and a test suite.

## Input Contract

The agent receives:
- A natural language description of the desired API
- Optionally: a database schema or data model reference
- Optionally: existing code files that need integration

## Output Contract

The agent must produce:
- One or more `.py` files containing the FastAPI application
- A `requirements.txt` listing dependencies
- Optionally: a `README.md` with usage instructions

## Verification Criteria

| Check ID            | Type    | Weight | Description                                        |
|---------------------|---------|--------|----------------------------------------------------|
| `python_syntax`     | syntax  | 0.15   | All `.py` files parse without syntax errors          |
| `pydantic_models`   | type    | 0.20   | All request/response models are valid Pydantic       |
| `import_chain`      | runtime | 0.15   | Application imports resolve without errors           |
| `fastapi_app`       | runtime | 0.20   | FastAPI app instance is created and routes are registered |
| `openapi_spec`      | runtime | 0.10   | Generated OpenAPI spec is valid and complete         |
| `test_suite`        | test    | 0.20   | Provided test suite passes against the generated app |

**Total weight: 1.00**

## Difficulty Levels

- **easy:** Single-resource CRUD API (e.g., todo list)
- **medium:** Multi-resource API with relationships and filters
- **hard:** API with auth, pagination, background tasks, webhooks
- **expert:** Microservice with multiple routers, middleware, custom exceptions, database migrations

## Tags

`python`, `fastapi`, `api-design`, `code-generation`, `pydantic`, `rest`, `openapi`
