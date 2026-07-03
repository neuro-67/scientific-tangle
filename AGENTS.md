# AGENTS.md

This file is the entry point for LLM agents working in this repository.
Read the relevant documentation before creating files, editing code, changing architecture, or running verification.

## Global repository context

Start with these files for any task:

- [README.md](README.md) — project overview and quick start.
- [docs/README.md](docs/README.md) — documentation index.
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — system-level architecture.
- [docs/STACK.md](docs/STACK.md) — technology stack.
- [docs/ROADMAP.md](docs/ROADMAP.md) — planned work and milestones.

Domain and research-specific documentation:

- [docs/ONTOLOGY.md](docs/ONTOLOGY.md) — ontology and knowledge graph concepts.
- [docs/NLP_PIPELINE.md](docs/NLP_PIPELINE.md) — NLP pipeline design.

## Backend instructions

Before changing anything under `backend/`, read:

- [docs/backend/ARCHITECTURE.md](docs/backend/ARCHITECTURE.md) — backend architecture rules: DDD, vertical slices, dependency rule, layers, events, repositories, infrastructure.
- [docs/backend/CODE_STYLE.md](docs/backend/CODE_STYLE.md) — Python code style, naming, slice file contracts, domain object rules, errors, typing, async, tests, and self-review checklist.

Backend agents MUST follow these documents as normative instructions.

## Frontend instructions

Before changing anything under `frontend/`, read:

- [docs/frontend/AGENTS.md](docs/frontend/AGENTS.md) — frontend-specific agent rules and project conventions.
- [docs/frontend/SKILL.md](docs/frontend/SKILL.md) — Feature-Sliced Design (FSD) architecture guide and placement rules.
- [docs/frontend/ARCHITECTURE.md](docs/frontend/ARCHITECTURE.md) — frontend architecture overview.
- [docs/frontend/CODE_STYLE.md](docs/frontend/CODE_STYLE.md) — frontend code style rules.

Frontend reference materials:

- [docs/frontend/references/asset-handling.md](docs/frontend/references/asset-handling.md)
- [docs/frontend/references/cross-import-patterns.md](docs/frontend/references/cross-import-patterns.md)
- [docs/frontend/references/excessive-entities.md](docs/frontend/references/excessive-entities.md)
- [docs/frontend/references/framework-integration.md](docs/frontend/references/framework-integration.md)
- [docs/frontend/references/layer-structure.md](docs/frontend/references/layer-structure.md)
- [docs/frontend/references/migration-guide.md](docs/frontend/references/migration-guide.md)
- [docs/frontend/references/practical-examples.md](docs/frontend/references/practical-examples.md)

Frontend agents MUST follow FSD and the project-specific conventions from `docs/frontend/AGENTS.md`.

## Area-specific guidance

- For backend tasks, prioritize backend architecture and code style documents over generic repository docs.
- For frontend tasks, prioritize `docs/frontend/AGENTS.md`, then `docs/frontend/SKILL.md`, then frontend architecture/code-style docs.
- For NLP, ontology, graph, extraction, or research-data tasks, read `docs/NLP_PIPELINE.md` and `docs/ONTOLOGY.md` first.
- For infrastructure/deployment tasks, read `docs/STACK.md` and `docs/ARCHITECTURE.md` first.

## Agent behavior

- Do not make speculative abstractions or create unused files.
- Do not bypass documented public APIs or architectural boundaries.
- Keep documentation in `/docs` accurate when code changes affect documented behavior.
- Prefer small, focused changes that match the repository conventions.
- Run the relevant formatter, linter, type checker, and tests before declaring implementation work complete when such commands are available.
