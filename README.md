# Infrahub Repository

Welcome! This repository was initialized via the `uv tool run --from 'infrahub-sdk[ctl]' infrahubctl repository init <directory>` command. That bootstraps a repository for use with some example data.

## Installation

Running `uv sync` will install all the main dependencies you need to interact with this repository.

```bash
uv sync --all-packages
source .venv/bin/activate
```

## Starting Infrahub

Included in the repository are a set of helper commands to get Infrahub up and running using `invoke`.

```bash
Available tasks:

  destroy                 Stop and remove containers, networks, and volumes.
  download-compose-file   Download docker-compose.yml from InfraHub if missing or override is True.
  load-schema             Load schemas into InfraHub using infrahubctl.
  restart                 Restart all services or a specific one using docker-compose.
  start                   Start the services using docker-compose in detached mode.
  stop                    Stop containers and remove networks.
  test                    Run tests using pytest.
```

To start infrahub simply use `invoke start`

## Spec-Driven Development

This repository includes [GitHub Spec Kit](https://github.com/github/spec-kit) pre-configured with Infrahub best practices. Spec-driven development uses natural-language specifications as the primary development artifact — your AI agent generates plans, tasks, and working code from those specs.

Infrahub skills give your AI agent domain-specific knowledge about Infrahub's schema design, data modeling, validation checks, generators, transforms, and more. When installed, the agent automatically uses the right skill at each workflow step — for example, invoking the schema-creator skill when designing data models, or the check-creator skill when writing validation logic. Without skills installed, the agent falls back to the general conventions in the constitution, but loses the detailed guidance that produces correct Infrahub artifacts on the first try.

### Prerequisites

1. **Install the Infrahub skills** for your AI agent:

   **Claude Code** (recommended):
   ```bash
   /plugin marketplace add opsmill/claude-marketplace
   /plugin install infrahub@opsmill
   ```

   **Any other AI tool** (Copilot, Cursor, Windsurf, etc.):
   ```bash
   git clone https://github.com/opsmill/infrahub-skills.git
   cp -r infrahub-skills/skills ./skills/
   rm -rf infrahub-skills
   ```

2. **Install the Specify CLI and agent commands**:

   Install the CLI:
   ```bash
   uv tool install specify-cli --from git+https://github.com/github/spec-kit.git
   ```

   Then install the slash commands for your AI agent. This adds agent-specific command files (e.g., `.claude/commands/` for Claude, `.github/prompts/` for Copilot) without overwriting the Infrahub-customized `.specify/` directory:

   ```bash
   # Install agent commands (replace <agent> with: claude, copilot, cursor-agent, gemini, windsurf, etc.)
   specify init --here --ai <agent> --force

   # Restore Infrahub customizations that specify init overwrites
   git checkout -- .specify/
   ```

   This gives you the best of both worlds — speckit slash commands for your AI tool, plus the Infrahub-specific constitution and workflow templates.

### Workflow

The speckit workflow follows four steps. At each step, the AI agent uses the appropriate Infrahub skill automatically based on the constitution's workflow routing table.

```
/speckit.specify  →  /speckit.plan  →  /speckit.tasks  →  /speckit.implement
```

1. **Specify** — describe what you want to build. The agent selects the right workflow template:

   | What you're building | Template used |
   |---------------------|---------------|
   | Data models | `spec-schema-template.md` |
   | Infrastructure data | `spec-objects-template.md` |
   | Validation checks | `spec-check-template.md` |
   | Design-driven generators | `spec-generator-template.md` |
   | Data transforms / configs | `spec-transform-template.md` |
   | UI navigation menus | `spec-menu-template.md` |

2. **Plan** — the agent creates an implementation plan and validates design artifacts against the relevant Infrahub skills
3. **Tasks** — the plan is broken into discrete, parallelizable tasks annotated with which skill to use
4. **Implement** — the agent executes tasks, invoking the correct Infrahub skill for each one

### Key Files

```
.specify/
├── memory/constitution.md       # Infrahub conventions and skill routing table
├── specs/                       # Your feature specs go here
└── templates/
    ├── overrides/               # Infrahub workflow-specific spec templates
    ├── plan-template.md         # Implementation plan template (with skill validation gate)
    ├── tasks-template.md        # Task breakdown template (with skill annotations)
    └── spec-template.md         # Generic spec template (with skill selection)
```

### Constitution

The constitution at `.specify/memory/constitution.md` defines the rules every AI agent follows:

- **Schema-First Development** — naming conventions, `human_friendly_id`, generics, relationships
- **Validate Before Load** — always run `infrahubctl schema check`
- **Skill-Driven Workflows** — routing table mapping tasks to Infrahub skills
- **Schema Library First** — check `opsmill/schema-library` before creating custom schemas
- **Code Quality Standards** — Python 3.11+, ruff, mypy, yamllint

## Tests

By default there are some integration tests that will spin up Infrahub and its dependencies in docker and load the repository and schema. This can be run using the following:

```bash
uv sync --extras dev
pytest tests/integration
```

To change the version of infrahub being used you can use an environment variable: `export INFRAHUB_TESTING_IMAGE_VERSION=1.3.0`.
