"""Continuous Strength Memory — simple algorithms, emergent intelligence."""

from .engine import BrainMemoryEngine
from .models import Memory, MemoryOp, MemoryStatus, MemoryWrite, MemoryWritePlan
from .embedding import LocalSentenceTransformerEmbeddingBackend, build_embedding_backend_from_env
from .retrieval import HybridRetriever, RetrievalMode, SearchResult
from .store import MemoryStore
from .strength import INITIAL_STRENGTH, DECAY_RATE, current_strength, reinforce
from .security import MemorySecurityPolicy, classify_sensitivity
from .evolution import EvolutionEngine, apply_feedback, detect_feedback, inherit_from
from .adapters import BrainMemoryAdapter, HermesMemoryProvider, OpenClawMemorySidecar, PiAgentMemoryHook
from .extractor import (
    DeepSeekMemoryExtractor, JSONMemoryExtractor, NullMemoryExtractor,
    build_default_extractor, memory_extractor_schema, parse_memory_write_plan,
)
from .server import create_handler, run_server
from .api_contract import openapi_spec

__all__ = [
    "BrainMemoryEngine", "MemoryStore",
    "Memory", "MemoryOp", "MemoryStatus", "MemoryWrite", "MemoryWritePlan",
    "LocalSentenceTransformerEmbeddingBackend", "build_embedding_backend_from_env",
    "HybridRetriever", "RetrievalMode", "SearchResult",
    "INITIAL_STRENGTH", "DECAY_RATE", "current_strength", "reinforce",
    "MemorySecurityPolicy", "classify_sensitivity",
    "EvolutionEngine", "apply_feedback", "detect_feedback", "inherit_from",
    "BrainMemoryAdapter", "HermesMemoryProvider", "OpenClawMemorySidecar", "PiAgentMemoryHook",
    "DeepSeekMemoryExtractor", "JSONMemoryExtractor", "NullMemoryExtractor",
    "build_default_extractor", "memory_extractor_schema", "parse_memory_write_plan",
    "create_handler", "run_server", "openapi_spec",
]
