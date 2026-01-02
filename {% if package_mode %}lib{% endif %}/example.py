import logging

from infrahub_sdk.node import InfrahubNode


def print_nodes(log: logging.Logger, nodes: list[InfrahubNode]) -> None:
    """Print all nodes in the provided list."""
    for node in nodes:
        log.info(f"{node} present.")
