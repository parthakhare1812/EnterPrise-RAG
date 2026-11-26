import logging
import time
from contextlib import contextmanager


logger = logging.getLogger("enterprise_rag")

_initialized = False


class LocalSpan:
    def __init__(self, name: str):
        self.name = name
        self.attributes = {}

    def set_attribute(self, key: str, value) -> None:
        self.attributes[key] = value

    def record_exception(self, error: Exception) -> None:
        logger.exception(
            "Exception during operation %s: %s",
            self.name,
            error
        )

    def set_status(self, status) -> None:
        self.attributes["status"] = str(status)


def initialize_observability():
    global _initialized

    if _initialized:
        return

    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )

    logger.info("Local observability initialized")
    _initialized = True


@contextmanager
def trace_operation(name: str, attributes: dict | None = None):
    start = time.perf_counter()
    span = LocalSpan(name)

    if attributes:
        for key, value in attributes.items():
            span.set_attribute(key, value)

    logger.info("Starting operation: %s", name)

    try:
        yield span
    except Exception as error:
        span.record_exception(error)
        span.set_status("ERROR")
        raise
    finally:
        duration = time.perf_counter() - start
        span.set_attribute("operation.duration_seconds", duration)

        logger.info(
            "Operation %s completed in %.3f seconds",
            name,
            duration
        )


def shutdown_observability():
    logger.info("Local observability shutdown")