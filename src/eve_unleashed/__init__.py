"""
Eve Unleashed - Azazael Inference Engine
========================================
High-performance inference engine for ML model deployment.
Provides model loading, batch inference, result caching, and streaming.
"""

from .cache import InferenceCache
from .config import EveConfig
from .core import BatchResult, InferenceResult, ModelLoader
from .engine import (
    GGUFEngine,
    InferenceEngine,
    KVQuantizer,
    SpeculativeEngine,
    create_engine,
)

#: Swallows recorded when the failure ledger is unavailable (it is a stdlib-only
#: leaf, so this fallback should never fire -- if it does, the ledger is missing).

try:
    from CORE.failure_ledger import note_failure
except ImportError:  # never break the host

    def note_failure(where: str, exc: BaseException | None = None) -> None:
        pass  # ledger missing; evidence-vs-silence tradeoff capped here


__all__ = [
    "BatchResult",
    "EveConfig",
    "GGUFEngine",
    "InferenceCache",
    "InferenceEngine",
    "InferenceResult",
    "KVQuantizer",
    "ModelLoader",
    "SpeculativeEngine",
    "create_engine",
]
__version__ = "1.1.0"
