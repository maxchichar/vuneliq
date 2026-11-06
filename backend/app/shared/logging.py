import logging
import sys


def setup_logging(log_level: str = "INFO") -> None:
    """Configures structured root logging with timestamps and module namespaces."""
    level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )


def get_module_logger(module_name: str) -> logging.Logger:
    """
    Returns a logger namespaced by module.
    Example: get_module_logger("donations") -> logs as '[vuneliq.donations]'
    """
    return logging.getLogger(f"vuneliq.{module_name}")
