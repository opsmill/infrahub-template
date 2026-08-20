# Infrahub Repository

Welcome! This repository was initialized via the `uv tool run --from 'copier' copier copy https://github.com/opsmill/infrahub-template.git <directory>` command. That bootstraps a repository for use with some example data.

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

  bootstrap               Bring up a stack that loads this repository itself.
  destroy                 Stop and remove containers, networks, and volumes.
  download-compose-file   Download docker-compose.yml from InfraHub if missing or override is True.
  load-schema             Load schemas into InfraHub using infrahubctl.
  restart                 Restart all services or a specific one using docker-compose.
  start                   Start the services using docker-compose in detached mode.
  stop                    Stop containers and remove networks.
  test                    Run tests using pytest.
```

`invoke start` brings up an empty Infrahub.

To get a **populated** one in a single command, use `invoke bootstrap`:

```bash
invoke bootstrap
```

It publishes the current commit as a Git origin the containers can reach, starts the stack,
registers that origin with Infrahub as a repository, and waits for the import to finish.
Infrahub then reads `.infrahub.yml` and loads your schemas — and your objects and menus, if
this repository has them — **itself**. That is the same mechanism Infrahub runs in
production, rather than pushing files in from the host the way the `load-*` tasks do.

Two things to know about it:

- **Only committed history is loaded.** Infrahub clones a Git origin, so an uncommitted edit
  is invisible to it. `bootstrap` warns when your working tree is dirty.
- **It loads onto the default branch.** That is what a bootstrap is for — an empty instance
  has no data to migrate and nothing to preview. Once the instance has data, load a schema
  onto a branch and merge it through a proposed change instead.

Re-running is safe and fast: the repository is registered once, and later runs publish the
new commit and wait for Infrahub's scheduled sync (once a minute) to pick it up.

`docker-compose.override.yml` mounts the published origin into the task workers, which is
what makes the repository location resolvable from inside the containers. docker compose
merges that file in on its own, so no extra flags are needed.

The `load-schema`, `load-menu` and `load-objects` tasks are still there, and remain the
faster loop while you are iterating on a schema you have not committed yet.

## Spec-Driven Development

This repository includes [GitHub Spec Kit](https://github.com/github/spec-kit) pre-configured with Infrahub best practices. Spec-driven development uses natural-language specifications as the primary development artifact — your AI agent generates plans, tasks, and working code from those specs.

Infrahub skills give your AI agent domain-specific knowledge about Infrahub's schema design, data modeling, validation checks, generators, transforms, and more. When installed, the agent automatically uses the right skill at each workflow step — for example, invoking the schema-creator skill when designing data models, or the check-creator skill when writing validation logic. Without skills installed, the agent falls back to the general conventions in the constitution, but loses the detailed guidance that produces correct Infrahub artifacts on the first try.

### Prerequisites

1. **Install the Infrahub skills** for your AI agent:

   **NPX installer** (recommended — auto-detects your AI tool):
   ```bash
   npx skills add opsmill/infrahub-skills
   ```


2. **Install the Specify CLI and agent commands**:

   Install the CLI:
   ```bash
   uv tool install specify-cli --from git+https://github.com/github/spec-kit.git
   ```

   Initialize speckit in the repository:
   ```bash
   # Replace <integration> with: claude, copilot, cursor-agent, gemini, windsurf, etc.
   specify init --here --integration <integration> --force
   ```

3. **Add the Infrahub speckit preset**:

   ```bash
   specify preset add --from https://github.com/opsmill/infrahub-speckit/archive/refs/heads/main.zip
   ```

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


## Tests

By default there are some integration tests that will spin up Infrahub and its dependencies in docker and load the repository and schema. This can be run using the following:

```bash
uv sync --extras dev
pytest tests/integration
```

The Infrahub version under test defaults to the installed `infrahub-testcontainers` version. To pin a different one, set the variable the SDK actually reads:
`export INFRAHUB_TESTING_IMAGE_VER=1.11.0`.
