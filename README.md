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

   Initialize speckit in the repository:
   ```bash
   # Install agent commands (replace <agent> with: claude, copilot, cursor-agent, gemini, windsurf, etc.)
   specify init --here --ai <agent> --force
   ```

   The Infrahub extension and preset are preserved automatically — they live in `.specify/extensions/infrahub/` and `.specify/presets/infrahub/`, which `specify init` does not overwrite.

### Workflow

The speckit workflow follows four steps. At each step, the AI agent uses the appropriate Infrahub skill automatically based on the constitution's workflow routing table.

```
/speckit.specify  →  /speckit.plan  →  /speckit.tasks  →  /speckit.implement
```

1. **Specify** — describe what you want to build. The Infrahub preset detects `.infrahub.yml`, verifies Infrahub connectivity (`infrahubctl info`), and routes to the right template:

   | What you're building | Template used | Infrahub Skill |
   |---------------------|---------------|----------------|
   | Data models | `spec-schema-template` | `infrahub:schema-creator` |
   | Infrastructure data | `spec-objects-template` | `infrahub:object-creator` |
   | Validation checks | `spec-check-template` | `infrahub:check-creator` |
   | Design-driven generators | `spec-generator-template` | `infrahub:generator-creator` |
   | Data transforms / configs | `spec-transform-template` | `infrahub:transform-creator` |
   | UI navigation menus | `spec-menu-template` | `infrahub:menu-creator` |

   If your prompt spans multiple artifact types (e.g., "model devices and render configs"), the preset detects this and guides you through one spec at a time in dependency order: **Schema first**, then checks/generators/transforms/menus.

2. **Plan** — the agent creates an implementation plan and validates design artifacts against the relevant Infrahub skills
3. **Tasks** — the plan is broken into discrete, parallelizable tasks annotated with which skill to use
4. **Implement** — the agent executes tasks, invoking the correct Infrahub skill for each one

### Key Files

```
.specify/
├── extensions/
│   └── infrahub/                    # Infrahub extension (templates + constitution)
│       ├── extension.yml            # Extension manifest
│       ├── memory/
│       │   └── constitution.md      # Infrahub conventions and skill routing table
│       └── templates/               # Infrahub-specific spec templates (6 templates)
├── presets/
│   └── infrahub/                    # Infrahub preset (command routing)
│       ├── preset.yml               # Preset manifest
│       └── commands/
│           └── speckit.specify.md   # Routing: .infrahub.yml detection → template selection
├── templates/
│   ├── overrides/                   # Local overrides (empty by default, highest priority)
│   ├── spec-template.md             # Core spec template (fallback for non-Infrahub projects)
│   ├── plan-template.md             # Implementation plan template
│   └── tasks-template.md            # Task breakdown template
└── specs/                           # Your feature specs go here
```

**Template resolution priority**: local overrides → presets → extensions → core templates. To customize an Infrahub template for a specific customer repo, copy it from the extension to `.specify/templates/overrides/`.

### Constitution

The constitution at `.specify/extensions/infrahub/memory/constitution.md` defines the rules every AI agent follows:

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
