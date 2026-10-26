import logging
from collections.abc import Iterable


def print_kinds(log: logging.Logger, kinds: Iterable[str]) -> None:
    for kind in kinds:
        log.info(f"{kind} present.")
