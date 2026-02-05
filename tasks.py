import os
import shutil
import tempfile
from pathlib import Path

import httpx
from invoke import Context, task

# If no version is indicated, we will take the latest
VERSION = os.getenv("INFRAHUB_IMAGE_VER", None)
CURRENT_DIRECTORY = Path(__file__).resolve()
MAIN_DIRECTORY_PATH = Path(__file__).parent


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

    with compose_file.open("w", encoding="utf-8") as f:
        f.write(response.content.decode())

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
    exec_cmd = "mypy --show-error-codes infrahub_sdk"
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


@task(name="schema-library-get")
def get_schema_library(ctx: Context) -> None:
    """
    Download base and extensions folders from the opsmill/schema-library repository.

    Creates a schema-library folder and copies the base and extensions folders
    from GitHub, overwriting any existing content.
    """
    schema_library_dir = MAIN_DIRECTORY_PATH / "schema-library"
    repo_url = "https://github.com/opsmill/schema-library.git"

    # Create schema-library directory if it doesn't exist
    schema_library_dir.mkdir(exist_ok=True)

    # Clone repo to temp directory and copy folders
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        repo_path = tmp_path / "repo"

        print("Cloning schema-library repository...")
        ctx.run(f"git clone --depth 1 {repo_url} {repo_path}", hide=True)

        # Copy base folder (overwrite if exists)
        base_src = repo_path / "base"
        base_dst = schema_library_dir / "base"
        if base_dst.exists():
            shutil.rmtree(base_dst)
        shutil.copytree(base_src, base_dst)
        print(f"Copied 'base' to {base_dst}")

        # Copy extensions folder (overwrite if exists)
        extensions_src = repo_path / "extensions"
        extensions_dst = schema_library_dir / "extensions"
        if extensions_dst.exists():
            shutil.rmtree(extensions_dst)
        shutil.copytree(extensions_src, extensions_dst)
        print(f"Copied 'extensions' to {extensions_dst}")

    print(f"Schema library updated at {schema_library_dir}")


@task(name="schema-library-bootstrap")
def bootstrap_schema_library(ctx: Context) -> None:
    """
    Bootstrap schemas from the schema-library into the schemas folder.

    Copies base and location-minimal schemas, then loads them into InfraHub.
    """
    schema_library_dir = MAIN_DIRECTORY_PATH / "schema-library"
    schemas_dir = MAIN_DIRECTORY_PATH / "schemas"

    # Source paths
    base_src = schema_library_dir / "base"
    location_minimal_src = schema_library_dir / "extensions" / "location_minimal"

    # Destination paths
    base_dst = schemas_dir / "base"
    location_minimal_dst = schemas_dir / "location_minimal"

    # Copy base folder (overwrite if exists)
    if base_dst.exists():
        shutil.rmtree(base_dst)
    shutil.copytree(base_src, base_dst)
    print(f"Copied 'base' to {base_dst}")

    # Copy location-minimal folder (overwrite if exists)
    if location_minimal_dst.exists():
        shutil.rmtree(location_minimal_dst)
    shutil.copytree(location_minimal_src, location_minimal_dst)
    print(f"Copied 'location_minimal' to {location_minimal_dst}")

    # Load schemas into InfraHub
    print("Loading schemas into InfraHub...")
    ctx.run("infrahubctl schema load schemas/base", pty=True)
    ctx.run("infrahubctl schema load schemas/location_minimal", pty=True)

    print("Schema bootstrap complete!")
