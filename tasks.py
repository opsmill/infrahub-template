import os
import shutil
import tempfile
import time
import tomllib
from pathlib import Path

import httpx
from invoke import Context, task

# If no version is indicated, we will take the latest
VERSION = os.getenv("INFRAHUB_IMAGE_VER", None)
CURRENT_DIRECTORY = Path(__file__).resolve()
MAIN_DIRECTORY_PATH = Path(__file__).parent

# --- invoke bootstrap --------------------------------------------------------
# Infrahub's task workers clone a repository themselves, so a path on the host is
# not a location they can reach. `invoke bootstrap` publishes the current commit
# as a bare repository under ORIGIN_DIR, which docker-compose.override.yml mounts
# at ORIGIN_MOUNT inside the workers.
ORIGIN_DIR = Path("./.origin")
ORIGIN_MOUNT = "/remote"


@task
def start(context: Context) -> None:
    """
    Start the services using docker-compose in detached mode.
    """
    download_compose_file(context, override=False)
    context.run("docker compose up -d")


@task
def destroy(context: Context) -> None:
    """
    Stop and remove containers, networks, and volumes.
    """
    download_compose_file(context, override=False)
    context.run("docker compose down -v")


@task
def stop(context: Context) -> None:
    """
    Stop containers and remove networks.
    """
    download_compose_file(context, override=False)
    context.run("docker compose down")


@task(help={"component": "Optional name of a specific service to restart."})
def restart(context: Context, component: str = "") -> None:
    """
    Restart all services or a specific one using docker-compose.
    """
    download_compose_file(context, override=False)
    if component:
        context.run(f"docker compose restart {component}")
        return

    context.run("docker compose restart")


def _project_name() -> str:
    """This repository's name, as it was written into pyproject.toml."""
    config = tomllib.loads((MAIN_DIRECTORY_PATH / "pyproject.toml").read_text(encoding="utf-8"))
    return str(config["project"]["name"])


def _api_config() -> tuple[str, str]:
    """Server address and API token, read from the file infrahubctl itself reads."""
    config = tomllib.loads((MAIN_DIRECTORY_PATH / "infrahubctl.toml").read_text(encoding="utf-8"))
    return config.get("server_address", "http://localhost:8000").rstrip("/"), config.get("api_token", "")


