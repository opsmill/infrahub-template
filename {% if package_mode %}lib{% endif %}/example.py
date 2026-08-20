import logging
from collections.abc import Mapping

from infrahub_sdk.schema import MainSchemaTypesAPI


def print_nodes(log: logging.Logger, nodes: Mapping[str, MainSchemaTypesAPI]) -> None:
    for kind in nodes:
        log.info(f"{kind} present.")
