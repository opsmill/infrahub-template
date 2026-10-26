import logging

from infrahub_sdk import InfrahubClient


async def run(client: InfrahubClient, log: logging.Logger, branch: str) -> None:
    log.info(f"Running example script on {branch}...")
    schemas = await client.schema.all(branch=branch)
    for kind in schemas:
        log.info(f"{kind} present.")
