import logging

from infrahub_sdk import InfrahubClient

from lib.example import print_nodes


async def run(
    client: InfrahubClient,
    log: logging.Logger,
    branch: str,
) -> None:
    log.info(f"Running example script on {branch}...")
    nodes = await client.schema.all()
    print_nodes(log, nodes)
