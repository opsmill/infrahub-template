import logging

from infrahub_sdk import InfrahubClient

from lib.example import print_nodes


async def run(
    client: InfrahubClient,
    log: logging.Logger,
    branch: str,
) -> None:
    """Print all nodes in the current branch."""
    log.info(f"Running example script on {branch}...")
    nodes = await client.schema.all()
    print_nodes(log, nodes)
