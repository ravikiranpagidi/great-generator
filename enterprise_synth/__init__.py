"""Backward-compatible import alias for the renamed great_generator package."""

from __future__ import annotations

import importlib
import sys

_module = importlib.import_module("great_generator")
sys.modules[__name__] = _module
