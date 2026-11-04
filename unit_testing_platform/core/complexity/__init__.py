"""Cyclomatic Complexity Module (public surface).

Everything outside ``core/complexity`` should import from here, never from ``third_party``."""
from core.complexity.engine import ENGINE_NAME, ComplexityEngine, EngineUnavailableError

__all__ = ["ComplexityEngine", "EngineUnavailableError", "ENGINE_NAME"]
