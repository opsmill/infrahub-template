# Infrahub Repository Constitution

## Core Principles

### I. Schema-First Development

All infrastructure modeling starts with schema design. Conventions:

- PascalCase for node and generic `kind` names (e.g., `DcimDevice`, `IpamIPAddress`)
- snake_case for attribute and relationship names
- Always include `human_friendly_id` on nodes
- Set `identifier` on bidirectional relationships
- Use generics for shared attributes across multiple node types
- Use `InfraGenericDevice` or similar generics for device hierarchies

### II. Validate Before Load

Always run `infrahubctl schema check` before loading schemas into Infrahub. Never skip validation — schema errors caught early prevent data corruption.

### III. Skill-Driven Workflows

Use the appropriate Infrahub skill for each task type. The workflow routing table below maps tasks to skills. If the AI agent has Infrahub skills installed, invoke them directly. If not, follow the patterns and conventions described in the constitution and templates.

### IV. Schema Library First

Before creating custom schemas, check `opsmill/schema-library` for standard models. Use `invoke schema-library-get` to download and integrate. Extend standard models via generics rather than duplicating them.

### V. Code Quality Standards

- Python 3.11+ required
- Ruff for formatting and linting (line length: 120, max complexity: 17)
- Mypy for type checking (strict mode)
- yamllint for YAML files (max line length: 140)
- All code must pass `invoke lint` before commit

## Workflow Routing Table

| Task | Skill | Key Files |
|------|-------|-----------|
| Design or modify data models | `infrahub:schema-creator` | `schemas/*.yml` |
| Populate infrastructure data | `infrahub:object-creator` | `objects/*.yml` |
| Build validation checks | `infrahub:check-creator` | `checks/*.py`, `.infrahub.yml` |
| Create design-driven generators | `infrahub:generator-creator` | `generators/*.py`, `queries/*.gql`, `.infrahub.yml` |
| Build data transforms or configs | `infrahub:transform-creator` | `transforms/*.py`, `transforms/templates/*.j2`, `queries/*.gql`, `.infrahub.yml` |
| Customize UI navigation | `infrahub:menu-creator` | `menus/*.yml` |

## Cross-Cutting Conventions

- **GraphQL queries** — all checks, generators, and transforms require GraphQL queries in `queries/*.gql`. Follow the patterns in the `infrahub:schema-creator` and shared `common/graphql-queries.md` reference.
- **`.infrahub.yml` manifest** — checks, generators, transforms, and artifacts must be registered here. Loading order: schemas, queries, objects, Python, Jinja2, artifacts.

## Development Workflow

1. **Check schema library** — run `invoke schema-library-get` and check for existing standard models before creating custom schemas
2. **Schema first** — define or update the data model
3. **Validate** — run `infrahubctl schema check`
4. **Load** — run `invoke load-schema`
5. **Populate** — create object data files and run `invoke load-objects`
6. **Extend** — add checks, generators, transforms, menus as needed
7. **Test** — run `invoke test` for integration tests
8. **Lint** — run `invoke lint` before committing

## Governance

Constitution principles are enforced in all specs and plans. Deviations must be documented in the Complexity Tracking table of the implementation plan with justification.

**Version**: 1.0.0 | **Ratified**: 2026-03-17
