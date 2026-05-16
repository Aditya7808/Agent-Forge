"""Centralized logging configuration for audio_chat."""

from __future__ import annotations

import logging
import sys
from typing import Optional

_CONFIGURED = False


def configure_logging(level: str = "INFO", json_format: bool = False) -> None:
    """Configure root logger with sensible defaults.

    Safe to call multiple times; only configures the first time.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    log_level = getattr(logging, level.upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stdout)

    if json_format:
        fmt = (
            '{"timestamp":"%(asctime)s","level":"%(levelname)s",'
            '"logger":"%(name)s","message":"%(message)s"}'
        )
    else:
        fmt = "%(asctime)s | %(levelname)-7s | %(name)-30s | %(message)s"

    handler.setFormatter(logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S"))

    root = logging.getLogger("audio_chat")
    root.setLevel(log_level)
    root.handlers.clear()
    root.addHandler(handler)
    root.propagate = False

    _CONFIGURED = True


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a logger scoped under the audio_chat namespace."""
    if name is None:
        return logging.getLogger("audio_chat")
    if not name.startswith("audio_chat"):
        name = f"audio_chat.{name}"
    return logging.getLogger(name)