def _graphql(query: str) -> dict:
    address, token = _api_config()
    response = httpx.post(
        f"{address}/graphql",
        json={"query": query},
        headers={"X-INFRAHUB-KEY": token},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if errors := payload.get("errors"):
        msg = f"GraphQL query failed: {errors}"
        raise RuntimeError(msg)
    return payload["data"]


def _wait_for_api(timeout: int = 300) -> None:
    """Block until the API answers.

    `docker compose up -d` returns once the containers report started, which is
    well before the server serves its first request.
    """
    address, _ = _api_config()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if httpx.get(f"{address}/api/config", timeout=5).status_code == httpx.codes.OK:
                return
        except httpx.HTTPError:
            pass
        time.sleep(5)

    msg = f"Infrahub did not answer at {address} within {timeout}s"
    raise RuntimeError(msg)


def _repository(name: str) -> dict | None:
    """The repository's tracked commit and status, or None if it is not registered."""
    query = f"""
    query {{
      CoreRepository(name__value: "{name}") {{
        edges {{
          node {{
            commit {{ value }}
            sync_status {{ value }}
            operational_status {{ value }}
          }}
        }}
      }}
    }}
    """
    edges = _graphql(query)["CoreRepository"]["edges"]
    return edges[0]["node"] if edges else None


def _wait_for_import(name: str, commit: str, timeout: int, stale_status: str | None) -> None:
    """Block until Infrahub has imported `commit`.

    The import runs asynchronously once the repository is registered, and a later
    commit is picked up by a scheduled sync that runs every minute — so the same
    wait covers a first bootstrap and a re-run against a stack already up.

    Waiting on the commit rather than on the status alone is what makes a re-run
    meaningful: a repository left over from the previous run already reads
    `in-sync`, at the commit from last time.
    """
    deadline = time.monotonic() + timeout
    node: dict | None = None
    while time.monotonic() < deadline:
        node = _repository(name)
        if node:
            sync_status = node["sync_status"]["value"]
            if sync_status == "in-sync" and node["commit"]["value"] == commit:
                return
            # An import error carried over from a previous run is not this run's
            # verdict, so only a transition into the error state ends the wait.
            if sync_status == "error-import" and sync_status != stale_status:
                msg = (
                    f"Infrahub failed to import {name}. The error is on the repository in the UI, "
                    f"and in `docker compose logs task-worker`."
                )
                raise RuntimeError(msg)
        time.sleep(5)

    observed = "not registered" if node is None else f"{node['sync_status']['value']}, commit {node['commit']['value']}"
    msg = f"Infrahub did not import {name} at {commit[:8]} within {timeout}s (last seen: {observed})"
    raise RuntimeError(msg)


@task(
    help={
        "name": "Name to register the repository under. Defaults to the project name.",
        "ref": "Git ref for Infrahub to track. Defaults to the checked-out branch.",
        "timeout": "Seconds to wait for the repository import to finish.",
    }
)
def bootstrap(ctx: Context, name: str = "", ref: str = "", timeout: int = 600) -> None:
    """
    Bring up a stack that loads this repository itself.

    Publishes the current commit as a Git origin the containers can reach, starts
    them, registers it with Infrahub as a repository, and waits for the import.
    Infrahub reads .infrahub.yml and loads the schemas — and the objects and menus,
    if this repository has them — on its own, so none of the load-* tasks are
    needed afterwards.

    This is the same mechanism Infrahub runs in production, rather than pushing
    files in from the host, which is what the load-* tasks do.

    Two things to know:

    - Infrahub clones a Git origin, so it only ever sees COMMITTED history. An
      uncommitted edit is not loaded, and this task warns when the tree is dirty.
    - It loads onto the default branch. That is what a bootstrap is for: an empty
      instance has no data to migrate and nothing to preview. Once the instance
      has data, load a schema onto a branch and merge it through a proposed
      change instead.

    Re-running is safe: the repository is registered once, and every later run
    publishes the new commit and waits for Infrahub to pick it up.
    """
    name = name or _project_name()
    ref = ref or ctx.run("git rev-parse --abbrev-ref HEAD", hide=True).stdout.strip()
    commit = ctx.run("git rev-parse HEAD", hide=True).stdout.strip()

    if ctx.run("git status --porcelain", hide=True).stdout.strip():
        print("! Uncommitted changes are not published — commit them to have Infrahub load them.\n", flush=True)

    origin = ORIGIN_DIR / f"{name}.git"
    if not (origin / "HEAD").exists():
        ctx.run(f"git init --bare --quiet {origin}")
    print(f"Publishing {commit[:8]} to {origin} as {ref}", flush=True)
    ctx.run(f"git push --force --quiet {origin} HEAD:refs/heads/{ref}")
    # Point the origin's HEAD at the ref Infrahub tracks, so a plain clone of it
    # checks out the same branch rather than looking empty.
    ctx.run(f"git --git-dir={origin} symbolic-ref HEAD refs/heads/{ref}")

    start(ctx)
    _wait_for_api()

    # Doubles as the existence check: `repository add` fails on a name that is
    # already taken, and the pre-existing status tells the import wait which
    # error state is left over from a previous run.
    existing = _repository(name)
    location = f"file://{ORIGIN_MOUNT}/{name}.git"
    if existing is None:
        print(f"Registering {name} at {location} (ref {ref})", flush=True)
        ctx.run(f"infrahubctl repository add {name} {location} --ref {ref}", pty=True)
    else:
        print(f"{name} is already registered; waiting for it to pick up {commit[:8]}", flush=True)

    _wait_for_import(
        name=name,
        commit=commit,
        timeout=timeout,
        stale_status=existing["sync_status"]["value"] if existing else None,
    )

    address, _ = _api_config()
    print(f"\nBootstrapped {name} at {commit[:8]}. Infrahub is at {address}", flush=True)


@task
def load_menu(ctx: Context) -> None:
    """
    Load schemas into InfraHub using infrahubctl.
    """
    ctx.run("infrahubctl menu load menus/", pty=True)


@task
def load_schema(ctx: Context) -> None:
    """
    Load schemas into InfraHub using infrahubctl.
    """
    ctx.run("infrahubctl schema load schemas")


@task
def load_objects(ctx: Context) -> None:
    """
    Load objects into InfraHub using infrahubctl.
    """
    ctx.run("infrahubctl object load objects")


@task
def test(ctx: Context) -> None:
    """
    Run tests using pytest.
    """
    ctx.run("pytest tests")


@task(help={"override": "Redownload the compose file even if it already exists."})
def download_compose_file(context: Context, override: bool = False) -> Path:  # noqa: ARG001
    """
    Download docker-compose.yml from InfraHub if missing or override is True.
    """
    compose_file = Path("./docker-compose.yml")
    compose_url = os.getenv("INFRAHUB_COMPOSE_URL", "https://infrahub.opsmill.io")

    if compose_file.exists() and not override:
        return compose_file

    response = httpx.get(compose_url)
    response.raise_for_status()

    compose_file.write_text(response.content.decode(), encoding="utf-8")

    return compose_file


@task(name="format")
def format_python(ctx: Context) -> None:
    """Run RUFF to format all Python files."""

    exec_cmds = ["ruff format .", "ruff check . --fix"]
    with ctx.cd(MAIN_DIRECTORY_PATH):
        for cmd in exec_cmds:
            ctx.run(cmd, pty=True)


@task
def lint_yaml(ctx: Context) -> None:
    """Run Linter to check all Python files."""
    print(" - Check code with yamllint")
    exec_cmd = "yamllint ."
    with ctx.cd(MAIN_DIRECTORY_PATH):
        ctx.run(exec_cmd, pty=True)


@task
def lint_mypy(ctx: Context) -> None:
    """Run Linter to check all Python files."""
    print(" - Check code with mypy")
    # Only the paths this repository actually has: which of lib/, scripts/ and
    # tests/ exist depends on the features it was generated with, and mypy fails
    # outright on a path that is not there.
    candidates = ["tasks.py", "lib", "scripts", "tests"]
    targets = " ".join(p for p in candidates if (MAIN_DIRECTORY_PATH / p).exists())
    exec_cmd = f"mypy --show-error-codes {targets}"
    with ctx.cd(MAIN_DIRECTORY_PATH):
        ctx.run(exec_cmd, pty=True)


@task
def lint_ruff(ctx: Context) -> None:
    """Run Linter to check all Python files."""
    print(" - Check code with ruff")
    exec_cmd = "ruff check ."
    with ctx.cd(MAIN_DIRECTORY_PATH):
        ctx.run(exec_cmd, pty=True)


@task(name="lint")
def lint_all(ctx: Context) -> None:
    """Run all linters."""
    lint_yaml(ctx)
    lint_ruff(ctx)
    lint_mypy(ctx)


def _overwrite_copy(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


@task(name="schema-library-get")
def get_schema_library(ctx: Context) -> None:
    """
    Download base and extensions folders from the opsmill/schema-library repository
    into schema-library/, then copy a subset into schemas/.
    """
    repo_url: str = "https://github.com/opsmill/schema-library.git"
    schema_library_dir: Path = MAIN_DIRECTORY_PATH / "schema-library"
    schemas_dir: Path = MAIN_DIRECTORY_PATH / "schemas"

    schema_library_dir.mkdir(exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp_dir:
        repo_path: Path = Path(tmp_dir) / "repo"
        print("Cloning schema-library repository...")
        ctx.run(f"git clone --depth 1 {repo_url} {repo_path}", hide=True)

        _overwrite_copy(repo_path / "base", schema_library_dir / "base")
        _overwrite_copy(repo_path / "extensions", schema_library_dir / "extensions")

    print(f"Schema library updated at {schema_library_dir}")

    _overwrite_copy(schema_library_dir / "base", schemas_dir / "base")
    _overwrite_copy(schema_library_dir / "extensions" / "location_minimal", schemas_dir / "location_minimal")

    print(f"Schemas updated at {schemas_dir}")
