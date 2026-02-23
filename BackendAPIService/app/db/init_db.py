from __future__ import annotations

from app.core.logging import get_logger
from app.db.models import Base
from app.db.session import engine

logger = get_logger(__name__)


# PUBLIC_INTERFACE
def init_db() -> None:
    """Initialize database schema.

    This uses SQLAlchemy `create_all` for initial scaffolding.
    For production, replace with Alembic migrations and keep this for dev only.
    """
    logger.info("Initializing database schema (create_all)")
    Base.metadata.create_all(bind=engine)
