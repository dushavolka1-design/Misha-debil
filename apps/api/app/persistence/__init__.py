"""PostgreSQL-backed persistence for in-memory service stores (local/dev)."""

from app.persistence.bootstrap import attach_persistence, flush_persistence, load_persistence

__all__ = ["attach_persistence", "load_persistence", "flush_persistence"]
