"""
Structured JSON logger for production-ready logging.
Outputs logs in JSON format compatible with monitoring tools like ELK, Datadog, etc.
"""
import logging
import sys
from datetime import datetime
from typing import Any, Dict
from pythonjsonlogger import jsonlogger
from ..config.settings import settings
from logging import getLevelNamesMapping


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter that adds standard fields to every log record.
    """

    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        """
        Add custom fields to the log record.

        Args:
            log_record: The dictionary that will be output as JSON
            record: The original LogRecord
            message_dict: Additional fields from the log call
        """
        super().add_fields(log_record, record, message_dict)

        # Add timestamp in ISO format
        log_record['timestamp'] = datetime.utcnow().isoformat() + 'Z'

        # Add log level
        log_record['level'] = record.levelname

        # Add logger name (module path)
        log_record['logger'] = record.name

        # Add service information
        log_record['service'] = settings.API_TITLE
        log_record['version'] = settings.API_VERSION

        # Add environment
        log_record['environment'] = settings.ENV

        # Add file and line number for debugging
        if settings.LOG_LEVEL == 'DEBUG':
            log_record['file'] = record.filename
            log_record['line'] = record.lineno
            log_record['function'] = record.funcName


def setup_logger(name: str = __name__) -> logging.Logger:
    """
    Setup and configure a JSON logger.

    Args:
        name: Logger name (usually __name__ of the calling module)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Set log level based on DEBUG setting
    log_level = getLevelNamesMapping()[settings.LOG_LEVEL.upper()]
    print('LOG LEVEL IS', log_level)
    logger.setLevel(log_level)

    log_format = settings.LOG_FORMAT.lower()

    # Avoid duplicate handlers
    if not logger.handlers and log_format == 'json':
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)

        # Create JSON formatter
        formatter = CustomJsonFormatter(
            fmt='%(timestamp)s %(level)s %(logger)s %(message)s'
        )
        console_handler.setFormatter(formatter)

        # Add handler to logger
        logger.addHandler(console_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def get_logger(name: str = None) -> logging.Logger:
    """
    Get or create a logger instance.

    Args:
        name: Logger name (if None, uses module name)

    Returns:
        Logger instance
    """
    if name is None:
        name = 'sum_impact_assessment'
    return setup_logger(name)
